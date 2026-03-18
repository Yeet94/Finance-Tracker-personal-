# Phase 7: Testing, Polish & Developer Workflow

> **Goal:** Write backend tests with pytest, understand how to use pgAdmin effectively, add error handling polish to the React frontend, and recap the complete development workflow.

---

## 7.1 Backend Testing with pytest

### Test Setup

```bash
# Install test dependencies (should already be in requirements.txt):
pip install pytest pytest-asyncio httpx

# Create test directory:
mkdir backend/tests
touch backend/tests/__init__.py
touch backend/tests/conftest.py
touch backend/tests/test_auth.py
touch backend/tests/test_transactions.py
```

### `conftest.py` — Shared Test Fixtures

A **fixture** is a reusable piece of test setup. `conftest.py` makes fixtures available to all test files in the `tests/` directory automatically.

```python
# backend/tests/conftest.py

import pytest
from fastapi.testclient import TestClient
from sqlalchemy import create_engine
from sqlalchemy.orm import sessionmaker
from app.main import app
from app.database import Base
from app.core.dependencies import get_db

# ─── TEST DATABASE ─────────────────────────────────────────────────────────────
# Use an in-memory SQLite database for tests — fast, no Docker needed
SQLALCHEMY_TEST_DATABASE_URL = "sqlite:///./test.db"

test_engine = create_engine(
    SQLALCHEMY_TEST_DATABASE_URL,
    connect_args={"check_same_thread": False}  # Required for SQLite
)
TestingSessionLocal = sessionmaker(bind=test_engine)

# ─── FIXTURES ─────────────────────────────────────────────────────────────────
@pytest.fixture(scope="function")
def db():
    """Provide a fresh db session per test, rolled back after each test."""
    Base.metadata.create_all(bind=test_engine)  # Create tables
    session = TestingSessionLocal()
    try:
        yield session
    finally:
        session.close()
        Base.metadata.drop_all(bind=test_engine)  # Wipe tables after test

@pytest.fixture(scope="function")
def client(db):
    """FastAPI test client with database dependency overridden to use test db."""
    def override_get_db():
        try:
            yield db
        finally:
            pass

    app.dependency_overrides[get_db] = override_get_db
    with TestClient(app) as c:
        yield c
    app.dependency_overrides.clear()

@pytest.fixture
def test_user(client):
    """Create a test user and return their credentials + token."""
    # Register
    client.post("/api/auth/register", json={
        "email": "test@example.com",
        "password": "testpassword123",
        "name": "Test User"
    })
    # Login
    res = client.post("/api/auth/login", json={
        "email": "test@example.com",
        "password": "testpassword123"
    })
    token = res.json()["access_token"]
    return {"email": "test@example.com", "token": token}
```

### `test_auth.py`

```python
# backend/tests/test_auth.py

def test_register_success(client):
    response = client.post("/api/auth/register", json={
        "email": "new@example.com",
        "password": "password123",
        "name": "New User",
    })
    assert response.status_code == 201
    assert response.json()["email"] == "new@example.com"
    assert "password_hash" not in response.json()  # Never expose this!

def test_register_duplicate_email(client, test_user):
    response = client.post("/api/auth/register", json={
        "email": "test@example.com",  # Already registered in test_user fixture
        "password": "anotherpassword",
    })
    assert response.status_code == 400
    assert "already registered" in response.json()["detail"]

def test_login_success(client, test_user):
    response = client.post("/api/auth/login", json={
        "email": "test@example.com",
        "password": "testpassword123",
    })
    assert response.status_code == 200
    assert "access_token" in response.json()
    assert response.json()["token_type"] == "bearer"

def test_login_wrong_password(client, test_user):
    response = client.post("/api/auth/login", json={
        "email": "test@example.com",
        "password": "wrongpassword",
    })
    assert response.status_code == 401

def test_get_me(client, test_user):
    response = client.get(
        "/api/auth/me",
        headers={"Authorization": f"Bearer {test_user['token']}"}
    )
    assert response.status_code == 200
    assert response.json()["email"] == "test@example.com"

def test_get_me_no_token(client):
    response = client.get("/api/auth/me")
    assert response.status_code == 403  # HTTPBearer returns 403 if no header
```

### `test_transactions.py`

```python
# backend/tests/test_transactions.py

def auth_headers(token: str) -> dict:
    return {"Authorization": f"Bearer {token}"}

def test_create_transaction(client, test_user, db):
    from app.models.account import Account
    from app.models.user import User
    from app.models.category import Category
    
    # Get the user and their default account
    user = db.query(User).filter(User.email == "test@example.com").first()
    account = db.query(Account).filter(Account.user_id == user.id).first()
    category = db.query(Category).first()

    response = client.post(
        "/api/transactions",
        json={
            "account_id": account.id,
            "category_id": category.id,
            "amount": 50.00,
            "type": "expense",
            "note": "Test lunch",
        },
        headers=auth_headers(test_user["token"])
    )
    assert response.status_code == 201
    data = response.json()
    assert data["amount"] == "50.00"
    assert data["type"] == "expense"

def test_cannot_access_other_users_transaction(client, test_user):
    # Create a second user
    client.post("/api/auth/register", json={
        "email": "other@example.com",
        "password": "otherpassword"
    })
    other_login = client.post("/api/auth/login", json={
        "email": "other@example.com",
        "password": "otherpassword"
    })
    other_token = other_login.json()["access_token"]

    # Try to get user1's transaction using user2's token
    response = client.get(
        "/api/transactions/1",  # Assumes transaction ID 1 belongs to user1
        headers=auth_headers(other_token)
    )
    assert response.status_code == 404  # Not found (not 403, which reveals existence)

def test_list_transactions_empty(client, test_user):
    response = client.get(
        "/api/transactions",
        headers=auth_headers(test_user["token"])
    )
    assert response.status_code == 200
    assert response.json() == []
```

### Run Tests

```bash
# From backend/ directory:
pytest tests/ -v                    # Verbose output
pytest tests/ -v -k "test_auth"    # Only auth tests
pytest tests/ --cov=app             # With coverage report (pip install pytest-cov)
```

---

## 7.2 Using pgAdmin Effectively

**Connect pgAdmin to your Docker Postgres:**

1. Open `http://localhost:5050`
2. Right-click "Servers" → Register → Server
3. **General tab:** Name: `Finance Dev`
4. **Connection tab:**
   - Host: `postgres` (Docker service name) or `host.docker.internal` (if pgAdmin isn't in Docker)
   - Port: `5432`
   - Database: `financedb`
   - Username: `financeuser`
   - Password: `financepass`

**Useful pgAdmin query examples:**

```sql
-- See all tables
SELECT table_name FROM information_schema.tables
WHERE table_schema = 'public';

-- View all transactions for a user
SELECT t.id, t.amount, t.type, c.name as category, t.transaction_date
FROM transactions t
LEFT JOIN categories c ON t.category_id = c.id
WHERE t.user_id = 1
ORDER BY t.transaction_date DESC;

-- Sum by category for current month
SELECT c.name, c.icon, SUM(t.amount) as total
FROM transactions t
JOIN categories c ON t.category_id = c.id
WHERE t.user_id = 1
  AND t.type = 'expense'
  AND DATE_TRUNC('month', t.transaction_date) = DATE_TRUNC('month', NOW())
GROUP BY c.id, c.name, c.icon
ORDER BY total DESC;
```

**pgAdmin shortcuts:**
- `F5` — Execute query
- `Ctrl+/` — Comment/uncomment line
- `Explain` tab — See query execution plan (useful for optimization)

---

## 7.3 Frontend Error Handling Polish

### Centralized API Error Handler

```typescript
// src/api/client.ts — enhance the response interceptor

api.interceptors.response.use(
  (response) => response,
  (error) => {
    const status   = error.response?.status;
    const message  = error.response?.data?.detail;

    if (status === 401) {
      localStorage.removeItem("access_token");
      window.location.href = "/login";
    } else if (status === 422) {
      // Pydantic validation error — detail is an array of errors
      const errors = error.response.data.detail;
      const msg = Array.isArray(errors)
        ? errors.map((e: any) => `${e.loc.join(".")}: ${e.msg}`).join(", ")
        : message;
      error.message = msg;
    } else if (status === 404) {
      error.message = "Resource not found";
    } else if (status >= 500) {
      error.message = "Server error — please try again later";
    }

    return Promise.reject(error);
  }
);
```

### Loading Skeleton Component

```tsx
// src/components/Skeleton.tsx

export function Skeleton({ className = "" }: { className?: string }) {
  return (
    <div
      className={`animate-pulse bg-gray-200 rounded-lg ${className}`}
    />
  );
}

// Usage in DashboardPage when loading:
if (loading) {
  return (
    <div className="space-y-4 p-6">
      <Skeleton className="h-24 w-full" />   {/* Summary card skeleton */}
      <Skeleton className="h-16 w-full" />   {/* Transaction row skeleton */}
      <Skeleton className="h-16 w-full" />
      <Skeleton className="h-16 w-full" />
    </div>
  );
}
```

---

## 7.4 The Complete Dev Workflow

### Daily Development Loop

```bash
# Terminal 1 — Start Docker (Postgres)
docker-compose up -d

# Terminal 2 — Start FastAPI backend
cd backend
source venv/bin/activate  # or: venv\Scripts\activate (Windows)
uvicorn app.main:app --reload --port 8000

# Terminal 3 — Start React frontend
cd frontend
npm run dev
# → http://localhost:5173

# Terminal 4 (optional) — Watch test output
cd backend
pytest tests/ -v --watch   # Requires: pip install pytest-watch
```

### Feature Development Checklist (Per Feature)

```
1. DB → Add/update SQLAlchemy model
2. DB → alembic revision --autogenerate -m "Add X column"
3. DB → alembic upgrade head
4. Backend → Update Pydantic schema (input + response)
5. Backend → Write route handler
6. Backend → Test in Swagger UI (/docs)
7. Backend → Write pytest tests
8. Frontend → Update TypeScript types to match
9. Frontend → Add API function to client.ts
10. Frontend → Build the component/page
11. Frontend → Manually test in browser
```

---

## 7.5 Concept Comparison: Project 1 vs Project 2

| Concept | Project 1 (Expo/Supabase) | Project 2 (React/FastAPI) |
|---------|--------------------------|--------------------------|
| **Auth** | Supabase does it for you | You build it (bcrypt + JWT) |
| **DB Security** | Row Level Security (SQL) | `user_id` filter in every query |
| **Migrations** | Drizzle Kit | Alembic |
| **Type Safety** | TypeScript end-to-end (tRPC) | TypeScript + Python (manual sync) |
| **API testing** | tRPC hooks in components | Swagger UI + pytest |
| **Forms** | React Native TextInput | HTML `<input>` + React state |
| **Routing** | File-based (Expo Router) | Component-based (react-router-dom) |
| **State** | React Context + TanStack Query | React Context + `useState` |

**The key insight:** Project 2 forces you to implement things that Project 1's libraries handled automatically. This is intentional — you will truly understand auth, databases, and APIs by building them from scratch.

---

## 7.6 Week-by-Week Build Schedule

| Week | Goal | Deliverable |
|------|------|------------|
| **Week 1** | Backend foundation | Docker+Postgres running, FastAPI `/docs` accessible, Alembic migrations applied |
| **Week 2** | Auth routes | Register, login, JWT working. Tested via Swagger |
| **Week 3** | Transaction CRUD | All 5 endpoints working, tested with pytest |
| **Week 4** | React frontend | Login page, dashboard with transactions, add form |
| **Week 5** | Analytics | Pie chart, bar chart, `/summary` endpoint |
| **Week 6** | Polish | CSV export, error handling, loading states, responsive layout |

---

## 7.7 Useful Resources

| Resource | URL |
|----------|-----|
| FastAPI Docs | https://fastapi.tiangolo.com |
| SQLAlchemy Tutorial | https://docs.sqlalchemy.org/orm/quickstart.html |
| Alembic Tutorial | https://alembic.sqlalchemy.org/en/latest/tutorial.html |
| React Router v6 | https://reactrouter.com/en/main |
| Recharts Docs | https://recharts.org/en-US/examples |
| Tailwind CSS | https://tailwindcss.com/docs |
| dbdiagram.io | https://dbdiagram.io |
| JWT Debugger | https://jwt.io |
| pgAdmin Docs | https://www.pgadmin.org/docs |

---

## 🎓 You've Mapped the Entire Stack!

You now have a complete outline for building this project from scratch. The architecture is:

```
React (Vite)           ← Browser UI
     ↓ HTTP (Axios)
FastAPI (Uvicorn)      ← Python API server
     ↓ SQLAlchemy
PostgreSQL (Docker)    ← Relational database
```

Every layer is **your code** — no magic backends. This is what makes Project 2 the better teacher.

---

*Previous: [06-Phase6-Analytics-and-Export.md](./06-Phase6-Analytics-and-Export.md)*  
*Return to: [00-Project-Overview.md](./00-Project-Overview.md)*
