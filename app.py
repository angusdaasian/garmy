import sys
import os
import logging
import json
import random
import garth
from fastapi import FastAPI, HTTPException
from fastapi.middleware.cors import CORSMiddleware
from pydantic import BaseModel
from typing import Optional

# Setup logging
logging.basicConfig(level=logging.INFO)
logger = logging.getLogger("runward-bridge")

# 1. Path Setup
sys.path.insert(0, os.path.join(os.getcwd(), "src"))

try:
    from garmy import AuthClient
except ImportError:
    try:
        from src.garmy import AuthClient
    except ImportError:
        logger.error("Could not find garmy. Make sure the 'src' folder exists.")

app = FastAPI()

app.add_middleware(
    CORSMiddleware,
    allow_origins=["*"],
    allow_methods=["*"],
    allow_headers=["*"],
)

class LoginRequest(BaseModel):
    email: str
    password: Optional[str] = None
    token: Optional[str] = None

# --- PROXY LOGIC FOR YOUR WEBSHARE LIST ---
def get_webshare_proxy():
    """Reads your uploaded proxy list and formats a random one for garth."""
    try:
        # Assuming the file is in your root directory
        file_path = "Webshare 10 proxies.txt"
        if not os.path.exists(file_path):
            logger.warning(f"{file_path} not found. Using direct connection.")
            return None
            
        with open(file_path, "r") as f:
            proxies = [line.strip() for line in f if line.strip()]
            
        if not proxies:
            return None
            
        # Select a random proxy from your list
        chosen = random.choice(proxies)
        # Format: IP:PORT:USER:PASS
        parts = chosen.split(':')
        if len(parts) == 4:
            ip, port, user, pw = parts
            return f"http://{user}:{pw}@{ip}:{port}"
    except Exception as e:
        logger.error(f"Error reading proxy list: {e}")
    return None

@app.get("/")
def health():
    return {"status": "Bridge Online", "app": "RunWard"}

@app.post("/auth")
async def authenticate(data: LoginRequest):
    logger.info(f"Auth request for: {data.email}")
    
    # Select and apply a proxy from your file
    proxy_url = get_webshare_proxy()
    if proxy_url:
        garth.client.proxies = {"http": proxy_url, "https": proxy_url}
        logger.info("Proxy applied from Webshare list.")
    
    try:
        auth_client = AuthClient()

        # 1. Attempt Resume
        if data.token:
            try:
                auth_client.garth.loads(data.token)
                return {
                    "success": True, 
                    "display_name": getattr(auth_client, 'display_name', 'User'), 
                    "session_data": data.token
                }
            except Exception as e:
                logger.warning(f"Token resume failed: {e}")

        # 2. Fresh Login
        if not data.password:
            raise ValueError("Password is required for fresh login.")
            
        logger.info(f"Performing Garmin login for {data.email}")
        auth_client.login(data.email, data.password)
        
        # Success!
        session_string = auth_client.garth.dumps()
        return {
            "success": True,
            "display_name": getattr(auth_client, 'display_name', data.email.split('@')[0]),
            "session_data": session_string
        }

    except Exception as e:
        error_msg = str(e)
        logger.error(f"Auth Error: {error_msg}")
        
        status_code = 429 if "429" in error_msg else 400
        # If it's a 429, the next attempt will automatically pick a different IP from your list
        raise HTTPException(status_code=status_code, detail=error_msg)

if __name__ == "__main__":
    import uvicorn
    port = int(os.environ.get("PORT", 8000))
    uvicorn.run(app, host="0.0.0.0", port=port)
