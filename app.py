import sys
import os
from fastapi import FastAPI, HTTPException
from fastapi.middleware.cors import CORSMiddleware
from pydantic import BaseModel

# 1. Ensure the src directory is in the path
sys.path.append(os.path.join(os.getcwd(), "src"))

# 2. Use the modern Garmy exports as per the library's __init__.py
try:
    from garmy import AuthClient, APIClient
except ImportError as e:
    print(f"Import failed: {e}")
    # Fallback if structure is nested differently on Railway
    from src.garmy import AuthClient, APIClient

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
        # 3. Use the modern usage pattern from the Garmy docs
        auth_client = AuthClient()
        auth_client.login(data.email, data.password)
        
        # Once logged in, the auth_client stores the session tokens internally.
        # We return the session data so your React app can store it.
        return {
            "success": True,
            "display_name": auth_client.display_name,
            "session": auth_client.session_data # Returns tokens for Supabase storage
        }
    except Exception as e:
        raise HTTPException(status_code=400, detail=str(e))

@app.post("/sync")
async def sync_activities(data: dict):
    # This is a placeholder for your leaderboard logic
    # Once you have the session saved in Supabase, you can use it here
    # to fetch 5K/Marathon data.
    return {"message": "Ready to sync metrics"}
