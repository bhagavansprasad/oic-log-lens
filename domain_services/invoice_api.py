from fastapi import APIRouter, HTTPException
from domain_services.invoice_service import InvoiceService

router = APIRouter()
service = InvoiceService()


@router.get("/invoice/{invoice_id}")
def get_invoice_by_id(invoice_id: str):
    try:
        invoice = service.get_invoice_by_id(invoice_id)

        if not invoice:
            raise HTTPException(
                status_code=404,
                detail=f"No invoice found for Invoice ID {invoice_id}"
            )

        return invoice

    except ValueError as ve:
        raise HTTPException(status_code=400, detail=str(ve))

    except Exception as e:
        raise HTTPException(
            status_code=500,
            detail="Internal server error"
        )
