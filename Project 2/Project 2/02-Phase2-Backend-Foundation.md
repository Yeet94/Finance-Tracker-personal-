# Phase 2: Backend Foundation

> **Goal:** Stand up the entire backend skeleton — Docker + Postgres running, FastAPI connected to the database, environment config loaded, and a health check endpoint working. Everything before writing actual business logic.

---

## 2.1 Project Folder Structure

Create this exact structure. Every file has a specific role:

```
finance-tracker/
│
├── backend/
│   ├── app/
│   │   ├── __init__.py
│   │   ├── main.py                  # FastAPI app + router includes
│   │   ├── database.py              # SQLAlchemy engine + session factory
│   │   │
│   │   ├── core/                    # Framework-level config
│   │   │   ├── __init__.py
│   │   │   ├── config.py            # Pydantic Settings (reads .env)
│   │   │   ├── security.py          # Password hashing + JWT functions
│   │   │   └── dependencies.py      # get_db(), get_current_user() (FastAPI deps)
│   │   │
│   │   ├── models/                  # SQLAlchemy ORM table definitions
│   │   │   ├── __init__.py
│   │   │   ├── user.py
│   │   │   ├── account.py
│   │   │   ├── category.py
│   │   │   └── transaction.py
│   │   │
│   │   ├── schemas/                 # Pydantic request/response validation
│   │   │   ├── __init__.py
│   │   │   ├── user.py
│   │   │   ├── account.py
│   │   │   ├── category.py
│   │   │   ├── transaction.py
│   │   │   └── auth.py
│   │   │
│   │   └── api/
│   │       ├── __init__.py
│   │       └── routes/
│   │           ├── __init__.py
│   │           ├── auth.py
│   │           ├── users.py
│   │           ├── accounts.py
│   │           ├── categories.py
│   │           ├── transactions.py
│   │           └── analytics.py
│   │
│   ├── alembic/                     # Database migration files
│   │   ├── versions/
│   │   └── env.py
│   │
│   ├── requirements.txt
│   ├── alembic.ini
│   ├── .env                         # Local secrets — NEVER commit
│   └── .env.example                 # Template — DO commit
│
├── frontend/
│   └── (Phase 5)
│
└── docker-compose.yml               # Postgres + pgAdmin
```

**The `__init__.py` files** make Python treat directories as packages, enabling imports like `from app.models.user import User`.

---

## 2.2 Docker Compose — Postgres + pgAdmin

Create `docker-compose.yml` in the project root:

```yaml
# docker-compose.yml
version: '3.8'

services:
  postgres:
    image: postgres:16-alpine        # Lightweight Postgres image
    container_name: finance_db
    restart: unless-stopped
    environment:
      POSTGRES_USER: financeuser
      POSTGRES_PASSWORD: financepass  # Change this!
      POSTGRES_DB: financedb
    ports:
      - "5432:5432"                   # host:container
    volumes:
      - postgres_data:/var/lib/postgresql/data  # Persist data across restarts

  pgadmin:
    image: dpage/pgadmin4
    container_name: pgadmin
    restart: unless-stopped
    environment:
      PGADMIN_DEFAULT_EMAIL: admin@admin.com
      PGADMIN_DEFAULT_PASSWORD: admin
    ports:
      - "5050:80"                     # pgAdmin UI at http://localhost:5050
    depends_on:
      - postgres

volumes:
  postgres_data:                      # Named volume = data persists
```

**Commands:**

```bash
# Start in background
docker-compose up -d

# Check status
docker-compose ps

# View Postgres logs
docker-compose logs postgres

# Stop everything
docker-compose down

# Stop AND delete all data (⚠️ nuclear option)
docker-compose down -v
```

**Access pgAdmin:** Open `http://localhost:5050` → login with `admin@admin.com` / `admin`
- Add Server → Host: `postgres` (the container name!), Port: `5432`
- Username: `financeuser`, Password: `financepass`

> **Why `postgres` as the host and not `localhost`?**  
> Inside Docker's network, containers talk to each other by service name. `postgres` IS the hostname of the Postgres container from pgAdmin's perspective.

---

## 2.3 Environment Variables

### `.env.example` (commit this to git)

```bash
# .env.example — copy to .env and fill in real values
DATABASE_URL=postgresql://USER:PASSWORD@HOST:PORT/DBNAME
SECRET_KEY=change-this-to-a-long-random-string-at-least-32-chars
ALGORITHM=HS256
ACCESS_TOKEN_EXPIRE_MINUTES=10080  # 7 days
```

### `.env` (NEVER commit this)

```bash
# .env — your actual local values
DATABASE_URL=postgresql://financeuser:financepass@localhost:5432/financedb
SECRET_KEY=s3cr3t-k3y-abc123-make-this-very-long-and-random-in-production
ALGORITHM=HS256
ACCESS_TOKEN_EXPIRE_MINUTES=10080
```

**Generate a strong SECRET_KEY:**

```bash
# In terminal (Python):
python -c "import secrets; print(secrets.token_hex(32))"
# → a random 64-character hex string

# Or using openssl:
openssl rand -hex 32
```

---

## 2.4 `core/config.py` — Load Settings with Pydantic

```python
# app/core/config.py

from pydantic_settings import BaseSettings  # pip install pydantic-settings

class Settings(BaseSettings):
    """
    Settings class reads from environment variables.
    Pydantic validates types automatically.
    If a required variable is missing → app crashes immediately with a clear error.
    """
    DATABASE_URL: str
    SECRET_KEY: str
    ALGORITHM: str = "HS256"                         # Default value
    ACCESS_TOKEN_EXPIRE_MINUTES: int = 10080         # Default: 7 days

    class Config:
        env_file = ".env"          # Read from .env file in dev
        env_file_encoding = "utf-8"

# Singleton instance — import this everywhere
settings = Settings()
```

**Usage anywhere in the codebase:**
```python
from app.core.config import settings

print(settings.DATABASE_URL)
print(settings.SECRET_KEY)
```

> **Why Pydantic Settings?**  
> It validates that `ACCESS_TOKEN_EXPIRE_MINUTES` is actually an `int`, not a string. Raw `os.environ.get()` returns strings for everything — you'd have to `int()` cast manually and handle errors yourself.

---

## 2.5 `database.py` — Database Connection

```python
# app/database.py

from sqlalchemy import create_engine
from sqlalchemy.ext.declarative import declarative_base
from sqlalchemy.orm import sessionmaker
from app.core.config import settings

# ─── ENGINE ──────────────────────────────────────────────────────────────────
# The engine is the connection to Postgres. One engine per app.
engine = create_engine(
    settings.DATABASE_URL,
    # pool_pre_ping: test connection before using it (handles dropped connections)
    pool_pre_ping=True,
    # echo=True: print all SQL queries (useful for debugging, disable in production)
    echo=False,
)

# ─── SESSION FACTORY ─────────────────────────────────────────────────────────
# SessionLocal creates individual database sessions (like a "conversation" with the DB)
SessionLocal = sessionmaker(
    autocommit=False,   # Must explicitly call session.commit() — prevents accidental writes
    autoflush=False,    # Must call session.flush() manually
    bind=engine
)

# ─── BASE CLASS ──────────────────────────────────────────────────────────────
# All SQLAlchemy models inherit from Base
# This lets Alembic and SQLAlchemy discover your tables automatically
Base = declarative_base()
```

**What's a "session"?**  
A SQLAlchemy session is like a transaction with the database. All operations within one session are committed or rolled back together. Each API request gets its own session, then closes it when done.

---

## 2.6 `core/dependencies.py` — FastAPI Dependency Injection

FastAPI's "dependency injection" system is one of its most powerful features. Define reusable functions and inject them into route handlers:

```python
# app/core/dependencies.py

from typing import Generator
from fastapi import Depends, HTTPException, status
from fastapi.security import HTTPBearer, HTTPAuthorizationCredentials
from sqlalchemy.orm import Session
from app.database import SessionLocal
from app.core.security import decode_access_token
from app.models.user import User

# ─── DATABASE DEPENDENCY ─────────────────────────────────────────────────────
def get_db() -> Generator:
    """
    Creates a new database session for each request.
    Automatically closes it when the request finishes (even if error occurs).
    
    Usage in routes:
        def my_route(db: Session = Depends(get_db)):
    """
    db = SessionLocal()
    try:
        yield db          # Give the session to the route function
    finally:
        db.close()        # Always close, even if exception was raised

# ─── AUTH DEPENDENCY ─────────────────────────────────────────────────────────
security = HTTPBearer()  # Expects "Authorization: Bearer <token>" header

def get_current_user(
    credentials: HTTPAuthorizationCredentials = Depends(security),
    db: Session = Depends(get_db)
) -> User:
    """
    Validates the JWT token and returns the current authenticated user.
    Raises 401 if token is missing, invalid, or expired.
    
    Usage in routes:
        def my_protected_route(current_user: User = Depends(get_current_user)):
    """
    token = credentials.credentials  # Extracts the token string from "Bearer <token>"
    
    token_data = decode_access_token(token)
    if token_data is None:
        raise HTTPException(
            status_code=status.HTTP_401_UNAUTHORIZED,
            detail="Invalid or expired token",
            headers={"WWW-Authenticate": "Bearer"},
        )
    
    user = db.query(User).filter(User.id == token_data.user_id).first()
    if user is None:
        raise HTTPException(
            status_code=status.HTTP_401_UNAUTHORIZED,
            detail="User not found"
        )
    
    return user
```

**Why dependency injection?**

```python
# WITHOUT dependency injection — repeated in every route:
@app.get("/transactions")
def get_transactions():
    db = SessionLocal()
    try:
        token = request.headers.get("Authorization").split(" ")[1]
        user_id = decode_token(token)
        user = db.query(User).filter(User.id == user_id).first()
        result = db.query(Transaction).filter(Transaction.user_id == user.id).all()
        return result
    finally:
        db.close()

# WITH dependency injection — clean and DRY:
@router.get("/transactions")
def get_transactions(
    db: Session = Depends(get_db),           # ← Auto-created and closed
    current_user: User = Depends(get_current_user)  # ← Auth validated
):
    return db.query(Transaction).filter(Transaction.user_id == current_user.id).all()
```

---

## 2.7 `main.py` — The FastAPI App Entry Point

```python
# app/main.py

from fastapi import FastAPI
from fastapi.middleware.cors import CORSMiddleware
from app.api.routes import auth, transactions, accounts, categories, analytics

# ─── APP INSTANCE ─────────────────────────────────────────────────────────────
app = FastAPI(
    title="Finance Tracker API",
    description="Track your income and expenses",
    version="1.0.0",
    docs_url="/docs",       # Swagger UI at /docs
    redoc_url="/redoc",     # ReDoc UI at /redoc
)

# ─── CORS MIDDLEWARE ──────────────────────────────────────────────────────────
# Required so the React frontend (running on port 5173) can call the API (port 8000)
app.add_middleware(
    CORSMiddleware,
    allow_origins=["http://localhost:5173", "https://yourfrontend.com"],
    allow_credentials=True,   # Allow cookies
    allow_methods=["*"],      # Allow GET, POST, PATCH, DELETE, etc.
    allow_headers=["*"],      # Allow Authorization, Content-Type, etc.
)

# ─── ROUTERS ─────────────────────────────────────────────────────────────────
# Include each router with a prefix — all auth routes start with /api/auth
app.include_router(auth.router,         prefix="/api/auth",         tags=["Auth"])
app.include_router(transactions.router, prefix="/api/transactions",  tags=["Transactions"])
app.include_router(accounts.router,     prefix="/api/accounts",      tags=["Accounts"])
app.include_router(categories.router,   prefix="/api/categories",    tags=["Categories"])
app.include_router(analytics.router,    prefix="/api/analytics",     tags=["Analytics"])

# ─── HEALTH CHECK ─────────────────────────────────────────────────────────────
@app.get("/api/health", tags=["System"])
def health_check():
    return {"status": "ok", "message": "Finance Tracker API is running"}
```

---

## 2.8 `requirements.txt`

```text
fastapi==0.115.0
uvicorn[standard]==0.30.0
sqlalchemy==2.0.36
alembic==1.13.3
pydantic[email]==2.9.0
pydantic-settings==2.5.2
psycopg2-binary==2.9.9   # PostgreSQL driver for Python
python-jose[cryptography]==3.3.0  # JWT handling
passlib[bcrypt]==1.7.4   # Password hashing
python-multipart==0.0.12  # Required for form data in FastAPI
httpx==0.27.0             # For testing FastAPI with async client
pytest==8.3.3
pytest-asyncio==0.23.8
```

**Install everything:**

```bash
# Create a virtual environment first
python -m venv venv

# Activate it
# Windows:
venv\Scripts\activate
# Mac/Linux:
source venv/bin/activate

# Install all dependencies
pip install -r requirements.txt
```

**Generate requirements.txt from your imports (after coding):**

```bash
pip install pipreqs
pipreqs backend/ --force
# Scans import statements and finds the packages needed
```

---

## 2.9 Running the Backend

```bash
# From the backend/ directory:
cd backend

# Start FastAPI with hot-reload
uvicorn app.main:app --reload --port 8000

# Output:
# INFO:     Uvicorn running on http://127.0.0.1:8000 (Press CTRL+C to quit)
# INFO:     Started reloader process [12345]

# Now visit:
# http://localhost:8000/docs         ← Swagger UI
# http://localhost:8000/api/health   ← Health check
```

---

## 2.10 Step-by-Step: Phase 2 Execution Order

```
1. docker-compose up -d              ← Start Postgres
2. Create virtual environment        ← python -m venv venv
3. pip install -r requirements.txt   ← Install dependencies
4. Create .env from .env.example     ← Fill in DB credentials
5. Write core/config.py              ← Load .env settings
6. Write database.py                 ← Engine + session factory
7. Write app/main.py                 ← Empty FastAPI app with /api/health
8. Run uvicorn → visit /docs         ← Verify it's working
9. Write core/dependencies.py        ← get_db() ready for later
```

At the end of Phase 2: the backend runs, connects to Postgres, and the Swagger docs show at `/docs`. No routes (except health check) yet — but the foundation is solid.

---

*Previous: [01-Phase1-Planning.md](./01-Phase1-Planning.md)*  
*Next: [03-Phase3-Models-and-Schemas.md](./03-Phase3-Models-and-Schemas.md)*
