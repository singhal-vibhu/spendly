from datetime import datetime

from database.db import get_db


def insert_expense(user_id, amount, category, date, description):
    conn = get_db()
    try:
        cursor = conn.execute(
            "INSERT INTO expenses (user_id, amount, category, date, description) VALUES (?, ?, ?, ?, ?)",
            (user_id, amount, category, date, description),
        )
        conn.commit()
        expense_id = cursor.lastrowid
        return expense_id
    finally:
        conn.close()


def get_user_by_id(user_id):
    conn = get_db()
    row = conn.execute(
        "SELECT id, name, email, created_at FROM users WHERE id = ?",
        (user_id,),
    ).fetchone()
    conn.close()

    if row is None:
        return None

    name = row["name"]
    initials = "".join(w[0].upper() for w in name.split() if w)
    member_since = datetime.strptime(row["created_at"], "%Y-%m-%d %H:%M:%S").strftime("%B %Y")

    return {
        "name": name,
        "email": row["email"],
        "initials": initials,
        "member_since": member_since,
    }


def get_recent_transactions(user_id, date_from=None, date_to=None, limit=10):
    conn = get_db()
    query = """
        SELECT date, description, category, amount
        FROM expenses
        WHERE user_id = ?
    """
    params = [user_id]

    if date_from and date_to:
        query += " AND date BETWEEN ? AND ?"
        params.extend([date_from, date_to])

    query += " ORDER BY date DESC, id DESC LIMIT ?"
    params.append(limit)

    rows = conn.execute(query, params).fetchall()
    conn.close()

    return [
        {
            "date": datetime.strptime(row["date"], "%Y-%m-%d").strftime("%d %b %Y"),
            "description": row["description"],
            "category": row["category"],
            "amount": "{:,.2f}".format(row["amount"]),
        }
        for row in rows
    ]


def get_summary_stats(user_id, date_from=None, date_to=None):
    conn = get_db()
    query = "SELECT COALESCE(SUM(amount), 0) AS total, COUNT(*) AS count FROM expenses WHERE user_id = ?"
    params = [user_id]

    if date_from and date_to:
        query += " AND date BETWEEN ? AND ?"
        params.extend([date_from, date_to])

    row = conn.execute(query, params).fetchone()
    total_value = row["total"]
    count = row["count"]

    cat_query = "SELECT category FROM expenses WHERE user_id = ?"
    cat_params = [user_id]

    if date_from and date_to:
        cat_query += " AND date BETWEEN ? AND ?"
        cat_params.extend([date_from, date_to])

    cat_query += " GROUP BY category ORDER BY SUM(amount) DESC LIMIT 1"
    cat_row = conn.execute(cat_query, cat_params).fetchone()
    conn.close()

    return {
        "total": "{:,.2f}".format(total_value),
        "count": count,
        "top_category": cat_row["category"] if cat_row else "—",
    }


def get_category_breakdown(user_id, date_from=None, date_to=None):
    conn = get_db()
    query = """
        SELECT category AS name, SUM(amount) AS total
        FROM expenses
        WHERE user_id = ?
    """
    params = [user_id]

    if date_from and date_to:
        query += " AND date BETWEEN ? AND ?"
        params.extend([date_from, date_to])

    query += """
        GROUP BY category
        ORDER BY total DESC
    """
    rows = conn.execute(query, params).fetchall()
    conn.close()

    grand_total = sum(r["total"] for r in rows)
    if grand_total == 0:
        return []

    pcts = [int(r["total"] / grand_total * 100) for r in rows]
    pcts[0] += 100 - sum(pcts)

    return [
        {
            "name": r["name"],
            "amount": "{:,.2f}".format(r["total"]),
            "percent": pct,
        }
        for r, pct in zip(rows, pcts)
    ]
