from fastapi import APIRouter
from app.api.v1.endpoints import invoices

api_router = APIRouter()
api_router.include_router(invoices.router, prefix="/invoices", tags=["Invoices"])
