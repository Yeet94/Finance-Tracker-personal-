# Phase 3: SQLAlchemy Models, Pydantic Schemas & Alembic

> **Goal:** Define your database tables as Python classes (SQLAlchemy models), define input/output validation shapes (Pydantic schemas), and set up Alembic to manage database migrations.

---

## 3.1 SQLAlchemy Models — Python as Your DB Schema

SQLAlchemy models are Python classes that map 1:1 to database tables. Each class attribute becomes a column.

### `models/user.py`

```python
# app/models/user.py

from sqlalchemy import Column, Integer, String, DateTime, func
from app.database import Base

class User(Base):
    __tablename__ = "users"      # The actual SQL table name

    id            = Column(Integer, primary_key=True, index=True)
    email         = Column(String(320), unique=True, nullable=False, index=True)
    password_hash = Column(String(255), nullable=False)
    name          = Column(String(100), nullable=True)
    
    # func.now() = SQL NOW() function — set by the database
    created_at    = Column(DateTime(timezone=True), server_default=func.now())
    updated_at    = Column(DateTime(timezone=True), server_default=func.now(), onupdate=func.now())
    
    # ORM relationship — access user.accounts to get all their accounts
    # lazy="dynamic" = don't load automatically, query on demand
    accounts      = relationship("Account", back_populates="user", cascade="all, delete-orphan")
    transactions  = relationship("Transaction", back_populates="user", cascade="all, delete-orphan")
```

**`server_default=func.now()` vs `default=datetime.utcnow`:**
- `server_default=func.now()` → Postgres sets the value. Consistent, timezone-aware.
- `default=datetime.utcnow` → Python sets the value before INSERT. Can drift if server timezone differs.
- Always prefer `server_default` for timestamps.

**`cascade="all, delete-orphan"`:** If a User is deleted, all their Accounts and Transactions are also deleted automatically. Same as `ON DELETE CASCADE` in SQL.

### `models/account.py`

```python
# app/models/account.py

from sqlalchemy import Column, Integer, String, Boolean, ForeignKey, DateTime, func
from sqlalchemy.orm import relationship
from app.database import Base

class Account(Base):
    __tablename__ = "accounts"

    id         = Column(Integer, primary_key=True, index=True)
    user_id    = Column(Integer, ForeignKey("users.id", ondelete="CASCADE"), nullable=False)
    name       = Column(String(100), nullable=False)
    type       = Column(String(50), default="general")   # "cash", "bank", "credit"
    is_default = Column(Boolean, default=False)
    created_at = Column(DateTime(timezone=True), server_default=func.now())
    updated_at = Column(DateTime(timezone=True), server_default=func.now(), onupdate=func.now())

    # Relationships
    user         = relationship("User", back_populates="accounts")
    transactions = relationship("Transaction", back_populates="account")
```

### `models/category.py`

```python
# app/models/category.py

from sqlalchemy import Column, Integer, String, ForeignKey, DateTime, func
from sqlalchemy.orm import relationship
from app.database import Base

class Category(Base):
    __tablename__ = "categories"

    id         = Column(Integer, primary_key=True, index=True)
    user_id    = Column(Integer, ForeignKey("users.id", ondelete="CASCADE"), nullable=True)
    # ↑ nullable=True: system categories have NULL user_id

    name       = Column(String(100), nullable=False)
    type       = Column(String(10), nullable=False)  # "income" or "expense"
    color      = Column(String(7), default="#6B7280")  # Hex color for charts
    icon       = Column(String(10), default="📦")      # Emoji icon
    created_at = Column(DateTime(timezone=True), server_default=func.now())

    user         = relationship("User", back_populates="categories")
    transactions = relationship("Transaction", back_populates="category")
```

### `models/transaction.py`

```python
# app/models/transaction.py

from sqlalchemy import Column, Integer, String, Numeric, Boolean, Date, ForeignKey, DateTime, func
from sqlalchemy.orm import relationship
from app.database import Base

class Transaction(Base):
    __tablename__ = "transactions"

    id               = Column(Integer, primary_key=True, index=True)
    user_id          = Column(Integer, ForeignKey("users.id", ondelete="CASCADE"), nullable=False)
    account_id       = Column(Integer, ForeignKey("accounts.id", ondelete="SET NULL"), nullable=True)
    category_id      = Column(Integer, ForeignKey("categories.id", ondelete="SET NULL"), nullable=True)

    amount           = Column(Numeric(12, 2), nullable=False)  # DECIMAL(12,2)
    type             = Column(String(10), nullable=False)       # "income" | "expense"
    note             = Column(String, nullable=True)
    transaction_date = Column(Date, nullable=False, index=True)

    is_recurring     = Column(Boolean, default=False)

    created_at  = Column(DateTime(timezone=True), server_default=func.now(), index=True)
    updated_at  = Column(DateTime(timezone=True), server_default=func.now(), onupdate=func.now())

    # Relationships
    user     = relationship("User", back_populates="transactions")
    account  = relationship("Account", back_populates="transactions")
    category = relationship("Category", back_populates="transactions")
```

**`Numeric(12, 2)` vs `Float`:**  
`Numeric` maps to SQL `DECIMAL` — exact decimal storage. Never use `Float` for currency. Same lesson as Project 1, now in Python.

### `models/__init__.py` — Import All Models Here

```python
# app/models/__init__.py
# This lets Alembic discover all models when it imports this package

from app.models.user import User
from app.models.account import Account
from app.models.category import Category
from app.models.transaction import Transaction
```

---

## 3.2 Pydantic Schemas — The API Contract

Schemas are separate from models. Models define the database table. Schemas define what's valid to send/receive via the API.

### `schemas/transaction.py` (Full Version)

```python
# app/schemas/transaction.py

from pydantic import BaseModel, field_validator
from decimal import Decimal
from datetime import date, datetime
from typing import Optional, Literal

TransactionType = Literal["income", "expense"]

# ─── INPUT SCHEMAS (what client sends) ────────────────────────────────────────
class TransactionCreate(BaseModel):
    account_id:        int
    category_id:       int
    amount:            Decimal
    type:              TransactionType
    note:              Optional[str] = None
    transaction_date:  date = date.today()

    @field_validator("amount")
    @classmethod
    def amount_must_be_positive(cls, v: Decimal) -> Decimal:
        if v <= 0:
            raise ValueError("Amount must be greater than 0")
        return v

class TransactionUpdate(BaseModel):
    account_id:        Optional[int] = None
    category_id:       Optional[int] = None
    amount:            Optional[Decimal] = None
    type:              Optional[TransactionType] = None
    note:              Optional[str] = None
    transaction_date:  Optional[date] = None

# ─── OUTPUT SCHEMAS (what API returns) ────────────────────────────────────────
class CategoryInTransaction(BaseModel):
    """Nested category data included in transaction responses"""
    id:    int
    name:  str
    icon:  str
    color: str

    class Config:
        from_attributes = True

class TransactionResponse(BaseModel):
    id:               int
    user_id:          int
    account_id:       Optional[int]
    category_id:      Optional[int]
    category:         Optional[CategoryInTransaction]  # Nested object
    amount:           Decimal
    type:             TransactionType
    note:             Optional[str]
    transaction_date: date
    is_recurring:     bool
    created_at:       datetime
    updated_at:       datetime

    class Config:
        from_attributes = True  # Required to read from SQLAlchemy model objects
```

**`from_attributes = True`** (renamed from `orm_mode = True` in Pydantic v2):  
Allows Pydantic to read data from SQLAlchemy objects. Without this, `TransactionResponse(**transaction_orm_object)` would fail because SQLAlchemy objects aren't plain dicts.

**Nested schemas:** `CategoryInTransaction` is embedded inside `TransactionResponse`. The API returns:
```json
{
  "id": 1,
  "amount": "50.00",
  "category": {
    "id": 3,
    "name": "Food",
    "icon": "🍜",
    "color": "#FF6B6B"
  }
}
```

---

## 3.3 Alembic — Database Migrations

Alembic tracks every change to your database schema over time.

### Initial Setup

```bash
# From the backend/ directory:
cd backend

# Initialize Alembic (creates alembic/ directory and alembic.ini)
alembic init alembic
```

### Configure `alembic/env.py`

Edit `alembic/env.py` to connect to your database and discover your models:

```python
# alembic/env.py (key lines to add/change)

from app.core.config import settings
from app.database import Base  # Your declarative base
import app.models              # Ensures all models are imported → Alembic sees them

# Tell Alembic where the database is
config.set_main_option("sqlalchemy.url", settings.DATABASE_URL)

# Tell Alembic what tables to manage (your Base's metadata)
target_metadata = Base.metadata
```

### `alembic.ini` — One Key Setting

```ini
# alembic.ini
[alembic]
script_location = alembic
# Leave sqlalchemy.url blank — it's set in env.py from settings
sqlalchemy.url =
```

### Creating Your First Migration

```bash
# Auto-generate migration from your models
# Alembic compares current DB state vs your models → generates the diff
alembic revision --autogenerate -m "Initial schema: users, accounts, categories, transactions"

# This creates: alembic/versions/xxxxxxxxxxxx_initial_schema.py
```

**The generated file looks like:**
```python
# alembic/versions/abc123_initial_schema.py

def upgrade() -> None:
    """Apply this migration (forward)"""
    op.create_table("users",
        sa.Column("id", sa.Integer(), primary_key=True),
        sa.Column("email", sa.String(320), unique=True, nullable=False),
        sa.Column("password_hash", sa.String(255), nullable=False),
        # ... etc
    )
    op.create_table("accounts", ...)
    # etc.

def downgrade() -> None:
    """Undo this migration (reverse)"""
    op.drop_table("accounts")
    op.drop_table("users")
```

### Applying Migrations

```bash
# Apply all pending migrations to the database
alembic upgrade head

# Check current version
alembic current

# See migration history
alembic history

# Roll back one migration
alembic downgrade -1
```

### Adding a New Column Later

```bash
# After adding a column to your SQLAlchemy model:
alembic revision --autogenerate -m "Add description column to accounts"
alembic upgrade head
```

**The Golden Rule:** Never modify the database directly in production. Always use Alembic migrations. This ensures every environment (local, staging, production) has the same schema.

---

## 3.4 Seeding Default Categories

After running your first migration, seed the database with default categories:

```python
# scripts/seed_categories.py

from app.database import SessionLocal
from app.models.category import Category

DEFAULT_CATEGORIES = [
    # Expense categories
    {"name": "Food",       "type": "expense", "icon": "🍜", "color": "#EF4444"},
    {"name": "Transport",  "type": "expense", "icon": "🚇", "color": "#F59E0B"},
    {"name": "Shopping",   "type": "expense", "icon": "🛍️", "color": "#8B5CF6"},
    {"name": "Bills",      "type": "expense", "icon": "📄", "color": "#6366F1"},
    {"name": "Groceries",  "type": "expense", "icon": "🛒", "color": "#22C55E"},
    {"name": "Utilities",  "type": "expense", "icon": "💡", "color": "#0EA5E9"},
    {"name": "Healthcare", "type": "expense", "icon": "🏥", "color": "#EC4899"},
    {"name": "Others",     "type": "expense", "icon": "📦", "color": "#6B7280"},
    # Income categories
    {"name": "Salary",     "type": "income",  "icon": "💰", "color": "#22C55E"},
    {"name": "Allowance",  "type": "income",  "icon": "💵", "color": "#10B981"},
    {"name": "Investment", "type": "income",  "icon": "📈", "color": "#3B82F6"},
    {"name": "Gift",       "type": "income",  "icon": "🎁", "color": "#F97316"},
]

def seed():
    db = SessionLocal()
    try:
        # Only seed if empty
        if db.query(Category).filter(Category.user_id == None).count() == 0:
            for cat_data in DEFAULT_CATEGORIES:
                cat = Category(**cat_data, user_id=None)  # None = system category
                db.add(cat)
            db.commit()
            print(f"Seeded {len(DEFAULT_CATEGORIES)} default categories")
        else:
            print("Categories already seeded, skipping")
    finally:
        db.close()

if __name__ == "__main__":
    seed()
```

Run with: `python scripts/seed_categories.py`

---

## 3.5 Phase 3 Execution Order

```
1. Write models/ (User, Account, Category, Transaction)
2. Write models/__init__.py (import all models)
3. Configure alembic/env.py (connect to DB, point to Base.metadata)
4. alembic revision --autogenerate -m "Initial schema"
5. Review generated migration file — check it looks sane
6. alembic upgrade head
7. Verify tables in pgAdmin
8. Run seed script
9. Write schemas/ (UserCreate, UserResponse, TransactionCreate, etc.)
```

---

*Previous: [02-Phase2-Backend-Foundation.md](./02-Phase2-Backend-Foundation.md)*  
*Next: [04-Phase4-API-Routes.md](./04-Phase4-API-Routes.md)*
