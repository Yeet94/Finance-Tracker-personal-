# 📁 Project 2 — Finance Tracker MVP (React + FastAPI + PostgreSQL + Docker)

> This is a **greenfield project** — built from scratch using Python on the backend and React on the frontend. The architecture is deliberately simpler and more "textbook" than Project 1 (the Expo app), making it the ideal learning vehicle for full-stack web development fundamentals.

---

## 📁 File Index

| File | What It Covers |
|------|---------------|
| `00-Project-Overview.md` | **This file** — tech stack rationale, mental model, comparison to Project 1 |
| `01-Phase1-Planning.md` | MVP definition, DB schema, API contract (FastAPI + Pydantic) |
| `02-Phase2-Backend-Foundation.md` | Docker + Postgres, project structure, config, DB connection |
| `03-Phase3-Models-and-Schemas.md` | SQLAlchemy models, Pydantic schemas, Alembic migrations |
| `04-Phase4-API-Routes.md` | FastAPI routes (CRUD), auth middleware, JWT implementation |
| `05-Phase5-Frontend-React.md` | Vite setup, Axios, React components, state management |
| `06-Phase6-Analytics-and-Export.md` | Recharts/Chart.js, CSV export, aggregation endpoints |
| `07-Phase7-Testing-and-Polish.md` | pytest, Jest, pgAdmin tips, Swagger testing |

---

## 🧠 Mental Model: How This Stack Differs from Project 1

| Concern | Project 1 (Expo App) | Project 2 (This Project) |
|---------|---------------------|--------------------------|
| **Frontend** | React Native (Expo) | React (web browser) |
| **Backend** | Supabase (BaaS) + Express/tRPC | FastAPI (Python) — YOU write the backend |
| **Database** | Supabase PostgreSQL (managed) | PostgreSQL via Docker (self-hosted) |
| **Auth** | Supabase Auth (built-in) | JWT from scratch via FastAPI |
| **ORM** | Drizzle (TypeScript) | SQLAlchemy (Python) |
| **Migrations** | Drizzle Kit | Alembic |
| **API Design** | tRPC (type-safe, no REST) | REST (explicit HTTP routes) |
| **Styling** | NativeWind (Tailwind for RN) | Tailwind CSS or CSS Modules |
| **Platform** | iOS + Android + Web | Web only |

**The key shift:** In Project 1, Supabase handled auth, database, and security (RLS). In Project 2, **you build all of that yourself** in Python. This is harder — but you will understand EXACTLY what's happening at every layer.

---

## 🛠️ Full Tech Stack Explained

### Frontend

#### React (via Vite)
- **React** is a UI library for building component-based interfaces in JavaScript
- **Vite** is the build tool/dev server — it starts in milliseconds (unlike Create React App)
- Every UI element is a React component: `<TransactionList />`, `<LoginForm />`, etc.

#### Axios (HTTP Client)
- Makes API calls from React to your FastAPI backend
- `axios.get('/api/transactions')` → returns your data as JSON
- Handles request headers (auth tokens), error interception, base URL config

#### Tailwind CSS
- Utility-first CSS framework — same concept as NativeWind but for real browsers
- `className="flex justify-between p-4 bg-white rounded-lg"` → pure CSS output
- No CSS-in-JS overhead

#### React Context API (or Redux for larger state)
- **React Context:** Built into React. Good for auth state, theme, current user
- **Redux:** External library for complex state with many actions. For a simple MVP, Context is enough.

---

### Backend

#### FastAPI (Python)
- A modern, high-performance Python web framework
- Auto-generates Swagger docs at `/docs` — interactive API testing in the browser
- Based on Python type hints → Pydantic automatically validates requests
- **ASGI** (Async Server Gateway Interface) — supports async/await for non-blocking I/O

#### Pydantic (Data Validation)
- Defines what valid request/response data looks like using Python classes
- Enforces types at runtime: if you send a string where a float is expected → 422 error automatically
- Used for: request bodies, response shapes, environment variable loading

#### SQLAlchemy (ORM)
- Python's most popular ORM — write Python classes that map to database tables
- Execute queries using Python instead of raw SQL
- Handles connection pooling, transactions, and relationships between tables

#### Alembic (Migrations)
- Version control for your database schema
- Every schema change (add column, create table) becomes a migration file
- `alembic upgrade head` applies all migrations in order
- Never lose data when changing your schema in production

#### Uvicorn (ASGI Server)
- Runs your FastAPI app in production
- Like `gunicorn` but for async Python (ASGI)
- `uvicorn app.main:app --reload` — `--reload` is hot-reload for development

---

### Infrastructure

#### Docker (PostgreSQL)
- Runs a PostgreSQL database in an isolated container
- `docker-compose up` → Postgres is running locally, no installation needed
- On your team/deployment server, Docker ensures the exact same environment

#### pgAdmin (Database GUI)
- Visual interface for exploring your PostgreSQL database
- Equivalent to the Supabase Dashboard's Table Editor
- Can run as another Docker container in your `docker-compose.yml`

---

## 🔁 The Request Lifecycle

Understanding how a request flows through this stack is the most important mental model:

```
User clicks "Add Transaction" in React
│
├─ 1. React calls axios.post('/api/transactions', { amount: 50, category: 'Food' })
│
├─ 2. Axios adds Authorization header: "Bearer <jwt-token>"
│
├─ 3. Request hits FastAPI (Uvicorn receives it)
│
├─ 4. FastAPI middleware validates the JWT → extracts user_id
│
├─ 5. Route function receives validated Pydantic model:
│     TransactionCreate(amount=50.0, category="Food", type="expense")
│
├─ 6. Route calls the service/CRUD function
│
├─ 7. SQLAlchemy generates SQL:
│     INSERT INTO transactions (user_id, amount, category, type)
│     VALUES (1, 50.00, 'Food', 'expense')
│
├─ 8. PostgreSQL executes the query, returns the new row
│
├─ 9. SQLAlchemy maps the row to a Python object (Transaction model)
│
├─ 10. Pydantic serializes the Python object to JSON
│
└─ 11. React receives the response → updates state → re-renders list
```

---

## 🗺️ Learning Path

```
Phase 1: Plan (1 day)
  → Define MVP, draw DB schema on dbdiagram.io, design API routes

Phase 2: Backend Foundation (2-3 days)
  → Docker + Postgres, FastAPI skeleton, config, DB connection

Phase 3: Models & Schemas (1-2 days)
  → SQLAlchemy tables, Pydantic validation schemas, Alembic migrations

Phase 4: API Routes (3-4 days)
  → Full CRUD endpoints, JWT auth, Swagger testing

Phase 5: Frontend React (3-4 days)
  → Vite setup, Axios hooks, Login/Signup/Dashboard/AddTransaction screens

Phase 6: Analytics (2 days)
  → Aggregation endpoints, Recharts integration, CSV export

Phase 7: Polish (1-2 days)
  → Error handling, loading states, responsive design, tests
```

---

*Next: [01-Phase1-Planning.md](./01-Phase1-Planning.md)*
