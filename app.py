import sys
import os
import logging
import json
import requests
import random
from fastapi import FastAPI, HTTPException
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

class LoginRequest(BaseModel):
    email: str
    password: Optional[str] = None
    token: Optional[str] = None

# HELPER: Get a random proxy from Proxifly
def get_random_proxy():
    try:
        # Fetching the latest HTTP proxy list from Proxifly CDN
        url = "https://cdn.jsdelivr.net/gh/proxifly/free-proxy-list@main/proxies/protocols/http/data.txt"
        response = requests.get(url, timeout=5)
        if response.status_code == 200:
            proxies = response.text.strip().split('\n')
            return random.choice(proxies)
    except Exception as e:
        logger.error(f"Failed to fetch proxy list: {e}")
    return None

@app.get("/")
def health():
    return {"status": "Bridge Online", "app": "RunWard"}

@app.post("/auth")
async def authenticate(data: LoginRequest):
    logger.info(f"Auth request for: {data.email}")
    
    try:
        auth_client = AuthClient()

        # 1. Attempt to resume if token exists
        if data.token:
            try:
                auth_client.garth.loads(data.token)
                return {"success": True, "display_name": getattr(auth_client, 'display_name', 'User'), "session_data": data.token}
            except:
                logger.warning("Token resume failed, falling back to login")

        # 2. Fresh Login with Proxy
        proxy_addr = get_random_proxy()
        proxy_config = None
        
        if proxy_addr:
            logger.info(f"Using proxy: {proxy_addr}")
            proxy_config = {
                "http": f"http://{proxy_addr}",
                "https": f"http://{proxy_addr}"
            }

        # Passing proxies to the login method (supported by garth/requests)
        # We wrap this in a retry because free proxies often fail
        for attempt in range(3):
            try:
                auth_client.login(data.email, data.password, proxies=proxy_config)
                break 
            except Exception as e:
                if attempt == 2: raise e
                logger.warning(f"Login attempt {attempt+1} failed with proxy, trying another...")
                proxy_addr = get_random_proxy()
                if proxy_addr:
                    proxy_config = {"http": f"http://{proxy_addr}", "https": f"http://{proxy_addr}"}

        # 3. Success Logic
        session_string = auth_client.garth.dumps() if hasattr(auth_client, 'garth') else ""
        
        return {
            "success": True,
            "display_name": getattr(auth_client, 'display_name', data.email.split('@')[0]),
            "session_data": session_string
        }

    except Exception as e:
        error_msg = str(e)
        logger.error(f"Final Auth Error: {error_msg}")
        raise HTTPException(status_code=400, detail=f"Garmin login failed. {error_msg}")

if __name__ == "__main__":
    import uvicorn
    uvicorn.run(app, host="0.0.0.0", port=int(os.environ.get("PORT", 8000)))
