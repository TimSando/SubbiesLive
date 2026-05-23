import logging
from typing import Dict, Any, List, Optional
from fastapi import APIRouter, Header, HTTPException, Query
from pydantic import BaseModel
import httpx

router = APIRouter()
logger = logging.getLogger("uvicorn")

RX_BASE_URL = "https://api.rugbyxplorer.com.au"

class LoginRequest(BaseModel):
    email: str
    password: str

def get_rx_headers(token: Optional[str] = None) -> Dict[str, str]:
    headers = {
        'clientId': 'portal',
        "Content-Type": "application/json",
        "Origin": "https://auth.rugbyxplorer.com.au",
        'Referer': 'https://auth.rugbyxplorer.com.au/',
        'User-Agent': 'Mozilla/5.0 (Windows NT 10.0; Win64; x64; rv:148.0) Gecko/20100101 Firefox/148.0',
    }
    if token:
        headers['Authorization'] = f'Bearer {token}'
    else:
        headers['Authorization'] = 'Basic YXV0aDozanowbkRsZGtQVERFcGdKT2I2bXlYTmhMN0h4Nk4zVnM5eFJHcDcyQ1c1V0w0UmtWTw=='
    return headers

@router.post("/login")
async def rx_login(body: LoginRequest):
    url = f"{RX_BASE_URL}/rau/api/v3/login"
    payload = {
        "email": body.email,
        "encodedParams": ["email", "password"],
        "password": body.password,
        "samlRequest": {}
    }
    headers = get_rx_headers()
    
    async with httpx.AsyncClient() as client:
        try:
            r = await client.post(url, json=payload, headers=headers, timeout=10.0)
            if r.status_code != 200:
                logger.error(f"RX Login failed: status={r.status_code}, response={r.text}")
                raise HTTPException(status_code=r.status_code, detail=f"Login failed: {r.text}")
            return r.json()
        except httpx.RequestError as exc:
            logger.error(f"RX API error: {exc}")
            raise HTTPException(status_code=503, detail="RugbyXplorer service unavailable")

@router.get("/appointments")
async def get_appointments(
    userId: str,
    authorization: Optional[str] = Header(None)
):
    if not authorization or not authorization.startswith("Bearer "):
        raise HTTPException(status_code=401, detail="Missing or invalid Authorization header")
    
    token = authorization.split(" ")[1]
    headers = get_rx_headers(token)
    
    confirmed_url = f"{RX_BASE_URL}/rau/api/v3/appointments/user/{userId}"
    pending_url = f"{confirmed_url}?pending=true"
    
    async with httpx.AsyncClient() as client:
        try:
            # Fetch confirmed
            confirmed_res = await client.get(confirmed_url, headers=headers, timeout=10.0)
            if confirmed_res.status_code == 401:
                raise HTTPException(status_code=401, detail="RugbyXplorer unauthorized")
            elif confirmed_res.status_code != 200:
                raise HTTPException(status_code=confirmed_res.status_code, detail="Failed to fetch confirmed appointments")
            
            # Fetch pending
            pending_res = await client.get(pending_url, headers=headers, timeout=10.0)
            if pending_res.status_code == 401:
                raise HTTPException(status_code=401, detail="RugbyXplorer unauthorized")
            elif pending_res.status_code != 200:
                raise HTTPException(status_code=pending_res.status_code, detail="Failed to fetch pending appointments")
            
            confirmed_data = confirmed_res.json()
            pending_data = pending_res.json()
            
            # Combine appointments
            appointments = []
            if isinstance(confirmed_data, list):
                for app in confirmed_data:
                    appointments.append(app)
            
            if isinstance(pending_data, list):
                for app in pending_data:
                    # Make sure status is set/normalized
                    if "status" not in app:
                        app["status"] = "pending"
                    appointments.append(app)
                
            return appointments
            
        except httpx.RequestError as exc:
            logger.error(f"RX API error fetching appointments: {exc}")
            raise HTTPException(status_code=503, detail="RugbyXplorer service unavailable")

@router.get("/profile")
async def get_profile(
    userId: str,
    authorization: Optional[str] = Header(None)
):
    if not authorization or not authorization.startswith("Bearer "):
        raise HTTPException(status_code=401, detail="Missing or invalid Authorization header")
    
    token = authorization.split(" ")[1]
    headers = get_rx_headers(token)
    
    url = f"{RX_BASE_URL}/rau/api/v2/myprofile/{userId}"
    
    async with httpx.AsyncClient() as client:
        try:
            res = await client.get(url, headers=headers, timeout=10.0)
            if res.status_code == 401:
                raise HTTPException(status_code=401, detail="RugbyXplorer unauthorized")
            elif res.status_code != 200:
                raise HTTPException(status_code=res.status_code, detail="Failed to fetch profile")
            return res.json()
        except httpx.RequestError as exc:
            logger.error(f"RX API error fetching profile: {exc}")
            raise HTTPException(status_code=503, detail="RugbyXplorer service unavailable")
