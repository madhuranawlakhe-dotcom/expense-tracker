import streamlit as st
import pandas as pd
import plotly.express as px
import json
from datetime import datetime, date
import google.generativeai as genai

st.set_page_config(
    page_title="Smart Expense Tracker",
    page_icon="💰",
    layout="wide"
)

st.markdown("""
<style>
    .main { background-color: #f8f9fa; }
    .stButton>button { border-radius: 8px; font-weight: 500; }
    .chat-msg-user {
        background: #e8f4fd; border-radius: 10px;
        padding: 10px 14px; margin: 6px 0;
        text-align: right; color: #1a3c5e;
    }
    .chat-msg-ai {
        background: #f0f2f6; border-radius: 10px;
        padding: 10px 14px; margin: 6px 0; color: #1a1a2e;
    }
</style>
""", unsafe_allow_html=True)

CATEGORIES = ["Food", "Transport", "Shopping", "Entertainment", "Health", "Utilities", "Other"]
CAT_COLORS = {
    "Food": "#D85A30", "Transport": "#378ADD", "Shopping": "#D4537E",
    "Entertainment": "#7F77DD", "Health": "#639922", "Utilities": "#BA7517", "Other": "#888780"
}

st.sidebar.title("Settings")
api_key = st.sidebar.text_input(
    "Google Gemini API Key",
    type="password",
    placeholder="Paste your API key here",
    help="Get free key at https://aistudio.google.com"
)

if api_key:
    genai.configure(api_key=api_key)
    model = genai.GenerativeModel("gemini-1.5-flash")
    st.sidebar.success("API Key set!")
else:
    st.sidebar.warning("Enter API key to enable AI features")
    model = None

if "expenses" not in st.session_state:
    st.session_state.expenses = pd.DataFrame([
        {"Date": "2026-04-10", "Description": "Zomato dinner",       "Amount": 450,  "Category": "Food"},
        {"Date": "2026-04-10", "Description": "Uber ride",            "Amount": 180,  "Category": "Transport"},
        {"Date": "2026-04-09", "Description": "Netflix subscription", "Amount": 649,  "Category": "Entertainment"},
        {"Date": "2026-04-08", "Description": "Grocery store",        "Amount": 1200, "Category": "Food"},
        {"Date": "2026-04-07", "Description": "Electricity bill",     "Amount": 890,  "Category": "Utilities"},
    ])
if "chat_history" not in st.session_state:
    st.session_state.chat_history = []


def get_expense_summary():
    df = st.session_state.expenses
    if df.empty:
        return "No expenses recorded yet."
    total = df["Amount"].sum()
    by_cat = df.groupby("Category")["Amount"].sum().to_dict()
    recent = df.tail(5)[["Date", "Description", "Amount", "Category"]].to_dict("records")
    cat_str = ", ".join(str(k) + ": Rs." + str(v) for k, v in by_cat.items())
    recent_str = ", ".join(str(r["Description"]) + " Rs." + str(r["Amount"]) for r in recent)
    return (
        "Total expenses: Rs." + str(total) + " across " + str(len(df)) + " transactions. "
        "Category breakdown: " + cat_str + ". "
        "Recent: " + recent_str + "."
    )


def ai_categorize(description, amount):
    if not model:
        return {"category": "Other", "note": ""}
    try:
        prompt = (
            'Expense: "' + description + '", Amount: Rs.' + str(amount) + '. '
            'Return ONLY raw JSON (no markdown, no backticks): '
            '{"category":"...", "note":"..."} '
            'Category must be one of: ' + ", ".join(CATEGORIES) + '. '
            'Note is a one-line money-saving tip.'
        )
        resp = model.generate_content(prompt)
        text = resp.text.strip().replace("```json", "").replace("```", "").strip()
        return json.loads(text)
    except Exception:
        return {"category": "Other", "note": ""}


def ai_chat(user_message):
    if not model:
        return "Please enter your Gemini API key in the sidebar to use AI chat."
    summary = get_expense_summary()
    try:
        history_text = "\n".join(
            ("User: " if m["role"] == "user" else "Assistant: ") + m["content"]
            for m in st.session_state.chat_history[-6:]
        )
        prompt = (
            "You are a smart personal finance assistant.\n"
            "User expense data: " + summary + "\n"
            "Previous conversation:\n" + history_text + "\n"
            "User: " + user_message + "\n"
            "Give concise, actionable advice in 2-3 sentences. Use Rs. for currency."
        )
        resp = model.generate_content(prompt)
        reply = resp.text.strip()
        st.session_state.chat_history.append({"role": "user", "content": user_message})
        st.session_state.chat_history.append({"role": "assistant", "content": reply})
        return reply
    except Exception as e:
        return "AI error: " + str(e)


st.title("💰 Smart Expense Tracker")
st.caption("Track spending · AI auto-categorize · Get personalized insights · Powered by Google Gemini")

df = st.session_state.expenses

c1, c2, c3, c4 = st.columns(4)
total   = df["Amount"].sum() if not df.empty else 0
top_cat = df.groupby("Category")["Amount"].sum().idxmax() if not df.empty else "---"
top_amt = df.groupby("Category")["Amount"].sum().max()    if not df.empty else 0
avg     = df["Amount"].mean() if not df.empty else 0

c1.metric("Total Spent",     "Rs." + str(int(total)))
c2.metric("Transactions",    len(df))
c3.metric("Top Category",    str(top_cat) + " (Rs." + str(int(top_amt)) + ")")
c4.metric("Avg per Expense", "Rs." + str(int(avg)))

st.divider()

left, right = st.columns([1, 1], gap="large")

with left:
    st.subheader("Add Expense")

    with st.form("add_form", clear_on_submit=True):
        desc     = st.text_input("Description", placeholder="e.g. Swiggy biryani")
        amt      = st.number_input("Amount (Rs.)", min_value=0.0, step=10.0)
        col_a, col_b = st.columns(2)
        with col_a:
            cat      = st.selectbox("Category", CATEGORIES)
        with col_b:
            exp_date = st.date_input("Date", value=date.today())

        col_add, col_ai = st.columns([2, 1])
        with col_add:
            submitted = st.form_submit_button("Add Expense", use_container_width=True, type="primary")
        with col_ai:
            ai_btn = st.form_submit_button("AI Fill", use_container_width=True)

    if ai_btn:
        if not desc:
            st.warning("Enter a description first.")
        elif not model:
            st.warning("Enter your Gemini API key in the sidebar.")
        else:
            with st.spinner("AI categorizing..."):
                result = ai_categorize(desc, amt)
            suggested = result.get("category", "Other")
            note      = result.get("note", "")
            st.success("AI suggests: " + suggested + (" -- " + note if note else ""))

    if submitted:
        if not desc or amt <= 0:
            st.error("Please enter description and a valid amount.")
        else:
            new_row = pd.DataFrame([{
                "Date":        str(exp_date),
                "Description": desc,
                "Amount":      amt,
                "Category":    cat,
            }])
            st.session_state.expenses = pd.concat(
                [st.session_state.expenses, new_row], ignore_index=True
            )
            st.success("Added: " + desc + " -- Rs." + str(int(amt)))
            st.rerun()

    st.subheader("Expenses")
    if df.empty:
        st.info("No expenses yet. Add one above!")
    else:
        display = df.copy().sort_values("Date", ascending=False).reset_index(drop=True)
        display.index += 1
        display["Amount"] = display["Amount"].apply(lambda x: "Rs." + str(int(x)))
        st.dataframe(
            display[["Date", "Description", "Category", "Amount"]],
            use_container_width=True,
            hide_index=False,
        )
        if st.button("Clear All Expenses", type="secondary"):
            st.session_state.expenses = pd.DataFrame(
                columns=["Date", "Description", "Amount", "Category"]
            )
            st.rerun()

with right:
    st.subheader("Spending Breakdown")

    if df.empty:
        st.info("Add expenses to see charts.")
    else:
        tab1, tab2 = st.tabs(["By Category", "Over Time"])

        with tab1:
            by_cat = df.groupby("Category")["Amount"].sum().reset_index()
            fig = px.pie(
                by_cat, values="Amount", names="Category",
                color="Category", color_discrete_map=CAT_COLORS, hole=0.4,
            )
            fig.update_layout(margin=dict(t=20, b=20, l=20, r=20), height=280,
                              legend=dict(orientation="h", y=-0.15))
            fig.update_traces(textposition="inside", textinfo="percent+label")
            st.plotly_chart(fig, use_container_width=True)

        with tab2:
            df2 = df.copy()
            df2["Date"] = pd.to_datetime(df2["Date"])
            daily = df2.groupby(["Date", "Category"])["Amount"].sum().reset_index()
            fig2 = px.bar(
                daily, x="Date", y="Amount", color="Category",
                color_discrete_map=CAT_COLORS,
            )
            fig2.update_layout(margin=dict(t=20, b=20, l=20, r=20), height=280,
                               legend=dict(orientation="h", y=-0.25))
            st.plotly_chart(fig2, use_container_width=True)

    st.divider()

    st.subheader("AI Finance Assistant")
    st.caption("Powered by Google Gemini -- Ask anything about your spending!")

    chat_container = st.container(height=260)
    with chat_container:
        if not st.session_state.chat_history:
            st.markdown(
                '<div class="chat-msg-ai">Hi! Ask me about your spending habits, '
                'where to cut costs, or budget tips!</div>',
                unsafe_allow_html=True,
            )
        for msg in st.session_state.chat_history:
            css    = "chat-msg-user" if msg["role"] == "user" else "chat-msg-ai"
            prefix = "You: "         if msg["role"] == "user" else "AI: "
            st.markdown(
                '<div class="' + css + '">' + prefix + msg["content"] + '</div>',
                unsafe_allow_html=True,
            )

    with st.form("chat_form", clear_on_submit=True):
        user_q = st.text_input(
            "Ask", placeholder="Where am I overspending?", label_visibility="collapsed"
        )
        send = st.form_submit_button("Send", use_container_width=True, type="primary")

    if send and user_q:
        with st.spinner("AI thinking..."):
            ai_chat(user_q)
        st.rerun()

    if st.button("Clear Chat"):
        st.session_state.chat_history = []
        st.rerun()