import sqlite3
import os
import sys

if getattr(sys, 'frozen', False):
    BASE_DIR = os.path.dirname(os.path.abspath(sys.executable))
else:
    BASE_DIR = os.path.dirname(os.path.abspath(__file__))

DB_PATH = os.path.join(BASE_DIR, "veloxdonate.db")

def get_connection():
    conn = sqlite3.connect(DB_PATH)
    conn.row_factory = sqlite3.Row
    return conn

def init_db():
    conn = get_connection()
    cursor = conn.cursor()
    cursor.execute("""
        CREATE TABLE IF NOT EXISTS donations (
            id TEXT PRIMARY KEY,
            name TEXT NOT NULL,
            message TEXT,
            amount REAL NOT NULL,
            status TEXT NOT NULL,
            created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
            paid_at TIMESTAMP
        )
    """)
    
    # Check if legacy decimal_amount column exists
    cursor.execute("PRAGMA table_info(donations)")
    columns = [row["name"] for row in cursor.fetchall()]
    if "decimal_amount" in columns:
        cursor.execute("CREATE TABLE donations_new (id TEXT PRIMARY KEY, name TEXT NOT NULL, message TEXT, amount REAL NOT NULL, status TEXT NOT NULL, created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP, paid_at TIMESTAMP)")
        cursor.execute("INSERT INTO donations_new (id, name, message, amount, status, created_at, paid_at) SELECT id, name, message, amount, status, created_at, paid_at FROM donations")
        cursor.execute("DROP TABLE donations")
        cursor.execute("ALTER TABLE donations_new RENAME TO donations")
        conn.commit()
        print("[SQLite Migration] Legacy decimal_amount column removed cleanly!")
        
    conn.close()
    print(f"[SQLite] Database initialized cleanly at: {DB_PATH}")

def save_donation(donation_id, name, message, amount, status="pending"):
    try:
        conn = get_connection()
        cursor = conn.cursor()
        cursor.execute("""
            INSERT OR REPLACE INTO donations (id, name, message, amount, status)
            VALUES (?, ?, ?, ?, ?)
        """, (donation_id, name, message, float(amount), status))
        conn.commit()
        conn.close()
        print(f"[SQLite] Saved donation: {donation_id} ({name} - {amount} THB)")
    except Exception as e:
        print(f"[SQLite Error] Failed to save donation: {e}")

def mark_donation_paid(donation_id):
    try:
        conn = get_connection()
        cursor = conn.cursor()
        cursor.execute("""
            UPDATE donations
            SET status = 'success', paid_at = CURRENT_TIMESTAMP
            WHERE id = ?
        """, (donation_id,))
        conn.commit()
        conn.close()
        print(f"[SQLite] Marked donation as PAID: {donation_id}")
    except Exception as e:
        print(f"[SQLite Error] Failed to mark donation paid: {e}")

def mark_donation_abandoned(donation_id):
    try:
        conn = get_connection()
        cursor = conn.cursor()
        cursor.execute("""
            UPDATE donations
            SET status = 'abandoned'
            WHERE id = ? AND status = 'pending'
        """, (donation_id,))
        conn.commit()
        conn.close()
        print(f"[SQLite] Marked donation as ABANDONED: {donation_id}")
    except Exception as e:
        print(f"[SQLite Error] Failed to mark donation abandoned: {e}")

def get_top_donators(limit=10, start_date=None):
    try:
        conn = get_connection()
        cursor = conn.cursor()
        if start_date and str(start_date).strip():
            cursor.execute("""
                SELECT name, SUM(amount) as total_amount, COUNT(id) as total_count
                FROM donations
                WHERE (status = 'success' OR status = 'paid')
                  AND date(COALESCE(paid_at, created_at)) >= date(?)
                GROUP BY LOWER(name)
                ORDER BY total_amount DESC
                LIMIT ?
            """, (start_date, limit))
        else:
            cursor.execute("""
                SELECT name, SUM(amount) as total_amount, COUNT(id) as total_count
                FROM donations
                WHERE (status = 'success' OR status = 'paid')
                GROUP BY LOWER(name)
                ORDER BY total_amount DESC
                LIMIT ?
            """, (limit,))
        rows = cursor.fetchall()
        conn.close()
        return [dict(row) for row in rows]
    except Exception as e:
        print(f"[SQLite Error] Failed to fetch top donators: {e}")
        return []

def get_recent_donations(limit=10):
    try:
        conn = get_connection()
        cursor = conn.cursor()
        cursor.execute("""
            SELECT id, name, message, amount, paid_at, created_at
            FROM donations
            WHERE (status = 'success' OR status = 'paid')
            ORDER BY COALESCE(paid_at, created_at) DESC
            LIMIT ?
        """, (limit,))
        rows = cursor.fetchall()
        conn.close()
        return [dict(row) for row in rows]
    except Exception as e:
        print(f"[SQLite Error] Failed to fetch recent donations: {e}")
        return []

def get_goal_total(start_date=None, end_date=None):
    try:
        conn = get_connection()
        cursor = conn.cursor()
        query = "SELECT COALESCE(SUM(amount), 0) as total FROM donations WHERE (status = 'success' OR status = 'paid')"
        params = []
        if start_date and str(start_date).strip():
            query += " AND date(COALESCE(paid_at, created_at)) >= date(?)"
            params.append(start_date)
        if end_date and str(end_date).strip():
            query += " AND date(COALESCE(paid_at, created_at)) <= date(?)"
            params.append(end_date)
            
        cursor.execute(query, params)
        row = cursor.fetchone()
        conn.close()
        return float(row["total"]) if row and row["total"] else 0.0
    except Exception as e:
        print(f"[SQLite Error] Failed to fetch goal total: {e}")
        return 0.0

def get_donation_stats():
    try:
        conn = get_connection()
        cursor = conn.cursor()
        cursor.execute("""
            SELECT COUNT(id) as total_donations, COALESCE(SUM(amount), 0) as total_raised
            FROM donations
            WHERE (status = 'success' OR status = 'paid')
        """)
        row = cursor.fetchone()
        conn.close()
        return dict(row)
    except Exception as e:
        print(f"[SQLite Error] Failed to fetch stats: {e}")
        return {"total_donations": 0, "total_raised": 0}

def get_all_donations(limit=200):
    try:
        conn = get_connection()
        cursor = conn.cursor()
        cursor.execute("""
            SELECT id, name, amount, message, status, COALESCE(paid_at, created_at) as timestamp
            FROM donations
            ORDER BY COALESCE(paid_at, created_at) DESC
            LIMIT ?
        """, (limit,))
        rows = cursor.fetchall()
        conn.close()
        return [dict(row) for row in rows]
    except Exception as e:
        print(f"[SQLite Error] Failed to fetch all donations: {e}")
        return []

def delete_donation(donation_id):
    try:
        conn = get_connection()
        cursor = conn.cursor()
        cursor.execute("DELETE FROM donations WHERE id = ?", (donation_id,))
        conn.commit()
        conn.close()
        return True
    except Exception as e:
        print(f"[SQLite Error] Failed to delete donation {donation_id}: {e}")
        return False

def clear_all_donations():
    try:
        conn = get_connection()
        cursor = conn.cursor()
        cursor.execute("DELETE FROM donations")
        conn.commit()
        conn.close()
        return True
    except Exception as e:
        print(f"[SQLite Error] Failed to clear donations: {e}")
        return False

if __name__ == "__main__":
    init_db()
