from supabase import create_client, Client
from app.config import get_settings

settings = get_settings()

# Public reads (respects RLS, uses anon key)
anon_client: Client = create_client(settings.SUPABASE_URL, settings.SUPABASE_ANON_KEY)

# Backend writes (bypasses RLS, uses service key)
service_client: Client = create_client(settings.SUPABASE_URL, settings.SUPABASE_SERVICE_KEY)
