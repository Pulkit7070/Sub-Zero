"""Gmail API integration service - Fast, precise billing-focused approach."""

import asyncio
import base64
import re
import time
from datetime import datetime, timedelta, timezone
from typing import Optional

import httpx
from google.oauth2.credentials import Credentials
from googleapiclient.discovery import build
from googleapiclient.errors import HttpError

from app.config import get_settings
from app.utils.encryption import decrypt_token, encrypt_token

settings = get_settings()


# ============================================================================
# PHASE 3: HARD BILLING GATE - Strict filters
# ============================================================================

# REQUIRED billing indicators in subject (at least ONE must match)
BILLING_INDICATORS = [
    "receipt",
    "invoice",
    "tax invoice",
    "charged",
    "payment successful",
    "payment received",
    "order total",
    "renewal",
    "subscription",
    "billed",
    "your order",
    "payment confirmation",
    "billing statement",
]

# BLOCKED sender domains/patterns - immediately discard
BLOCKED_DOMAINS = [
    "linkedin.com",
    "github.com",
    "naukri.com",
    "indeed.com",
    "glassdoor.com",
    "monster.com",
    "hackerrank.com",
    "leetcode.com",
    "stackoverflow.com",
]

BLOCKED_SENDER_PATTERNS = [
    "notifications@",
    "alerts@",
    "jobs@",
    "careers@",
    "newsletter@",
    "news@",
    "security@",
    "noreply@accounts",
    "no-reply@accounts",
    "notification@",
    "alert@",
    "marketing@",
    "promo@",
]

# Google addresses - only allow payments
GOOGLE_ALLOWED = ["payments@google.com", "googleplay@google.com"]

# ============================================================================
# PHASE 5: Non-subscription payment patterns to REJECT
# ============================================================================

NON_SUBSCRIPTION_PATTERNS = [
    r"mobile.*recharge",
    r"prepaid.*recharge",
    r"upi.*payment",
    r"wallet.*added",
    r"top.?up",
    r"electricity.*bill",
    r"water.*bill",
    r"gas.*bill",
    r"one.?time.*purchase",
    r"gift.*card",
]

# ============================================================================
# Known subscription merchants for scoring
# ============================================================================

KNOWN_MERCHANTS = {
    "netflix.com": "Netflix",
    "spotify.com": "Spotify",
    "apple.com": "Apple",
    "amazon.com": "Amazon Prime",
    "primevideo.com": "Amazon Prime",
    "microsoft.com": "Microsoft",
    "adobe.com": "Adobe",
    "dropbox.com": "Dropbox",
    "slack.com": "Slack",
    "zoom.us": "Zoom",
    "notion.so": "Notion",
    "figma.com": "Figma",
    "canva.com": "Canva",
    "openai.com": "OpenAI",
    "anthropic.com": "Anthropic",
    "hulu.com": "Hulu",
    "disneyplus.com": "Disney+",
    "hbomax.com": "HBO Max",
    "youtube.com": "YouTube Premium",
    "grammarly.com": "Grammarly",
    "1password.com": "1Password",
    "nordvpn.com": "NordVPN",
    "expressvpn.com": "ExpressVPN",
    "evernote.com": "Evernote",
    "todoist.com": "Todoist",
    "notion.so": "Notion",
    "linear.app": "Linear",
    "vercel.com": "Vercel",
    "netlify.com": "Netlify",
    "digitalocean.com": "DigitalOcean",
    "cloudflare.com": "Cloudflare",
    "cursor.com": "Cursor",
    "chatgpt.com": "ChatGPT",
    "claude.ai": "Claude",
    "midjourney.com": "Midjourney",
    "github.com": "GitHub",  # Only if from billing email
}

# Strong billing keywords for scoring
STRONG_BILLING_KEYWORDS = [
    "receipt", "invoice", "charged", "billed", "renewal",
    "subscription", "monthly", "annual", "yearly"
]


class GmailService:
    """Service for interacting with Gmail API - billing-focused."""

    GMAIL_API_VERSION = "v1"

    def __init__(self, access_token: str, refresh_token: Optional[str] = None):
        self.access_token = access_token
        self.refresh_token = refresh_token
        self._service = None

    def _get_service(self):
        if self._service is None:
            credentials = Credentials(
                token=self.access_token,
                refresh_token=self.refresh_token,
                token_uri=settings.google_token_url,
                client_id=settings.google_client_id,
                client_secret=settings.google_client_secret,
            )
            self._service = build("gmail", self.GMAIL_API_VERSION, credentials=credentials)
        return self._service

    def _passes_billing_gate(self, from_header: str, subject: str) -> bool:
        """
        PHASE 3: Hard billing gate - must pass BEFORE any scoring.
        Returns True only if email is likely a billing/receipt email.
        """
        from_lower = from_header.lower()
        subject_lower = subject.lower()

        # CHECK 1: Is sender blocked?
        for blocked in BLOCKED_DOMAINS:
            if blocked in from_lower:
                # Exception: GitHub billing emails
                if blocked == "github.com" and "billing" in from_lower:
                    pass
                else:
                    return False

        for pattern in BLOCKED_SENDER_PATTERNS:
            if pattern in from_lower:
                return False

        # CHECK 2: Google emails - only allow specific payment addresses
        if "google.com" in from_lower:
            if not any(allowed in from_lower for allowed in GOOGLE_ALLOWED):
                return False

        # CHECK 3: Must have at least ONE billing indicator in subject
        has_billing_indicator = any(
            indicator in subject_lower for indicator in BILLING_INDICATORS
        )
        if not has_billing_indicator:
            return False

        # CHECK 4: Reject non-subscription payment patterns (PHASE 5)
        for pattern in NON_SUBSCRIPTION_PATTERNS:
            if re.search(pattern, subject_lower):
                return False

        return True

    def _score_email(self, from_header: str, subject: str, email_date: Optional[datetime]) -> float:
        """
        PHASE 4: Score only emails that passed billing gate.
        Threshold: >= 0.7 to be a candidate
        """
        score = 0.0
        subject_lower = subject.lower()
        from_lower = from_header.lower()

        # Strong billing keyword (+0.5)
        if any(kw in subject_lower for kw in STRONG_BILLING_KEYWORDS):
            score += 0.5

        # Known merchant domain (+0.3)
        for domain in KNOWN_MERCHANTS:
            if domain in from_lower:
                score += 0.3
                break

        # Recency bonus (+0.2) - within 45 days
        if email_date:
            days_old = (datetime.now(timezone.utc) - email_date).days
            if days_old <= 45:
                score += 0.2

        return min(score, 1.0)

    async def fetch_receipt_emails(
        self,
        after_date: Optional[datetime] = None,
        days_back: int = 90,  # PHASE 2: Max 90 days for first sync
        max_results: int = 1000,
    ) -> list[dict]:
        """
        Fetch billing emails using strict filtering.
        """
        start_time = time.time()
        service = self._get_service()

        # Calculate date range
        if after_date is not None:
            date_query = after_date.strftime("%Y/%m/%d")
        else:
            date_query = (datetime.now(timezone.utc) - timedelta(days=days_back)).strftime("%Y/%m/%d")

        # Focused query - only billing-related emails
        query = f"after:{date_query} (receipt OR invoice OR charged OR billed OR payment OR subscription OR renewal)"
        print(f"[GMAIL] Search query: {query}")

        # Fetch message IDs
        message_ids = []
        page_token = None

        while len(message_ids) < max_results:
            print(f"[GMAIL] Fetching message list (current: {len(message_ids)})")
            try:
                results = service.users().messages().list(
                    userId="me",
                    q=query,
                    maxResults=min(100, max_results - len(message_ids)),
                    pageToken=page_token,
                ).execute()
            except HttpError as e:
                print(f"[GMAIL] Error listing messages: {e}")
                break

            messages = results.get("messages", [])
            print(f"[GMAIL] Found {len(messages)} messages in batch")

            if not messages:
                break

            message_ids.extend([m["id"] for m in messages])
            page_token = results.get("nextPageToken")

            if not page_token:
                break

        print(f"[GMAIL] Total message IDs: {len(message_ids)}")

        if not message_ids:
            return []

        # Fetch and filter emails
        emails = []
        passed_gate = 0
        failed_gate = 0

        for i, msg_id in enumerate(message_ids):
            if i % 50 == 0:
                print(f"[GMAIL] Processing {i}/{len(message_ids)}...")

            try:
                # Fetch metadata first (fast)
                msg = service.users().messages().get(
                    userId="me",
                    id=msg_id,
                    format="metadata",
                    metadataHeaders=["From", "Subject", "Date"]
                ).execute()

                headers = {h["name"].lower(): h["value"] for h in msg.get("payload", {}).get("headers", [])}
                from_header = headers.get("from", "")
                subject = headers.get("subject", "")

                # PHASE 3: Apply hard billing gate
                if not self._passes_billing_gate(from_header, subject):
                    failed_gate += 1
                    continue

                passed_gate += 1

                # Parse date
                internal_date = msg.get("internalDate")
                email_date = None
                if internal_date:
                    email_date = datetime.fromtimestamp(int(internal_date) / 1000, tz=timezone.utc)

                # PHASE 4: Score the email
                score = self._score_email(from_header, subject, email_date)

                if score < 0.7:  # Threshold
                    continue

                print(f"[GMAIL] ✓ Candidate: {subject[:60]} (score: {score:.2f})")

                # Fetch full message for candidates only
                full_msg = service.users().messages().get(
                    userId="me",
                    id=msg_id,
                    format="full"
                ).execute()

                email_data = self._parse_message(full_msg)
                if email_data:
                    email_data["score"] = score
                    emails.append(email_data)

            except Exception as e:
                print(f"[GMAIL] Error processing {msg_id}: {e}")
                continue

        elapsed = time.time() - start_time
        print(f"[GMAIL] Completed: {len(emails)} candidates from {passed_gate} passed gate ({failed_gate} filtered) in {elapsed:.2f}s")

        return emails

    def _parse_message(self, message: dict) -> Optional[dict]:
        """Parse Gmail message into structured data."""
        try:
            headers = message.get("payload", {}).get("headers", [])
            header_dict = {h["name"].lower(): h["value"] for h in headers}

            from_email = header_dict.get("from", "")
            subject = header_dict.get("subject", "")

            body = self._get_body(message.get("payload", {}))

            internal_date = message.get("internalDate")
            date = None
            if internal_date:
                date = datetime.fromtimestamp(int(internal_date) / 1000, tz=timezone.utc)

            return {
                "message_id": message.get("id"),
                "thread_id": message.get("threadId"),
                "from": from_email,
                "subject": subject,
                "date": date,
                "snippet": message.get("snippet", ""),
                "body": body,
                "labels": message.get("labelIds", []),
            }
        except Exception as e:
            print(f"[GMAIL] Error parsing message: {e}")
            return None

    def _get_body(self, payload: dict) -> str:
        """Extract email body safely."""
        body = ""
        try:
            if "body" in payload and payload["body"].get("data"):
                body = base64.urlsafe_b64decode(payload["body"]["data"]).decode("utf-8", errors="ignore")
            elif "parts" in payload:
                for part in payload["parts"]:
                    if part.get("mimeType") == "text/plain":
                        if part.get("body", {}).get("data"):
                            body = base64.urlsafe_b64decode(part["body"]["data"]).decode("utf-8", errors="ignore")
                            break
                    elif part.get("mimeType") == "text/html":
                        if part.get("body", {}).get("data"):
                            body = base64.urlsafe_b64decode(part["body"]["data"]).decode("utf-8", errors="ignore")
                    elif "parts" in part:
                        body = self._get_body(part)
                        if body:
                            break
        except Exception:
            return ""
        return body[:10000]


class TokenRefreshError(Exception):
    """Raised when token refresh fails."""
    def __init__(self, message: str, is_retryable: bool = True):
        super().__init__(message)
        self.is_retryable = is_retryable


async def refresh_gmail_token(
    refresh_token_encrypted: str,
    max_retries: int = 3,
) -> tuple[str, str, datetime]:
    """Refresh Gmail access token with retry logic."""
    refresh_token = decrypt_token(refresh_token_encrypted)
    last_error = None

    for attempt in range(max_retries):
        try:
            async with httpx.AsyncClient() as client:
                response = await client.post(
                    settings.google_token_url,
                    data={
                        "client_id": settings.google_client_id,
                        "client_secret": settings.google_client_secret,
                        "refresh_token": refresh_token,
                        "grant_type": "refresh_token",
                    },
                    timeout=30.0,
                )

                if response.status_code == 200:
                    tokens = response.json()
                    new_access_token = tokens["access_token"]
                    new_refresh_token = tokens.get("refresh_token", refresh_token)
                    expires_in = tokens.get("expires_in", 3600)
                    expires_at = datetime.now(timezone.utc) + timedelta(seconds=expires_in)

                    return (
                        encrypt_token(new_access_token),
                        encrypt_token(new_refresh_token),
                        expires_at,
                    )

                if response.status_code == 400:
                    error_data = response.json()
                    error_type = error_data.get("error", "")
                    if error_type == "invalid_grant":
                        raise TokenRefreshError(
                            "Refresh token is invalid. Please reconnect your account.",
                            is_retryable=False,
                        )
                    raise TokenRefreshError(f"Token refresh failed: {error_type}")

                if response.status_code == 429:
                    await asyncio.sleep(2 ** attempt * 2)
                    continue

                raise TokenRefreshError(f"Unexpected error: {response.status_code}")

        except httpx.RequestError as e:
            last_error = TokenRefreshError(f"Network error: {str(e)}")
        except TokenRefreshError as e:
            if not e.is_retryable:
                raise
            last_error = e

        if attempt < max_retries - 1:
            await asyncio.sleep(2 ** attempt)

    raise last_error or TokenRefreshError("Token refresh failed after all retries")
