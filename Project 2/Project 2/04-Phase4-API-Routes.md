# Phase 4: API Routes & JWT Authentication

> **Goal:** Implement all FastAPI endpoints — auth (register/login/me), full CRUD for transactions, accounts, and categories. Wire up JWT so every protected route requires authentication.

---

## 4.1 `core/security.py` — Passwords + JWT

```python
# app/core/security.py

from datetime import datetime, timedelta, timezone
from typing import Optional
from jose import JWTError, jwt
from passlib.context import CryptContext
from app.core.config import settings
from app.schemas.auth import TokenData

# ─── PASSWORD HASHING ─────────────────────────────────────────────────────────
# CryptContext wraps bcrypt — the industry standard for password hashing
pwd_context = CryptContext(schemes=["bcrypt"], deprecated="auto")

def hash_password(password: str) -> str:
    """Hash a plain-text password. Call this at registration."""
    return pwd_context.hash(password)

def verify_password(plain_password: str, hashed_password: str) -> bool:
    """Check if a plain-text password matches the hash. Call this at login."""
    return pwd_context.verify(plain_password, hashed_password)


# ─── JWT TOKENS ──────────────────────────────────────────────────────────────
def create_access_token(user_id: int) -> str:
    """
    Create a JWT token for the given user_id.
    The token encodes: who (user_id), when it expires (exp).
    """
    expire = datetime.now(timezone.utc) + timedelta(
        minutes=settings.ACCESS_TOKEN_EXPIRE_MINUTES
    )
    payload = {
        "sub": str(user_id),   # Subject — the user this token belongs to
        "exp": expire,          # Expiry — after this, token is invalid
        "iat": datetime.now(timezone.utc),  # Issued-at timestamp
    }
    return jwt.encode(payload, settings.SECRET_KEY, algorithm=settings.ALGORITHM)


def decode_access_token(token: str) -> Optional[TokenData]:
    """
    Decode and validate a JWT token.
    Returns TokenData(user_id=...) if valid, None if invalid/expired.
    """
    try:
        payload = jwt.decode(token, settings.SECRET_KEY, algorithms=[settings.ALGORITHM])
        user_id_str: str = payload.get("sub")
        if user_id_str is None:
            return None
        return TokenData(user_id=int(user_id_str))
    except JWTError:
        # Invalid signature, expired token, malformed token → return None
        return None
```

**Why bcrypt?**  
bcrypt is intentionally slow (configurable "cost factor"). This makes brute-force attacks computationally expensive. MD5 and SHA-256 are fast — attackers can try billions per second. bcrypt limits to thousands.

---

## 4.2 Auth Routes

```python
# app/api/routes/auth.py

from fastapi import APIRouter, Depends, HTTPException, status
from sqlalchemy.orm import Session
from app.core.dependencies import get_db, get_current_user
from app.core.security import hash_password, verify_password, create_access_token
from app.models.user import User
from app.models.account import Account
from app.schemas.user import UserCreate, UserResponse
from app.schemas.auth import Token

router = APIRouter()

# ─── POST /api/auth/register ──────────────────────────────────────────────────
@router.post("/register", response_model=UserResponse, status_code=status.HTTP_201_CREATED)
def register(user_data: UserCreate, db: Session = Depends(get_db)):
    # Check if email already exists
    existing = db.query(User).filter(User.email == user_data.email).first()
    if existing:
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail="Email already registered"
        )
    
    # Create the user
    new_user = User(
        email=user_data.email,
        password_hash=hash_password(user_data.password),
        name=user_data.name,
    )
    db.add(new_user)
    db.flush()  # Gets the new_user.id without committing yet
    
    # Create a default "Main Account" for the new user
    default_account = Account(
        user_id=new_user.id,
        name="Main Account",
        type="general",
        is_default=True,
    )
    db.add(default_account)
    db.commit()
    db.refresh(new_user)
    
    return new_user


# ─── POST /api/auth/login ─────────────────────────────────────────────────────
@router.post("/login", response_model=Token)
def login(credentials: UserLogin, db: Session = Depends(get_db)):
    user = db.query(User).filter(User.email == credentials.email).first()
    
    # Important: don't reveal whether email or password was wrong
    # "Invalid credentials" is intentionally vague for security
    if not user or not verify_password(credentials.password, user.password_hash):
        raise HTTPException(
            status_code=status.HTTP_401_UNAUTHORIZED,
            detail="Invalid credentials",
            headers={"WWW-Authenticate": "Bearer"},
        )
    
    token = create_access_token(user_id=user.id)
    return {"access_token": token, "token_type": "bearer"}


# ─── GET /api/auth/me ─────────────────────────────────────────────────────────
@router.get("/me", response_model=UserResponse)
def get_me(current_user: User = Depends(get_current_user)):
    # current_user is automatically injected by the dependency
    return current_user
```

**`db.flush()` vs `db.commit()`:**
- `flush()`: Sends SQL to the database but doesn't finalize — lets you get the generated `id` without fully committing
- `commit()`: Finalizes all pending operations — data is permanently saved

---

## 4.3 Transaction Routes (Full CRUD)

```python
# app/api/routes/transactions.py

from fastapi import APIRouter, Depends, HTTPException, Query, status
from sqlalchemy.orm import Session, joinedload
from typing import Optional, List
from datetime import date
from app.core.dependencies import get_db, get_current_user
from app.models.user import User
from app.models.transaction import Transaction
from app.schemas.transaction import TransactionCreate, TransactionUpdate, TransactionResponse

router = APIRouter()

# ─── GET /api/transactions ─────────────────────────────────────────────────────
@router.get("/", response_model=List[TransactionResponse])
def list_transactions(
    db: Session = Depends(get_db),
    current_user: User = Depends(get_current_user),
    # Optional query parameters for filtering:
    account_id:  Optional[int] = Query(None),
    category_id: Optional[int] = Query(None),
    type:        Optional[str] = Query(None),  # "income" or "expense"
    start_date:  Optional[date] = Query(None),
    end_date:    Optional[date] = Query(None),
    limit:       int = Query(50, le=200),       # Max 200 per request
    offset:      int = Query(0),                # For pagination
):
    query = (
        db.query(Transaction)
        .options(joinedload(Transaction.category))  # Eager load category → avoids N+1 queries
        .filter(Transaction.user_id == current_user.id)
    )
    
    # Apply optional filters
    if account_id:  query = query.filter(Transaction.account_id == account_id)
    if category_id: query = query.filter(Transaction.category_id == category_id)
    if type:        query = query.filter(Transaction.type == type)
    if start_date:  query = query.filter(Transaction.transaction_date >= start_date)
    if end_date:    query = query.filter(Transaction.transaction_date <= end_date)
    
    return query.order_by(Transaction.transaction_date.desc()).offset(offset).limit(limit).all()


# ─── POST /api/transactions ────────────────────────────────────────────────────
@router.post("/", response_model=TransactionResponse, status_code=status.HTTP_201_CREATED)
def create_transaction(
    body: TransactionCreate,
    db: Session = Depends(get_db),
    current_user: User = Depends(get_current_user),
):
    # Validate that the account belongs to the current user
    from app.models.account import Account
    account = db.query(Account).filter(
        Account.id == body.account_id,
        Account.user_id == current_user.id
    ).first()
    if not account:
        raise HTTPException(status_code=404, detail="Account not found")
    
    transaction = Transaction(
        user_id=current_user.id,
        **body.model_dump()  # Unpacks all Pydantic fields as keyword args
    )
    db.add(transaction)
    db.commit()
    db.refresh(transaction)
    return transaction


# ─── GET /api/transactions/{id} ────────────────────────────────────────────────
@router.get("/{transaction_id}", response_model=TransactionResponse)
def get_transaction(
    transaction_id: int,
    db: Session = Depends(get_db),
    current_user: User = Depends(get_current_user),
):
    transaction = db.query(Transaction).filter(
        Transaction.id == transaction_id,
        Transaction.user_id == current_user.id  # Ownership check!
    ).first()
    
    if not transaction:
        raise HTTPException(status_code=404, detail="Transaction not found")
    return transaction


# ─── PATCH /api/transactions/{id} ─────────────────────────────────────────────
@router.patch("/{transaction_id}", response_model=TransactionResponse)
def update_transaction(
    transaction_id: int,
    body: TransactionUpdate,
    db: Session = Depends(get_db),
    current_user: User = Depends(get_current_user),
):
    transaction = db.query(Transaction).filter(
        Transaction.id == transaction_id,
        Transaction.user_id == current_user.id
    ).first()
    if not transaction:
        raise HTTPException(status_code=404, detail="Transaction not found")
    
    # Only update fields that were explicitly provided (exclude_unset=True)
    update_data = body.model_dump(exclude_unset=True)
    for field, value in update_data.items():
        setattr(transaction, field, value)
    
    db.commit()
    db.refresh(transaction)
    return transaction


# ─── DELETE /api/transactions/{id} ────────────────────────────────────────────
@router.delete("/{transaction_id}", status_code=status.HTTP_204_NO_CONTENT)
def delete_transaction(
    transaction_id: int,
    db: Session = Depends(get_db),
    current_user: User = Depends(get_current_user),
):
    transaction = db.query(Transaction).filter(
        Transaction.id == transaction_id,
        Transaction.user_id == current_user.id
    ).first()
    if not transaction:
        raise HTTPException(status_code=404, detail="Transaction not found")
    
    db.delete(transaction)
    db.commit()
    # 204 No Content — return nothing after successful deletion
```

**`exclude_unset=True`** on PATCH: Only updates fields the client explicitly sent. If the client sends `{"note": "Coffee"}`, only `note` is changed — `amount`, `category_id`, etc. stay the same.

**`joinedload(Transaction.category)`** — The N+1 Problem:  
Without this, SQLAlchemy makes 1 query to get 50 transactions, then 50 MORE queries (one per transaction) to get each category. With `joinedload`, it does a SQL JOIN — 1 query total.

---

## 4.4 Analytics Routes

```python
# app/api/routes/analytics.py

from fastapi import APIRouter, Depends, Query
from sqlalchemy.orm import Session
from sqlalchemy import func, case
from typing import Optional
from datetime import date
from app.core.dependencies import get_db, get_current_user
from app.models.transaction import Transaction
from app.models.category import Category

router = APIRouter()

@router.get("/summary")
def get_summary(
    db: Session = Depends(get_db),
    current_user=Depends(get_current_user),
    start_date: Optional[date] = Query(None),
    end_date:   Optional[date] = Query(None),
):
    """Returns total income, total expense, and net balance for the period."""
    query = db.query(
        # SUM of income amounts
        func.sum(
            case((Transaction.type == "income", Transaction.amount), else_=0)
        ).label("total_income"),
        # SUM of expense amounts
        func.sum(
            case((Transaction.type == "expense", Transaction.amount), else_=0)
        ).label("total_expense"),
    ).filter(Transaction.user_id == current_user.id)

    if start_date: query = query.filter(Transaction.transaction_date >= start_date)
    if end_date:   query = query.filter(Transaction.transaction_date <= end_date)

    result = query.one()
    income  = float(result.total_income  or 0)
    expense = float(result.total_expense or 0)

    return {
        "total_income":  income,
        "total_expense": expense,
        "net_balance":   income - expense,
    }


@router.get("/by-category")
def get_by_category(
    db: Session = Depends(get_db),
    current_user=Depends(get_current_user),
    type:       str = Query("expense"),   # Default to expense breakdown
    start_date: Optional[date] = Query(None),
    end_date:   Optional[date] = Query(None),
):
    """Returns spending grouped by category — used for the pie chart."""
    query = (
        db.query(
            Category.name,
            Category.color,
            Category.icon,
            func.sum(Transaction.amount).label("total"),
        )
        .join(Transaction, Transaction.category_id == Category.id)
        .filter(
            Transaction.user_id == current_user.id,
            Transaction.type == type,
        )
        .group_by(Category.id, Category.name, Category.color, Category.icon)
        .order_by(func.sum(Transaction.amount).desc())
    )

    if start_date: query = query.filter(Transaction.transaction_date >= start_date)
    if end_date:   query = query.filter(Transaction.transaction_date <= end_date)

    results = query.all()
    return [
        {"name": r.name, "color": r.color, "icon": r.icon, "total": float(r.total)}
        for r in results
    ]
```

**SQLAlchemy `func`** maps Python to SQL aggregate functions:
- `func.sum(column)` → SQL `SUM(column)`
- `func.count(column)` → SQL `COUNT(column)`
- `func.avg(column)` → SQL `AVG(column)`

---

## 4.5 Testing with Swagger UI

FastAPI auto-generates Swagger UI at `http://localhost:8000/docs`. Test your endpoints here:

**Order to test:**
1. `POST /api/auth/register` → Create a user
2. `POST /api/auth/login` → Get a JWT token
3. Click **"Authorize"** (lock icon top right) → paste `<token>` (without `Bearer `)
4. `GET /api/auth/me` → Verify auth works
5. `POST /api/transactions` → Add a transaction
6. `GET /api/transactions` → List all
7. `GET /api/analytics/summary` → Check totals

---

## 4.6 HTTP Status Codes Reference

| Code | Meaning | When to Use |
|------|---------|-------------|
| `200 OK` | Success | Default GET, PATCH |
| `201 Created` | Resource created | POST that creates something |
| `204 No Content` | Success, no body | DELETE |
| `400 Bad Request` | Client sent bad data | Validation failed |
| `401 Unauthorized` | Not authenticated | Missing or invalid token |
| `403 Forbidden` | Authenticated but not allowed | Trying to access another user's data |
| `404 Not Found` | Resource doesn't exist | Wrong ID |
| `422 Unprocessable Entity` | Schema validation failed | Pydantic catches this automatically |
| `500 Internal Server Error` | Bug in your code | Should never happen in production |

---

*Previous: [03-Phase3-Models-and-Schemas.md](./03-Phase3-Models-and-Schemas.md)*  
*Next: [05-Phase5-Frontend-React.md](./05-Phase5-Frontend-React.md)*
