# Phase 5: Frontend — React + Vite + Axios

> **Goal:** Build the React frontend — project setup with Vite, an Axios API client with auth token injection, the authentication flow, the main dashboard, and the add transaction form.

---

## 5.1 Scaffold the React App

```bash
# From project root:
cd frontend

# Create React + TypeScript app with Vite
npm create vite@latest . -- --template react-ts

# Install dependencies
npm install

# Install additional packages:
npm install axios react-router-dom@6 recharts
npm install -D tailwindcss postcss autoprefixer @types/node

# Initialize Tailwind CSS
npx tailwindcss init -p
```

### Frontend Folder Structure

```
frontend/
├── src/
│   ├── api/
│   │   └── client.ts          # Axios instance with interceptors
│   ├── components/
│   │   ├── Layout.tsx          # Shared layout (navbar, sidebar)
│   │   ├── TransactionList.tsx
│   │   ├── TransactionItem.tsx
│   │   ├── AddTransactionForm.tsx
│   │   ├── SummaryCard.tsx
│   │   └── CategoryPieChart.tsx
│   ├── contexts/
│   │   └── AuthContext.tsx     # Global auth state
│   ├── hooks/
│   │   ├── useTransactions.ts
│   │   └── useAnalytics.ts
│   ├── pages/
│   │   ├── LoginPage.tsx
│   │   ├── SignupPage.tsx
│   │   ├── DashboardPage.tsx
│   │   └── AnalyticsPage.tsx
│   ├── types/
│   │   └── index.ts            # TypeScript interfaces
│   ├── App.tsx                 # Router setup
│   └── main.tsx                # Entry point
├── tailwind.config.js
├── vite.config.ts
└── package.json
```

---

## 5.2 TypeScript Types — Mirror Your Backend Schemas

```typescript
// src/types/index.ts

export interface User {
  id: number;
  email: string;
  name: string | null;
  created_at: string;
}

export type TransactionType = "income" | "expense";

export interface Category {
  id: number;
  name: string;
  icon: string;
  color: string;
  type: TransactionType;
}

export interface Transaction {
  id: number;
  user_id: number;
  account_id: number | null;
  category_id: number | null;
  category: Category | null;  // Nested from joinedload
  amount: string;             // Decimal comes as string from JSON
  type: TransactionType;
  note: string | null;
  transaction_date: string;   // ISO date string "2026-03-13"
  is_recurring: boolean;
  created_at: string;
  updated_at: string;
}

export interface TransactionCreate {
  account_id: number;
  category_id: number;
  amount: number;
  type: TransactionType;
  note?: string;
  transaction_date?: string;
}

export interface Summary {
  total_income: number;
  total_expense: number;
  net_balance: number;
}

export interface CategoryTotal {
  name: string;
  color: string;
  icon: string;
  total: number;
}

export interface AuthToken {
  access_token: string;
  token_type: string;
}
```

---

## 5.3 Axios API Client with Auth Interceptor

```typescript
// src/api/client.ts

import axios from "axios";

const API_BASE_URL = import.meta.env.VITE_API_URL ?? "http://localhost:8000";

export const api = axios.create({
  baseURL: API_BASE_URL,
  headers: {
    "Content-Type": "application/json",
  },
});

// ─── REQUEST INTERCEPTOR ──────────────────────────────────────────────────────
// Automatically attach the JWT token to every request
api.interceptors.request.use((config) => {
  const token = localStorage.getItem("access_token");
  if (token) {
    config.headers.Authorization = `Bearer ${token}`;
  }
  return config;
});

// ─── RESPONSE INTERCEPTOR ─────────────────────────────────────────────────────
// Handle 401 globally — redirect to login if token expired
api.interceptors.response.use(
  (response) => response,       // Pass through successful responses unchanged
  (error) => {
    if (error.response?.status === 401) {
      localStorage.removeItem("access_token");
      window.location.href = "/login";  // Force redirect
    }
    return Promise.reject(error);
  }
);

// ─── API FUNCTIONS ────────────────────────────────────────────────────────────
// Auth
export const authApi = {
  register:  (data: { email: string; password: string; name?: string }) =>
               api.post("/api/auth/register", data),
  login:     (data: { email: string; password: string }) =>
               api.post<AuthToken>("/api/auth/login", data),
  me:        () =>
               api.get<User>("/api/auth/me"),
};

// Transactions
export const transactionApi = {
  list:   (params?: Record<string, any>) =>
            api.get<Transaction[]>("/api/transactions", { params }),
  create: (data: TransactionCreate) =>
            api.post<Transaction>("/api/transactions", data),
  update: (id: number, data: Partial<TransactionCreate>) =>
            api.patch<Transaction>(`/api/transactions/${id}`, data),
  delete: (id: number) =>
            api.delete(`/api/transactions/${id}`),
};

// Analytics
export const analyticsApi = {
  summary:    (params?: { start_date?: string; end_date?: string }) =>
                api.get<Summary>("/api/analytics/summary", { params }),
  byCategory: (params?: { type?: string; start_date?: string; end_date?: string }) =>
                api.get<CategoryTotal[]>("/api/analytics/by-category", { params }),
};
```

**.env in Vite:**
```bash
# frontend/.env
VITE_API_URL=http://localhost:8000
```

Vite exposes `import.meta.env.VITE_*` variables (note: must be prefixed `VITE_`, similar to Expo's `EXPO_PUBLIC_`).

---

## 5.4 Auth Context — Global Auth State

```typescript
// src/contexts/AuthContext.tsx

import { createContext, useContext, useState, useEffect, ReactNode } from "react";
import { authApi } from "../api/client";
import { User } from "../types";

interface AuthContextType {
  user: User | null;
  isLoading: boolean;
  isAuthenticated: boolean;
  login: (email: string, password: string) => Promise<void>;
  logout: () => void;
}

const AuthContext = createContext<AuthContextType | undefined>(undefined);

export function AuthProvider({ children }: { children: ReactNode }) {
  const [user, setUser] = useState<User | null>(null);
  const [isLoading, setIsLoading] = useState(true);

  // On app load: check if there's a stored token → fetch current user
  useEffect(() => {
    const token = localStorage.getItem("access_token");
    if (token) {
      authApi.me()
        .then(res => setUser(res.data))
        .catch(() => localStorage.removeItem("access_token"))  // Bad token
        .finally(() => setIsLoading(false));
    } else {
      setIsLoading(false);
    }
  }, []);

  const login = async (email: string, password: string) => {
    const { data } = await authApi.login({ email, password });
    localStorage.setItem("access_token", data.access_token);
    const userRes = await authApi.me();
    setUser(userRes.data);
  };

  const logout = () => {
    localStorage.removeItem("access_token");
    setUser(null);
  };

  return (
    <AuthContext.Provider value={{
      user,
      isLoading,
      isAuthenticated: !!user,
      login,
      logout,
    }}>
      {children}
    </AuthContext.Provider>
  );
}

export function useAuth() {
  const ctx = useContext(AuthContext);
  if (!ctx) throw new Error("useAuth must be used within AuthProvider");
  return ctx;
}
```

---

## 5.5 App Router — Protected Routes

```typescript
// src/App.tsx

import { BrowserRouter, Routes, Route, Navigate } from "react-router-dom";
import { AuthProvider, useAuth } from "./contexts/AuthContext";
import LoginPage from "./pages/LoginPage";
import SignupPage from "./pages/SignupPage";
import DashboardPage from "./pages/DashboardPage";
import AnalyticsPage from "./pages/AnalyticsPage";

// ─── ROUTE GUARD ─────────────────────────────────────────────────────────────
function ProtectedRoute({ children }: { children: JSX.Element }) {
  const { isAuthenticated, isLoading } = useAuth();
  if (isLoading) return <div className="flex h-screen items-center justify-center">Loading...</div>;
  if (!isAuthenticated) return <Navigate to="/login" replace />;
  return children;
}

export default function App() {
  return (
    <AuthProvider>
      <BrowserRouter>
        <Routes>
          {/* Public routes */}
          <Route path="/login"  element={<LoginPage />} />
          <Route path="/signup" element={<SignupPage />} />

          {/* Protected routes */}
          <Route path="/" element={
            <ProtectedRoute><DashboardPage /></ProtectedRoute>
          } />
          <Route path="/analytics" element={
            <ProtectedRoute><AnalyticsPage /></ProtectedRoute>
          } />

          {/* Catch-all */}
          <Route path="*" element={<Navigate to="/" replace />} />
        </Routes>
      </BrowserRouter>
    </AuthProvider>
  );
}
```

---

## 5.6 Login Page

```tsx
// src/pages/LoginPage.tsx

import { useState } from "react";
import { useNavigate, Link } from "react-router-dom";
import { useAuth } from "../contexts/AuthContext";

export default function LoginPage() {
  const [email, setEmail]       = useState("");
  const [password, setPassword] = useState("");
  const [error, setError]       = useState<string | null>(null);
  const [loading, setLoading]   = useState(false);
  const { login } = useAuth();
  const navigate = useNavigate();

  const handleSubmit = async (e: React.FormEvent) => {
    e.preventDefault();  // Prevent browser page reload on form submit
    try {
      setLoading(true);
      setError(null);
      await login(email, password);
      navigate("/");     // Redirect to dashboard after login
    } catch (err: any) {
      setError(err.response?.data?.detail ?? "Login failed");
    } finally {
      setLoading(false);
    }
  };

  return (
    <div className="min-h-screen bg-gray-50 flex items-center justify-center p-4">
      <div className="bg-white rounded-2xl shadow-lg p-8 w-full max-w-md">
        <h1 className="text-3xl font-bold text-gray-900 mb-2">Welcome back</h1>
        <p className="text-gray-500 mb-8">Sign in to your Finance Tracker</p>

        {error && (
          <div className="bg-red-50 border border-red-200 text-red-700 rounded-lg px-4 py-3 mb-6">
            {error}
          </div>
        )}

        <form onSubmit={handleSubmit} className="space-y-4">
          <div>
            <label className="block text-sm font-medium text-gray-700 mb-1">Email</label>
            <input
              type="email"
              value={email}
              onChange={e => setEmail(e.target.value)}
              className="w-full border border-gray-300 rounded-xl px-4 py-3 focus:outline-none focus:ring-2 focus:ring-blue-500"
              placeholder="you@example.com"
              required
            />
          </div>
          <div>
            <label className="block text-sm font-medium text-gray-700 mb-1">Password</label>
            <input
              type="password"
              value={password}
              onChange={e => setPassword(e.target.value)}
              className="w-full border border-gray-300 rounded-xl px-4 py-3 focus:outline-none focus:ring-2 focus:ring-blue-500"
              placeholder="••••••••"
              required
            />
          </div>
          <button
            type="submit"
            disabled={loading}
            className="w-full bg-blue-600 hover:bg-blue-700 disabled:opacity-50 text-white font-semibold rounded-xl py-3 transition-colors"
          >
            {loading ? "Signing in..." : "Sign In"}
          </button>
        </form>

        <p className="text-center text-gray-500 mt-6">
          No account?{" "}
          <Link to="/signup" className="text-blue-600 hover:underline font-medium">
            Create one
          </Link>
        </p>
      </div>
    </div>
  );
}
```

---

## 5.7 Dashboard Page (Simplified)

```tsx
// src/pages/DashboardPage.tsx

import { useState, useEffect } from "react";
import { transactionApi, analyticsApi } from "../api/client";
import { Transaction, Summary } from "../types";

export default function DashboardPage() {
  const [transactions, setTransactions] = useState<Transaction[]>([]);
  const [summary, setSummary]           = useState<Summary | null>(null);
  const [loading, setLoading]           = useState(true);

  useEffect(() => {
    const load = async () => {
      const [txRes, sumRes] = await Promise.all([
        transactionApi.list({ limit: 20 }),
        analyticsApi.summary(),  // Current month by default
      ]);
      setTransactions(txRes.data);
      setSummary(sumRes.data);
      setLoading(false);
    };
    load();
  }, []);

  const handleDelete = async (id: number) => {
    await transactionApi.delete(id);
    setTransactions(prev => prev.filter(tx => tx.id !== id));
  };

  return (
    <div className="min-h-screen bg-gray-50">
      <div className="max-w-4xl mx-auto p-6">
        <h1 className="text-2xl font-bold text-gray-900 mb-6">Dashboard</h1>

        {/* Summary Cards */}
        {summary && (
          <div className="grid grid-cols-3 gap-4 mb-8">
            <div className="bg-white rounded-2xl p-5 shadow-sm">
              <p className="text-gray-500 text-sm">Total Income</p>
              <p className="text-2xl font-bold text-green-600">
                +${summary.total_income.toFixed(2)}
              </p>
            </div>
            <div className="bg-white rounded-2xl p-5 shadow-sm">
              <p className="text-gray-500 text-sm">Total Expenses</p>
              <p className="text-2xl font-bold text-red-500">
                -${summary.total_expense.toFixed(2)}
              </p>
            </div>
            <div className="bg-white rounded-2xl p-5 shadow-sm">
              <p className="text-gray-500 text-sm">Net Balance</p>
              <p className={`text-2xl font-bold ${summary.net_balance >= 0 ? "text-green-600" : "text-red-500"}`}>
                ${summary.net_balance.toFixed(2)}
              </p>
            </div>
          </div>
        )}

        {/* Transaction List */}
        <div className="bg-white rounded-2xl shadow-sm overflow-hidden">
          {transactions.map(tx => (
            <div key={tx.id} className="flex items-center justify-between p-4 border-b last:border-0">
              <div className="flex items-center gap-3">
                <span className="text-2xl">{tx.category?.icon ?? "💰"}</span>
                <div>
                  <p className="font-medium text-gray-900">{tx.category?.name ?? "Uncategorized"}</p>
                  <p className="text-sm text-gray-400">{tx.transaction_date}</p>
                </div>
              </div>
              <div className="flex items-center gap-3">
                <p className={`font-bold ${tx.type === "income" ? "text-green-600" : "text-gray-900"}`}>
                  {tx.type === "income" ? "+" : "-"}${parseFloat(tx.amount).toFixed(2)}
                </p>
                <button
                  onClick={() => handleDelete(tx.id)}
                  className="text-gray-300 hover:text-red-500 transition-colors text-xl"
                >
                  ×
                </button>
              </div>
            </div>
          ))}
        </div>
      </div>
    </div>
  );
}
```

---

## 5.8 Vite Config — Proxy for Dev

```typescript
// vite.config.ts

import { defineConfig } from "vite";
import react from "@vitejs/plugin-react";

export default defineConfig({
  plugins: [react()],
  server: {
    port: 5173,
    proxy: {
      // Forward /api requests to FastAPI during development
      // This avoids CORS issues in dev (treats them as same-origin)
      "/api": {
        target: "http://localhost:8000",
        changeOrigin: true,
      },
    },
  },
});
```

With this proxy, `axios.get('/api/transactions')` from the browser goes to `http://localhost:5173/api/transactions` which Vite forwards to `http://localhost:8000/api/transactions`. No CORS needed in development.

---

*Previous: [04-Phase4-API-Routes.md](./04-Phase4-API-Routes.md)*  
*Next: [06-Phase6-Analytics-and-Export.md](./06-Phase6-Analytics-and-Export.md)*
