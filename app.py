import sys
import os
import logging
from fastapi import FastAPI, HTTPException, Request
from fastapi.middleware.cors import CORSMiddleware
from pydantic import BaseModel

# Setup basic logging to see Garmin errors in Railway console
logging.basicConfig(level=logging.INFO)
logger = logging.getLogger("runward-bridge")

# 1. Force the 'src' directory into the search path
sys.path.insert(0, os.path.join(os.getcwd(), "src"))

# 2. Modern Garmy Import
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

class LoginRequest(BaseModel):
    email: str
    password: str

@app.get("/")
def health():
    return {"status": "Bridge Online", "app": "RunWard"}

@app.post("/auth")
async def authenticate(data: LoginRequest):
    logger.info(f"Received auth request for: {data.email}")
    try:
        auth_client = AuthClient()
        
        # This performs the login. 
        # If this fails, it usually raises a GarthHTTPError or similar.
        auth_client.login(data.email, data.password)
        
        # Extract display name safely
        display_name = getattr(auth_client, 'display_name', data.email.split('@')[0])
        
        # Get session data. Note: 'garmy' usually stores tokens in auth_client.garth
        # We need to ensure we're returning a dictionary for Supabase to JSONify.
        session_data = {}
        if hasattr(auth_client, 'session_data'):
            session_data = auth_client.session_data
        elif hasattr(auth_client, 'garth'):
            # Fallback if garmy is using raw garth sessions
            session_data = auth_client.garth.dumps()

        logger.info(f"Login successful for {data.email}")

        return {
            "success": True,
            "display_name": display_name,
            "session_data": session_data
        }

    except Exception as e:
        error_msg = str(e)
        logger.error(f"Garmin Auth Error for {data.email}: {error_msg}")
        
        # Check for common Garmin triggers
        if "MFA" in error_msg.upper():
            detail = "Garmin requires Multi-Factor Authentication. Please login on a browser first."
        elif "401" in error_msg or "403" in error_msg:
            detail = "Invalid Garmin credentials or account locked."
        else:
            detail = f"Garmin login failed: {error_msg}"
            
        raise HTTPException(status_code=400, detail=detail)

# For local testing
if __name__ == "__main__":
    import uvicorn
    uvicorn.run(app, host="0.0.0.0", port=int(os.environ.get("PORT", 8000)))
