
import os
import sqlite3
from datetime import date
from flask import Flask, request, redirect, render_template_string, session, flash
from werkzeug.security import generate_password_hash, check_password_hash

app = Flask(__name__)
app.secret_key = os.environ.get("SECRET_KEY", "change-this-secret")
DB = os.environ.get("DATABASE_PATH", "expenses.db")

def connect():
    db = sqlite3.connect(DB)
    db.row_factory = sqlite3.Row
    return db

with connect() as db:
    db.execute("""CREATE TABLE IF NOT EXISTS users (
        id INTEGER PRIMARY KEY AUTOINCREMENT,
        username TEXT UNIQUE, password TEXT)""")
    db.execute("""CREATE TABLE IF NOT EXISTS transactions (
        id INTEGER PRIMARY KEY AUTOINCREMENT,
        user_id INTEGER, kind TEXT, category TEXT,
        amount REAL, note TEXT, tx_date TEXT)""")

PAGE = """
<!DOCTYPE html><html><head><meta name="viewport" content="width=device-width,initial-scale=1">
<title>My Expense Tracker</title>
<style>
*{box-sizing:border-box}body{margin:0;background:#101827;color:#f1f5f9;font-family:Arial;padding:25px}
main{max-width:950px;margin:auto}h1{color:#67e8f9}
.card{background:#1e293b;padding:20px;border-radius:14px;margin:15px 0}
.grid{display:grid;grid-template-columns:repeat(auto-fit,minmax(180px,1fr));gap:12px}
input,select,button{padding:12px;border-radius:8px;border:0;margin:5px 0;width:100%}
button{background:#06b6d4;color:#06202a;font-weight:bold;cursor:pointer}
a{color:#67e8f9}table{width:100%;border-collapse:collapse}td,th{text-align:left;padding:12px;border-bottom:1px solid #475569}
.green{color:#4ade80}.red{color:#fb7185}.muted{color:#94a3b8}
</style></head><body><main>
<h1>💰 My Expense Tracker</h1>
{% if not user %}
<div class="card"><h2>{{ mode }}</h2>
<form method="post">
<input name="username" placeholder="Username" required>
<input name="password" type="password" placeholder="Password" required>
<button>{{ mode }}</button></form>
{% if mode == 'Login' %}<p>New user? <a href="/register">Create account</a></p>
{% else %}<p>Already registered? <a href="/login">Login</a></p>{% endif %}
</div>
{% else %}
<p>Welcome, {{ user }}! · <a href="/logout">Logout</a></p>
<div class="grid">
<div class="card"><p class="muted">Total income</p><h2 class="green">₹{{ '%.2f'|format(income) }}</h2></div>
<div class="card"><p class="muted">Total expenses</p><h2 class="red">₹{{ '%.2f'|format(expense) }}</h2></div>
<div class="card"><p class="muted">Balance</p><h2>₹{{ '%.2f'|format(income-expense) }}</h2></div>
</div>
<div class="card"><h2>Add transaction</h2>
<form method="post" action="/add">
<div class="grid">
<select name="kind"><option>Expense</option><option>Income</option></select>
<select name="category">
<option>Food</option><option>Travel</option><option>Shopping</option>
<option>Bills</option><option>Education</option><option>Salary</option>
<option>Investment</option><option>Other</option></select>
<input name="amount" type="number" step="0.01" min="0.01" placeholder="Amount ₹" required>
<input name="tx_date" type="date" value="{{ today }}" required>
</div>
<input name="note" placeholder="Description (optional)">
<button>Add transaction</button></form></div>
<div class="card"><h2>Transaction history</h2>
<table><tr><th>Date</th><th>Type</th><th>Category</th><th>Amount</th><th></th></tr>
{% for t in transactions %}
<tr><td>{{ t.tx_date }}</td><td>{{ t.kind }}</td><td>{{ t.category }}</td>
<td>₹{{ '%.2f'|format(t.amount) }}</td>
<td><form method="post" action="/delete/{{ t.id }}"><button>Delete</button></form></td></tr>
{% else %}<tr><td colspan="5">No transactions yet.</td></tr>{% endfor %}
</table></div>
{% endif %}
</main></body></html>
"""

@app.route("/")
def home():
    if "uid" not in session:
        return redirect("/login")
    with connect() as db:
        rows = db.execute("SELECT * FROM transactions WHERE user_id=? ORDER BY tx_date DESC",
                          (session["uid"],)).fetchall()
    income = sum(t["amount"] for t in rows if t["kind"] == "Income")
    expense = sum(t["amount"] for t in rows if t["kind"] == "Expense")
    return render_template_string(PAGE, user=session["username"],
        transactions=rows, income=income, expense=expense, today=date.today().isoformat())

@app.route("/register", methods=["GET","POST"])
def register():
    if request.method == "POST":
        try:
            with connect() as db:
                db.execute("INSERT INTO users(username,password) VALUES(?,?)",
                    (request.form["username"], generate_password_hash(request.form["password"])))
            return redirect("/login")
        except sqlite3.IntegrityError:
            return "Username already exists. Go back and try another."
    return render_template_string(PAGE, user=None, mode="Register")

@app.route("/login", methods=["GET","POST"])
def login():
    if request.method == "POST":
        with connect() as db:
            u = db.execute("SELECT * FROM users WHERE username=?",
                           (request.form["username"],)).fetchone()
        if u and check_password_hash(u["password"], request.form["password"]):
            session["uid"], session["username"] = u["id"], u["username"]
            return redirect("/")
        return "Invalid username or password. Go back and try again."
    return render_template_string(PAGE, user=None, mode="Login")

@app.route("/add", methods=["POST"])
def add():
    if "uid" not in session: return redirect("/login")
    amount = float(request.form["amount"])
    if amount <= 0: return "Amount must be positive."
    with connect() as db:
        db.execute("""INSERT INTO transactions
            (user_id,kind,category,amount,note,tx_date) VALUES(?,?,?,?,?,?)""",
            (session["uid"],request.form["kind"],request.form["category"],
             amount,request.form["note"],request.form["tx_date"]))
    return redirect("/")

@app.route("/delete/<int:tid>", methods=["POST"])
def delete(tid):
    if "uid" not in session: return redirect("/login")
    with connect() as db:
        db.execute("DELETE FROM transactions WHERE id=? AND user_id=?",
                   (tid,session["uid"]))
    return redirect("/")

@app.route("/logout")
def logout():
    session.clear()
    return redirect("/login")

if __name__ == "__main__":
    app.run(host="0.0.0.0", port=5000)
