"""
CrisisLens Supabase Client Singleton
Provides authenticated database connectivity using the service-role key.
"""
from functools import lru_cache
from supabase import create_client, Client
from app.core.config import settings


@lru_cache()
def get_supabase_client() -> Client:
    """
    Initializes and returns a cached Supabase client.
    Uses the privileged SUPABASE_SERVICE_ROLE_KEY to perform backend operations.
    """
    if (
        not settings.SUPABASE_URL
        or settings.SUPABASE_URL == "https://your-project.supabase.co"
        or not settings.SUPABASE_SERVICE_ROLE_KEY
        or settings.SUPABASE_SERVICE_ROLE_KEY == "your_supabase_service_role_key"
    ):
        raise ValueError(
            "Supabase credentials are not configured. "
            "Please update SUPABASE_URL and SUPABASE_SERVICE_ROLE_KEY in your backend/.env file."
        )

    url = settings.SUPABASE_URL.strip().rstrip("/")
    if url.endswith("/rest/v1"):
        url = url[:-8].rstrip("/")

    return create_client(url, settings.SUPABASE_SERVICE_ROLE_KEY.strip())
