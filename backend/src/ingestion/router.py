import logging
import threading
from fastapi import APIRouter, HTTPException, Depends
from pydantic import BaseModel
from sqlalchemy.orm import sessionmaker

from src.core.config import get_settings, Settings
from src.ingestion.engine import get_sync_engine
from src.ingestion.service import run_ingestion, is_ingestion_running

router = APIRouter()
logger = logging.getLogger("uvicorn")

class TriggerRequest(BaseModel):
    password: str

@router.post("/trigger")
async def trigger_ingestion(
    body: TriggerRequest,
    settings: Settings = Depends(get_settings)
):
    if body.password != settings.ingestion_password:
        raise HTTPException(status_code=401, detail="Invalid password")
    
    if is_ingestion_running():
        return {
            "status": "running",
            "message": "Database ingestion is already running."
        }
    
    # Start ingestion in the background
    engine = get_sync_engine()
    Session = sessionmaker(bind=engine)
    
    thread = threading.Thread(target=run_ingestion, args=(Session,), daemon=True)
    thread.start()
    
    return {
        "status": "started",
        "message": "Database ingestion started in background."
    }

@router.get("/status")
async def get_ingestion_status():
    return {
        "running": is_ingestion_running()
    }
