import os
import time
from discord.ext import commands
from fastapi import FastAPI, Request, HTTPException
from fastapi.responses import JSONResponse
from fastapi.middleware.cors import CORSMiddleware
from starlette.middleware.base import BaseHTTPMiddleware
from dotenv import load_dotenv

from config import logger

from app.api.routes import create_api_router
from services.redis import check_rate_limit

load_dotenv()


class RateLimitMiddleware(BaseHTTPMiddleware):
    async def dispatch(self, request: Request, call_next):
        client_ip = request.client.host if request.client else "unknown"
        if not check_rate_limit(client_ip):
            logger.warning(f"Rate limit exceeded for IP: {client_ip}")
            raise HTTPException(status_code=429, detail="Rate limit exceeded. Try again later.")
        response = await call_next(request)
        return response


class RequestLoggerMiddleware(BaseHTTPMiddleware):
    async def dispatch(self, request: Request, call_next):
        start_time = time.time()
        method = request.method
        path = request.url.path
        query = request.url.query
        full_path = f"{path}?{query}" if query else path

        logger.info(f"Incoming request: {method} {full_path}")

        try:
            response = await call_next(request)
            process_time = (time.time() - start_time) * 1000
            logger.info(
                f"Completed request: {method} {path} - Status: {response.status_code} - Duration: {process_time:.2f}ms"
            )
            return response
        except Exception as e:
            process_time = (time.time() - start_time) * 1000
            logger.error(
                f"Failed request: {method} {path} - Error: {str(e)} - Duration: {process_time:.2f}ms"
            )
            raise e


def create_fastapi_app(bot: commands.Bot) -> FastAPI:
    app = FastAPI(title="Discord Bot API")

    frontend_url = os.getenv("FRONTEND_URL", "http://localhost:5173")

    app.add_middleware(RequestLoggerMiddleware)
    app.add_middleware(RateLimitMiddleware)

    app.add_middleware(
        CORSMiddleware,
        allow_origins=[frontend_url],
        allow_credentials=True,
        allow_methods=["*"],
        allow_headers=["*"],
    )
    app.include_router(create_api_router(bot))

    @app.exception_handler(404)
    async def custom_404_handler(request: Request, __):
        logger.warning(f"404 Not Found: {request.method} {request.url.path}")
        return JSONResponse(
            status_code=404,
            content={"detail": "Not Found", "path": request.url.path},
        )

    return app
