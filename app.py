import sys
import os
from fastapi import FastAPI, HTTPException
from fastapi.middleware.cors import CORSMiddleware
from pydantic import BaseModel

# 1. Force the 'src' directory into the search path
sys.path.insert(0, os.path.join(os.getcwd(), "src"))

# 2. Modern Garmy Import
try:
    # This works if 'src' is successfully added to path
    from garmy import AuthClient
except ImportError:
    # Fallback for certain container environments
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
    try:
        auth_client = AuthClient()
        # This performs the SSO dance and internal token storage
        auth_client.login(data.email, data.password)
        
        # Return the essential info for your React app
        return {
            "success": True,
            "display_name": getattr(auth_client, 'display_name', 'User'),
            "session_data": auth_client.session_data if hasattr(auth_client, 'session_data') else {}
        }
    except Exception as e:
        # If Garmin rejects the login (MFA, wrong pass), we see it here
        raise HTTPException(status_code=400, detail=str(e))
