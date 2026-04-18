import os
from discord.ext import commands
from fastapi import FastAPI, Request, HTTPException
from fastapi.middleware.cors import CORSMiddleware
from starlette.middleware.base import BaseHTTPMiddleware
from dotenv import load_dotenv

from app.api.routes import create_api_router
from services.redis import check_rate_limit

load_dotenv()


class RateLimitMiddleware(BaseHTTPMiddleware):
    async def dispatch(self, request: Request, call_next):
        client_ip = request.client.host if request.client else "unknown"
        if not check_rate_limit(client_ip):
            raise HTTPException(status_code=429, detail="Rate limit exceeded. Try again later.")
        response = await call_next(request)
        return response


def create_fastapi_app(bot: commands.Bot) -> FastAPI:
    app = FastAPI(title="Discord Bot API")

    frontend_url = os.getenv("FRONTEND_URL", "http://localhost:5173")

    app.add_middleware(RateLimitMiddleware)

    app.add_middleware(
        CORSMiddleware,
        allow_origins=[frontend_url],
        allow_credentials=True,
        allow_methods=["*"],
        allow_headers=["*"],
    )
    app.include_router(create_api_router(bot))
    return app
