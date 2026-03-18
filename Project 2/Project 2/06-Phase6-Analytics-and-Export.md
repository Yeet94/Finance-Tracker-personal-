# Phase 6: Analytics & Export

> **Goal:** Build the analytics screen using Recharts for visualization, and implement CSV export from both the backend and frontend.

---

## 6.1 The Analytics Page

```tsx
// src/pages/AnalyticsPage.tsx

import { useState, useEffect } from "react";
import { PieChart, Pie, Cell, Tooltip, Legend, ResponsiveContainer,
         BarChart, Bar, XAxis, YAxis, CartesianGrid } from "recharts";
import { analyticsApi } from "../api/client";
import { CategoryTotal } from "../types";

type Period = "week" | "month" | "year";

function getPeriodDates(period: Period): { start_date: string; end_date: string } {
  const now = new Date();
  let start: Date;
  
  if (period === "week") {
    const day = now.getDay();
    start = new Date(now);
    start.setDate(now.getDate() - (day === 0 ? 6 : day - 1)); // Monday
    start.setHours(0, 0, 0, 0);
  } else if (period === "month") {
    start = new Date(now.getFullYear(), now.getMonth(), 1);
  } else {
    start = new Date(now.getFullYear(), 0, 1);
  }
  
  return {
    start_date: start.toISOString().split("T")[0],  // "2026-03-01"
    end_date:   now.toISOString().split("T")[0],     // "2026-03-13"
  };
}

export default function AnalyticsPage() {
  const [period, setPeriod]           = useState<Period>("month");
  const [categories, setCategories]   = useState<CategoryTotal[]>([]);
  const [loading, setLoading]         = useState(true);

  useEffect(() => {
    const { start_date, end_date } = getPeriodDates(period);
    analyticsApi.byCategory({ type: "expense", start_date, end_date })
      .then(res => setCategories(res.data))
      .finally(() => setLoading(false));
  }, [period]);

  const totalExpense = categories.reduce((sum, c) => sum + c.total, 0);

  return (
    <div className="max-w-4xl mx-auto p-6">
      <h1 className="text-2xl font-bold text-gray-900 mb-6">Analytics</h1>

      {/* Period Selector */}
      <div className="flex gap-2 mb-8">
        {(["week", "month", "year"] as Period[]).map(p => (
          <button
            key={p}
            onClick={() => setPeriod(p)}
            className={`px-5 py-2 rounded-full text-sm font-medium transition-colors ${
              period === p
                ? "bg-blue-600 text-white"
                : "bg-white text-gray-600 border border-gray-200 hover:border-blue-300"
            }`}
          >
            {p.charAt(0).toUpperCase() + p.slice(1)}
          </button>
        ))}
      </div>

      {/* Pie Chart */}
      {categories.length > 0 && (
        <div className="bg-white rounded-2xl p-6 shadow-sm mb-6">
          <h2 className="font-semibold text-gray-800 mb-4">Spending by Category</h2>
          <ResponsiveContainer width="100%" height={300}>
            <PieChart>
              <Pie
                data={categories}
                dataKey="total"
                nameKey="name"
                cx="50%"
                cy="50%"
                outerRadius={100}
                innerRadius={60}    // Donut chart (0 for full pie)
                paddingAngle={2}
              >
                {categories.map((entry, index) => (
                  <Cell key={index} fill={entry.color} />
                ))}
              </Pie>
              <Tooltip
                formatter={(value: number) => [`$${value.toFixed(2)}`, "Amount"]}
              />
              <Legend />
            </PieChart>
          </ResponsiveContainer>
        </div>
      )}

      {/* Category Breakdown Table */}
      <div className="bg-white rounded-2xl shadow-sm overflow-hidden">
        <div className="p-4 border-b">
          <h2 className="font-semibold text-gray-800">Breakdown</h2>
        </div>
        {categories.map((cat) => (
          <div key={cat.name} className="flex items-center justify-between p-4 border-b last:border-0">
            <div className="flex items-center gap-3">
              {/* Color dot */}
              <div className="w-3 h-3 rounded-full" style={{ backgroundColor: cat.color }} />
              <span className="text-gray-700">{cat.icon} {cat.name}</span>
            </div>
            <div className="text-right">
              <p className="font-semibold text-gray-900">${cat.total.toFixed(2)}</p>
              <p className="text-xs text-gray-400">
                {totalExpense > 0 ? ((cat.total / totalExpense) * 100).toFixed(1) : 0}%
              </p>
            </div>
          </div>
        ))}
      </div>
    </div>
  );
}
```

**Recharts key concepts:**
- `ResponsiveContainer` — Makes the chart fill its parent's width (required!)
- `PieChart > Pie` — The pie chart. `dataKey` is the numeric field, `nameKey` is the label
- `Cell` — Set individual slice colors from your data
- `Tooltip` — The hover popup. `formatter` customizes the displayed value
- `innerRadius={60}` turns a pie chart into a donut chart

---

## 6.2 Bar Chart — Monthly Trend

Add a backend endpoint first:

```python
# In app/api/routes/analytics.py

@router.get("/monthly-trend")
def get_monthly_trend(
    db: Session = Depends(get_db),
    current_user=Depends(get_current_user),
    year: int = Query(default=datetime.now().year),
):
    """Returns month-by-month income and expense totals for the given year."""
    from sqlalchemy import extract

    result = (
        db.query(
            extract("month", Transaction.transaction_date).label("month"),
            func.sum(case((Transaction.type == "income", Transaction.amount), else_=0)).label("income"),
            func.sum(case((Transaction.type == "expense", Transaction.amount), else_=0)).label("expense"),
        )
        .filter(
            Transaction.user_id == current_user.id,
            extract("year", Transaction.transaction_date) == year,
        )
        .group_by(extract("month", Transaction.transaction_date))
        .order_by(extract("month", Transaction.transaction_date))
        .all()
    )

    MONTHS = ["Jan", "Feb", "Mar", "Apr", "May", "Jun",
              "Jul", "Aug", "Sep", "Oct", "Nov", "Dec"]
    return [
        {
            "month": MONTHS[int(row.month) - 1],
            "income":  float(row.income  or 0),
            "expense": float(row.expense or 0),
        }
        for row in result
    ]
```

Frontend bar chart:

```tsx
<ResponsiveContainer width="100%" height={300}>
  <BarChart data={monthlyData} margin={{ top: 5, right: 20, left: 20, bottom: 5 }}>
    <CartesianGrid strokeDasharray="3 3" stroke="#F3F4F6" />
    <XAxis dataKey="month" tick={{ fontSize: 12 }} />
    <YAxis tick={{ fontSize: 12 }} tickFormatter={(v) => `$${v}`} />
    <Tooltip formatter={(v: number) => `$${v.toFixed(2)}`} />
    <Legend />
    <Bar dataKey="income"  name="Income"  fill="#22C55E" radius={[4, 4, 0, 0]} />
    <Bar dataKey="expense" name="Expense" fill="#EF4444" radius={[4, 4, 0, 0]} />
  </BarChart>
</ResponsiveContainer>
```

---

## 6.3 CSV Export

### Backend Endpoint

```python
# In app/api/routes/transactions.py

from fastapi.responses import StreamingResponse
import csv
import io

@router.get("/export/csv")
def export_csv(
    db: Session = Depends(get_db),
    current_user: User = Depends(get_current_user),
    start_date: Optional[date] = Query(None),
    end_date:   Optional[date] = Query(None),
):
    """Exports all transactions as a CSV file download."""
    query = (
        db.query(Transaction)
        .options(joinedload(Transaction.category))
        .filter(Transaction.user_id == current_user.id)
        .order_by(Transaction.transaction_date.desc())
    )
    if start_date: query = query.filter(Transaction.transaction_date >= start_date)
    if end_date:   query = query.filter(Transaction.transaction_date <= end_date)
    
    transactions = query.all()

    # Build CSV in memory
    output = io.StringIO()
    writer = csv.writer(output)

    # Header row
    writer.writerow(["Date", "Type", "Category", "Amount", "Note"])

    # Data rows
    for tx in transactions:
        writer.writerow([
            tx.transaction_date.strftime("%Y-%m-%d"),
            tx.type,
            tx.category.name if tx.category else "",
            f"{'-' if tx.type == 'expense' else ''}{tx.amount}",
            tx.note or "",
        ])

    output.seek(0)  # Go back to start of the "file"

    return StreamingResponse(
        iter([output.getvalue()]),
        media_type="text/csv",
        headers={
            "Content-Disposition": "attachment; filename=transactions.csv"
            # Forces browser to download instead of displaying
        }
    )
```

### Frontend: Trigger the Download

```typescript
// In your React component:
const handleExport = async () => {
  const token = localStorage.getItem("access_token");
  const response = await fetch("/api/transactions/export/csv", {
    headers: { Authorization: `Bearer ${token}` }
  });
  
  const blob = await response.blob();              // Binary data
  const url  = URL.createObjectURL(blob);          // Create temporary URL
  const link = document.createElement("a");        // Create invisible <a> tag
  link.href     = url;
  link.download = "transactions.csv";
  link.click();                                    // Trigger download
  URL.revokeObjectURL(url);                        // Clean up
};

// In JSX:
<button onClick={handleExport} className="btn">
  Export CSV
</button>
```

**Why not use Axios for file download?**  
Axios doesn't handle binary streams well for direct downloads. The native `fetch` + `blob()` approach is the standard for file downloads from a React frontend.

---

*Previous: [05-Phase5-Frontend-React.md](./05-Phase5-Frontend-React.md)*  
*Next: [07-Phase7-Testing-and-Polish.md](./07-Phase7-Testing-and-Polish.md)*
