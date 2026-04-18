import os
from discord.ext import commands
from fastapi import FastAPI
from fastapi.middleware.cors import CORSMiddleware
from dotenv import load_dotenv

from app.api.routes import create_api_router

load_dotenv()

def create_fastapi_app(bot: commands.Bot) -> FastAPI:
    app = FastAPI(title="Discord Bot API")

    frontend_url = os.getenv("FRONTEND_URL", "http://localhost:5173")

    # Add CORS middleware
    app.add_middleware(
        CORSMiddleware,
        allow_origins=[frontend_url],  # Allow frontend origin
        allow_credentials=True,
        allow_methods=["*"],  # Allow all methods (GET, POST, etc.)
        allow_headers=["*"],  # Allow all headers
    )
    app.include_router(create_api_router(bot))
    return app
