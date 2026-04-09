import sys
import os
from fastapi import FastAPI, HTTPException
from fastapi.middleware.cors import CORSMiddleware
from pydantic import BaseModel

# 1. This line is CRITICAL. It tells Python to look inside the 'src' folder
# for the 'garmy' package.
sys.path.append(os.path.join(os.getcwd(), "src"))

# 2. Update this import line to match the folder structure
try:
    from garmy.auth.session import GarminSession
except ImportError:
    # Fallback in case the structure is different in your specific fork
    from src.garmy.auth.session import GarminSession

app = FastAPI()

# Standard CORS settings so your React app can talk to this API
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
def health_check():
    return {"status": "RunWard Bridge is Online"}

@app.post("/auth")
async def authenticate(data: LoginRequest):
    try:
        session = GarminSession(email=data.email, password=data.password)
        # Garmy's login method usually returns the session/tokens
        tokens = session.login() 
        return tokens
    except Exception as e:
        raise HTTPException(status_code=400, detail=str(e))
