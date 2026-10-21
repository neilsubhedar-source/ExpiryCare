"""Healthcare guidance chatbot for ExpiryCare.

Uses OpenAI when explicitly configured; otherwise uses a deterministic local
knowledge base so the demo works without a paid API key or internet access.
The offline mode is intentionally described as a knowledge-base fallback, not
as generative AI, and never certifies that food or medicine is safe.
"""
import os
import logging
from typing import Dict, Any, Tuple, Optional
import requests

logger = logging.getLogger("expirycare.guidance")
HEALTHCARE_DISCLAIMER = (
    "General information only; this is not medical advice or a safety certification. "
    "Never use this answer to decide that expired or unidentified food/medicine is safe. "
    "For medicines, contact a pharmacist or licensed healthcare professional."
)

SYSTEM_PROMPT = (
    "You are ExpiryCare, a cautious product-expiry awareness assistant. Give concise, "
    "practical information about food storage, expiry labels, household product storage, "
    "and safe next steps. Never certify a product as safe. Do not recommend taking expired "
    "medicines or tasting suspicious food. For medicine decisions, advise contacting a pharmacist. "
    "If uncertain, say so. Answer in 2-5 short sentences."
)

# Deterministic offline fallback for reliable demonstrations without API credentials.
RULES = [
    (("milk", "dairy", "yogurt", "yoghurt", "curd"),
     "Keep milk and other refrigerated dairy products refrigerated according to the label. Discard them if they smell unusual, show mould, have a changed texture, or were left warm for an unsafe period. Do not taste a product to test whether it is safe; follow the date and storage instructions on its packaging."),
    (("expired medicine", "medicine expired", "expired tablet", "expired drug", "expired medication", "expiry medicine", "can i take medicine"),
     "Do not rely on an expired medicine being effective or safe, and do not take it based on this chatbot's answer. Check the exact product and date with a pharmacist or healthcare professional. Keep it in its original packaging and follow local pharmacy guidance for disposal."),
    (("medicine", "tablet", "capsule", "syrup", "pharma", "drug"),
     "Store medicines exactly as their label or leaflet instructs; some require specific temperature conditions. Keep them in their original packaging, away from children, heat and moisture. For a missed, unclear or expired date, ask a pharmacist rather than guessing."),
    (("missing expiry", "expiry date missing", "expiry date is missing", "if the expiry date is missing", "expiry is missing", "no expiry", "unknown expiry", "date missing", "date is missing", "can't find expiry", "cannot find expiry"),
     "Treat the expiry date as unknown rather than assuming the item is safe. Check all sides of the package and any leaflet, then contact the manufacturer; for medicines, ask a pharmacist. You can record it as 'Expiry Unknown' and set a review reminder, but a reminder is not an expiry date."),
    (("storage", "store", "stored", "keep food", "refrigerat", "temperature"),
     "Follow the storage instructions printed on the specific product because requirements vary. Keep perishable food refrigerated when the label requires it, and avoid leaving it at room temperature for extended periods. If storage conditions are unknown or were not followed, do not assume the item is safe."),
    (("best before", "use by", "expiry label", "exp date", "exp:", "mfg", "manufactur", "batch number", "lot number", "label"),
     "EXP or Use By usually refers to an expiry/use-by date; Best Before is generally about expected quality, but the meaning depends on the product and local rules. MFG means manufacturing date, and a batch/lot code identifies a production run. If the label is unclear, check the manufacturer's guidance rather than guessing."),
    (("barcode", "scan", "qr code"),
     "A barcode usually identifies a product; it does not reliably contain the product's expiry date. Product databases may help identify the item, but always verify dates and storage instructions on the physical package."),
    (("mould", "mold", "smell", "spoiled", "spoilt", "rotten", "food safety", "safe to eat", "safe to drink"),
     "Do not eat or drink food that shows spoilage or has been stored unsafely, even if its date has not passed. Do not taste it to check. When in doubt, discard it safely and follow the package's storage instructions."),
    (("hello", "hi", "hey", "good morning", "good evening"),
     "Hi! I can help explain expiry labels, storage instructions, barcode limitations, and safe next steps. Ask me about a product, but remember I cannot certify that food or medicine is safe."),
]


def offline_answer(message: str) -> str:
    text = message.casefold()
    for keywords, answer in RULES:
        if any(keyword in text for keyword in keywords):
            return answer
    return (
        "I can provide general expiry-awareness guidance, but I don't have enough detail to answer that confidently. "
        "Check the product label and storage instructions, and do not assume an item with an unknown or passed date is safe. "
        "For medicine questions, ask a pharmacist; for food that may be spoiled, do not taste it. "
        "You can ask me about storage, expiry labels, missing dates, or barcodes."
    )


class GuidanceService:
    """Handles healthcare / expiry guidance chat requests."""
    def __init__(self, api_key: Optional[str] = None):
        self.api_key = api_key or os.getenv("OPENAI_API_KEY", "").strip()
        self.gemini_api_key = os.getenv("GEMINI_API_KEY", "").strip()

    def answer_query(self, message: str) -> Tuple[bool, Optional[Dict[str, Any]], Optional[str], int]:
        clean_msg = message.strip() if isinstance(message, str) else ""
        if not clean_msg:
            return False, None, "message is required", 400
        if len(clean_msg) > 2000:
            return False, None, "Message exceeds 2000 character limit", 400

        # Optional Google Gemini API support. A key is required; free-tier quota/availability
        # depends on the Google AI Studio account and current provider limits. Offline mode remains
        # available when no key is supplied or the provider fails.
        if self.gemini_api_key:
            try:
                model = os.getenv("GEMINI_MODEL", "gemini-2.5-flash").strip()
                resp = requests.post(
                    f"https://generativelanguage.googleapis.com/v1beta/models/{model}:generateContent",
                    params={"key": self.gemini_api_key},
                    json={"systemInstruction": {"parts": [{"text": SYSTEM_PROMPT}]},
                          "contents": [{"role": "user", "parts": [{"text": clean_msg}]}],
                          "generationConfig": {"temperature": 0.2, "maxOutputTokens": 300}},
                    timeout=12,
                )
                if resp.ok:
                    candidates = resp.json().get("candidates", [])
                    parts = candidates[0].get("content", {}).get("parts", []) if candidates else []
                    reply = " ".join(str(part.get("text", "")).strip() for part in parts if part.get("text"))
                    if reply:
                        return True, {"reply": reply, "disclaimer": HEALTHCARE_DISCLAIMER,
                                      "mode": "live_ai", "provider": "Google Gemini"}, None, 200
                logger.warning("Gemini provider returned HTTP %s; trying configured alternatives/offline guidance.", resp.status_code)
            except Exception as exc:
                logger.warning("Gemini provider unavailable; trying configured alternatives/offline guidance (%s).", type(exc).__name__)

        if self.api_key and not self.api_key.startswith("test_"):
            try:
                resp = requests.post(
                    "https://api.openai.com/v1/chat/completions",
                    headers={"Authorization": f"Bearer {self.api_key}", "Content-Type": "application/json"},
                    json={"model": os.getenv("OPENAI_MODEL", "gpt-4o-mini"),
                          "messages": [{"role": "system", "content": SYSTEM_PROMPT},
                                       {"role": "user", "content": clean_msg}],
                          "max_tokens": 300, "temperature": 0.2},
                    timeout=12,
                )
                if resp.ok:
                    reply = resp.json()["choices"][0]["message"]["content"].strip()
                    if reply:
                        return True, {"reply": reply, "disclaimer": HEALTHCARE_DISCLAIMER,
                                      "mode": "live_ai", "provider": "OpenAI"}, None, 200
                logger.warning("AI provider returned HTTP %s; using offline guidance.", resp.status_code)
            except Exception as exc:
                logger.warning("AI provider unavailable; using offline guidance (%s).", type(exc).__name__)

        return True, {"reply": offline_answer(clean_msg), "disclaimer": HEALTHCARE_DISCLAIMER,
                      "mode": "offline_knowledge_base", "provider": "ExpiryCare offline guidance"}, None, 200
