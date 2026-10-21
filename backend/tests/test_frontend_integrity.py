"""Basic frontend package integrity checks (not a cryptographic baseline)."""
from pathlib import Path

PROJECT_ROOT = Path(__file__).resolve().parents[2]
FRONTEND_DIR = PROJECT_ROOT / "frontend"

def test_frontend_required_pages_and_assets_exist():
    required = [
        "index.html", "dashboard.html", "inventory.html", "add-product.html",
        "healthcare-guidance.html", "alerts.html", "login.html", "register.html",
        "css/styles.css", "js/app.js",
    ]
    missing = [item for item in required if not (FRONTEND_DIR / item).is_file()]
    assert not missing, f"Missing frontend files: {missing}"

def test_frontend_chatbot_and_api_configuration_present():
    app_js = (FRONTEND_DIR / "js/app.js").read_text(encoding="utf-8")
    guidance_html = (FRONTEND_DIR / "healthcare-guidance.html").read_text(encoding="utf-8")
    assert '"/guidance/chat"' in app_js
    assert "EXPIRYCARE_API_BASE" in app_js
    assert "offline" in guidance_html.lower() and "knowledge base" in guidance_html.lower()
