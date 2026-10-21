"""Retail Intelligence and Retail Catalog routes for ExpiryCare."""
from flask import Blueprint, request
from backend.services.retail_service import RetailService
from backend.utils.response import success_response, error_response

retail_bp = Blueprint("retail", __name__, url_prefix="/api/retail")
retail_service = RetailService()


@retail_bp.route("/summary", methods=["GET"])
def get_retail_summary():
    """Retrieve top-level retail metrics across branches, lots, and workflows."""
    summary = retail_service.get_summary()
    return success_response(data=summary)


@retail_bp.route("/branches", methods=["GET"])
def list_branches():
    """List active retail branches."""
    branches = retail_service.retail_repo.get_branches(active_only=True)
    return success_response(data=branches)


@retail_bp.route("/batches", methods=["GET"])
def list_batches():
    """List retail inventory batches sorted in FEFO order."""
    branch_id = request.args.get("branchId")
    batches = retail_service.list_batches(branch_id=branch_id)
    return success_response(data=batches, count=len(batches))


@retail_bp.route("/clearance", methods=["GET"])
def get_clearance_recommendations():
    """Generate or retrieve explainable clearance recommendations."""
    recs = retail_service.generate_clearance_recommendations()
    return success_response(data=recs, count=len(recs))


@retail_bp.route("/clearance/<clearance_id>/review", methods=["POST"])
def review_clearance(clearance_id: str):
    """Approve or reject a clearance recommendation."""
    body = request.get_json(silent=True) or {}
    status = body.get("status", "")
    success, updated, err = retail_service.review_clearance(clearance_id, status)
    if not success:
        return error_response(err or "Failed to review clearance", status_code=400)
    return success_response(data=updated, message=f"Clearance suggestion set to '{status}'")


@retail_bp.route("/transfers", methods=["GET"])
def list_transfers():
    """Retrieve transfer records and historical workflow status."""
    transfers = retail_service.retail_repo.get_transfers()
    return success_response(data=transfers, count=len(transfers))


@retail_bp.route("/transfers", methods=["POST"])
def create_transfer():
    """Create a new inter-branch transfer request."""
    body = request.get_json(silent=True) or {}
    batch_id = body.get("batchId", "")
    destination_id = body.get("destinationId", "")
    qty = body.get("qty")
    try:
        qty_int = int(qty)
    except (ValueError, TypeError):
        return error_response("Quantity must be an integer", status_code=400)

    success, transfer, err = retail_service.create_transfer(batch_id, destination_id, qty_int)
    if not success:
        return error_response(err or "Failed to create transfer", status_code=400)
    return success_response(data=transfer, message="Transfer requested successfully", status_code=201)


@retail_bp.route("/transfers/<transfer_id>/transition", methods=["POST"])
def transition_transfer(transfer_id: str):
    """Advance a transfer through its lifecycle (Approve, Rejected, Cancel, Dispatch, Receive, Complete)."""
    body = request.get_json(silent=True) or {}
    action = body.get("action", "")
    if not action:
        return error_response("Action is required", status_code=400)

    success, updated, err = retail_service.transition_transfer(transfer_id, action)
    if not success:
        return error_response(err or "Invalid transfer transition", status_code=400)
    return success_response(data=updated, message=f"Transfer transitioned with action '{action}'")


@retail_bp.route("/catalog", methods=["GET"])
def get_catalog():
    """Public store availability view matching retail-catalog.html."""
    q = request.args.get("q")
    branch_id = request.args.get("branch", "all")
    status_filter = request.args.get("status", "all")

    rows = retail_service.get_customer_catalog(
        search_query=q,
        branch_id=branch_id,
        status_filter=status_filter
    )
    return success_response(data=rows, count=len(rows))


@retail_bp.route("/demo/seed", methods=["POST"])
def seed_retail_demo():
    """Seed or reset retail demo records."""
    data = retail_service.retail_repo.seed_demo_data()
    return success_response(data=data, message="Retail demo seeded successfully")
