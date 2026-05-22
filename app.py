import sqlite3
import math
from datetime import datetime, timedelta

from flask import Flask, flash, redirect, render_template, request, session, url_for, abort
from werkzeug.security import check_password_hash

from database.db import create_user, get_db, get_user_by_email, init_db, seed_db
from database.queries import (
    get_category_breakdown,
    get_recent_transactions,
    get_summary_stats,
    get_user_by_id,
    insert_expense,
    get_expense_by_id,
    update_expense,
)

app = Flask(__name__)
app.secret_key = "dev-secret-key"

with app.app_context():
    init_db()
    seed_db()



# ------------------------------------------------------------------ #
# Constants                                                              #
# ------------------------------------------------------------------ #

VALID_CATEGORIES = ["Food", "Transport", "Bills", "Health", "Entertainment", "Shopping", "Other"]


# ------------------------------------------------------------------ #
# Routes                                                              #
# ------------------------------------------------------------------ #

@app.route("/")
def landing():
    return render_template("landing.html")


@app.route("/register", methods=["GET", "POST"])
def register():
    if session.get("user_id"):
        return redirect(url_for("profile"))
    if request.method == "POST":
        name = request.form.get("name", "").strip()
        email = request.form.get("email", "").strip()
        password = request.form.get("password", "")
        confirm_password = request.form.get("confirm_password", "")

        if not all([name, email, password, confirm_password]):
            flash("All fields are required.", "error")
            return render_template("register.html")

        if password != confirm_password:
            flash("Passwords do not match.", "error")
            return render_template("register.html")

        try:
            create_user(name, email, password)
        except sqlite3.IntegrityError:
            flash("Email already registered.", "error")
            return render_template("register.html")

        flash("Account created! Please sign in.", "success")
        return redirect(url_for("login"))

    return render_template("register.html")


@app.route("/login", methods=["GET", "POST"])
def login():
    if session.get("user_id"):
        return redirect(url_for("profile"))
    if request.method == "POST":
        email = request.form.get("email", "").strip()
        password = request.form.get("password", "")

        user = get_user_by_email(email)
        if not user or not check_password_hash(user["password_hash"], password):
            flash("Invalid email or password.", "error")
            return render_template("login.html")

        session["user_id"] = user["id"]
        session["user_name"] = user["name"]
        return redirect(url_for("profile"))

    return render_template("login.html")


# ------------------------------------------------------------------ #
# Placeholder routes — students will implement these                  #
# ------------------------------------------------------------------ #

@app.route("/terms")
def terms():
    return render_template("terms.html")


@app.route("/privacy")
def privacy():
    return render_template("privacy.html")


@app.route("/logout")
def logout():
    session.clear()
    flash("You have been logged out.", "success")
    return redirect(url_for("landing"))


def get_date_range(preset, date_from, date_to):
    """Calculates and validates date ranges for profile filtering."""
    today = datetime.now()

    match preset:
        case "this_month":
            date_from = today.replace(day=1).strftime("%Y-%m-%d")
            date_to = today.strftime("%Y-%m-%d")
        case "last_3_months":
            date_from = (today - timedelta(days=90)).strftime("%Y-%m-%d")
            date_to = today.strftime("%Y-%m-%d")
        case "last_6_months":
            date_from = (today - timedelta(days=180)).strftime("%Y-%m-%d")
            date_to = today.strftime("%Y-%m-%d")
        case "all_time" | None:
            date_from, date_to = None, None

    if date_from and date_to:
        try:
            d_from = datetime.strptime(date_from, "%Y-%m-%d")
            d_to = datetime.strptime(date_to, "%Y-%m-%d")
            if d_from > d_to:
                return None, None, "all_time", "Start date must be before end date."
        except ValueError:
            return None, None, "all_time", None

    # Determine active preset if not set by preset param
    active_preset = preset if preset else ("custom" if date_from and date_to else "all_time")

    return date_from, date_to, active_preset, None

@app.route("/profile")
def profile():
    if not session.get("user_id"):
        return redirect(url_for("login"))

    uid = session["user_id"]

    active_preset = request.args.get("preset")
    date_from = request.args.get("date_from")
    date_to = request.args.get("date_to")

    date_from, date_to, active_preset, error = get_date_range(active_preset, date_from, date_to)
    if error:
        flash(error, "error")

    return render_template(
        "profile.html",
        user=get_user_by_id(uid),
        stats=get_summary_stats(uid, date_from, date_to),
        expenses=get_recent_transactions(uid, date_from=date_from, date_to=date_to),
        categories=get_category_breakdown(uid, date_from, date_to),
        date_from=date_from,
        date_to=date_to,
        active_preset=active_preset,
    )


@app.route("/analytics")
def analytics():
    if not session.get("user_id"):
        return redirect(url_for("login"))
    return render_template("analytics.html")


@app.route("/expenses/add", methods=["GET", "POST"])
def add_expense():
    if not session.get("user_id"):
        return redirect(url_for("login"))

    if request.method == "POST":
        amount_str = request.form.get("amount", "").strip()
        category = request.form.get("category", "").strip()
        date_str = request.form.get("date", "").strip()
        description = request.form.get("description", "").strip()

        errors = []

        # Amount validation
        try:
            amount = float(amount_str)
            if not math.isfinite(amount) or amount <= 0:
                errors.append("Amount must be a finite number greater than 0.")
        except (ValueError, TypeError):
            errors.append("Please enter a valid numeric amount.")

        # Category validation
        if not category or category not in VALID_CATEGORIES:
            errors.append("Please select a valid category.")

        # Date validation
        if not date_str:
            errors.append("Date is required.")
        else:
            try:
                parsed_date = datetime.strptime(date_str, "%Y-%m-%d")
                if parsed_date > datetime.now():
                    errors.append("Expense date cannot be in the future.")
            except ValueError:
                errors.append("Invalid date format. Please use YYYY-MM-DD.")

        if errors:
            for error in errors:
                flash(error, "error")
            return render_template("add_expense.html")

        # Successful validation
        insert_expense(
            user_id=session["user_id"],
            amount=amount,
            category=category,
            date=date_str,
            description=description if description else None,
        )
        flash("Expense added successfully!", "success")
        return redirect(url_for("profile"))

    return render_template("add_expense.html")


@app.route("/expenses/<int:id>/edit", methods=["GET", "POST"])
def edit_expense(id):
    if not session.get("user_id"):
        return redirect(url_for("login"))

    uid = session["user_id"]
    expense = get_expense_by_id(id, uid)

    if not expense:
        return abort(404)

    if request.method == "POST":
        amount_str = request.form.get("amount", "").strip()
        category = request.form.get("category", "").strip()
        date_str = request.form.get("date", "").strip()
        description = request.form.get("description", "").strip()

        errors = []

        # Amount validation
        try:
            amount = float(amount_str)
            if not math.isfinite(amount) or amount <= 0:
                errors.append("Amount must be a finite number greater than 0.")
        except (ValueError, TypeError):
            errors.append("Please enter a valid numeric amount.")

        # Category validation
        if not category or category not in VALID_CATEGORIES:
            errors.append("Please select a valid category.")

        # Date validation
        if not date_str:
            errors.append("Date is required.")
        else:
            try:
                parsed_date = datetime.strptime(date_str, "%Y-%m-%d")
                if parsed_date > datetime.now():
                    errors.append("Expense date cannot be in the future.")
            except ValueError:
                errors.append("Invalid date format. Please use YYYY-MM-DD.")

        if errors:
            for error in errors:
                flash(error, "error")
            return render_template(
                "edit_expense.html",
                expense=expense,
                categories=VALID_CATEGORIES,
                form_data={
                    "amount": amount_str,
                    "category": category,
                    "date": date_str,
                    "description": description,
                },
            )

        # Successful validation
        update_expense(
            expense_id=id,
            user_id=uid,
            amount=amount,
            category=category,
            date=date_str,
            description=description if description else None,
        )
        flash("Expense updated successfully!", "success")
        return redirect(url_for("profile"))

    return render_template(
        "edit_expense.html",
        expense=expense,
        categories=VALID_CATEGORIES
    )


@app.route("/expenses/<int:id>/delete")
def delete_expense(id):
    return "Delete expense — coming in Step 9"


if __name__ == "__main__":
    app.run(debug=True, port=5001)
