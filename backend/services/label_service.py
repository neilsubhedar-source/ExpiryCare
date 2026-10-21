
"""Product-label OCR service with optional online vision and local Tesseract OCR.

OCR extracts text only. Dates must be confirmed against the physical package;
OCR output is never treated as proof that a product is safe.
"""

import os
import re
import base64
import logging
import io
from datetime import datetime
from typing import Dict, Any, Tuple, Optional

from backend.utils.validators import validate_image_payload

logger = logging.getLogger("expirycare.label")


def _extract_date(text: str, labels: str) -> Optional[str]:
    """Extract a date associated with a specific label."""

    date_patterns = [
        (r"\b(20\d{2})[-/.](\d{1,2})[-/.](\d{1,2})\b", "ymd"),
        (r"\b(\d{1,2})[-/.](\d{1,2})[-/.](20\d{2})\b", "dmy"),
        (
            r"\b(\d{1,2})\s+"
            r"(Jan(?:uary)?|Feb(?:ruary)?|Mar(?:ch)?|Apr(?:il)?|May|"
            r"Jun(?:e)?|Jul(?:y)?|Aug(?:ust)?|Sep(?:tember)?|"
            r"Oct(?:ober)?|Nov(?:ember)?|Dec(?:ember)?)\s+(20\d{2})\b",
            "month",
        ),
    ]

    def parse_candidate(candidate: str) -> Optional[str]:
        for pattern, kind in date_patterns:
            match = re.search(pattern, candidate, re.I)
            if not match:
                continue

            try:
                if kind == "ymd":
                    dt = datetime(
                        int(match.group(1)),
                        int(match.group(2)),
                        int(match.group(3)),
                    )
                elif kind == "dmy":
                    day, month, year = map(int, match.groups())
                    dt = datetime(year, month, day)
                else:
                    day, month_name, year = match.groups()
                    month_number = datetime.strptime(
                        month_name[:3].title(), "%b"
                    ).month
                    dt = datetime(int(year), month_number, int(day))

                return dt.strftime("%Y-%m-%d")
            except ValueError:
                continue

        return None

    lines = [line.strip() for line in text.splitlines() if line.strip()]
    label_regex = re.compile(r"(?:" + labels + r")(?![A-Za-z])", re.I)

    for index, line in enumerate(lines):
        match = label_regex.search(line)
        if not match:
            continue

        # First check the text following the date label.
        date = parse_candidate(line[match.end():])
        if date:
            return date

        # Some packages put the date on the next line.
        if index + 1 < len(lines):
            next_line = lines[index + 1]
            if not label_regex.search(next_line):
                date = parse_candidate(next_line)
                if date:
                    return date

    return None


class LabelService:
    """Analyze product labels using vision or local Tesseract OCR."""

    def __init__(self, api_key: Optional[str] = None):
        self.api_key = api_key or os.getenv("OPENAI_API_KEY", "").strip()

    def analyze_label_image(
        self, payload: Dict[str, Any]
    ) -> Tuple[bool, Optional[Dict[str, Any]], Optional[str], int]:

        is_valid, err = validate_image_payload(payload)
        if not is_valid:
            return False, None, err, 413 if "exceeds" in (err or "") else 400

        image_data = payload.get("imageData", "")

        # Optional online vision service.
        if self.api_key and not self.api_key.startswith("test_"):
            try:
                import requests
                import json

                prompt = (
                    "Read the product label in this image. Return JSON only "
                    "with these fields: name, category "
                    "(grocery, medicine, personal-care, or other), "
                    "manufacturingDate, expiryDate in YYYY-MM-DD when "
                    "unambiguous, batchNumber, storageInstructions. "
                    "Use the printed product name, not a guess. "
                    "If a value is unreadable or ambiguous, return an empty "
                    "string. Never invent a name, date, or batch number."
                )

                resp = requests.post(
                    "https://api.openai.com/v1/chat/completions",
                    headers={
                        "Authorization": f"Bearer {self.api_key}",
                        "Content-Type": "application/json",
                    },
                    json={
                        "model": os.getenv("OPENAI_MODEL", "gpt-4o-mini"),
                        "messages": [
                            {
                                "role": "user",
                                "content": [
                                    {"type": "text", "text": prompt},
                                    {
                                        "type": "image_url",
                                        "image_url": {"url": image_data},
                                    },
                                ],
                            }
                        ],
                        "max_tokens": 350,
                        "response_format": {"type": "json_object"},
                    },
                    timeout=15,
                )

                if resp.ok:
                    parsed = json.loads(
                        resp.json()["choices"][0]["message"]["content"]
                    )
                    parsed.setdefault("name", "")
                    parsed.setdefault("category", "other")
                    parsed.setdefault("manufacturingDate", "")
                    parsed.setdefault("expiryDate", "")
                    parsed.setdefault("batchNumber", "")
                    parsed.setdefault("storageInstructions", "")
                    parsed["mode"] = "live_vision"
                    parsed.setdefault(
                        "warnings",
                        [
                            "Verify the product name and all dates "
                            "against the physical package before saving."
                        ],
                    )
                    return True, parsed, None, 200

                logger.warning(
                    "Vision provider returned HTTP %s; trying local OCR.",
                    resp.status_code,
                )

            except Exception as exc:
                logger.warning(
                    "Vision provider unavailable; trying local OCR (%s).",
                    type(exc).__name__,
                )

        # Local Tesseract OCR fallback.
        try:
            from PIL import Image, ImageOps, ImageEnhance
            import pytesseract

            pytesseract.pytesseract.tesseract_cmd = (
                r"C:\Users\neils\OneDrive\Desktop\mini project (sem iii)"
                r"\smart expiry tracker (code)\smart expiry tracker (backend-2)"
                r"\tesseract.exe"
            )

            if "," not in image_data:
                raise ValueError("Invalid image data URL")

            header, encoded = image_data.split(",", 1)
            raw = base64.b64decode(encoded, validate=True)

            if not raw or len(raw) > 9 * 1024 * 1024:
                raise ValueError("Image is empty or too large")

            image = Image.open(io.BytesIO(raw)).convert("RGB")

            # Improve contrast for printed text.
            image = ImageOps.grayscale(image)
            image = ImageOps.autocontrast(image)
            image = ImageEnhance.Contrast(image).enhance(1.7)

            text = pytesseract.image_to_string(
                image, timeout=8
            ).strip()

            if not text:
                return (
                    False,
                    {
                        "error": (
                            "No readable text found. Try a clear, well-lit "
                            "close-up or enter details manually."
                        ),
                        "mode": "local_ocr",
                    },
                    "No readable text found",
                    422,
                )

            expiry = _extract_date(
                text,
                r"EXP(?:IRY|IRATION)?|USE\s*BY|BEST\s*BEFORE",
            )
            manufacturing = _extract_date(
                text,
                r"MFG|MANUFACT(?:URED|URING)?|PROD(?:UCTION)?\s*DATE",
            )

            # Reject common packaging labels and obviously noisy text.
            ignored_labels = re.compile(
                r"\b(EXPIRY|EXPIRATION|EXP|MFG|MANUFACTURED|"
                r"MANUFACTURING|BATCH|LOT|BEST BEFORE|USE BY|"
                r"NET WT|NET QTY|MRP|PRICE|INGREDIENTS|"
                r"STORAGE|CAUTION|WARNING|DIRECTIONS|"
                r"PACKED|MARKETED|CUSTOMER CARE|"
                r"MANUFACTURER|CONTENTS|COMPOSITION)\b",
                re.I,
            )

            candidates = []

            for line in text.splitlines():
                candidate = line.strip(" :-|\t")
                candidate = re.sub(r"\s+", " ", candidate)

                if not 3 <= len(candidate) <= 60:
                    continue

                if ignored_labels.search(candidate):
                    continue

                if re.search(r"\d{2,}", candidate):
                    continue

                # Reject unusual symbols and punctuation.
                if not re.fullmatch(
                    r"[A-Za-z][A-Za-z0-9 &'./()-]{2,59}",
                    candidate,
                ):
                    continue

                letters = sum(ch.isalpha() for ch in candidate)

                if letters / len(candidate) < 0.75:
                    continue

                candidates.append(candidate)

            # Do not invent a product name if no plausible line is found.
            name = candidates[0] if candidates else ""

            batch_match = re.search(
                r"(?:BATCH|LOT)(?:\s*(?:NO|NUMBER))?"
                r"\s*[:#\-]?\s*([A-Z0-9\-/]+)",
                text,
                re.I,
            )

            result = {
                "name": name,
                "category": "other",
                "manufacturingDate": manufacturing or "",
                "expiryDate": expiry or "",
                "batchNumber": (
                    batch_match.group(1) if batch_match else ""
                ),
                "rawText": text,
                "mode": "local_ocr",
                "warnings": [
                    "OCR may misread product names and dates. Verify every "
                    "field against the physical package before saving.",
                    "A missing extracted date does not mean the product "
                    "has no expiry date.",
                ],
            }

            return True, result, None, 200

        except Exception as exc:
            logger.warning(
                "Local OCR failed (%s).", type(exc).__name__
            )

            return (
                False,
                {
                    "error": (
                        "Label OCR could not read this image. Try a clearer "
                        "image or enter the fields manually."
                    ),
                    "mode": "manual_fallback",
                },
                "Label OCR unavailable or image unreadable; enter values manually",
                422,
            )
