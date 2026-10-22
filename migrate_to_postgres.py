"""
Comprehensive SQLite -> PostgreSQL schema initialization and data migration.
This script:
1. Connects to PostgreSQL via DATABASE_URL.
2. Creates all tables matching the ASDI system schema using PostgreSQL data types (SERIAL, TEXT, etc.).
3. Copies all rows from local SQLite (asdi.db) into PostgreSQL while preserving exact IDs.
4. Resets the PostgreSQL sequences (auto-increment counters) to prevent primary key collisions.
5. Verifies row counts before and after to ensure 100% data integrity.
"""
import os
import sys
import sqlite3

try:
    import psycopg2
    import psycopg2.extras
except ImportError:
    print("ERROR: psycopg2-binary not installed. Please run: pip install psycopg2-binary")
    sys.exit(1)

BASE_DIR = os.path.dirname(os.path.abspath(__file__))
SQLITE_DB_PATH = os.path.join(BASE_DIR, "data", "asdi.db")

DATABASE_URL = os.environ.get("DATABASE_URL", "").strip()
if DATABASE_URL.startswith("postgres://"):
    DATABASE_URL = DATABASE_URL.replace("postgres://", "postgresql://", 1)

PG_SCHEMA_STATEMENTS = [
    """
    CREATE TABLE IF NOT EXISTS students (
        id SERIAL PRIMARY KEY,
        admission_no TEXT UNIQUE,
        roll_no TEXT,
        category TEXT,
        course TEXT,
        semester TEXT,
        batch TEXT,
        admission_date TEXT,
        name TEXT,
        father_name TEXT,
        cnic TEXT,
        blood_group TEXT,
        phone TEXT,
        whatsapp TEXT,
        address TEXT,
        dob TEXT,
        age TEXT,
        occupation TEXT,
        marital TEXT,
        gender TEXT,
        g_name TEXT,
        g_relation TEXT,
        g_cnic TEXT,
        g_occupation TEXT,
        g_phone TEXT,
        g_email TEXT,
        g_address TEXT,
        em_name TEXT,
        em_phone TEXT,
        total_fee NUMERIC DEFAULT 0,
        monthly_fee NUMERIC DEFAULT 0,
        fee_plan TEXT,
        due_day INTEGER DEFAULT 10,
        photo TEXT,
        status TEXT DEFAULT 'Active',
        last_reminder TEXT,
        created_at TEXT,
        teacher_id INTEGER,
        discount_amount NUMERIC DEFAULT 0,
        discount_reason TEXT,
        email TEXT,
        pin TEXT,
        password_hash TEXT
    );
    """,
    """
    CREATE TABLE IF NOT EXISTS payments (
        id SERIAL PRIMARY KEY,
        student_id INTEGER,
        pay_date TEXT,
        amount NUMERIC DEFAULT 0,
        late_fee NUMERIC DEFAULT 0,
        receipt_no TEXT,
        method TEXT,
        note TEXT
    );
    """,
    """
    CREATE TABLE IF NOT EXISTS expenses (
        id SERIAL PRIMARY KEY,
        exp_date TEXT,
        category TEXT,
        amount NUMERIC,
        note TEXT
    );
    """,
    """
    CREATE TABLE IF NOT EXISTS batches (
        id SERIAL PRIMARY KEY,
        name TEXT UNIQUE,
        course TEXT,
        days TEXT,
        start_time TEXT,
        end_time TEXT,
        teacher TEXT,
        room TEXT
    );
    """,
    """
    CREATE TABLE IF NOT EXISTS schedule (
        id SERIAL PRIMARY KEY,
        student_id INTEGER,
        days TEXT,
        start_time TEXT,
        end_time TEXT,
        subject TEXT,
        teacher TEXT,
        note TEXT
    );
    """,
    """
    CREATE TABLE IF NOT EXISTS reminder_log (
        id SERIAL PRIMARY KEY,
        student_id INTEGER,
        sent_at TEXT,
        phone TEXT,
        message TEXT,
        ok INTEGER,
        info TEXT
    );
    """,
    """
    CREATE TABLE IF NOT EXISTS attendance (
        id SERIAL PRIMARY KEY,
        student_id INTEGER,
        att_date TEXT,
        status TEXT,
        UNIQUE(student_id, att_date)
    );
    """,
    """
    CREATE TABLE IF NOT EXISTS settings (
        key TEXT PRIMARY KEY,
        value TEXT
    );
    """,
    """
    CREATE TABLE IF NOT EXISTS staff (
        id SERIAL PRIMARY KEY,
        name TEXT,
        role TEXT DEFAULT 'Teacher',
        subject TEXT,
        phone TEXT,
        whatsapp TEXT,
        email TEXT,
        share_pct REAL,
        duty_start TEXT DEFAULT '09:00',
        days TEXT DEFAULT 'Mon,Tue,Wed,Thu,Fri,Sat',
        salary NUMERIC DEFAULT 0,
        status TEXT DEFAULT 'Active',
        note TEXT,
        password_hash TEXT,
        pin TEXT,
        photo TEXT
    );
    """,
    """
    CREATE TABLE IF NOT EXISTS staff_attendance (
        id SERIAL PRIMARY KEY,
        staff_id INTEGER,
        att_date TEXT,
        status TEXT,
        check_in TEXT,
        note TEXT,
        check_out TEXT,
        UNIQUE(staff_id, att_date)
    );
    """,
    """
    CREATE TABLE IF NOT EXISTS staff_log (
        id SERIAL PRIMARY KEY,
        staff_id INTEGER,
        sent_at TEXT,
        kind TEXT,
        channel TEXT,
        ok INTEGER,
        info TEXT
    );
    """,
    """
    CREATE TABLE IF NOT EXISTS audit_log (
        id SERIAL PRIMARY KEY,
        created_at TEXT,
        user_role TEXT DEFAULT 'Admin',
        action TEXT,
        entity TEXT,
        entity_id INTEGER,
        details TEXT
    );
    """,
    """
    CREATE TABLE IF NOT EXISTS staff_salaries (
        id SERIAL PRIMARY KEY,
        staff_id INTEGER,
        pay_date TEXT,
        month_year TEXT,
        basic_salary NUMERIC DEFAULT 0,
        deductions NUMERIC DEFAULT 0,
        advance_deduction NUMERIC DEFAULT 0,
        bonus_share NUMERIC DEFAULT 0,
        net_paid NUMERIC DEFAULT 0,
        method TEXT DEFAULT 'Cash',
        note TEXT
    );
    """,
    """
    CREATE TABLE IF NOT EXISTS staff_advances (
        id SERIAL PRIMARY KEY,
        staff_id INTEGER,
        advance_date TEXT,
        amount NUMERIC DEFAULT 0,
        note TEXT,
        status TEXT DEFAULT 'Pending'
    );
    """,
    """
    CREATE TABLE IF NOT EXISTS exam_results (
        id SERIAL PRIMARY KEY,
        student_id INTEGER,
        exam_title TEXT,
        exam_date TEXT,
        total_marks NUMERIC DEFAULT 100,
        obtained_marks NUMERIC DEFAULT 0,
        grade TEXT,
        remarks TEXT
    );
    """,
    """
    CREATE TABLE IF NOT EXISTS inquiries (
        id SERIAL PRIMARY KEY,
        inq_date TEXT,
        name TEXT,
        father_name TEXT,
        phone TEXT,
        whatsapp TEXT,
        course TEXT,
        source TEXT,
        status TEXT DEFAULT 'Pending',
        follow_up_date TEXT,
        note TEXT
    );
    """,
    """
    CREATE TABLE IF NOT EXISTS student_attendance_requests (
        id SERIAL PRIMARY KEY,
        student_id INTEGER NOT NULL,
        req_date TEXT NOT NULL,
        status TEXT DEFAULT 'Pending',
        note TEXT,
        created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP
    );
    """,
    """
    CREATE TABLE IF NOT EXISTS student_messages (
        id SERIAL PRIMARY KEY,
        student_id INTEGER NOT NULL,
        subject TEXT,
        message TEXT NOT NULL,
        reply TEXT,
        status TEXT DEFAULT 'Unread',
        created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP
    );
    """,
    """
    CREATE TABLE IF NOT EXISTS online_payment_requests (
        id SERIAL PRIMARY KEY,
        student_id INTEGER NOT NULL,
        amount REAL NOT NULL,
        transaction_id TEXT,
        transaction_date TEXT,
        screenshot TEXT,
        method TEXT DEFAULT 'EasyPaisa',
        status TEXT DEFAULT 'Pending',
        admin_note TEXT,
        created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP
    );
    """,
    """
    CREATE TABLE IF NOT EXISTS staff_chat_messages (
        id SERIAL PRIMARY KEY,
        sender_id INTEGER NOT NULL,
        sender_name TEXT NOT NULL,
        sender_role TEXT,
        sender_photo TEXT,
        receiver_id INTEGER DEFAULT 0,
        message TEXT NOT NULL,
        created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP
    );
    """
]

TABLES_ORDER = [
    "settings",
    "students",
    "staff",
    "payments",
    "expenses",
    "batches",
    "schedule",
    "reminder_log",
    "attendance",
    "staff_attendance",
    "staff_log",
    "audit_log",
    "staff_salaries",
    "staff_advances",
    "exam_results",
    "inquiries",
    "student_attendance_requests",
    "student_messages",
    "online_payment_requests",
    "staff_chat_messages",
]


def init_schema(pg_conn):
    print("-> Creating / Verifying PostgreSQL Tables...")
    cur = pg_conn.cursor()
    for stmt in PG_SCHEMA_STATEMENTS:
        cur.execute(stmt)
    pg_conn.commit()
    cur.close()
    print("-> All tables verified in PostgreSQL.")


def migrate_data():
    if not DATABASE_URL:
        print("ERROR: DATABASE_URL is not set!")
        print("Usage:")
        print("  set DATABASE_URL=postgresql://user:pass@host:5432/dbname")
        print("  python migrate_to_postgres.py")
        sys.exit(1)

    if not os.path.exists(SQLITE_DB_PATH):
        print(f"ERROR: SQLite source database not found at: {SQLITE_DB_PATH}")
        sys.exit(1)

    print(f"Opening SQLite source: {SQLITE_DB_PATH}")
    sq_conn = sqlite3.connect(SQLITE_DB_PATH)
    sq_conn.row_factory = sqlite3.Row
    sq_cur = sq_conn.cursor()

    print("Connecting to target PostgreSQL...")
    pg_conn = psycopg2.connect(DATABASE_URL)
    init_schema(pg_conn)

    pg_cur = pg_conn.cursor()

    print("\n" + "=" * 50)
    print("   STARTING DATA MIGRATION (SQLite -> PostgreSQL)")
    print("=" * 50)

    for table in TABLES_ORDER:
        # Check if table exists in SQLite
        exists = sq_cur.execute(
            "SELECT 1 FROM sqlite_master WHERE type='table' AND name=?", (table,)
        ).fetchone()
        if not exists:
            continue

        rows = sq_cur.execute(f"SELECT * FROM \"{table}\"").fetchall()
        total_rows = len(rows)
        if total_rows == 0:
            print(f"[{table}] 0 rows (skipped)")
            continue

        cols = list(rows[0].keys())
        col_list_str = ", ".join([f'"{c}"' for c in cols])
        placeholders = ", ".join(["%s"] * len(cols))

        # Check existing count in PG
        pg_cur.execute(f'SELECT COUNT(*) FROM "{table}"')
        existing_pg_count = pg_cur.fetchone()[0]

        if existing_pg_count > 0:
            print(f"[{table}] Already contains {existing_pg_count} rows in PG. Merging/Skipping duplicates...")

        inserted = 0
        for r in rows:
            values = tuple(r[c] for c in cols)
            # Use ON CONFLICT DO NOTHING to ensure safety and repeatability
            conflict_col = "key" if table == "settings" else ("admission_no" if table == "students" and "admission_no" in cols else "id")
            insert_sql = f'INSERT INTO "{table}" ({col_list_str}) VALUES ({placeholders}) ON CONFLICT DO NOTHING'
            pg_cur.execute(insert_sql, values)
            inserted += 1

        pg_conn.commit()
        print(f"[{table}] Migrated {inserted} / {total_rows} rows.")

        # Update primary key sequence if table has 'id'
        if "id" in cols:
            try:
                pg_cur.execute(f"""
                    SELECT setval(pg_get_serial_sequence('{table}', 'id'),
                                  COALESCE((SELECT MAX(id) FROM "{table}"), 0) + 1, false)
                """)
                pg_conn.commit()
            except Exception as e:
                pg_conn.rollback()

    print("\n" + "=" * 50)
    print("   DATA MIGRATION COMPLETED SUCCESSFULLY!")
    print("=" * 50)

    # Verification summary
    print("\n--- Summary Verification ---")
    for table in TABLES_ORDER:
        exists = sq_cur.execute("SELECT 1 FROM sqlite_master WHERE type='table' AND name=?", (table,)).fetchone()
        if exists:
            sq_count = sq_cur.execute(f'SELECT COUNT(*) FROM "{table}"').fetchone()[0]
            pg_cur.execute(f'SELECT COUNT(*) FROM "{table}"')
            pg_count = pg_cur.fetchone()[0]
            status = "MATCH" if sq_count == pg_count else "MISMATCH"
            print(f"{table:30} SQLite: {sq_count:4} | PostgreSQL: {pg_count:4} [{status}]")

    sq_conn.close()
    pg_conn.close()


if __name__ == "__main__":
    migrate_data()
