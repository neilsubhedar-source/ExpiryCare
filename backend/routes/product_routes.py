"""Product management, barcode lookup, and label analysis routes for ExpiryCare."""
from flask import Blueprint, request, g, jsonify
from backend.services.product_service import ProductService
from backend.services.barcode_service import BarcodeService
from backend.services.label_service import LabelService
from backend.middleware.auth import require_auth
from backend.utils.response import success_response, error_response

product_bp = Blueprint("products", __name__, url_prefix="/api/products")
product_service = ProductService()
barcode_service = BarcodeService()
label_service = LabelService()


# --- Personal Inventory Routes (Protected) ---

@product_bp.route("", methods=["GET"])
@require_auth
def list_products():
    """Retrieve all products for the authenticated user."""
    user_id = g.current_user["id"]
    category = request.args.get("category")
    search_q = request.args.get("search")
    sort_by = request.args.get("sortBy", "expiry-date")

    products = product_service.list_products(
        user_id=user_id,
        category=category,
        search_query=search_q,
        sort_by=sort_by
    )
    return success_response(data=products, count=len(products))


@product_bp.route("", methods=["POST"])
@require_auth
def create_product():
    """Create a new product in personal inventory."""
    user_id = g.current_user["id"]
    body = request.get_json(silent=True) or {}
    success, created, err = product_service.create_product(user_id, body)
    if not success:
        return error_response(err or "Failed to create product", status_code=400)
    return success_response(data=created, message="Product created successfully", status_code=201)


@product_bp.route("/<product_id>", methods=["GET"])
@require_auth
def get_product(product_id: str):
    """Retrieve a single product by ID."""
    user_id = g.current_user["id"]
    product = product_service.get_product(user_id, product_id)
    if not product:
        return error_response("Product not found or access denied", status_code=404)
    return success_response(data=product)


@product_bp.route("/<product_id>", methods=["PUT", "PATCH"])
@require_auth
def update_product(product_id: str):
    """Update an existing product."""
    user_id = g.current_user["id"]
    body = request.get_json(silent=True) or {}
    success, updated, err = product_service.update_product(user_id, product_id, body)
    if not success:
        return error_response(err or "Failed to update product", status_code=400)
    return success_response(data=updated, message="Product updated successfully")


@product_bp.route("/<product_id>", methods=["DELETE"])
@require_auth
def delete_product(product_id: str):
    """Delete a product from personal inventory."""
    user_id = g.current_user["id"]
    deleted = product_service.delete_product(user_id, product_id)
    if not deleted:
        return error_response("Product not found or access denied", status_code=404)
    return success_response(message="Product deleted successfully")


@product_bp.route("/demo", methods=["POST"])
@require_auth
def load_demo():
    """Seed initial demo products for the authenticated user if empty."""
    user_id = g.current_user["id"]
    success, items, msg = product_service.load_demo_data(user_id)
    if not success:
        return error_response(msg, status_code=400)
    return success_response(data=items, message=msg, count=len(items))


# --- Intelligence & Scanner Routes (Compatible with Existing Frontend) ---

@product_bp.route("/barcode/<barcode>", methods=["GET"])
def lookup_barcode(barcode: str):
    """Query Open Food Facts database for a product barcode."""
    success, product_data, err, status_code = barcode_service.lookup_barcode(barcode)
    if not success:
        return error_response(err or "Barcode lookup failed", status_code=status_code)
    return success_response(data=product_data)


@product_bp.route("/analyze-label", methods=["POST"])
def analyze_label():
    """Analyze product label photo for OCR dates, batch numbers, and identity.

    Directly matches the request/response shape expected by js/app.js:
    Request: { imageName, imageType, imageData }
    Response on success: { name, category, manufacturingDate, expiryDate, batchNumber }
    Response on unconfigured provider: HTTP 503 { error: '...' }
    """
    body = request.get_json(silent=True) or {}
    success, data, err, status_code = label_service.analyze_label_image(body)
    if not success:
        # Return exact error response shape for frontend catch handler
        return jsonify(error=err or "Label analysis failed"), status_code
    return jsonify(data), 200
