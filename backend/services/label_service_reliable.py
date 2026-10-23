"""Portable label OCR for ExpiryCare.

Uses a configured vision provider first, then local Tesseract if installed.
No machine-specific executable path is hard-coded. OCR is advisory: users must
confirm every extracted value against the package before saving.
"""
import base64
import json
import logging
import os
import re
import shutil
from datetime import datetime
from typing import Any, Dict, Optional, Tuple

from backend.utils.validators import validate_image_payload

logger = logging.getLogger("expirycare.label")


def _date_from_text(text: str) -> str:
    """Return a validated ISO date from text, or an empty string."""
    patterns = [
        (r"\b(20\d{2})[-/.](\d{1,2})[-/.](\d{1,2})\b", "ymd"),
        (r"\b(\d{1,2})[-/.](\d{1,2})[-/.](20\d{2})\b", "dmy"),
        (r"\b(\d{1,2})\s+(Jan|Feb|Mar|Apr|May|Jun|Jul|Aug|Sep|Oct|Nov|Dec)[a-z]*\s+(20\d{2})\b", "month"),
    ]
    for pattern, kind in patterns:
        m = re.search(pattern, text, re.I)
        if not m:
            continue
        try:
            if kind == "ymd":
                dt = datetime(int(m.group(1)), int(m.group(2)), int(m.group(3)))
            elif kind == "dmy":
                dt = datetime(int(m.group(3)), int(m.group(2)), int(m.group(1)))
            else:
                dt = datetime.strptime(f"{m.group(1)} {m.group(2)[:3]} {m.group(3)}", "%d %b %Y")
            return dt.strftime("%Y-%m-%d")
        except ValueError:
            continue
    return ""


def _extract_labeled_date(text: str, label: str) -> str:
    for line in text.splitlines():
        m = re.search(label, line, re.I)
        if m:
            found = _date_from_text(line[m.end():])
            if found:
                return found
    return ""


class ReliableLabelService:
    """Vision-first scanner with a portable local OCR fallback."""

    def analyze_label_image(self, payload: Dict[str, Any]) -> Tuple[bool, Optional[Dict[str, Any]], Optional[str], int]:
        valid, error = validate_image_payload(payload)
        if not valid:
            return False, None, error, 413 if "exceeds" in (error or "").lower() else 400

        image_data = str(payload.get("imageData", "")).strip()
        if not image_data.startswith("data:image/") or "," not in image_data:
            return False, None, "Please capture or upload a valid image.", 400

        openai_key = os.getenv("OPENAI_API_KEY", "").strip()
        if openai_key and not openai_key.startswith("test_"):
            result = self._openai_vision(image_data, openai_key)
            if result:
                return True, result, None, 200

        gemini_key = os.getenv("GEMINI_API_KEY", "").strip()
        if gemini_key:
            result = self._gemini_vision(image_data, gemini_key)
            if result:
                return True, result, None, 200

        local = self._tesseract(image_data)
        if local:
            return True, local, None, 200

        return False, {
            "error": "Label scanning is unavailable on this server right now. You can still enter the product details manually.",
            "mode": "manual_fallback",
            "warnings": ["Never rely on OCR alone. Confirm the product name and dates against the physical package."]
        }, "No configured vision provider or working local OCR was available.", 503

    @staticmethod
    def _prompt() -> str:
        return (
            "Read this product label. Return a JSON object with name, category "
            "(grocery, medicine, personal-care, or other), manufacturingDate, "
            "expiryDate, batchNumber, and storageInstructions. Dates must be "
            "YYYY-MM-DD only when the printed date is unambiguous. Use an empty "
            "string for unreadable/ambiguous values. Never infer or invent dates "
            "or a product name. Treat the image as a label, not as evidence that "
            "the product is safe."
        )

    @staticmethod
    def _normalize(data: Dict[str, Any], mode: str) -> Dict[str, Any]:
        allowed = {"grocery", "medicine", "personal-care", "other"}
        result = {
            "name": str(data.get("name") or "").strip()[:120],
            "category": data.get("category") if data.get("category") in allowed else "other",
            "manufacturingDate": str(data.get("manufacturingDate") or "").strip(),
            "expiryDate": str(data.get("expiryDate") or "").strip(),
            "batchNumber": str(data.get("batchNumber") or "").strip()[:80],
            "storageInstructions": str(data.get("storageInstructions") or "").strip()[:500],
            "mode": mode,
            "warnings": [
                "Verify the product name, manufacturing date and expiry date against the physical package before saving.",
                "A missing or unreadable date does not mean the product has no expiry date."
            ]
        }
        for key in ("manufacturingDate", "expiryDate"):
            value = result[key]
            if value and not re.fullmatch(r"\d{4}-\d{2}-\d{2}", value):
                result[key] = ""
            elif value:
                try:
                    datetime.strptime(value, "%Y-%m-%d")
                except ValueError:
                    result[key] = ""
        return result

    def _openai_vision(self, image_data: str, api_key: str) -> Optional[Dict[str, Any]]:
        try:
            import requests
            response = requests.post(
                "https://api.openai.com/v1/chat/completions",
                headers={"Authorization": f"Bearer {api_key}", "Content-Type": "application/json"},
                json={
                    "model": os.getenv("OPENAI_MODEL", "gpt-4o-mini"),
                    "messages": [{"role": "user", "content": [
                        {"type": "text", "text": self._prompt()},
                        {"type": "image_url", "image_url": {"url": image_data}}
                    ]}],
                    "max_tokens": 400,
                    "response_format": {"type": "json_object"}
                },
                timeout=25
            )
            if not response.ok:
                logger.warning("OpenAI vision returned HTTP %s", response.status_code)
                return None
            data = json.loads(response.json()["choices"][0]["message"]["content"])
            return self._normalize(data, "openai_vision")
        except Exception as exc:
            logger.warning("OpenAI vision failed (%s)", type(exc).__name__)
            return None

    def _gemini_vision(self, image_data: str, api_key: str) -> Optional[Dict[str, Any]]:
        try:
            import requests
            header, encoded = image_data.split(",", 1)
            mime = header.split(";")[0].replace("data:", "")
            response = requests.post(
                "https://generativelanguage.googleapis.com/v1beta/models/"
                + os.getenv("GEMINI_MODEL", "gemini-2.5-flash")
                + ":generateContent",
                params={"key": api_key},
                json={"contents": [{"parts": [
                    {"text": self._prompt() + " Return JSON only."},
                    {"inline_data": {"mime_type": mime, "data": encoded}}
                ]}], "generationConfig": {"responseMimeType": "application/json", "temperature": 0}},
                timeout=25
            )
            if not response.ok:
                logger.warning("Gemini vision returned HTTP %s", response.status_code)
                return None
            text = response.json()["candidates"][0]["content"]["parts"][0]["text"]
            data = json.loads(text)
            return self._normalize(data, "gemini_vision")
        except Exception as exc:
            logger.warning("Gemini vision failed (%s)", type(exc).__name__)
            return None

    def _tesseract(self, image_data: str) -> Optional[Dict[str, Any]]:
        try:
            import io
            from PIL import Image, ImageOps, ImageEnhance
            import pytesseract

            # On Render/Linux use PATH. Set TESSERACT_CMD only if installed elsewhere.
            custom_cmd = os.getenv("TESSERACT_CMD", "").strip()
            if custom_cmd:
                pytesseract.pytesseract.tesseract_cmd = custom_cmd
            elif not shutil.which("tesseract"):
                return None

            _, encoded = image_data.split(",", 1)
            raw = base64.b64decode(encoded, validate=True)
            if not raw or len(raw) > 9 * 1024 * 1024:
                return None
            image = Image.open(io.BytesIO(raw)).convert("RGB")
            image = ImageOps.autocontrast(ImageOps.grayscale(image))
            image = ImageEnhance.Contrast(image).enhance(1.6)
            text = pytesseract.image_to_string(image, timeout=10).strip()
            if not text:
                return None

            name = ""
            ignored = re.compile(r"\b(EXPIRY|EXPIRATION|EXP|MFG|MANUFACTURED|BATCH|LOT|BEST BEFORE|USE BY|MRP|PRICE|INGREDIENTS|STORAGE|CAUTION|WARNING)\b", re.I)
            for line in text.splitlines():
                candidate = re.sub(r"\s+", " ", line.strip(" :-|\t"))
                if 3 <= len(candidate) <= 60 and not ignored.search(candidate) and not re.search(r"\d{2,}", candidate) and re.fullmatch(r"[A-Za-z][A-Za-z0-9 &'./()-]{2,59}", candidate):
                    name = candidate
                    break
            expiry = _extract_labeled_date(text, r"EXP(?:IRY|IRATION)?|USE\s*BY|BEST\s*BEFORE")
            mfg = _extract_labeled_date(text, r"MFG|MANUFACT(?:URED|URING)?|PROD(?:UCTION)?\s*DATE")
            batch = re.search(r"(?:BATCH|LOT)(?:\s*(?:NO|NUMBER))?\s*[:#\-]?\s*([A-Z0-9\-/]+)", text, re.I)
            data = {"name": name, "category": "other", "manufacturingDate": mfg, "expiryDate": expiry, "batchNumber": batch.group(1) if batch else "", "storageInstructions": ""}
            result = self._normalize(data, "local_ocr")
            result["rawText"] = text[:4000]
            return result
        except Exception as exc:
            logger.warning("Local Tesseract OCR failed (%s)", type(exc).__name__)
            return None
