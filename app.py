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
        logger.error("Could not find garmy. Ensure 'src' folder is present.")

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

def get_all_webshare_proxies():
    """Reads the uploaded proxy list and returns a list of formatted proxy URLs."""
    file_path = "Webshare 10 proxies.txt"
    formatted_proxies = []
    try:
        if os.path.exists(file_path):
            with open(file_path, "r") as f:
                lines = [line.strip() for line in f if line.strip()]
                for line in lines:
                    parts = line.split(':')
                    if len(parts) == 4:
                        ip, port, user, pw = parts
                        formatted_proxies.append(f"http://{user}:{pw}@{ip}:{port}")
        else:
            logger.error(f"Proxy file {file_path} not found!")
    except Exception as e:
        logger.error(f"Error reading proxy file: {e}")
    return formatted_proxies

@app.get("/")
def health():
    return {"status": "Bridge Online", "app": "RunWard"}

@app.post("/auth")
async def authenticate(data: LoginRequest):
    logger.info(f"Auth request for: {data.email}")
    
    try:
        auth_client = AuthClient()

        # 1. ATTEMPT RESUME
        if data.token:
            try:
                auth_client.garth.loads(data.token)
                return {"success": True, "display_name": getattr(auth_client, 'display_name', 'User'), "session_data": data.token}
            except:
                logger.warning("Resume failed, trying login.")

        # 2. FRESH LOGIN WITH ROTATION
        if not data.password:
            raise ValueError("Password required.")

        proxies = get_all_webshare_proxies()
        if not proxies:
            raise Exception("No proxies available in Webshare list.")
        
        # Shuffle to try a different starting point each time
        random.shuffle(proxies)
        
        last_error = ""
        # We will try up to 3 different proxies from your list per request
        for i in range(min(3, len(proxies))):
            proxy_url = proxies[i]
            logger.info(f"Attempting login with proxy {i+1}/3")
            
            # Set proxy globally for garth
            garth.client.proxies = {"http": proxy_url, "https": proxy_url}
            
            try:
                auth_client.login(data.email, data.password)
                # If we reach here, it worked!
                session_string = auth_client.garth.dumps()
                return {
                    "success": True,
                    "display_name": getattr(auth_client, 'display_name', data.email.split('@')[0]),
                    "session_data": session_string
                }
            except Exception as e:
                last_error = str(e)
                logger.warning(f"Proxy attempt {i+1} failed: {last_error}")
                if "429" not in last_error: # If it's a password error, don't retry
                    break
        
        raise Exception(last_error)

    except Exception as e:
        error_msg = str(e)
        logger.error(f"Final Auth Error: {error_msg}")
        raise HTTPException(status_code=429 if "429" in error_msg else 400, detail=error_msg)

if __name__ == "__main__":
    import uvicorn
    port = int(os.environ.get("PORT", 8000))
    uvicorn.run(app, host="0.0.0.0", port=port)
