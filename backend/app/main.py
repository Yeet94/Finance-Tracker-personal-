from fastapi import FastAPI
from fastapi.middleware.cors import CORSMiddleware

app = FastAPI(
    title="Finance Tracker API",
    descriptions="Track your income and expenses",
    version="1.0.0",
    doc_url = "/docs",
    redoc_url = "/redoc",
)

app.add_middleware(
    CORSMiddleware,
    allow_origins=["http://localhost:5173", "https://yourfrontend.com"],
    allow_credentials=True,   # Allow cookies
    allow_methods=["*"],      # Allow GET, POST, PATCH, DELETE, etc.
    allow_headers=["*"],      # Allow Authorization, Content-Type, etc.
)

@app.get("/api/health", tags=["System"])
def health_check():
    return {
        "status": "ok",
        "message": "Finance Tracker API is running"
    }
