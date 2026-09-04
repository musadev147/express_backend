from fastapi import FastAPI, Request, status
from fastapi.middleware.cors import CORSMiddleware
from fastapi.responses import JSONResponse
from fastapi.exceptions import RequestValidationError
from starlette.exceptions import HTTPException as StarletteHTTPException

from app.config import settings
from app.database import engine, Base, SessionLocal
from app.seeds.initial_seed import seed_database

# Import routers
from app.routers.auth_router import router as auth_router
from app.routers.location_router import router as location_router
from app.routers.customer_router import router as customer_router
from app.routers.vendor_router import router as vendor_router
from app.routers.invoice_router import router as invoice_router
from app.routers.call_router import router as call_router
from app.routers.crm_router import router as crm_router
from app.websockets.signaling import router as ws_router

# Initialize database tables
Base.metadata.create_all(bind=engine)

app = FastAPI(
    title=settings.APP_NAME,
    version=settings.VERSION,
    description="Unified Backend API and Real-Time WebSocket Server for Flutter Mobile Apps (Customer/Vendor) and Web CRM Portal with 2% Category-Based Commission Engine.",
    docs_url="/docs",
    redoc_url="/redoc"
)

# CORS configuration
app.add_middleware(
    CORSMiddleware,
    allow_origins=["*"],
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
)

# Global Exception Handlers for Envelope Responses
@app.exception_handler(StarletteHTTPException)
async def http_exception_handler(request: Request, exc: StarletteHTTPException):
    return JSONResponse(
        status_code=exc.status_code,
        content={
            "success": False,
            "statusCode": exc.status_code,
            "error": "HTTP Error",
            "message": str(exc.detail),
            "errors": [{"message": str(exc.detail)}]
        }
    )

@app.exception_handler(RequestValidationError)
async def validation_exception_handler(request: Request, exc: RequestValidationError):
    error_details = []
    for err in exc.errors():
        field_name = ".".join(str(loc) for loc in err.get("loc", []))
        error_details.append({
            "field": field_name,
            "message": err.get("msg", "Validation error")
        })
    return JSONResponse(
        status_code=status.HTTP_400_BAD_REQUEST,
        content={
            "success": False,
            "statusCode": status.HTTP_400_BAD_REQUEST,
            "error": "Validation failed",
            "message": "Invalid request body or query parameters",
            "errors": error_details
        }
    )

# Startup Event: Seed Database
@app.on_event("startup")
def on_startup():
    db = SessionLocal()
    try:
        seed_database(db)
    finally:
        db.close()

# Mount API Routers
app.include_router(auth_router, prefix=settings.API_PREFIX)
app.include_router(location_router, prefix=settings.API_PREFIX)
app.include_router(customer_router, prefix=settings.API_PREFIX)
app.include_router(vendor_router, prefix=settings.API_PREFIX)
app.include_router(invoice_router, prefix=settings.API_PREFIX)
app.include_router(call_router, prefix=settings.API_PREFIX)
app.include_router(crm_router, prefix=settings.API_PREFIX)
app.include_router(ws_router) # WebSocket at /ws

@app.get("/", tags=["Health"])
def health_check():
    return {
        "success": True,
        "statusCode": 200,
        "message": "Express Platform API is active and running",
        "version": settings.VERSION,
        "commissionEngine": "2% Category-Based Commission System",
        "docsUrl": "/docs"
    }
