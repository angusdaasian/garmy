import sys
import os
from fastapi import FastAPI, HTTPException
from fastapi.middleware.cors import CORSMiddleware
from pydantic import BaseModel

# This ensures Python can find the Garmy code inside the /src folder
sys.path.append(os.path.join(os.getcwd(), "src"))

from garmy.auth.session import GarminSession # Adjust based on forked structure

app = FastAPI()

# Fixes the CORS issues we saw earlier with Lovable/React
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
        # Using the Garmy session logic to exchange credentials for tokens
        session = GarminSession(email=data.email, password=data.password)
        tokens = session.login() 
        return tokens
    except Exception as e:
        raise HTTPException(status_code=400, detail=str(e))