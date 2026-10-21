"""Tests for guidance chat, label image analysis, and barcode lookups."""
def test_guidance_chat_missing_message(client):
    """Verify empty or missing message returns 400."""
    resp = client.post("/api/guidance/chat", json={})
    assert resp.status_code == 400
    assert "message is required" in resp.get_json()["error"]


def test_guidance_chat_offline_fallback_works_without_provider(client):
    """The chatbot must return useful, clearly labelled guidance without a paid API key."""
    resp = client.post("/api/guidance/chat", json={"message": "Is expired milk safe to drink?"})
    assert resp.status_code == 200
    data = resp.get_json()
    assert "reply" in data and "discard" in data["reply"].lower()
    assert data["mode"] == "offline_knowledge_base"
    assert "disclaimer" in data


def test_analyze_label_invalid_image(client):
    """Verify non-image data URL returns 400."""
    resp = client.post("/api/products/analyze-label", json={"imageData": "not-a-data-url"})
    assert resp.status_code == 400
    assert "data:image/" in resp.get_json()["error"]


def test_analyze_label_unreadable_image_has_manual_fallback(client):
    """Unreadable images return a useful manual-entry response rather than a fake success."""
    sample_data_url = "data:image/jpeg;base64,/9j/4AAQSkZJRgABAQEASABIAAD/2wBDAP..."
    resp = client.post("/api/products/analyze-label", json={
        "imageName": "sample.jpg", "imageType": "image/jpeg", "imageData": sample_data_url
    })
    assert resp.status_code in (400, 422)
    data = resp.get_json()
    assert "error" in data


def test_barcode_lookup_validation(client):
    """Verify non-digit or wrong length barcode returns 400."""
    resp = client.get("/api/products/barcode/not-digits")
    assert resp.status_code == 400
    assert "8–14 digit" in resp.get_json()["error"]


def test_guidance_chat_unknown_question_returns_safe_fallback(client):
    resp = client.post("/api/guidance/chat", json={"message": "Can you identify this mystery chemical?"})
    assert resp.status_code == 200
    data = resp.get_json()
    assert data["mode"] == "offline_knowledge_base"
    assert "not enough detail" in data["reply"].lower()


def test_guidance_chat_rejects_oversized_message(client):
    resp = client.post("/api/guidance/chat", json={"message": "x" * 2001})
    assert resp.status_code == 400
