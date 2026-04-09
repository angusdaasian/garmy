import sys
import os
import logging
import json
import requests
import random
import garth  # Import garth directly to set proxies
from fastapi import FastAPI, HTTPException
from fastapi.middleware.cors import CORSMiddleware
from pydantic import BaseModel
from typing import Optional

# Setup logging
logging.basicConfig(level=logging.INFO)
logger = logging.getLogger("runward-bridge")

sys.path.insert(0, os.path.join(os.getcwd(), "src"))

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

def get_random_proxy():
    try:
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
        # 1. Attempt Resume
        if data.token:
            try:
                auth_client = AuthClient()
                auth_client.garth.loads(data.token)
                return {
                    "success": True, 
                    "display_name": getattr(auth_client, 'display_name', 'User'), 
                    "session_data": data.token
                }
            except:
                logger.warning("Token resume failed")

        # 2. Fresh Login with Proxy Rotation
        # We try 3 different proxies if they fail
        for attempt in range(3):
            proxy_addr = get_random_proxy()
            if proxy_addr:
                logger.info(f"Attempt {attempt+1}: Using proxy {proxy_addr}")
                # This is the correct way: Set it globally for garth
                garth.client.proxies = {
                    "http": f"http://{proxy_addr}",
                    "https": f"http://{proxy_addr}"
                }
            
            try:
                auth_client = AuthClient()
                auth_client.login(data.email, data.password)
                
                # If we get here, login worked!
                session_string = auth_client.garth.dumps()
                return {
                    "success": True,
                    "display_name": getattr(auth_client, 'display_name', data.email.split('@')[0]),
                    "session_data": session_string
                }
            except Exception as e:
                logger.warning(f"Login attempt {attempt+1} failed: {str(e)}")
                if attempt == 2:
                    raise e # Re-raise the last error if all attempts fail

    except Exception as e:
        error_msg = str(e)
        logger.error(f"Final Auth Error: {error_msg}")
        
        # Friendly error handling for the 429 block
        if "429" in error_msg:
            detail = "Garmin is rate-limiting this request. Please try again in a few minutes."
        else:
            detail = f"Garmin login failed: {error_msg}"
            
        raise HTTPException(status_code=400, detail=detail)

if __name__ == "__main__":
    import uvicorn
    uvicorn.run(app, host="0.0.0.0", port=int(os.environ.get("PORT", 8000)))
