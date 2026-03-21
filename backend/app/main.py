from fastapi import FastAPI
from fastapi.middleware.cors import CORSMiddleware
from app.config import settings
from app.routers import auth, categories, events

app = FastAPI(
    title="Social Event Mapper API",
    version="0.1.0",
)

app.add_middleware(
    CORSMiddleware,
    allow_origins=[o.strip() for o in settings.CORS_ORIGINS.split(",")],
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
)


app.include_router(auth.router)
app.include_router(events.router)
app.include_router(categories.router)


@app.get("/health")
def health_check():
    from app.database import get_supabase
    try:
        db = get_supabase()
        db.table("users").select("id").limit(1).execute()
        db_status = "connected"
    except Exception:
        db_status = "error"
    return {"status": "ok", "database": db_status}
