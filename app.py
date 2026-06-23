from flask import Flask, render_template, request, redirect, url_for, session, send_file
from dotenv import load_dotenv
from groq import Groq
import os
import sqlite3
from datetime import datetime

from werkzeug.security import (
    generate_password_hash,
    check_password_hash
)


from reportlab.platypus import SimpleDocTemplate, Paragraph, Spacer, Table, TableStyle
from reportlab.lib.styles import getSampleStyleSheet
from reportlab.lib import colors
from reportlab.platypus import Image

# Load environment variables
load_dotenv(dotenv_path=".env")

app = Flask(__name__)
app.secret_key = "finance_secret"
# -----------------------------
# LATEST REPORT DATA
# -----------------------------

latest_report = {}

# -----------------------------
# DATABASE
# -----------------------------


def init_db():

    conn = sqlite3.connect("finance.db")

    cursor = conn.cursor()

    # -----------------------------
    # HISTORY TABLE
    # -----------------------------
    cursor.execute("""

    CREATE TABLE IF NOT EXISTS history(

        id INTEGER PRIMARY KEY AUTOINCREMENT,

        user_id INTEGER,

        income REAL,

        expenses REAL,

        savings REAL,

        score INTEGER,

        created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP

    )

    """)

    # -----------------------------
    # USERS TABLE
    # -----------------------------
    cursor.execute("""

    CREATE TABLE IF NOT EXISTS users(

        id INTEGER PRIMARY KEY AUTOINCREMENT,

        name TEXT NOT NULL,

        email TEXT UNIQUE NOT NULL,

        username TEXT UNIQUE NOT NULL,

        password TEXT NOT NULL,

        created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP

    )

    """)

    conn.commit()

    conn.close()


init_db()

# Secure Groq Client (NO HARDCODED KEY)

client = Groq(api_key=os.getenv("GROQ_API_KEY"))


# -----------------------------
# Financial Score Logic
# -----------------------------
def calculate_financial_score(income, expenses):

    if income == 0:
        return 0, "No income data"

    savings = income - expenses
    savings_rate = (savings / income) * 100

    if savings_rate < 10:
        return 20, "Poor"
    elif savings_rate < 20:
        return 40, "Needs Improvement"
    elif savings_rate < 30:
        return 60, "Average"
    elif savings_rate < 40:
        return 80, "Good"
    else:
        return 100, "Excellent"


# -----------------------------
# Spending Insights
# -----------------------------
def spending_insights(income, rent, food, transport, entertainment):

    insights = []

    if rent > income * 0.3:
        insights.append("⚠ Rent spending is too high.")

    if food > income * 0.2:
        insights.append("⚠ Food expenses are high.")

    if transport > income * 0.15:
        insights.append("⚠ Transport cost is high.")

    if entertainment > income * 0.1:
        insights.append("⚠ Entertainment spending is too high.")

    if not insights:
        insights.append("✔ Your spending distribution looks healthy.")

    return insights


# -----------------------------
# Financial Advice
# -----------------------------
def financial_advice(income, expenses):

    savings = income - expenses

    if savings <= 0:
        return "You are spending more than you earn."
    elif savings < income * 0.2:
        return "Try to save at least 20% of your income."
    elif savings < income * 0.4:
        return "Good saving! Keep it up."
    else:
        return "Excellent savings! Consider investing."


# -----------------------------
# AI Financial Analysis
# -----------------------------
def ai_financial_analysis(income, expenses):
    try:
        prompt = f"""
You are an expert AI Financial Coach.

User Data:

Monthly Income: ₹{income}

Monthly Expenses: ₹{expenses}

Monthly Savings: ₹{income-expenses}

Analyze this financial profile.

Return ONLY in this format:

🏆 Financial Health:
(one line)

💡 Key Recommendation:
(one line)

📈 Investment Suggestion:
(one line)

🎯 Next Goal:
(one line)

⚠ Risk:
(one line)

Keep the response short and professional.
# -*- coding: utf-8 -*-
"""
        response = client.chat.completions.create(
            model="llama-3.3-70b-versatile",
            messages=[
                {"role": "system", "content": "You are a financial advisor."},
                {"role": "user", "content": prompt},
            ],
        )

        return response.choices[0].message.content
    except Exception as e:
        print("AI Error:", e)
        return "AI analysis currently unavailable."


# -----------------------------
# LOGIN
# -----------------------------
@app.route("/login", methods=["GET", "POST"])
def login():

    if request.method == "POST":

        username = request.form["username"]
        password = request.form["password"]

        conn = sqlite3.connect("finance.db")
        cursor = conn.cursor()

        cursor.execute(
            """
            SELECT id, username, password
            FROM users
            WHERE username = ?
            """,
            (username,)
        )

        user = cursor.fetchone()

        conn.close()

        if user and check_password_hash(
            user[2],
            password
        ):

            session["user_id"] = user[0]
            session["username"] = user[1]

            return redirect(url_for("home"))

        return "Invalid Username or Password"

    return render_template("login.html")

@app.route("/logout")
def logout():

    session.clear()

    return redirect(url_for("login"))

# -----------------------------
# LOGOUT
# -----------------------------
def logout():

    session.clear()

    return redirect(url_for("login"))

# -----------------------------
# REGISTER
# -----------------------------
@app.route("/register", methods=["GET", "POST"])
def register():

    if request.method == "POST":

        name = request.form["name"]
        email = request.form["email"]
        username = request.form["username"]
        password = request.form["password"]
        confirm_password = request.form["confirm_password"]

        if password != confirm_password:
            return "Passwords do not match"

        conn = sqlite3.connect("finance.db")
        cursor = conn.cursor()

        cursor.execute(
            "SELECT * FROM users WHERE username=? OR email=?",
            (username, email)
        )

        existing_user = cursor.fetchone()

        if existing_user:
            conn.close()
            return "Username or Email already exists"

        hashed_password = generate_password_hash(password)

        cursor.execute(
            """
            INSERT INTO users
            (name, email, username, password)
            VALUES (?, ?, ?, ?)
            """,
            (
                name,
                email,
                username,
                hashed_password
            )
        )

        conn.commit()
        conn.close()

        return redirect(url_for("login"))

    return render_template("register.html")


# -----------------------------
# HOME DASHBOARD
# -----------------------------
@app.route("/", methods=["GET", "POST"])
def home():

    global latest_report

    if "user_id" not in session:
        return redirect(url_for("login"))

    # Default values
    income = 0
    rent = 0
    food = 0
    transport = 0
    entertainment = 0

    expenses = 0
    savings = 0

    advice = ""
    ai_report = ""
    status = ""
    score = 0

    insights = []

    savings_rate = 0
    expense_ratio = 0

    goal_target = 100000
    goal_progress = 0

    needs = 0
    wants = 0
    recommended_savings = 0

    sip = 0
    gold = 0
    cash = 0

    if request.method == "POST":

        income = float(request.form["income"])
        rent = float(request.form["rent"])
        food = float(request.form["food"])
        transport = float(request.form["transport"])
        entertainment = float(request.form["entertainment"])

        expenses = rent + food + transport + entertainment
        savings = income - expenses

        needs = income * 0.50
        wants = income * 0.30
        recommended_savings = income * 0.20

        sip = recommended_savings * 0.60
        gold = recommended_savings * 0.20
        cash = recommended_savings * 0.20

        if income > 0:

            savings_rate = round((savings / income) * 100, 2)
            expense_ratio = round((expenses / income) * 100, 2)

            savings_rate = max(savings_rate, 0)
            expense_ratio = min(expense_ratio, 100)

        if savings > 0:
            goal_progress = min(round((savings / goal_target) * 100, 2), 100)

        advice = financial_advice(income, expenses)

        score, status = calculate_financial_score(income, expenses)

        ai_report = ai_financial_analysis(income, expenses)

        insights = spending_insights(income, rent, food, transport, entertainment)

        latest_report = {
            "income": income,
            "expenses": expenses,
            "savings": savings,
            "score": score,
            "status": status,
            "advice": advice,
            "ai_report": ai_report,
        }

        # Save to database
        conn = sqlite3.connect("finance.db")
        cursor = conn.cursor()

        cursor.execute(
         """
         INSERT INTO history
        (
             user_id,
             income,
             expenses,
             savings,
             score
        )
        VALUES (?, ?, ?, ?, ?)
        """,
        (
            session["user_id"],
            income,
            expenses,
            savings,
            score
        ),
    )
        conn.commit()
        conn.close()


    # -----------------------------
    # LOAD HISTORY
    # -----------------------------

    conn = sqlite3.connect("finance.db")
    cursor = conn.cursor()

    cursor.execute("""
        SELECT
            id,
            income,
            expenses,
            savings,
            score
        FROM history
        WHERE user_id = ?
        ORDER BY id DESC
        LIMIT 10
    """, (session["user_id"],)
    )
    history = cursor.fetchall()
    conn.close()

    return render_template(
        "index.html",
        income=income,
        advice=advice,
        history=history,
        savings=savings,
        ai_report=ai_report,
        score=score,
        status=status,
        insights=insights,
        savings_rate=savings_rate,
        expense_ratio=expense_ratio,
        goal_target=goal_target,
        goal_progress=goal_progress,
        rent=rent,
        food=food,
        transport=transport,
        entertainment=entertainment,
        needs=needs,
        wants=wants,
        recommended_savings=recommended_savings,
        sip=sip,
        gold=gold,
        cash=cash,
    )


# -----------------------------
# CHATBOT
# -----------------------------
@app.route("/chat", methods=["POST"])
def chat():

    user_message = request.form["message"]

    try:
        response = client.chat.completions.create(
            model="llama-3.1-8b-instant",
            messages=[
                {"role": "system", "content": "You are a financial advisor."},
                {"role": "user", "content": user_message},
            ],
        )

        reply = response.choices[0].message.content

    except Exception as e:
        print("Chat Error:", e)
        reply = "AI unavailable"

    return {"reply": reply}


# ----------------------------
# DOWNLOAD PDF REPORT
# -----------------------------


@app.route("/download_report")
def download_report():
    global latest_report

    styles = getSampleStyleSheet()

    doc = SimpleDocTemplate(
        "Financial_Report.pdf",
        topMargin=40,
        bottomMargin=40,
        leftMargin=40,
        rightMargin=40,
    )

    elements = []

    current_date = datetime.now().strftime("%d %B %Y %I:%M %p")

    report_id = datetime.now().strftime("MMAI-%Y%m%d-%H%M%S")

    # -----------------------------
    # LOGO
    # -----------------------------
    try:
        logo = Image("logo.png", width=55, height=55)
    except:
        logo = Paragraph("", styles["Normal"])

    left = [
        logo,
        Paragraph(
            "<font size=18 color='#0B3D91'><b>MoneyMind AI</b></font>", styles["Title"]
        ),
        Paragraph(
            "<font size=9 color='grey'>AI-powered Personal Finance & Wealth Assistant</font>",
            styles["Normal"],
        ),
    ]

    right = Paragraph(
        f"""
        <font size=10>
        <b>Report ID</b><br/>
        {report_id}

        <br/><br/>

        <b>Generated On</b><br/>
        {current_date}

        <br/><br/>

        <b>Status</b><br/>
        CONFIDENTIAL
        </font>
        """,
        styles["Normal"],
    )

    header = Table([[left, right]], colWidths=[330, 180])

    header.setStyle(
        TableStyle(
            [
                ("VALIGN", (0, 0), (-1, -1), "TOP"),
                ("ALIGN", (1, 0), (1, 0), "RIGHT"),
                ("BOTTOMPADDING", (0, 0), (-1, -1), 10),
            ]
        )
    )

    elements.append(header)
    elements.append(Spacer(1, 15))

    elements.append(
        Paragraph(
            "<font size=16 color='#0B3D91'><b>MONEYMIND AI FINANCIAL REPORT</b></font>",
            styles["Heading1"],
        )
    )

    elements.append(Spacer(1, 20))

    if latest_report:

        income = latest_report["income"]
        expenses = latest_report["expenses"]
        savings = latest_report["savings"]
        score = latest_report["score"]
        status = latest_report["status"]

        savings_rate = 0

        if income > 0:
            savings_rate = round((savings / income) * 100, 2)

        data = [
            ["Financial Summary", ""],
            ["Monthly Income", f"₹{income:,.0f}"],
            ["Monthly Expenses", f"₹{expenses:,.0f}"],
            ["Monthly Savings", f"₹{savings:,.0f}"],
            ["Savings Rate", f"{savings_rate}%"],
            ["Financial Score", f"{score}/100"],
            ["Status", status],
        ]

        table = Table(data, colWidths=[220, 220])

        table.setStyle(
            TableStyle(
                [
                    ("BACKGROUND", (0, 0), (-1, 0), colors.darkblue),
                    ("TEXTCOLOR", (0, 0), (-1, 0), colors.white),
                    ("FONTNAME", (0, 0), (-1, 0), "Helvetica-Bold"),
                    ("GRID", (0, 0), (-1, -1), 1, colors.grey),
                    ("ALIGN", (0, 0), (-1, -1), "CENTER"),
                    ("BACKGROUND", (0, 1), (-1, -1), colors.whitesmoke),
                ]
            )
        )

        elements.append(table)
        elements.append(Spacer(1, 20))

        elements.append(
            Paragraph(
                "<font size=15 color='darkgreen'><b>Financial Advice</b></font>",
                styles["Heading2"],
            )
        )

        elements.append(Paragraph(latest_report["advice"], styles["Normal"]))

        elements.append(Spacer(1, 15))

        elements.append(
            Paragraph(
                "<font size=15 color='darkblue'><b>AI Recommendation</b></font>",
                styles["Heading2"],
            )
        )

        elements.append(
            Paragraph(latest_report["ai_report"].replace("\n", "<br/>"), styles["Normal"])
        )

        elements.append(Spacer(1, 20))

        recommended = income * 0.20
        sip = recommended * 0.60
        gold = recommended * 0.20
        emergency = recommended * 0.20

        invest_data = [
            ["Investment Plan", ""],
            ["Recommended Savings", f"₹{recommended:,.0f}"],
            ["SIP", f"₹{sip:,.0f}"],
            ["Gold", f"₹{gold:,.0f}"],
            ["Emergency Fund", f"₹{emergency:,.0f}"],
        ]

        invest_table = Table(invest_data, colWidths=[220, 220])

        invest_table.setStyle(
            TableStyle(
                [
                    ("BACKGROUND", (0, 0), (-1, 0), colors.green),
                    ("TEXTCOLOR", (0, 0), (-1, 0), colors.white),
                    ("GRID", (0, 0), (-1, -1), 1, colors.grey),
                    ("ALIGN", (0, 0), (-1, -1), "CENTER"),
                    ("BACKGROUND", (0, 1), (-1, -1), colors.beige),
                ]
            )
        )

        elements.append(invest_table)
        elements.append(Spacer(1, 20))

        elements.append(
            Paragraph(
                "<font size=15 color='red'><b>Risk Analysis</b></font>", styles["Heading2"]
            )
        )

        risk = ""

        if savings_rate >= 30:
            risk += "✔ Excellent savings discipline.<br/>"
        else:
            risk += "⚠ Increase monthly savings.<br/>"

        if expenses > income * 0.8:
            risk += "⚠ Expenses are very high.<br/>"
        else:
            risk += "✔ Expenses are under control.<br/>"

        risk += "✔ Continue building emergency fund."

        elements.append(Paragraph(risk, styles["Normal"]))

    else:

        elements.append(Paragraph("No financial analysis available.", styles["Normal"]))

    elements.append(Spacer(1, 30))

    elements.append(
        Paragraph("<font color='grey'>Generated by MoneyMind AI</font>", styles["Italic"])
    )

    doc.build(elements)

    return send_file("Financial_Report.pdf", as_attachment=True)


# -----------------------------

# RUN APP

# -----------------------------

if __name__ == "__main__":
    app.run(debug=True)
