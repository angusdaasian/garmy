import sys
import os
import logging
import json
from fastapi import FastAPI, HTTPException, Request
from fastapi.middleware.cors import CORSMiddleware
from pydantic import BaseModel
from typing import Optional

# Setup logging
logging.basicConfig(level=logging.INFO)
logger = logging.getLogger("runward-bridge")

# 1. Path Setup
sys.path.insert(0, os.path.join(os.getcwd(), "src"))

# 2. Imports
try:
    from garmy import AuthClient
except ImportError:
    from src.garmy import AuthClient

app = FastAPI()

app.add_middleware(
    CORSMiddleware,
    allow_origins=["*"],
    allow_methods=["*"],
    allow_headers=["*"],
)

# 3. Model allows for either Password OR a stored Token
class LoginRequest(BaseModel):
    email: str
    password: Optional[str] = None
    token: Optional[str] = None  # Supabase can send the stored session here

@app.get("/")
def health():
    return {"status": "Bridge Online", "app": "RunWard"}

@app.post("/auth")
async def authenticate(data: LoginRequest):
    logger.info(f"Auth request for: {data.email}")
    try:
        auth_client = AuthClient()
        
        # --- PHASE 1: ATTEMPT TO RESUME EXISTING SESSION ---
        if data.token:
            logger.info(f"Attempting to resume session for {data.email}")
            try:
                # Load the JSON string back into the garth client
                auth_client.garth.loads(data.token)
                # Quick check to see if token is still valid
                display_name = getattr(auth_client, 'display_name', 'User')
                return {
                    "success": True,
                    "display_name": display_name,
                    "session_data": data.token # Return the same token back
                }
            except Exception as resume_err:
                logger.warning(f"Session resume failed for {data.email}, falling back to login")

        # --- PHASE 2: FRESH LOGIN (Only if resume fails or no token) ---
        if not data.password:
             raise HTTPException(status_code=400, detail="Password required for new login")
             
        logger.info(f"Performing fresh Garmin SSO login for {data.email}")
        auth_client.login(data.email, data.password)
        
        # Extract session data as a string for Supabase storage
        session_string = ""
        if hasattr(auth_client, 'garth'):
            session_string = auth_client.garth.dumps()
        elif hasattr(auth_client, 'session_data'):
            session_string = json.dumps(auth_client.session_data)

        return {
            "success": True,
            "display_name": getattr(auth_client, 'display_name', data.email.split('@')[0]),
            "session_data": session_string
        }

    except Exception as e:
        error_msg = str(e)
        logger.error(f"Garmin Auth Error: {error_msg}")
        
        if "429" in error_msg:
            detail = "Garmin is temporarily rate-limiting requests. Please try again in an hour."
            status = 429
        elif "MFA" in error_msg.upper():
            detail = "Garmin MFA required. Please check your email."
            status = 400
        else:
            detail = f"Garmin login failed: {error_msg}"
            status = 400
            
        raise HTTPException(status_code=status, detail=detail)

if __name__ == "__main__":
    import uvicorn
    uvicorn.run(app, host="0.0.0.0", port=int(os.environ.get("PORT", 8000)))
