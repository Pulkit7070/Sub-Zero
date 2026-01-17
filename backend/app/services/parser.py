"""Email parser service for extracting subscription data."""

import re
from dataclasses import dataclass
from datetime import datetime
from typing import Optional
from html import unescape


@dataclass
class ParsedSubscription:
    """Parsed subscription data from an email."""
    vendor_name: str
    vendor_normalized: str
    amount_cents: Optional[int]
    currency: str
    billing_cycle: Optional[str]
    charge_date: Optional[datetime]
    next_renewal_date: Optional[datetime]
    confidence: float
    raw_data: dict


class EmailParser:
    """Parser for extracting subscription information from emails."""

    # Common subscription vendors
    KNOWN_VENDORS = {
        "netflix": "Netflix",
        "spotify": "Spotify",
        "apple": "Apple",
        "google": "Google",
        "amazon": "Amazon",
        "microsoft": "Microsoft",
        "adobe": "Adobe",
        "dropbox": "Dropbox",
        "slack": "Slack",
        "zoom": "Zoom",
        "github": "GitHub",
        "notion": "Notion",
        "figma": "Figma",
        "canva": "Canva",
        "openai": "OpenAI",
        "anthropic": "Anthropic",
        "hulu": "Hulu",
        "disney": "Disney+",
        "hbo": "HBO Max",
        "paramount": "Paramount+",
        "youtube": "YouTube",
        "twitch": "Twitch",
        "linkedin": "LinkedIn",
        "grammarly": "Grammarly",
        "1password": "1Password",
        "lastpass": "LastPass",
        "nordvpn": "NordVPN",
        "expressvpn": "ExpressVPN",
        "evernote": "Evernote",
        "todoist": "Todoist",
        "asana": "Asana",
        "trello": "Trello",
        "mailchimp": "Mailchimp",
        "squarespace": "Squarespace",
        "wix": "Wix",
        "shopify": "Shopify",
        "heroku": "Heroku",
        "vercel": "Vercel",
        "netlify": "Netlify",
        "digitalocean": "DigitalOcean",
        "aws": "AWS",
        "cloudflare": "Cloudflare",
        "hotstar": "Disney+ Hotstar",
        "zee5": "ZEE5",
        "sony": "Sony LIV",
        "jio": "Jio Cinema",
        "swiggy": "Swiggy One",
        "zomato": "Zomato Gold",
        "rapido": "Rapido",
        "uber": "Uber",
        "ola": "Ola",
        "tataneu": "Tata Neu",
        "cult": "Cult.fit",
        "itunes": "iTunes",
        "apple": "Apple",
        "mlh": "Major League Hacking",
        "gonature": "Go Nature",
        "rapido": "Rapido",
    }

    # Currency symbols and codes
    CURRENCY_MAP = {
        "$": "USD",
        "€": "EUR",
        "£": "GBP",
        "¥": "JPY",
        "₹": "INR",
        "rs.": "INR",
        "inr": "INR",
        "USD": "USD",
        "EUR": "EUR",
        "GBP": "GBP",
        "JPY": "JPY",
        "INR": "INR",
        "CAD": "CAD",
        "AUD": "AUD",
    }

    # Amount patterns
    AMOUNT_PATTERNS = [
        # $XX.XX or $ XX.XX
        r'[\$€£₹]\s*(\d{1,7}(?:[.,]\d{2,3})?)',
        # Rs. XX.XX
        r'rs\.?\s*(\d{1,7}(?:[.,]\d{2,3})?)',
        # XX.XX USD/EUR/etc
        r'(\d{1,7}(?:[.,]\d{2,3})?)\s*(?:USD|EUR|GBP|CAD|AUD|INR)',
        # Total: $XX.XX
        r'(?:total|amount|charged?|paid?|price|payable|received)[\s:]*[\$€£₹]?\s*(\d{1,7}(?:[.,]\d{2,3})?)',
        # Total amount: ₹ XX
        # Total amount: ₹ XX
        r'total\s+amount[:\s]*[\$€£₹]?\s*(\d{1,7}(?:[.,]\d{2,3})?)',
        # Order Total: Rs. XX
        r'order\s+total[:\s]*[\$€£₹rs\.]*\s*(\d{1,7}(?:[.,]\d{2,3})?)',
        # Grand Total: XX
        r'grand\s+total[:\s]*[\$€£₹rs\.]*\s*(\d{1,7}(?:[.,]\d{2,3})?)',
        # Billed To ... Total ... XX
        r'total[:\s]*[\$€£₹rs\.]*\s*(\d{1,7}(?:[.,]\d{2,3})?)',
    ]

    # Date patterns for next renewal
    RENEWAL_PATTERNS = [
        r'next (?:payment|billing|charge|renewal) (?:is|will be)? (?:on|due)?\s*(?:on)?\s*(\w+ \d{1,2},? \d{4})',  # Jan 25, 2024
        r'renews (?:on)?\s*(\w+ \d{1,2},? \d{4})',
        r'valid (?:until|till)\s*(\w+ \d{1,2},? \d{4})',
        r'expires (?:on)?\s*(\w+ \d{1,2},? \d{4})',
    ]

    # Billing cycle patterns
    BILLING_PATTERNS = {
        "monthly": [r'monthly', r'per month', r'/month', r'/mo', r'each month', r'every month', r'billed month'],
        "yearly": [r'yearly', r'annual', r'per year', r'/year', r'/yr', r'each year', r'every year', r'billed year', r'12 months'],
        "weekly": [r'weekly', r'per week', r'/week', r'/wk'],
        "quarterly": [r'quarterly', r'per quarter', r'every 3 months', r'3 months'],
    }

    def parse_email(self, email_data: dict) -> Optional[ParsedSubscription]:
        """
        Parse an email and extract subscription information.

        Args:
            email_data: Dictionary with email fields (from, subject, body, date, etc.)

        Returns:
            ParsedSubscription if subscription data found, None otherwise
        """
        from_email = email_data.get("from", "")
        subject = email_data.get("subject", "")
        body = email_data.get("body", "")
        snippet = email_data.get("snippet", "")
        date = email_data.get("date")

        # Clean HTML from body
        body_text = self._clean_html(body)

        # Combine text for searching
        combined_text = f"{subject} {snippet} {body_text}".lower()

        # Extract vendor
        vendor_name, vendor_normalized = self._extract_vendor(from_email, subject)
        if not vendor_name:
            return None

        # Check if this looks like a subscription/receipt email
        if not self._is_subscription_email(combined_text, subject):
            return None

        # Extract amount
        amount_cents, currency = self._extract_amount(combined_text)

        # Extract billing cycle
        billing_cycle = self._extract_billing_cycle(combined_text)

        # Extract next renewal date
        renewal_date = self._extract_renewal_date(combined_text)

        # Calculate confidence score
        confidence = self._calculate_confidence(
            vendor_name=vendor_name,
            amount=amount_cents,
            billing_cycle=billing_cycle,
            has_receipt_keywords=self._has_receipt_keywords(combined_text),
        )

        return ParsedSubscription(
            vendor_name=vendor_name,
            vendor_normalized=vendor_normalized,
            amount_cents=amount_cents,
            currency=currency,
            billing_cycle=billing_cycle,
            charge_date=date,
            next_renewal_date=renewal_date,
            confidence=confidence,
            raw_data={
                "from": from_email,
                "subject": subject,
                "snippet": snippet,
                "message_id": email_data.get("message_id"),
            },
        )

    def _clean_html(self, text: str) -> str:
        """Remove HTML tags and decode entities."""
        # Remove HTML tags
        clean = re.sub(r'<[^>]+>', ' ', text)
        # Decode HTML entities
        clean = unescape(clean)
        # Normalize whitespace
        clean = re.sub(r'\s+', ' ', clean)
        return clean.strip()

    def _extract_vendor(self, from_email: str, subject: str) -> tuple[Optional[str], Optional[str]]:
        """Extract vendor name from email sender and subject."""
        # Try to extract from email address first
        email_match = re.search(r'<([^>]+)>|([^\s<]+@[^\s>]+)', from_email)
        if email_match:
            email_addr = email_match.group(1) or email_match.group(2)
            domain = email_addr.split('@')[-1].split('.')[0].lower()

            # Check against known vendors
            for key, name in self.KNOWN_VENDORS.items():
                if key in domain:
                    return name, key

        # Try to extract from display name
        name_match = re.match(r'^([^<]+)', from_email)
        if name_match:
            display_name = name_match.group(1).strip().strip('"')
            normalized = self._normalize_vendor(display_name)

            # Check against known vendors
            for key, name in self.KNOWN_VENDORS.items():
                if key in normalized:
                    return name, key

            # Use display name if it looks valid
            if len(display_name) > 1 and len(display_name) < 50:
                return display_name, normalized

        # Fall back to domain
        domain_match = re.search(r'@([^.]+)', from_email)
        if domain_match:
            domain = domain_match.group(1)
            return domain.title(), domain.lower()

        return None, None

    def _normalize_vendor(self, name: str) -> str:
        """Normalize vendor name for deduplication."""
        # Lowercase
        normalized = name.lower()
        # Remove common suffixes
        for suffix in [' inc', ' llc', ' ltd', ' corp', ' co']:
            normalized = normalized.replace(suffix, '')
        # Remove special characters
        normalized = re.sub(r'[^a-z0-9]', '', normalized)
        return normalized

    def _is_subscription_email(self, text: str, subject: str) -> bool:
        """Check if email appears to be subscription-related."""
        subscription_keywords = [
            'subscription', 'receipt', 'invoice', 'payment', 'billing',
            'order confirmation', 'thank you for your order', 'purchase',
            'charged', 'renewal', 'monthly', 'annual', 'plan',
        ]

        text_lower = text.lower()
        subject_lower = subject.lower()

        # Subject is more important
        for keyword in subscription_keywords:
            if keyword in subject_lower:
                return True

        # Check body with higher threshold
        keyword_count = sum(1 for kw in subscription_keywords if kw in text_lower)
        return keyword_count >= 2

    def _extract_amount(self, text: str) -> tuple[Optional[int], str]:
        """Extract amount from email text."""
        currency = "USD"  # Default
        text_lower = text.lower()

        # Detect currency
        for symbol, curr in self.CURRENCY_MAP.items():
            if symbol in text_lower:
                currency = curr
                break

        # Try each pattern
        for pattern in self.AMOUNT_PATTERNS:
            matches = re.findall(pattern, text, re.IGNORECASE)
            if matches:
                # Get the first reasonable amount
                for match in matches:
                    try:
                        # Handle comma as decimal separator (if not INR-style grouping)
                        # In many European countries, 1.234,56 means 1234.56
                        # In India, 12,345.67 means 12345.67
                        amount_str = match.replace(',', '')  # Remove all commas (common in US/India)
                        amount = float(amount_str)

                        # Sanity check: between 0 and 1,000,000 (INR 10 Lakhs is reasonable)
                        if 0 <= amount <= 1000000:
                            return int(amount * 100), currency
                    except ValueError:
                        continue

        return None, currency

    def _extract_billing_cycle(self, text: str) -> Optional[str]:
        """Extract billing cycle from email text."""
        text_lower = text.lower()

        for cycle, patterns in self.BILLING_PATTERNS.items():
            for pattern in patterns:
                if re.search(pattern, text_lower):
                    return cycle

        return None

    def _extract_renewal_date(self, text: str) -> Optional[datetime]:
        """Extract next renewal date from text."""
        try:
            for pattern in self.RENEWAL_PATTERNS:
                match = re.search(pattern, text, re.IGNORECASE)
                if match:
                    date_str = match.group(1)
                    # Try parsing common formats
                    for fmt in ["%b %d, %Y", "%B %d, %Y", "%d %b %Y", "%d %B %Y"]:
                        try:
                            # Normalize string (remove ordinal suffix like 1st, 2nd)
                            clean_date = re.sub(r'(\d+)(st|nd|rd|th)', r'\1', date_str)
                            return datetime.strptime(clean_date, fmt)
                        except ValueError:
                            continue
        except Exception:
            pass
        return None

    def _has_receipt_keywords(self, text: str) -> bool:
        """Check if text contains strong receipt indicators."""
        strong_keywords = ['receipt', 'invoice', 'payment received', 'order confirmation']
        return any(kw in text.lower() for kw in strong_keywords)

    def _calculate_confidence(
        self,
        vendor_name: str,
        amount: Optional[int],
        billing_cycle: Optional[str],
        has_receipt_keywords: bool,
    ) -> float:
        """Calculate confidence score for parsed subscription."""
        score = 0.3  # Base score

        # Known vendor
        if self._normalize_vendor(vendor_name) in self.KNOWN_VENDORS:
            score += 0.3

        # Has amount
        if amount is not None:
            score += 0.2

        # Has billing cycle
        if billing_cycle is not None:
            score += 0.1

        # Has receipt keywords
        if has_receipt_keywords:
            score += 0.1

        return min(score, 1.0)


def deduplicate_subscriptions(
    subscriptions: list[ParsedSubscription],
) -> list[ParsedSubscription]:
    """
    Deduplicate subscriptions by vendor, keeping the most recent.
    """
    vendor_map: dict[str, ParsedSubscription] = {}

    for sub in subscriptions:
        key = sub.vendor_normalized
        existing = vendor_map.get(key)

        if existing is None:
            vendor_map[key] = sub
        else:
            # Keep the one with higher confidence or more recent date
            if sub.confidence > existing.confidence:
                vendor_map[key] = sub
            elif sub.confidence == existing.confidence and sub.charge_date:
                if existing.charge_date is None or sub.charge_date > existing.charge_date:
                    vendor_map[key] = sub

    return list(vendor_map.values())
