#!/usr/bin/env python3
"""
Simple FastAPI service for smoke testing
"""

from fastapi import FastAPI
from fastapi.middleware.cors import CORSMiddleware
from pydantic import BaseModel
import datetime

class HealthResponse(BaseModel):
    status: str
    version: str
    service: str
    timestamp: str

app = FastAPI(
    title="NextGen Fusion Design Service",
    description="Solar system design service",
    version="1.0.0"
)

# Add CORS middleware
app.add_middleware(
    CORSMiddleware,
    allow_origins=["http://localhost:5173", "http://localhost:3001"],
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
)

@app.get("/health", response_model=HealthResponse)
async def health_check():
    """Health check endpoint"""
    return HealthResponse(
        status="healthy",
        version="1.0.0",
        service="design",
        timestamp=str(datetime.datetime.now())
    )

@app.get("/")
async def root():
    """Root endpoint"""
    return {
        "service": "NextGen Fusion Design Service",
        "version": "1.0.0",
        "status": "running"
    }

@app.get("/api/v1/ping")
async def ping():
    """Simple ping endpoint for testing"""
    return {"message": "pong", "timestamp": str(datetime.datetime.now())}

if __name__ == "__main__":
    import uvicorn
    uvicorn.run("simple_main:app", host="0.0.0.0", port=8001, reload=True)