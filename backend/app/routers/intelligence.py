"""Intelligence layer endpoints - waste stats, price history, trial alerts."""

from datetime import datetime, timedelta, timezone
from typing import Optional, List
from uuid import UUID

from fastapi import APIRouter, Depends, HTTPException, status, Cookie
from sqlalchemy import text
from sqlalchemy.ext.asyncio import AsyncSession
from pydantic import BaseModel

from app.config import get_settings
from app.database import get_db
from app.routers.auth import verify_token

router = APIRouter()
settings = get_settings()


# Pydantic models
class WasteEquivalent(BaseModel):
    label: str
    value: float
    emoji: str


class WasteStats(BaseModel):
    annual_total_cents: int
    monthly_avg_cents: int
    waste_score: int  # 0-100
    potentially_wasted_cents: int
    equivalents: List[WasteEquivalent]
    shock_stat: str


class PriceChange(BaseModel):
    subscription_id: str
    vendor_name: str
    old_amount_cents: int
    new_amount_cents: int
    change_percent: float
    detected_at: str


class TrialAlert(BaseModel):
    subscription_id: str
    vendor_name: str
    trial_started_at: str
    days_remaining: int
    is_urgent: bool
    estimated_charge_cents: int


class OverlapGroup(BaseModel):
    category: str
    subscriptions: List[dict]
    combined_monthly_cents: int
    potential_savings_cents: int


class NonUsePrediction(BaseModel):
    subscription_id: str
    vendor_name: str
    probability: int  # 0-100
    risk_level: str  # "low", "medium", "high"
    reason: str
    days_inactive: int
    amount_cents: int


class IntelligenceResponse(BaseModel):
    waste_stats: WasteStats
    price_changes: List[PriceChange]
    trial_alerts: List[TrialAlert]
    overlaps: List[OverlapGroup]
    non_use_predictions: List[NonUsePrediction]


async def get_current_user_id(
    access_token: Optional[str] = Cookie(default=None),
) -> UUID:
    """Get current user ID from token."""
    if not access_token:
        raise HTTPException(
            status_code=status.HTTP_401_UNAUTHORIZED,
            detail="Not authenticated",
        )

    payload = verify_token(access_token)
    if payload is None or "sub" not in payload:
        raise HTTPException(
            status_code=status.HTTP_401_UNAUTHORIZED,
            detail="Invalid token",
        )

    return UUID(payload["sub"])


# Price per item in cents (INR)
EQUIVALENTS = [
    {"label": "months of groceries", "per_unit": 800000, "emoji": "🛒"},
    {"label": "AirPods Pro", "per_unit": 2499000, "emoji": "🎧"},
    {"label": "Netflix subscriptions", "per_unit": 64900, "emoji": "📺"},
    {"label": "cups of coffee", "per_unit": 30000, "emoji": "☕"},
    {"label": "movie tickets", "per_unit": 50000, "emoji": "🎬"},
]

# Overlap detection categories
OVERLAP_CATEGORIES = {
    "streaming": {
        "vendors": ["netflix", "prime", "hotstar", "disney", "hulu", "apple tv", "zee5", "sony liv", "jio cinema"],
        "label": "Streaming Services",
        "avg_cost": 49900,  # Average monthly cost in cents
    },
    "music": {
        "vendors": ["spotify", "apple music", "amazon music", "youtube music", "gaana", "jiosaavn"],
        "label": "Music Streaming",
        "avg_cost": 29900,
    },
    "notes": {
        "vendors": ["notion", "evernote", "obsidian", "bear", "onenote", "google keep", "roam"],
        "label": "Note-Taking Apps",
        "avg_cost": 50000,
    },
    "communication": {
        "vendors": ["slack", "teams", "discord", "zoom", "meet", "webex"],
        "label": "Communication Tools",
        "avg_cost": 100000,
    },
    "project": {
        "vendors": ["jira", "asana", "clickup", "trello", "notion", "monday", "linear", "basecamp"],
        "label": "Project Management",
        "avg_cost": 150000,
    },
    "writing": {
        "vendors": ["grammarly", "quillbot", "hemingway", "prowritingaid", "wordtune"],
        "label": "Writing Assistants",
        "avg_cost": 80000,
    },
    "cloud": {
        "vendors": ["dropbox", "icloud", "google one", "onedrive", "box"],
        "label": "Cloud Storage",
        "avg_cost": 19900,
    },
}

# Known free trial durations
TRIAL_DURATIONS = {
    "netflix": 30,
    "spotify": 30,
    "amazon prime": 30,
    "hotstar": 30,
    "adobe": 7,
    "canva": 30,
    "notion": 14,
    "slack": 14,
    "zoom": 14,
    "dropbox": 30,
    "grammarly": 7,
}

# Default trial charge estimates (in cents)
TRIAL_CHARGES = {
    "netflix": 64900,
    "spotify": 11900,
    "amazon prime": 17900,
    "hotstar": 29900,
    "adobe": 489900,
    "canva": 89900,
    "notion": 50000,
    "grammarly": 99900,
}


def calculate_waste_score(subscriptions: list, decisions: list) -> int:
    """Calculate waste score 0-100 based on subscription health."""
    if not subscriptions:
        return 100  # No subscriptions = perfect health
    
    score = 100
    
    # Deduct for each subscription flagged as cancellable
    cancel_count = sum(1 for d in decisions if d.get("decision_type") == "cancel")
    score -= cancel_count * 15
    
    # Deduct for subscriptions with no recent activity
    for sub in subscriptions:
        if sub.get("last_charge_at"):
            last = datetime.fromisoformat(sub["last_charge_at"].replace("Z", "+00:00"))
            days_since = (datetime.now(timezone.utc) - last).days
            if days_since > 90:
                score -= 15
            elif days_since > 60:
                score -= 10
            elif days_since > 30:
                score -= 5
    
    return max(0, min(100, score))


def detect_overlaps(subscriptions: list) -> List[OverlapGroup]:
    """Detect overlapping subscriptions in the same category."""
    overlaps = []
    
    for cat_id, cat_data in OVERLAP_CATEGORIES.items():
        matching_subs = []
        for sub in subscriptions:
            vendor_lower = (sub.get("vendor_normalized") or sub.get("vendor_name", "")).lower()
            for known_vendor in cat_data["vendors"]:
                if known_vendor in vendor_lower or vendor_lower in known_vendor:
                    matching_subs.append({
                        "id": sub["id"],
                        "vendor_name": sub["vendor_name"],
                        "amount_cents": sub["amount_cents"] or cat_data["avg_cost"],
                        "billing_cycle": sub.get("billing_cycle", "monthly"),
                    })
                    break
        
        if len(matching_subs) > 1:
            combined = sum(s["amount_cents"] for s in matching_subs)
            # Assume keeping one and saving the rest
            potential_savings = combined - min(s["amount_cents"] for s in matching_subs)
            
            overlaps.append(OverlapGroup(
                category=cat_data["label"],
                subscriptions=matching_subs,
                combined_monthly_cents=combined,
                potential_savings_cents=potential_savings,
            ))
    
    return overlaps


def detect_trials(subscriptions: list) -> List[TrialAlert]:
    """Detect free trials that are about to end."""
    trials = []
    now = datetime.now(timezone.utc)
    
    for sub in subscriptions:
        # Check if this looks like a trial (amount is 0 or very low)
        amount = sub.get("amount_cents") or 0
        if amount > 100:  # Not a free/low-cost trial
            continue
        
        vendor_lower = (sub.get("vendor_normalized") or sub.get("vendor_name", "")).lower()
        created_at = sub.get("created_at")
        
        if not created_at:
            continue
        
        try:
            created = datetime.fromisoformat(created_at.replace("Z", "+00:00"))
        except:
            continue
        
        # Determine trial duration
        trial_days = 14  # Default
        for known_vendor, days in TRIAL_DURATIONS.items():
            if known_vendor in vendor_lower:
                trial_days = days
                break
        
        # Calculate days remaining
        days_since = (now - created).days
        days_remaining = max(0, trial_days - days_since)
        
        # Only alert if trial is ending within 7 days
        if days_remaining <= 7:
            # Estimate charge
            estimated_charge = 49900  # Default
            for known_vendor, charge in TRIAL_CHARGES.items():
                if known_vendor in vendor_lower:
                    estimated_charge = charge
                    break
            
            trials.append(TrialAlert(
                subscription_id=sub["id"],
                vendor_name=sub["vendor_name"],
                trial_started_at=created_at,
                days_remaining=days_remaining,
                is_urgent=days_remaining <= 2,
                estimated_charge_cents=estimated_charge,
            ))
    
    return trials


# High-churn subscription categories
HIGH_CHURN_CATEGORIES = ["streaming", "fitness", "gaming", "entertainment", "news", "magazine"]


def predict_non_use(subscriptions: list) -> List[NonUsePrediction]:
    """Predict which subscriptions are likely to go unused next month."""
    predictions = []
    now = datetime.now(timezone.utc)
    
    for sub in subscriptions:
        score = 0
        reasons = []
        
        # Factor 1: Days since last charge (most important)
        days_inactive = 0
        if sub.get("last_charge_at"):
            try:
                last = datetime.fromisoformat(sub["last_charge_at"].replace("Z", "+00:00"))
                days_inactive = (now - last).days
                
                if days_inactive > 90:
                    score += 45
                    reasons.append(f"No activity in {days_inactive} days")
                elif days_inactive > 60:
                    score += 30
                    reasons.append(f"Inactive for {days_inactive} days")
                elif days_inactive > 30:
                    score += 15
                    reasons.append(f"{days_inactive} days since last use")
            except:
                pass
        
        # Factor 2: High cost subscriptions more likely forgotten
        amount = sub.get("amount_cents") or 0
        if amount > 500000:  # > ₹5000
            score += 20
            reasons.append("High-cost subscription")
        elif amount > 200000:  # > ₹2000
            score += 10
            reasons.append("Moderate cost")
        
        # Factor 3: Category-based risk
        vendor_lower = (sub.get("vendor_normalized") or sub.get("vendor_name", "")).lower()
        for category in HIGH_CHURN_CATEGORIES:
            if category in vendor_lower:
                score += 15
                reasons.append(f"High-churn category ({category})")
                break
        
        # Factor 4: Entertainment/streaming services often go unused
        for streaming in ["netflix", "prime", "hotstar", "disney", "hulu", "spotify", "youtube"]:
            if streaming in vendor_lower:
                score += 10
                if "streaming" not in " ".join(reasons).lower():
                    reasons.append("Streaming service (often underused)")
                break
        
        # Cap at 95% - never say 100% certain
        probability = min(95, score)
        
        # Only include predictions with >40% probability
        if probability >= 40:
            risk_level = "high" if probability >= 70 else ("medium" if probability >= 50 else "low")
            
            predictions.append(NonUsePrediction(
                subscription_id=sub["id"],
                vendor_name=sub["vendor_name"],
                probability=probability,
                risk_level=risk_level,
                reason=reasons[0] if reasons else "Usage pattern suggests low engagement",
                days_inactive=days_inactive,
                amount_cents=amount,
            ))
    
    # Sort by probability descending
    predictions.sort(key=lambda x: x.probability, reverse=True)
    
    return predictions[:5]  # Top 5 at-risk subscriptions


@router.get("/stats", response_model=IntelligenceResponse)
async def get_intelligence_stats(
    user_id: UUID = Depends(get_current_user_id),
    db: AsyncSession = Depends(get_db),
):
    """Get comprehensive intelligence stats for dashboard."""
    
    # Get all active subscriptions
    result = await db.execute(
        text("""
        SELECT id, vendor_name, vendor_normalized, amount_cents, currency,
               billing_cycle, last_charge_at, status, created_at
        FROM subscriptions
        WHERE user_id = :user_id AND status = 'active'
        """),
        {"user_id": str(user_id)},
    )
    rows = result.fetchall()
    
    subscriptions = []
    annual_total = 0
    
    for row in rows:
        sub = {
            "id": str(row[0]),
            "vendor_name": row[1],
            "vendor_normalized": row[2],
            "amount_cents": row[3] or 0,
            "currency": row[4],
            "billing_cycle": row[5],
            "last_charge_at": row[6].isoformat() if row[6] else None,
            "status": row[7],
            "created_at": row[8].isoformat() if row[8] else None,
        }
        subscriptions.append(sub)
        
        # Calculate annual cost
        amount = row[3] or 0
        if row[5] == "yearly":
            annual_total += amount
        else:
            annual_total += amount * 12
    
    # Get pending cancel/review decisions
    decisions_result = await db.execute(
        text("""
        SELECT d.subscription_id, d.decision_type, s.amount_cents, s.vendor_name
        FROM decisions d
        JOIN subscriptions s ON d.subscription_id = s.id
        WHERE d.user_id = :user_id AND d.user_action IS NULL
        """),
        {"user_id": str(user_id)},
    )
    decisions = [
        {"subscription_id": str(r[0]), "decision_type": r[1], "amount_cents": r[2] or 0, "vendor_name": r[3]}
        for r in decisions_result.fetchall()
    ]
    
    # Calculate potentially wasted (cancel + review recommendations)
    potentially_wasted = sum(
        d["amount_cents"] * 12 
        for d in decisions 
        if d["decision_type"] in ["cancel", "review"]
    )
    
    # Calculate waste score
    waste_score = calculate_waste_score(subscriptions, decisions)
    
    # Generate equivalents
    equivalents = []
    for eq in EQUIVALENTS[:3]:  # Top 3
        value = potentially_wasted / eq["per_unit"]
        if value >= 0.5:
            equivalents.append(WasteEquivalent(
                label=eq["label"],
                value=round(value, 1),
                emoji=eq["emoji"]
            ))
    
    # Generate shock stat
    months = round(potentially_wasted / 800000, 1)
    if months >= 2:
        shock_stat = f"That's {months} months of groceries just... gone."
    elif months >= 1:
        shock_stat = f"That's {months} month of groceries wasted."
    elif potentially_wasted > 0:
        shock_stat = f"You're wasting ₹{potentially_wasted / 100:.0f} per year on unused subscriptions."
    else:
        shock_stat = "Your subscriptions are well-optimized! 🎉"
    
    # Price hike detection using pattern analysis
    # (Compare current amount vs expected based on vendor averages)
    price_changes = []
    # For hackathon demo: detect if any subscription amount seems high
    for sub in subscriptions:
        vendor_lower = (sub.get("vendor_normalized") or sub.get("vendor_name", "")).lower()
        current = sub.get("amount_cents") or 0
        
        # Check against known typical prices
        typical_prices = {
            "netflix": 64900, "spotify": 11900, "amazon prime": 17900,
            "adobe": 489900, "grammarly": 99900, "canva": 89900,
        }
        
        for vendor, typical in typical_prices.items():
            if vendor in vendor_lower and current > typical * 1.1:
                change_pct = ((current - typical) / typical) * 100
                if change_pct > 5:
                    price_changes.append(PriceChange(
                        subscription_id=sub["id"],
                        vendor_name=sub["vendor_name"],
                        old_amount_cents=typical,
                        new_amount_cents=current,
                        change_percent=round(change_pct, 1),
                        detected_at=datetime.now(timezone.utc).isoformat(),
                    ))
                break
    
    # Trial detection
    trial_alerts = detect_trials(subscriptions)
    
    # Overlap detection
    overlaps = detect_overlaps(subscriptions)
    
    # Non-use predictions
    non_use_predictions = predict_non_use(subscriptions)
    
    return IntelligenceResponse(
        waste_stats=WasteStats(
            annual_total_cents=annual_total,
            monthly_avg_cents=annual_total // 12 if annual_total else 0,
            waste_score=waste_score,
            potentially_wasted_cents=potentially_wasted,
            equivalents=equivalents,
            shock_stat=shock_stat,
        ),
        price_changes=price_changes,
        trial_alerts=trial_alerts,
        overlaps=overlaps,
        non_use_predictions=non_use_predictions,
    )
