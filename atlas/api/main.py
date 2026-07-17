import uuid

from fastapi import FastAPI, HTTPException, status
from fastapi.responses import JSONResponse

from api.routes import router

app = FastAPI(
    title="Atlas - Knowledge Research Engine",
    description="Phase 1: Topic → Research → Fact Extraction → Knowledge Storage",
    version="0.1.0",
)

app.include_router(router, prefix="/api")


@app.exception_handler(Exception)
async def global_exception_handler(request, exc: Exception) -> JSONResponse:
    return JSONResponse(
        status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
        content={"detail": "Internal server error. Please check logs."},
    )
