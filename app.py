import sys
import os
import logging
import json
import requests
import random
import garth  # Ensure 'garth' is in your requirements.txt
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

def get_random_proxy():
    try:
        # Fetch fresh proxies from Proxifly
        url = "https://cdn.jsdelivr.net/gh/proxifly/free-proxy-list@main/proxies/protocols/http/data.txt"
        response = requests.get(url, timeout=5)
        if response.status_code == 200:
            proxies = [p.strip() for p in response.text.split('\n') if p.strip()]
            if proxies:
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
        # 1. ATTEMPT RESUME (No Proxy needed for tokens usually)
        if data.token:
            try:
                auth_client = AuthClient()
                auth_client.garth.loads(data.token)
                return {
                    "success": True, 
                    "display_name": getattr(auth_client, 'display_name', 'User'), 
                    "session_data": data.token
                }
            except Exception as resume_err:
                logger.warning(f"Token resume failed: {resume_err}")

        # 2. FRESH LOGIN WITH PROXY ROTATION
        last_error = "Unknown Error"
        for attempt in range(3):
            proxy_addr = get_random_proxy()
            if proxy_addr:
                logger.info(f"Attempt {attempt+1}: Using proxy {proxy_addr}")
                # Set garth proxies globally
                garth.client.proxies = {
                    "http": f"http://{proxy_addr}",
                    "https": f"http://{proxy_addr}"
                }
            
            try:
                auth_client = AuthClient()
                auth_client.login(data.email, data.password)
                
                # Success!
                session_string = auth_client.garth.dumps()
                return {
                    "success": True,
                    "display_name": getattr(auth_client, 'display_name', data.email.split('@')[0]),
                    "session_data": session_string
                }
            except Exception as e:
                last_error = str(e)
                logger.warning(f"Login attempt {attempt+1} failed: {last_error}")
                if "429" not in last_error: # If it's a wrong password, don't bother retrying with proxies
                    break
        
        # If we exhausted retries or hit a non-retryable error
        raise Exception(last_error)

    except Exception as e:
        error_msg = str(e)
        logger.error(f"Final Auth Error: {error_msg}")
        
        status = 400
        if "429" in error_msg:
            detail = "Garmin is blocking these requests. Wait 15 mins or try again."
            status = 429
        else:
            detail = f"Garmin login failed: {error_msg}"
            
        raise HTTPException(status_code=status, detail=detail)

if __name__ == "__main__":
    import uvicorn
    port = int(os.environ.get("PORT", 8000))
    uvicorn.run(app, host="0.0.0.0", port=port)
