"""Application entry point: creates the app and registers the routers only."""
from fastapi import FastAPI

from app.core.config import settings
from app.routers import address_routes, user_routes

app = FastAPI(
    title=settings.APP_NAME,
    version=settings.APP_VERSION,
    description="Independent User Management microservice (profiles and delivery addresses). "
                "Authentication is handled by the Authentication Service; send its JWT as a Bearer token.",
)
app.include_router(user_routes.router)
app.include_router(address_routes.router)


@app.get("/", tags=["Health"])
def health_check():
    return {"service": settings.APP_NAME, "status": "running", "version": settings.APP_VERSION}
