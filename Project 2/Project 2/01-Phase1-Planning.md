# Phase 1: Planning & MVP Definition

> Before writing any code, define what you're building, design the database schema, and document every API endpoint. This is your spec sheet.

---

## 1.1 MVP Feature List

### ✅ Must Have — v1.0

| # | Feature | Why It's Core |
|---|---------|--------------|
| 1 | **User Registration & Login** | Without auth, all data is public |
| 2 | **Add Transaction** | The single most important action in the app |
| 3 | **List All Transactions** | Must see what was entered |
| 4 | **Delete Transaction** | Mistakes happen |
| 5 | **Total Summary** | Income vs Expense vs Net Balance |

### ⬜ Should Have — v1.1

| # | Feature |
|---|---------|
| 6 | Edit/Update a transaction |
| 7 | Filter by category |
| 8 | Filter by date range (this week/month/year) |
| 9 | Pie chart — spending by category |
| 10 | Multiple accounts (cash, bank, credit card) |

### 💡 Could Have — v2.0

| # | Feature |
|---|---------|
| 11 | Recurring transactions |
| 12 | Budget limits per category |
| 13 | Export to CSV |
| 14 | Dark mode |
| 15 | Email OTP / OAuth login |

### ❌ Won't Have (This Project)

- Mobile app (Project 1 is the mobile app)
- Bank API integration
- Investment/portfolio tracking

---

## 1.2 Database Schema Design

Design this on **[dbdiagram.io](https://dbdiagram.io)** before writing any code.

### Table: `users`

```
users
─────────────────────────────────────────────────
id            SERIAL PRIMARY KEY
email         VARCHAR(320) UNIQUE NOT NULL
password_hash VARCHAR(255) NOT NULL
name          VARCHAR(100)
created_at    TIMESTAMPTZ DEFAULT NOW()
updated_at    TIMESTAMPTZ DEFAULT NOW()
```

> No plain-text passwords ever. `password_hash` stores the result of `bcrypt.hash(password)`.

### Table: `accounts`

```
accounts
─────────────────────────────────────────────────
id            SERIAL PRIMARY KEY
user_id       INTEGER NOT NULL → FK users.id (CASCADE DELETE)
name          VARCHAR(100) NOT NULL   -- "Main Wallet", "DBS Account"
type          VARCHAR(50)             -- "cash", "bank", "credit"
is_default    BOOLEAN DEFAULT FALSE
created_at    TIMESTAMPTZ DEFAULT NOW()
updated_at    TIMESTAMPTZ DEFAULT NOW()
```

### Table: `categories`

```
categories
─────────────────────────────────────────────────
id            SERIAL PRIMARY KEY
user_id       INTEGER → FK users.id (CASCADE DELETE)  -- NULL = system default
name          VARCHAR(100) NOT NULL    -- "Food", "Transport", "Salary"
type          VARCHAR(10)              -- "expense" | "income"
color         VARCHAR(7)              -- "#FF6B6B" (hex for charts)
icon          VARCHAR(10)             -- "🍜"
created_at    TIMESTAMPTZ DEFAULT NOW()
```

> `user_id = NULL` means it's a **system category** (visible to all users). `user_id = 5` means it's a **custom category** created by user 5 only.

### Table: `transactions`

```
transactions
─────────────────────────────────────────────────
id                 SERIAL PRIMARY KEY
user_id            INTEGER NOT NULL → FK users.id (CASCADE DELETE)
account_id         INTEGER → FK accounts.id (SET NULL)
category_id        INTEGER → FK categories.id (SET NULL)

amount             DECIMAL(12, 2) NOT NULL     -- Always positive
type               VARCHAR(10) NOT NULL        -- "income" | "expense"
note               TEXT
transaction_date   DATE NOT NULL DEFAULT CURRENT_DATE

is_recurring       BOOLEAN DEFAULT FALSE
recurring_id       INTEGER → FK recurring_transactions.id (SET NULL)

created_at         TIMESTAMPTZ DEFAULT NOW()
updated_at         TIMESTAMPTZ DEFAULT NOW()
```

> `amount` is always stored as a **positive number**. The `type` field determines if it's income or expense. This prevents confusion with negative numbers.

### Table: `recurring_transactions` *(v1.1)*

```
recurring_transactions
─────────────────────────────────────────────────
id             SERIAL PRIMARY KEY
user_id        INTEGER NOT NULL → FK users.id
account_id     INTEGER → FK accounts.id
category_id    INTEGER → FK categories.id
amount         DECIMAL(12, 2) NOT NULL
type           VARCHAR(10) NOT NULL
note           TEXT
frequency      VARCHAR(20)    -- "daily" | "weekly" | "monthly" | "yearly"
start_date     DATE NOT NULL
next_run_date  DATE NOT NULL
is_active      BOOLEAN DEFAULT TRUE
created_at     TIMESTAMPTZ DEFAULT NOW()
```

### ER Diagram (dbdiagram.io Syntax)

Paste this into dbdiagram.io to visualize the relationships:

```
Table users {
  id serial [pk]
  email varchar(320) [unique, not null]
  password_hash varchar(255) [not null]
  name varchar(100)
  created_at timestamptz
  updated_at timestamptz
}

Table accounts {
  id serial [pk]
  user_id integer [ref: > users.id]
  name varchar(100) [not null]
  type varchar(50)
  is_default boolean
  created_at timestamptz
}

Table categories {
  id serial [pk]
  user_id integer [ref: > users.id]
  name varchar(100) [not null]
  type varchar(10) [not null]
  color varchar(7)
  icon varchar(10)
}

Table transactions {
  id serial [pk]
  user_id integer [ref: > users.id]
  account_id integer [ref: > accounts.id]
  category_id integer [ref: > categories.id]
  amount decimal(12,2) [not null]
  type varchar(10) [not null]
  note text
  transaction_date date [not null]
  is_recurring boolean
  created_at timestamptz
  updated_at timestamptz
}
```

---

## 1.3 API Endpoint Design

### Convention: REST API

| Method | Pattern | Action |
|--------|---------|--------|
| `GET` | `/resource` | List all |
| `POST` | `/resource` | Create one |
| `GET` | `/resource/{id}` | Get one |
| `PATCH` | `/resource/{id}` | Update one (partial) |
| `DELETE` | `/resource/{id}` | Delete one |

### Full Endpoint Map

**Authentication** — `/api/auth/`

| Method | Path | Description | Auth Required |
|--------|------|-------------|:---:|
| `POST` | `/api/auth/register` | Create new user | ❌ |
| `POST` | `/api/auth/login` | Returns JWT token | ❌ |
| `GET` | `/api/auth/me` | Get current user profile | ✅ |

**Transactions** — `/api/transactions/`

| Method | Path | Description | Auth Required |
|--------|------|-------------|:---:|
| `GET` | `/api/transactions` | List (supports `?period=month&category=Food`) | ✅ |
| `POST` | `/api/transactions` | Create new transaction | ✅ |
| `GET` | `/api/transactions/{id}` | Get single transaction | ✅ |
| `PATCH` | `/api/transactions/{id}` | Update transaction | ✅ |
| `DELETE` | `/api/transactions/{id}` | Delete transaction | ✅ |

**Analytics** — `/api/analytics/`

| Method | Path | Description | Auth Required |
|--------|------|-------------|:---:|
| `GET` | `/api/analytics/summary` | Income, expenses, net balance for period | ✅ |
| `GET` | `/api/analytics/by-category` | Spending grouped by category | ✅ |
| `GET` | `/api/analytics/monthly-trend` | Month-by-month totals (for bar chart) | ✅ |

**Accounts** — `/api/accounts/`

| Method | Path | Description | Auth Required |
|--------|------|-------------|:---:|
| `GET` | `/api/accounts` | List all accounts for user | ✅ |
| `POST` | `/api/accounts` | Create account | ✅ |
| `PATCH` | `/api/accounts/{id}` | Update account | ✅ |
| `DELETE` | `/api/accounts/{id}` | Delete account | ✅ |

**Categories** — `/api/categories/`

| Method | Path | Description | Auth Required |
|--------|------|-------------|:---:|
| `GET` | `/api/categories` | List system + user categories | ✅ |
| `POST` | `/api/categories` | Create custom category | ✅ |
| `DELETE` | `/api/categories/{id}` | Delete custom category | ✅ |

---

## 1.4 Pydantic Schemas — The API Contract

Before building routes, define what data looks like going in and out. These are your Pydantic schemas. They live in `backend/app/schemas/`.

### `schemas/user.py`

```python
from pydantic import BaseModel, EmailStr
from datetime import datetime

# What the client sends to REGISTER
class UserCreate(BaseModel):
    email: EmailStr          # Validates email format automatically
    password: str
    name: str | None = None  # Optional

# What the client sends to LOGIN
class UserLogin(BaseModel):
    email: EmailStr
    password: str

# What the API RETURNS (never include password_hash!)
class UserResponse(BaseModel):
    id: int
    email: str
    name: str | None
    created_at: datetime

    class Config:
        from_attributes = True  # Allows reading from SQLAlchemy objects
```

### `schemas/transaction.py`

```python
from pydantic import BaseModel, condecimal
from datetime import date, datetime
from typing import Literal, Optional
from decimal import Decimal

TransactionType = Literal["income", "expense"]

# What the client sends to CREATE a transaction
class TransactionCreate(BaseModel):
    account_id: int
    category_id: int
    amount: Decimal            # Exact decimal, not float!
    type: TransactionType
    note: Optional[str] = None
    transaction_date: date = date.today()

# What the client sends to UPDATE (all optional = partial update)
class TransactionUpdate(BaseModel):
    account_id: Optional[int] = None
    category_id: Optional[int] = None
    amount: Optional[Decimal] = None
    type: Optional[TransactionType] = None
    note: Optional[str] = None
    transaction_date: Optional[date] = None

# What the API RETURNS
class TransactionResponse(BaseModel):
    id: int
    user_id: int
    account_id: Optional[int]
    category_id: Optional[int]
    amount: Decimal
    type: TransactionType
    note: Optional[str]
    transaction_date: date
    created_at: datetime
    updated_at: datetime

    class Config:
        from_attributes = True
```

### `schemas/auth.py`

```python
from pydantic import BaseModel

# What the login endpoint returns
class Token(BaseModel):
    access_token: str
    token_type: str = "bearer"   # JWT convention

# The data encoded inside the JWT
class TokenData(BaseModel):
    user_id: int
```

---

## 1.5 JWT Authentication Design

```
Login Flow:
──────────
1. Client sends POST /api/auth/login { email, password }
2. FastAPI looks up user by email
3. FastAPI verifies: bcrypt.checkpw(password, user.password_hash)
4. FastAPI creates JWT: { "sub": str(user_id), "exp": now + 30 days }
5. FastAPI returns: { "access_token": "eyJ...", "token_type": "bearer" }
6. Client stores token in localStorage (or httpOnly cookie for security)

Subsequent Requests:
────────────────────
1. Client includes header: Authorization: Bearer eyJ...
2. FastAPI middleware decodes JWT → extracts user_id
3. FastAPI fetches user from DB using user_id
4. Route function receives current_user as a dependency
```

JWT structure (HS256):
```
Header.Payload.Signature

Payload = {
  "sub": "42",                        // subject = user_id as string
  "exp": 1753000000,                  // expiry timestamp
  "iat": 1750000000,                  // issued-at timestamp
}
```

The **secret key** (stored in `.env` as `SECRET_KEY`) is used to sign and verify the token. Anyone with the secret key can create valid tokens — never expose it.

---

## 1.6 Planning Checklist

Before moving to Phase 2, complete all of these:

- [x] Draw the ER diagram on dbdiagram.io (copy the syntax from 1.3 above)
- [ ] Write the Pydantic schemas on paper / in a doc
- [ ] Map every API endpoint with its method, path, and expected input/output
- [ ] Decide: start with `SERIAL` (auto-increment integer) primary keys for simplicity (vs UUID)
- [ ] Create a GitHub repository for the project

---

*Previous: [00-Project-Overview.md](./00-Project-Overview.md)*  
*Next: [02-Phase2-Backend-Foundation.md](./02-Phase2-Backend-Foundation.md)*
