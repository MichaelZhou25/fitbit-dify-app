from fastapi import APIRouter

from app.api.routes.imports import router as imports_router
from app.api.routes.segments import router as segments_router
from app.api.routes.users import router as users_router

api_router = APIRouter()
api_router.include_router(users_router, prefix="/users", tags=["users"])
api_router.include_router(segments_router, prefix="/segments", tags=["segments"])
api_router.include_router(imports_router, prefix="/imports", tags=["imports"])
