from fastapi import APIRouter
from datetime import datetime, timezone

router = APIRouter()


@router.get("/health")
async def health_check():
    supabase_status = "unknown"
    try:
        from app.services.supabase import anon_client
        # Test connectivity with a simple query
        anon_client.table("agents").select("id").limit(1).execute()
        supabase_status = "connected"
    except Exception as e:
        supabase_status = f"error: {str(e)}"

    return {
        "status": "ok",
        "supabase": supabase_status,
        "timestamp": datetime.now(timezone.utc).isoformat(),
    }
