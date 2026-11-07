import os
import requests
import pandas as pd
import streamlit as st
from datetime import date

API_URL = os.getenv("API_BASE_URL", "http://127.0.0.1:8000")

st.set_page_config(
    page_title="Expense Tracker",
    page_icon="💰",
    layout="wide"
)

st.title("💰 Expense Tracker")
st.caption("Manage your daily expenses with FastAPI and Streamlit")

# ---------------- API HELPERS ----------------

def api_request(method, endpoint, **kwargs):
    try:
        response = requests.request(
            method,
            f"{API_URL}{endpoint}",
            timeout=10,
            **kwargs
        )
        response.raise_for_status()

        if response.content:
            return response.json()

        return None

    except requests.exceptions.ConnectionError:
        st.error("Cannot connect to FastAPI. Start your backend first.")
    except requests.exceptions.HTTPError as e:
        try:
            detail = response.json().get("detail", response.text)
        except ValueError:
            detail = response.text

        st.error(f"API Error: {detail}")
    except requests.exceptions.RequestException as e:
        st.error(f"Request failed: {e}")

    return None


def refresh_data():
    st.session_state.pop("expenses", None)


def get_expenses(start_date, end_date):
    return api_request(
        "GET",
        "/expenses",
        params={
            "start_date": start_date.isoformat(),
            "end_date": end_date.isoformat()
        }
    )


# ---------------- SIDEBAR ----------------

st.sidebar.header("Navigation")

page = st.sidebar.radio(
    "Choose an operation",
    [
        "Dashboard",
        "Add Expense",
        "Edit Expense",
        "Delete Expense"
    ]
)

st.sidebar.divider()
st.sidebar.write("Backend API")
st.sidebar.code(API_URL)

if st.sidebar.button("Check API connection"):
    try:
        response = requests.get(f"{API_URL}/docs", timeout=5)
        if response.ok:
            st.sidebar.success("FastAPI Connected")
        else:
            st.sidebar.warning("API responded with an error")
    except requests.RequestException:
        st.sidebar.error("API is not reachable")


# ---------------- DASHBOARD ----------------

if page == "Dashboard":

    st.header("Expense Dashboard")

    col1, col2 = st.columns(2)

    with col1:
        start_date = st.date_input(
            "Start Date",
            value=date.today().replace(day=1)
        )

    with col2:
        end_date = st.date_input(
            "End Date",
            value=date.today()
        )

    if start_date > end_date:
        st.warning("Start date cannot be after end date.")

    else:
        if st.button("Load Expenses"):
            st.session_state.expenses = get_expenses(
                start_date,
                end_date
            )

        expenses = st.session_state.get("expenses")

        if expenses is not None:

            if expenses:

                df = pd.DataFrame(expenses)

                total = df["amount"].sum()
                count = len(df)
                average = total / count

                c1, c2, c3 = st.columns(3)

                c1.metric("Total Spending", f"₹{total:,.2f}")
                c2.metric("Total Transactions", count)
                c3.metric("Average Expense", f"₹{average:,.2f}")

                st.subheader("All Expenses")

                st.dataframe(
                    df,
                    use_container_width=True,
                    hide_index=True
                )

                st.subheader("Spending by Category")

                summary = api_request(
                    "GET",
                    "/expenses/summarize",
                    params={
                        "start_date": start_date.isoformat(),
                        "end_date": end_date.isoformat()
                    }
                )

                if summary:
                    summary_df = pd.DataFrame(summary)

                    st.bar_chart(
                        summary_df.set_index("category")["total_amount"]
                    )

                    st.dataframe(
                        summary_df,
                        use_container_width=True,
                        hide_index=True
                    )
                else:
                    st.info("No category summary available.")

            else:
                st.info("No expenses found for this date range.")


# ---------------- ADD EXPENSE ----------------

elif page == "Add Expense":

    st.header("Add a New Expense")

    with st.form("add_expense_form"):

        expense_date = st.date_input("Expense Date", value=date.today())

        amount = st.number_input(
            "Amount (₹)",
            min_value=0.01,
            step=1.0
        )

        category = st.text_input(
            "Category",
            placeholder="Food, Travel, Shopping..."
        )

        subcategory = st.text_input(
            "Subcategory",
            placeholder="Lunch, Bus, Clothes..."
        )

        note = st.text_area("Note")

        submitted = st.form_submit_button("Add Expense")

        if submitted:

            if not category.strip():
                st.warning("Please enter a category.")

            else:
                payload = {
                    "date": expense_date.isoformat(),
                    "amount": amount,
                    "category": category.strip(),
                    "subcategory": subcategory.strip(),
                    "note": note.strip()
                }

                result = api_request(
                    "POST",
                    "/expenses",
                    json=payload
                )

                if result:
                    st.success(
                        f"Expense added successfully! ID: {result['id']}"
                    )
                    refresh_data()


# ---------------- EDIT EXPENSE ----------------

elif page == "Edit Expense":

    st.header("Edit an Existing Expense")

    expense_id = st.number_input(
        "Expense ID",
        min_value=1,
        step=1
    )

    st.info("Enter only the fields you want to change.")

    with st.form("edit_expense_form"):

        new_date = st.date_input(
            "New Date",
            value=date.today()
        )

        update_date = st.checkbox("Update date")

        new_amount = st.number_input(
            "New Amount (₹)",
            min_value=0.01,
            step=1.0
        )

        update_amount = st.checkbox("Update amount")

        new_category = st.text_input("New Category")
        update_category = st.checkbox("Update category")

        new_subcategory = st.text_input("New Subcategory")
        update_subcategory = st.checkbox("Update subcategory")

        new_note = st.text_area("New Note")
        update_note = st.checkbox("Update note")

        submitted = st.form_submit_button("Save Changes")

        if submitted:

            payload = {}

            if update_date:
                payload["date"] = new_date.isoformat()

            if update_amount:
                payload["amount"] = new_amount

            if update_category:
                payload["category"] = new_category.strip()

            if update_subcategory:
                payload["subcategory"] = new_subcategory.strip()

            if update_note:
                payload["note"] = new_note.strip()

            if not payload:
                st.warning("Select at least one field to update.")

            else:
                result = api_request(
                    "PUT",
                    f"/expenses/{int(expense_id)}",
                    json=payload
                )

                if result:
                    st.success("Expense updated successfully!")
                    refresh_data()


