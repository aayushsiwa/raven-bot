import re
import secrets
from typing import Any
from urllib.parse import urlencode

import httpx
import jwt
from fastapi import HTTPException

import config


USERNAME_ALLOWED = re.compile(r"[^a-zA-Z0-9_.-]+")


def _provider_config(provider: str) -> dict[str, Any]:
    if provider == "google":
        if not config.OAUTH_GOOGLE_CLIENT_ID or not config.OAUTH_GOOGLE_CLIENT_SECRET:
            raise HTTPException(status_code=503, detail="Google OAuth not configured")
        return {
            "client_id": config.OAUTH_GOOGLE_CLIENT_ID,
            "client_secret": config.OAUTH_GOOGLE_CLIENT_SECRET,
            "authorize_url": "https://accounts.google.com/o/oauth2/v2/auth",
            "token_url": "https://oauth2.googleapis.com/token",
            "userinfo_url": "https://openidconnect.googleapis.com/v1/userinfo",
            "scope": "openid email profile",
        }

    if provider == "github":
        if not config.OAUTH_GITHUB_CLIENT_ID or not config.OAUTH_GITHUB_CLIENT_SECRET:
            raise HTTPException(status_code=503, detail="GitHub OAuth not configured")
        return {
            "client_id": config.OAUTH_GITHUB_CLIENT_ID,
            "client_secret": config.OAUTH_GITHUB_CLIENT_SECRET,
            "authorize_url": "https://github.com/login/oauth/authorize",
            "token_url": "https://github.com/login/oauth/access_token",
            "userinfo_url": "https://api.github.com/user",
            "scope": "read:user user:email",
        }

    if provider == "discord":
        if not config.OAUTH_DISCORD_CLIENT_ID or not config.OAUTH_DISCORD_CLIENT_SECRET:
            raise HTTPException(status_code=503, detail="Discord OAuth not configured")
        return {
            "client_id": config.OAUTH_DISCORD_CLIENT_ID,
            "client_secret": config.OAUTH_DISCORD_CLIENT_SECRET,
            "authorize_url": "https://discord.com/api/oauth2/authorize",
            "token_url": "https://discord.com/api/oauth2/token",
            "userinfo_url": "https://discord.com/api/users/@me",
            "scope": "identify email",
        }

    raise HTTPException(status_code=422, detail="Unsupported provider")


def create_oauth_state(provider: str, next_path: str = "/") -> str:
    payload = {
        "iss": f"{config.AUTH_ISSUER}:oauth-state",
        "provider": provider,
        "nonce": secrets.token_urlsafe(16),
        "next": next_path if next_path.startswith("/") else "/",
    }
    return jwt.encode(payload, config.AUTH_SECRET, algorithm="HS256")


def parse_oauth_state(provider: str, state: str) -> dict[str, Any]:
    try:
        payload = jwt.decode(
            state,
            config.AUTH_SECRET,
            algorithms=["HS256"],
            issuer=f"{config.AUTH_ISSUER}:oauth-state",
        )
    except Exception as exc:
        raise HTTPException(status_code=401, detail="Invalid oauth state") from exc

    if payload.get("provider") != provider:
        raise HTTPException(status_code=401, detail="OAuth provider mismatch")
    return payload


def build_oauth_start_url(provider: str, state: str) -> str:
    cfg = _provider_config(provider)
    query = urlencode(
        {
            "client_id": cfg["client_id"],
            "redirect_uri": config.oauth_callback_url(provider),
            "response_type": "code",
            "scope": cfg["scope"],
            "state": state,
            "prompt": "select_account" if provider == "google" else None,
        }
    )
    query = query.replace("prompt=None&", "").replace("prompt=None", "")
    return f"{cfg['authorize_url']}?{query}"


async def exchange_code_for_profile(provider: str, code: str) -> dict[str, Any]:
    cfg = _provider_config(provider)
    async with httpx.AsyncClient(timeout=20) as client:
        if provider == "github":
            token_res = await client.post(
                cfg["token_url"],
                headers={"Accept": "application/json"},
                data={
                    "client_id": cfg["client_id"],
                    "client_secret": cfg["client_secret"],
                    "code": code,
                    "redirect_uri": config.oauth_callback_url(provider),
                },
            )
        else:
            token_res = await client.post(
                cfg["token_url"],
                data={
                    "client_id": cfg["client_id"],
                    "client_secret": cfg["client_secret"],
                    "code": code,
                    "redirect_uri": config.oauth_callback_url(provider),
                    "grant_type": "authorization_code",
                },
                headers={"Accept": "application/json"},
            )

        if token_res.status_code >= 400:
            raise HTTPException(status_code=401, detail="OAuth token exchange failed")
        token_payload = token_res.json()
        access_token = token_payload.get("access_token")
        if not access_token:
            raise HTTPException(status_code=401, detail="OAuth access token missing")

        headers = {
            "Authorization": f"Bearer {access_token}",
            "Accept": "application/json",
        }
        profile_res = await client.get(cfg["userinfo_url"], headers=headers)
        if profile_res.status_code >= 400:
            raise HTTPException(status_code=401, detail="OAuth profile fetch failed")
        profile = profile_res.json()

        if provider == "github" and not profile.get("email"):
            email_res = await client.get("https://api.github.com/user/emails", headers=headers)
            if email_res.status_code < 400:
                emails = email_res.json()
                primary = next((e for e in emails if e.get("primary")), None)
                verified = next((e for e in emails if e.get("verified")), None)
                profile["email"] = (primary or verified or {}).get("email")

        return normalize_profile(provider, profile)


def normalize_profile(provider: str, profile: dict[str, Any]) -> dict[str, str | None]:
    if provider == "google":
        provider_user_id = str(profile.get("sub") or "")
        username_seed = str(profile.get("preferred_username") or profile.get("name") or profile.get("email") or "")
        return {
            "provider_user_id": provider_user_id,
            "username_seed": username_seed,
            "email": profile.get("email"),
            "display_name": profile.get("name"),
            "avatar_url": profile.get("picture"),
        }

    if provider == "github":
        provider_user_id = str(profile.get("id") or "")
        username_seed = str(profile.get("login") or profile.get("name") or profile.get("email") or "")
        return {
            "provider_user_id": provider_user_id,
            "username_seed": username_seed,
            "email": profile.get("email"),
            "display_name": profile.get("name") or profile.get("login"),
            "avatar_url": profile.get("avatar_url"),
        }

    provider_user_id = str(profile.get("id") or "")
    username_seed = str(profile.get("username") or profile.get("global_name") or profile.get("email") or "")
    return {
        "provider_user_id": provider_user_id,
        "username_seed": username_seed,
        "email": profile.get("email"),
        "display_name": profile.get("global_name") or profile.get("username"),
        "avatar_url": _discord_avatar_url(profile),
    }


def _discord_avatar_url(profile: dict[str, Any]) -> str | None:
    user_id = profile.get("id")
    avatar = profile.get("avatar")
    if not user_id or not avatar:
        return None
    return f"https://cdn.discordapp.com/avatars/{user_id}/{avatar}.png"


def normalized_username_candidates(provider: str, seed: str) -> list[str]:
    base = USERNAME_ALLOWED.sub("", seed.strip().replace(" ", ".")).strip("._-")
    base = base[:24] if base else provider
    if len(base) < 3:
        base = f"{provider}_{base}" if base else provider
    candidates = [base]
    for i in range(1, 10):
        suffix = f"_{i}"
        candidates.append((base[: 32 - len(suffix)] + suffix)[:32])
    return candidates
