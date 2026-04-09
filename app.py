import sys
import os
from fastapi import FastAPI, HTTPException
from fastapi.middleware.cors import CORSMiddleware
from pydantic import BaseModel

# Ensure the 'src' directory is searchable
sys.path.append(os.path.join(os.getcwd(), "src"))

# Now that __init__.py files are present, this should work perfectly
from garmy.auth.session import GarminSession

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
