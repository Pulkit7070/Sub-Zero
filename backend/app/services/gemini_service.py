"""Gemini LLM service for generating human-friendly explanations."""

import google.generativeai as genai
from typing import List
from app.config import get_settings

settings = get_settings()

# Configure Gemini
genai.configure(api_key=settings.gemini_api_key)
model = genai.GenerativeModel('gemini-pro')


async def generate_risk_narrative(probability: int, reasons: List[str]) -> str:
    """
    Generate human-friendly explanation for non-use risk prediction.
    
    Args:
        probability: Risk score 0-100
        reasons: List of reasons for the prediction
        
    Returns:
        Human-friendly narrative
    """
    risk_level = "high" if probability >= 70 else ("medium" if probability >= 50 else "low")
    reasons_text = "\n".join(f"- {r}" for r in reasons)
    
    prompt = f"""A user has a {probability}% chance of not using this subscription next month.

Reasons:
{reasons_text}

Explain this in a short, user-friendly way without using the word "AI". 
Keep it under 2 sentences. Be direct and helpful."""

    try:
        response = model.generate_content(prompt)
        return response.text.strip()
    except Exception as e:
        # Fallback to simple explanation
        return f"Based on your usage patterns, there's a {probability}% chance you won't use this next month. {reasons[0] if reasons else 'Consider reviewing this subscription.'}"


async def generate_final_summary(savings: int, count: int, alerts_avoided: int) -> str:
    """
    Generate motivational summary for demo ending.
    
    Args:
        savings: Total savings in cents
        count: Number of subscriptions canceled/optimized  
        alerts_avoided: Number of trial/price alerts avoided
        
    Returns:
        Motivational summary text
    """
    savings_rupees = savings / 100
    
    prompt = f"""Summarize how a user saved ₹{savings_rupees:.0f} by canceling {count} subscriptions
and avoiding {alerts_avoided} unnecessary charges.

Make it motivational but not cheesy. Keep it under 3 sentences.
Focus on empowerment and financial control."""

    try:
        response = model.generate_content(prompt)
        return response.text.strip()
    except Exception as e:
        # Fallback to simple message
        return f"You've saved ₹{savings_rupees:.0f} by taking control of {count} subscriptions. By staying alert to {alerts_avoided} potential charges, you're back in control of your money."
