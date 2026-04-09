import sys
import os
from fastapi import FastAPI, HTTPException
from fastapi.middleware.cors import CORSMiddleware
from pydantic import BaseModel

# 1. Force the 'src' directory into the system path correctly
root_dir = os.path.dirname(os.path.abspath(__file__))
src_path = os.path.join(root_dir, "src")
if src_path not in sys.path:
    sys.path.insert(0, src_path)

# 2. Try both common import patterns for this repository structure
try:
    from garmy.auth.session import GarminSession
except ImportError:
    try:
        from src.garmy.auth.session import GarminSession
    except ImportError as e:
        # This will print the exact reason in the Railway logs if it still fails
        print(f"DEBUG: Current Path: {sys.path}")
        print(f"DEBUG: Folder Contents: {os.listdir(src_path if os.path.exists(src_path) else '.')}")
        raise e

app = FastAPI()

# Standard CORS to allow your React app to connect
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
    return {"status": "Bridge Online", "service": "RunWard"}

@app.post("/auth")
async def authenticate(data: LoginRequest):
    try:
        session = GarminSession(email=data.email, password=data.password)
        tokens = session.login() 
        return tokens
    except Exception as e:
        raise HTTPException(status_code=400, detail=str(e))
