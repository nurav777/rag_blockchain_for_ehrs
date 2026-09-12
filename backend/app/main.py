from fastapi import FastAPI
from fastapi.middleware.cors import CORSMiddleware

from app.config import settings
from app.routers import auth, records, search, verify


app = FastAPI(
    title=settings.APP_NAME,
    version=settings.APP_VERSION,
    debug=settings.DEBUG,
)

app.add_middleware(
    CORSMiddleware,
    allow_origins=settings.CORS_ORIGINS,
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
)

app.include_router(auth.router, prefix="/api/auth", tags=["wallet-auth"])
app.include_router(records.router, prefix="/api/records", tags=["records"])
app.include_router(search.router, prefix="/api/search", tags=["search"])
app.include_router(verify.router, prefix="/api/verify", tags=["verify"])


@app.get("/")
def root() -> dict[str, str]:
    return {
        "message": "Medical Records API",
        "identity": "wallet",
        "docs": "/docs",
        "health": "/health",
    }


@app.get("/health")
def health_check() -> dict[str, str]:
    return {"status": "ok"}
