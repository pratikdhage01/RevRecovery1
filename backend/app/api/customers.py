"""
Customer API endpoints.
"""
from fastapi import APIRouter, HTTPException
from app.services import recovery_service

router = APIRouter(prefix="/api/customers", tags=["customers"])


@router.get("")
async def list_customers():
    """Get all customers with recovery state."""
    customers = await recovery_service.get_all_customers()
    return {"customers": customers, "total": len(customers)}


@router.get("/{customer_id}")
async def get_customer(customer_id: str):
    """Get a single customer by ID."""
    customer = await recovery_service.get_customer(customer_id)
    if not customer:
        raise HTTPException(status_code=404, detail=f"Customer {customer_id} not found")
    return customer


@router.get("/{customer_id}/audit")
async def get_customer_audit(customer_id: str):
    """Get full audit trail for a customer."""
    events = await recovery_service.get_audit_trail(customer_id)
    return {"customer_id": customer_id, "events": events, "total": len(events)}


@router.get("/{customer_id}/recovery")
async def get_customer_recovery(customer_id: str):
    """Get recovery state for a customer."""
    customer = await recovery_service.get_customer(customer_id)
    if not customer:
        raise HTTPException(status_code=404, detail=f"Customer {customer_id} not found")
    return customer.get("recovery_state", {})
