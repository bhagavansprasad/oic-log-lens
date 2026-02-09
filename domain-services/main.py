from fastapi import FastAPI
from domain_services.invoice_api import router as invoice_router

app = FastAPI(
    title="Intent-Driven Enterprise Assistant",
    version="0.1.0"
)

app.include_router(invoice_router, prefix="/api")
