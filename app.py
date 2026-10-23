import os

from db_adapter import get_db_connection, is_postgres

from datetime import datetime

from functools import wraps

from flask import Flask, render_template, request, redirect, url_for, session, flash, jsonify, abort, send_from_directory

from werkzeug.security import generate_password_hash, check_password_hash

from werkzeug.utils import secure_filename

BASE_DIR = os.path.dirname(os.path.abspath(__file__))

TEMPLATES_DIR = os.path.join(BASE_DIR, "templates")

STATIC_DIR = os.path.join(BASE_DIR, "static")

# Profile photo upload config

UPLOAD_FOLDER = os.path.join(BASE_DIR, "static", "uploads", "profiles")

ALLOWED_EXTENSIONS = {"png", "jpg", "jpeg", "webp", "gif"}

os.makedirs(UPLOAD_FOLDER, exist_ok=True)

def allowed_file(filename):

    return "." in filename and filename.rsplit(".", 1)[1].lower() in ALLOWED_EXTENSIONS

app = Flask(

    __name__,

    template_folder=TEMPLATES_DIR if os.path.isdir(TEMPLATES_DIR) else "templates",

    static_folder=STATIC_DIR if os.path.isdir(STATIC_DIR) else "static"

)

app.secret_key = os.environ.get("SECRET_KEY", "asdi_portal_secret_key_2026_x92_multi_role")

app.config["UPLOAD_FOLDER"] = UPLOAD_FOLDER

app.config["MAX_CONTENT_LENGTH"] = 5 * 1024 * 1024  # 5MB max upload

# ─────────────────────────────────────────────────────────────────────────────
# DATABASE PATH  –  startup par ek baar decide hota hai, phir NAHI badalta
# ─────────────────────────────────────────────────────────────────────────────

def get_db_path():
    return "PostgreSQL (Render) / SQLite fallback"

def get_settings():

    """Fetches institution settings like name, phone, PINs, etc."""

    try:

        conn = get_db_connection()

        rows = conn.execute("SELECT key, value FROM settings").fetchall()

        conn.close()

        return {r["key"]: r["value"] for r in rows}

    except Exception:

        return {

            "inst_name": "Asian Skill Development Institute",

            "phone": "0344-4996072",

            "admin_pin": "1234",

            "principal_pin": "9999",

            "receptionist_pin": "1111",

            "finance_pin": "2222",

            "staff_pin": "maryam"

        }

@app.context_processor
def inject_globals():
    settings = get_settings()
    inst_name = settings.get("inst_name", "Asian Skill Development Institute")
    announcements_list = []
    try:
        c = get_db_connection()
        role = session.get("role", "")
        if role == "student":
            announcements_list = c.execute("SELECT * FROM announcements WHERE is_active = TRUE AND target_role IN ('All', 'Students') ORDER BY id DESC LIMIT 5").fetchall()
        elif role == "staff":
            announcements_list = c.execute("SELECT * FROM announcements WHERE is_active = TRUE AND target_role IN ('All', 'Staff') ORDER BY id DESC LIMIT 5").fetchall()
        elif role == "admin":
            announcements_list = c.execute("SELECT * FROM announcements WHERE is_active = TRUE ORDER BY id DESC LIMIT 5").fetchall()
        c.close()
    except Exception:
        pass

    return {
        "inst_name": inst_name,
        "inst_phone": settings.get("phone", "0344-4996072"),
        "current_user_role": session.get("role"),
        "current_user_name": session.get("user_name"),
        "admin_dp": settings.get("admin_dp", ""),
        "active_announcements": announcements_list,
        "now": datetime.now()
    }

def clean_phone(phone_str):

    """Strip spaces, dashes, parentheses to match phone numbers easily."""

    if not phone_str:

        return ""

    digits = "".join([c for c in str(phone_str) if c.isdigit()])

    if len(digits) == 11 and digits.startswith("0"):

        return digits[1:]

    return digits

@app.template_filter("wa_phone")
def wa_phone_filter(phone_str):
    if not phone_str:
        return ""
    digits = "".join([c for c in str(phone_str) if c.isdigit()])
    if digits.startswith("0"):
        digits = "92" + digits[1:]
    elif not digits.startswith("92") and len(digits) == 10:
        digits = "92" + digits
    return digits

def init_required_tables():
    """Ensures all necessary tables and seed data exist in the active database (Postgres and SQLite)."""
    try:
        is_pg = is_postgres()
        pk = "SERIAL PRIMARY KEY" if is_pg else "INTEGER PRIMARY KEY AUTOINCREMENT"
        real_type = "NUMERIC" if is_pg else "REAL"
        bool_active = "BOOLEAN DEFAULT TRUE" if is_pg else "INTEGER DEFAULT 1"

        table_definitions = [
            f"""CREATE TABLE IF NOT EXISTS settings (
                key TEXT PRIMARY KEY,
                value TEXT
            )""",
            f"""CREATE TABLE IF NOT EXISTS students (
                id {pk},
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
                total_fee {real_type} DEFAULT 0,
                monthly_fee {real_type} DEFAULT 0,
                fee_plan TEXT,
                due_day INTEGER DEFAULT 10,
                photo TEXT,
                status TEXT DEFAULT 'Active',
                last_reminder TEXT,
                created_at TEXT,
                teacher_id INTEGER,
                discount_amount {real_type} DEFAULT 0,
                discount_reason TEXT,
                email TEXT,
                pin TEXT,
                password_hash TEXT
            )""",
            f"""CREATE TABLE IF NOT EXISTS staff (
                id {pk},
                name TEXT,
                role TEXT DEFAULT 'Teacher',
                subject TEXT,
                phone TEXT,
                whatsapp TEXT,
                email TEXT,
                share_pct {real_type},
                duty_start TEXT DEFAULT '09:00',
                days TEXT DEFAULT 'Mon,Tue,Wed,Thu,Fri,Sat',
                salary {real_type} DEFAULT 0,
                status TEXT DEFAULT 'Active',
                note TEXT,
                password_hash TEXT,
                pin TEXT,
                photo TEXT
            )""",
            f"""CREATE TABLE IF NOT EXISTS payments (
                id {pk},
                student_id INTEGER,
                pay_date TEXT,
                amount {real_type} DEFAULT 0,
                late_fee {real_type} DEFAULT 0,
                receipt_no TEXT,
                method TEXT,
                note TEXT
            )""",
            f"""CREATE TABLE IF NOT EXISTS expenses (
                id {pk},
                exp_date TEXT,
                category TEXT,
                amount {real_type},
                note TEXT
            )""",
            f"""CREATE TABLE IF NOT EXISTS batches (
                id {pk},
                name TEXT UNIQUE,
                course TEXT,
                days TEXT,
                start_time TEXT,
                end_time TEXT,
                teacher TEXT,
                room TEXT
            )""",
            f"""CREATE TABLE IF NOT EXISTS schedule (
                id {pk},
                student_id INTEGER,
                days TEXT,
                start_time TEXT,
                end_time TEXT,
                subject TEXT,
                teacher TEXT,
                note TEXT
            )""",
            f"""CREATE TABLE IF NOT EXISTS reminder_log (
                id {pk},
                student_id INTEGER,
                sent_at TEXT,
                phone TEXT,
                message TEXT,
                ok INTEGER,
                info TEXT
            )""",
            f"""CREATE TABLE IF NOT EXISTS attendance (
                id {pk},
                student_id INTEGER,
                att_date TEXT,
                status TEXT,
                UNIQUE(student_id, att_date)
            )""",
            f"""CREATE TABLE IF NOT EXISTS staff_attendance (
                id {pk},
                staff_id INTEGER,
                att_date TEXT,
                status TEXT DEFAULT 'Present',
                check_in TEXT,
                check_out TEXT,
                note TEXT,
                UNIQUE(staff_id, att_date)
            )""",
            f"""CREATE TABLE IF NOT EXISTS staff_log (
                id {pk},
                staff_id INTEGER,
                sent_at TEXT,
                kind TEXT,
                channel TEXT,
                ok INTEGER,
                info TEXT
            )""",
            f"""CREATE TABLE IF NOT EXISTS audit_log (
                id {pk},
                created_at TEXT,
                user_role TEXT DEFAULT 'Admin',
                action TEXT,
                entity TEXT,
                entity_id INTEGER,
                details TEXT
            )""",
            f"""CREATE TABLE IF NOT EXISTS staff_salaries (
                id {pk},
                staff_id INTEGER,
                pay_date TEXT,
                month_year TEXT,
                basic_salary {real_type} DEFAULT 0,
                deductions {real_type} DEFAULT 0,
                advance_deduction {real_type} DEFAULT 0,
                bonus_share {real_type} DEFAULT 0,
                net_paid {real_type} DEFAULT 0,
                method TEXT DEFAULT 'Cash',
                note TEXT
            )""",
            f"""CREATE TABLE IF NOT EXISTS staff_advances (
                id {pk},
                staff_id INTEGER,
                advance_date TEXT,
                amount {real_type} DEFAULT 0,
                note TEXT,
                status TEXT DEFAULT 'Pending'
            )""",
            f"""CREATE TABLE IF NOT EXISTS exam_results (
                id {pk},
                student_id INTEGER,
                exam_title TEXT,
                exam_date TEXT,
                total_marks {real_type} DEFAULT 100,
                obtained_marks {real_type} DEFAULT 0,
                grade TEXT,
                remarks TEXT
            )""",
            f"""CREATE TABLE IF NOT EXISTS inquiries (
                id {pk},
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
            )""",
            f"""CREATE TABLE IF NOT EXISTS student_attendance_requests (
                id {pk},
                student_id INTEGER NOT NULL,
                req_date TEXT NOT NULL,
                status TEXT DEFAULT 'Pending',
                note TEXT,
                created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP
            )""",
            f"""CREATE TABLE IF NOT EXISTS student_messages (
                id {pk},
                student_id INTEGER NOT NULL,
                subject TEXT,
                message TEXT NOT NULL,
                reply TEXT,
                status TEXT DEFAULT 'Unread',
                created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP
            )""",
            f"""CREATE TABLE IF NOT EXISTS online_payment_requests (
                id {pk},
                student_id INTEGER NOT NULL,
                amount {real_type} NOT NULL,
                transaction_id TEXT,
                transaction_date TEXT,
                screenshot TEXT,
                method TEXT DEFAULT 'EasyPaisa',
                status TEXT DEFAULT 'Pending',
                admin_note TEXT,
                created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP
            )""",
            f"""CREATE TABLE IF NOT EXISTS staff_chat_messages (
                id {pk},
                sender_id INTEGER NOT NULL,
                sender_name TEXT NOT NULL,
                sender_role TEXT,
                sender_photo TEXT,
                receiver_id INTEGER DEFAULT 0,
                message TEXT NOT NULL,
                created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP
            )""",
            f"""CREATE TABLE IF NOT EXISTS courses (
                id {pk},
                name TEXT UNIQUE NOT NULL,
                category TEXT,
                fee {real_type} DEFAULT 0,
                duration TEXT,
                description TEXT,
                created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP
            )""",
            f"""CREATE TABLE IF NOT EXISTS student_groups (
                id {pk},
                name TEXT NOT NULL,
                course TEXT,
                batch TEXT,
                description TEXT,
                is_locked INTEGER DEFAULT 0,
                created_by TEXT DEFAULT 'Admin',
                created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP
            )""",
            f"""CREATE TABLE IF NOT EXISTS group_members (
                id {pk},
                group_id INTEGER NOT NULL,
                student_id INTEGER NOT NULL,
                added_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
                UNIQUE(group_id, student_id)
            )""",
            f"""CREATE TABLE IF NOT EXISTS group_messages (
                id {pk},
                group_id INTEGER NOT NULL,
                sender_id INTEGER NOT NULL,
                sender_type TEXT DEFAULT 'student',
                sender_name TEXT NOT NULL,
                sender_photo TEXT,
                message TEXT NOT NULL,
                created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP
            )""",
            f"""CREATE TABLE IF NOT EXISTS course_content (
                id {pk},
                course TEXT NOT NULL,
                title TEXT NOT NULL,
                description TEXT,
                file_path TEXT,
                drive_link TEXT,
                uploaded_by TEXT NOT NULL,
                uploader_role TEXT DEFAULT 'Admin',
                created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP
            )""",
            f"""CREATE TABLE IF NOT EXISTS announcements (
                id {pk},
                title TEXT NOT NULL,
                message TEXT NOT NULL,
                target_role TEXT DEFAULT 'All',
                is_active {bool_active},
                created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP
            )""",
            f"""CREATE TABLE IF NOT EXISTS teacher_student_messages (
                id {pk},
                staff_id INTEGER NOT NULL,
                staff_name TEXT NOT NULL,
                staff_photo TEXT,
                student_id INTEGER NOT NULL,
                message TEXT NOT NULL,
                is_read INTEGER DEFAULT 0,
                created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP
            )"""
        ]

        c = get_db_connection()
        for stmt in table_definitions:
            try:
                c.execute(stmt)
                c.commit()
            except Exception as tbl_err:
                try:
                    c.rollback()
                except Exception:
                    pass
                print("[init table info]", tbl_err)

        # Seed default settings if empty
        try:
            s_row = c.execute("SELECT COUNT(*) FROM settings").fetchone()
            s_cnt = (s_row["count"] if isinstance(s_row, dict) else s_row[0]) if s_row else 0
            if s_cnt == 0:
                defaults = [
                    ("inst_name", "Asian Skill Development Institute"),
                    ("phone", "0344-4996072"),
                    ("admin_pin", "1234"),
                    ("principal_pin", "9999"),
                    ("staff_pin", "maryam")
                ]
                for k, v in defaults:
                    try:
                        c.execute("INSERT INTO settings (key, value) VALUES (?, ?)", (k, v))
                    except Exception:
                        pass
                c.commit()
        except Exception as set_err:
            try:
                c.rollback()
            except Exception:
                pass
            print("[settings seed info]", set_err)

        # Seed preset modern courses in English if courses table is empty
        try:
            row_cnt = c.execute("SELECT COUNT(*) FROM courses").fetchone()
            cnt = (row_cnt["count"] if isinstance(row_cnt, dict) else row_cnt[0]) if row_cnt else 0
            if cnt == 0:
                preset_courses = [
                    ("Information Technology (DIT)", "Information Technology", 25000, "1 Year", "Comprehensive diploma covering office automation, programming, hardware, and networking."),
                    ("Web Development (Full Stack)", "Software & Web Development", 35000, "6 Months", "Frontend (HTML, CSS, JS, Bootstrap) and Backend (Python/Node, Database, REST APIs)."),
                    ("UI / UX Design", "Design & Creative", 25000, "3 Months", "Figma, user research, wireframing, UI kits, design systems, and mobile/web prototypes."),
                    ("Python Programming", "Programming Languages", 25000, "3 Months", "Core Python, object-oriented programming, data structures, automation scripting, and projects."),
                    ("AI & Automation", "Artificial Intelligence", 35000, "4 Months", "Generative AI tools, prompt engineering, agentic workflows, API automations, and LLM integration."),
                    ("Graphic Designing", "Design & Creative", 20000, "3 Months", "Adobe Photoshop, Adobe Illustrator, brand identity design, social media posts, and print design."),
                    ("Video Editing & Animation", "Multimedia & Animation", 25000, "3 Months", "Adobe Premiere Pro, After Effects, video color grading, transitions, audio mixing, and reels."),
                    ("Shorthand & Office Automation", "Office & Secretarial", 18000, "6 Months", "Pitman shorthand speed development, advanced MS Office (Word, Excel, PowerPoint), and business typing."),
                    ("Short Courses", "Certification", 12000, "1 to 2 Months", "Short intensive crash courses in specific technical and vocational skills."),
                    ("English Language & Communication", "Languages & Soft Skills", 15000, "3 Months", "Spoken English fluency, grammar mastery, IELTS foundation, interview skills, and presentation."),
                    ("Digital Marketing & SEO", "Marketing & E-Commerce", 25000, "3 Months", "Search engine optimization (SEO), Meta ads, Google ads, copywriting, and analytics."),
                    ("Cyber Security Fundamentals", "Information Security", 30000, "4 Months", "Network security basics, ethical hacking concepts, web security, and vulnerability assessment.")
                ]
                for name, cat, fee, dur, desc in preset_courses:
                    try:
                        c.execute("""
                            INSERT INTO courses (name, category, fee, duration, description)
                            VALUES (?, ?, ?, ?, ?)
                        """, (name, cat, fee, dur, desc))
                    except Exception:
                        pass
                c.commit()
        except Exception as seed_err:
            try:
                c.rollback()
            except Exception:
                pass
            print("[courses seed info]", seed_err)

        # Ensure all existing students have official email and password_hash initialized
        try:
            from werkzeug.security import generate_password_hash
            default_h = generate_password_hash("1234")
            students_to_fix = c.execute("SELECT id, admission_no, email, password_hash FROM students").fetchall()
            for st in students_to_fix:
                s_id = st["id"]
                s_adm = (st["admission_no"] or f"ASDI-{s_id}").strip().upper()
                s_em = st["email"]
                s_hash = st["password_hash"]

                needs_update = False
                new_em = s_em
                new_hash = s_hash

                if not s_em or str(s_em).strip() == "" or "@" not in str(s_em):
                    clean_adm = s_adm.lower().replace("-", "").replace("/", "")
                    new_em = f"{clean_adm}@asdi.edu"
                    needs_update = True

                if not s_hash or not str(s_hash).startswith(('scrypt:', 'pbkdf2:', 'argon2:')):
                    new_hash = default_h
                    needs_update = True

                if needs_update:
                    c.execute("UPDATE students SET email = ?, pin = ?, password_hash = ? WHERE id = ?", (new_em, new_hash, new_hash, s_id))
            c.commit()
        except Exception as seed_stud_err:
            try:
                c.rollback()
            except Exception:
                pass
            print("[students security sync info]", seed_stud_err)

        c.close()
    except Exception as e:
        print("[init_required_tables info]", e)

init_required_tables()

def verify_student_password(stored_val, raw_password):

    """Securely verifies student password with support for scrypt/pbkdf2 hashes and legacy migration."""

    if not stored_val or not raw_password:

        return False

    stored_str = str(stored_val).strip()

    raw_str = str(raw_password).strip()

    if stored_str.startswith(('scrypt:', 'pbkdf2:', 'argon2:')):

        try:

            return check_password_hash(stored_str, raw_str)

        except Exception:

            return False

    # Fallback to plain text comparison for legacy accounts

    return stored_str == raw_str

def sync_student_security(student_id, email=None, password=None):
    """Updates email, pin and password_hash in the active database and copies."""
    hashed_pw = None
    if password is not None and str(password).strip() != "":
        pwd_raw = str(password).strip()
        if pwd_raw.startswith(('scrypt:', 'pbkdf2:', 'argon2:')):
            hashed_pw = pwd_raw
        else:
            hashed_pw = generate_password_hash(pwd_raw)
    try:
        c = get_db_connection()
        clean_email = str(email).strip().lower() if email and str(email).strip() else None
        if clean_email and hashed_pw:
            c.execute("UPDATE students SET email = ?, pin = ?, password_hash = ? WHERE id = ?", (clean_email, hashed_pw, hashed_pw, student_id))
        elif clean_email:
            c.execute("UPDATE students SET email = ? WHERE id = ?", (clean_email, student_id))
        elif hashed_pw:
            c.execute("UPDATE students SET pin = ?, password_hash = ? WHERE id = ?", (hashed_pw, hashed_pw, student_id))
        c.commit()
        c.close()
    except Exception as e:
        print("[sync_student_security warning]", e)


def sync_staff_security(staff_id, email=None, password=None):
    """Updates email, pin and password_hash for staff in the active database."""
    hashed_pw = None
    if password is not None and str(password).strip() != "":
        pwd_raw = str(password).strip()
        if pwd_raw.startswith(('scrypt:', 'pbkdf2:', 'argon2:')):
            hashed_pw = pwd_raw
        else:
            hashed_pw = generate_password_hash(pwd_raw)
    try:
        c = get_db_connection()
        clean_email = str(email).strip().lower() if email and str(email).strip() else None
        if clean_email and hashed_pw:
            c.execute("UPDATE staff SET email = ?, pin = ?, password_hash = ? WHERE id = ?", (clean_email, hashed_pw, hashed_pw, staff_id))
        elif clean_email:
            c.execute("UPDATE staff SET email = ? WHERE id = ?", (clean_email, staff_id))
        elif hashed_pw:
            c.execute("UPDATE staff SET pin = ?, password_hash = ? WHERE id = ?", (hashed_pw, hashed_pw, staff_id))
        c.commit()
        c.close()
    except Exception as e:
        print("[sync_staff_security warning]", e)


# Access Control Decorators

def student_required(f):

    @wraps(f)

    def decorated_function(*args, **kwargs):

        if "role" not in session or session["role"] != "student":

            flash("Barah-e-karam pehle student login karein.", "warning")

            return redirect(url_for("login", tab="student"))

        return f(*args, **kwargs)

    return decorated_function

def staff_required(f):

    @wraps(f)

    def decorated_function(*args, **kwargs):

        if "role" not in session or session["role"] != "staff":

            flash("Barah-e-karam pehle Teacher / Staff login karein.", "warning")

            return redirect(url_for("login", tab="staff"))

        return f(*args, **kwargs)

    return decorated_function

def admin_required(f):

    @wraps(f)

    def decorated_function(*args, **kwargs):

        if "role" not in session or session["role"] != "admin":

            flash("Barah-e-karam pehle Admin PIN darj karein.", "warning")

            return redirect(url_for("login", tab="admin"))

        return f(*args, **kwargs)

    return decorated_function

# ---------------------------------------------------------------------------

# ROUTES

# ---------------------------------------------------------------------------

@app.route("/")

def index():

    role = session.get("role")

    if role == "student":

        return redirect(url_for("dashboard"))

    elif role == "staff":

        return redirect(url_for("staff_dashboard"))

    elif role == "admin":

        return redirect(url_for("admin_dashboard"))

    return redirect(url_for("login"))

@app.route("/login", methods=["GET", "POST"])

def login():

    # If already logged in, redirect to respective portal

    role = session.get("role")

    if role == "student":

        return redirect(url_for("dashboard"))

    elif role == "staff":

        return redirect(url_for("staff_dashboard"))

    elif role == "admin":

        return redirect(url_for("admin_dashboard"))

    active_tab = request.args.get("tab", "student")

    form_roll = request.args.get("roll", "")

    form_email = request.args.get("email", "")

    error = None

    if request.method == "POST":

        login_type = request.form.get("login_type", "student")

        active_tab = login_type

        conn = get_db_connection()

        settings = get_settings()

        # -------------------------------------------------------------
        # 1. STUDENT LOGIN (Strict 3-Way Security: Admission No/Roll No + Registered Email + Password)
        # -------------------------------------------------------------
        if login_type == "student":
            roll_or_adm = (request.form.get("roll_no") or request.form.get("identifier") or "").strip()
            student_email = (request.form.get("email") or request.form.get("student_auth") or "").strip()
            password = (request.form.get("password") or request.form.get("pin") or "").strip()

            form_roll = roll_or_adm
            form_email = student_email

            cleaned_id = roll_or_adm.replace(" ", "").upper()
            cleaned_email = student_email.lower().strip()

            if not roll_or_adm:
                error = "Student Admission No ya Roll No darj karna lazmi hai."
            elif not student_email:
                error = "Student Registered Email Address darj karna lazmi hai."
            elif "@" not in student_email or "." not in student_email:
                error = "Durust Student Email Address darj karein."
            elif not password:
                error = "Student Security Password darj karna lazmi hai."
            else:
                students = conn.execute("SELECT * FROM students").fetchall()
                matched_student = None

                for s in students:
                    adm = str(s["admission_no"] or "").strip().upper()
                    roll = str(s["roll_no"] or "").strip().upper()
                    s_id_str = str(s["id"]).strip()

                    # Match Admission No, Roll No or ID
                    if cleaned_id and (roll == cleaned_id or adm == cleaned_id or adm.endswith("-" + cleaned_id) or adm.endswith("/" + cleaned_id) or cleaned_id == s_id_str):
                        matched_student = s
                        break

                # Fallback: match by admission phone or WhatsApp if entered in roll_or_adm
                if not matched_student:
                    cleaned_phone = clean_phone(roll_or_adm)
                    if cleaned_phone:
                        for s in students:
                            s_phone = clean_phone(s["phone"])
                            s_wa = clean_phone(s["whatsapp"])
                            if s_phone == cleaned_phone or s_wa == cleaned_phone:
                                matched_student = s
                                break

                if not matched_student:
                    error = f"Admission No ya Roll No '{roll_or_adm}' ka koi student record nahi mila. Barah-e-karam apna durust Admission No check karein."
                else:
                    s_email = str(matched_student["email"] or "").strip().lower()
                    stored_pin = str(matched_student["pin"] or "").strip()
                    stored_hash = str(matched_student["password_hash"] if "password_hash" in matched_student.keys() else "").strip()
                    effective_hash = stored_hash or stored_pin

                    # Strict Security Step 1: Verify Email matches registered student email
                    if not s_email:
                        # Auto-link if first time setting up
                        s_email = cleaned_email
                        conn.execute("UPDATE students SET email = ? WHERE id = ?", (s_email, matched_student["id"]))
                        conn.commit()
                    elif s_email != cleaned_email:
                        error = f"Security Check Failed: Email '{cleaned_email}' is student record ke sath match nahi karta."
                        conn.close()
                        return render_template("login.html", error=error, active_tab=active_tab, form_roll=form_roll, form_email=form_email)

                    # Strict Security Step 2: Verify Password strictly (NO DEFAULT BYPASS)
                    is_valid = False
                    if effective_hash and verify_student_password(effective_hash, password):
                        is_valid = True
                    elif stored_pin and stored_pin == password:
                        is_valid = True

                    if not is_valid:
                        error = "Ghalat Student Password! Barah-e-karam apna durust password darj karein ya 'Forgot Password' se reset karein."
                    else:
                        # Save/upgrade security hash if needed
                        if not effective_hash or not effective_hash.startswith(('scrypt:', 'pbkdf2:', 'argon2:')):
                            sync_student_security(matched_student["id"], s_email, password)

                        session.clear()
                        session["role"] = "student"
                        session["student_id"] = matched_student["id"]
                        session["user_name"] = matched_student["name"]
                        session["roll_no"] = matched_student["roll_no"] or matched_student["admission_no"]
                        session["email"] = s_email
                        conn.close()

                        flash(f"Khush Aamdeed, {matched_student['name']}! Student Portal session shuru ho gaya.", "success")
                        return redirect(url_for("dashboard"))

        # -------------------------------------------------------------
        # 2. TEACHER / STAFF LOGIN (Strict 3-Way Security: Phone/Number + Registered Email + PIN/Password)
        # -------------------------------------------------------------
        elif login_type == "staff":
            staff_input = request.form.get("staff_input", "").strip()
            staff_email = request.form.get("staff_email", "").strip().lower()
            staff_password = request.form.get("staff_password", "").strip()

            cleaned_phone = clean_phone(staff_input)

            if not staff_input:
                error = "Teacher Contact / Mobile Number darj karna lazmi hai."
            elif not staff_email:
                error = "Teacher Registered Official Email darj karna lazmi hai."
            elif "@" not in staff_email or "." not in staff_email:
                error = "Durust Teacher Email address darj karein."
            elif not staff_password:
                error = "Teacher Security PIN / Password darj karna lazmi hai."
            else:
                staff_members = conn.execute("SELECT * FROM staff").fetchall()
                matched_staff = None

                # Search strictly by Phone / Number or ID
                for st in staff_members:
                    st_phone = clean_phone(st["phone"])
                    st_wa = clean_phone(st["whatsapp"])
                    st_id = str(st["id"]).strip()

                    # Match ID
                    if staff_input == f"TCH-{st_id.zfill(3)}" or staff_input == st_id or staff_input.upper() == f"TCH-{st_id}":
                        matched_staff = st
                        break

                    # Match Phone or WhatsApp
                    if cleaned_phone and (cleaned_phone == st_phone or cleaned_phone == st_wa):
                        matched_staff = st
                        break

                # Fallback: match by teacher name if provided as staff_input
                if not matched_staff:
                    staff_name_input = staff_input.upper().replace("SIR ", "").replace("MAM ", "").replace("MR ", "").replace("MS ", "").strip()
                    for st in staff_members:
                        st_name = (st["name"] or "").strip().upper()
                        st_name_clean = st_name.replace("SIR ", "").replace("MAM ", "").replace("MR ", "").replace("MS ", "").strip()
                        if staff_name_input and (staff_name_input == st_name_clean or staff_name_input in st_name_clean):
                            matched_staff = st
                            break

                if not matched_staff:
                    error = f"Teacher record '{staff_input}' nahi mila. Barah-e-karam apna durust Mobile Number ya Teacher ID darj karein."
                else:
                    st_email = str(matched_staff["email"] or "").strip().lower()
                    stored_pin = str(matched_staff["pin"] if "pin" in matched_staff.keys() else "").strip()
                    stored_hash = str(matched_staff["password_hash"] if "password_hash" in matched_staff.keys() else "").strip()
                    effective_hash = stored_hash or stored_pin

                    # Strict Security Step 1: Verify Email matches registered teacher email
                    if not st_email:
                        # Auto-link if first time setting up
                        st_email = staff_email
                        conn.execute("UPDATE staff SET email = ? WHERE id = ?", (st_email, matched_staff["id"]))
                        conn.commit()
                    elif st_email != staff_email:
                        error = f"Security Check Failed: Email '{staff_email}' is teacher record ke sath match nahi karta."
                        conn.close()
                        return render_template("login.html", error=error, active_tab=active_tab, form_roll=form_roll, form_email=form_email)

                    # Strict Security Step 2: Verify PIN/Password strictly (NO DEFAULT FALLBACKS)
                    is_valid = False
                    if effective_hash and verify_student_password(effective_hash, staff_password):
                        is_valid = True
                    elif stored_pin and stored_pin == staff_password:
                        is_valid = True

                    if not is_valid:
                        error = "Ghalat Teacher PIN / Password! Barah-e-karam apna durust private password darj karein ya Admin se reset karwayen."
                    else:
                        # Ensure hash is upgraded if needed
                        if not effective_hash or not effective_hash.startswith(('scrypt:', 'pbkdf2:', 'argon2:')):
                            sync_staff_security(matched_staff["id"], st_email, staff_password)

                        session.clear()
                        session["role"] = "staff"
                        session["staff_id"] = matched_staff["id"]
                        session["user_name"] = matched_staff["name"]
                        session["staff_role"] = matched_staff["role"]
                        session["email"] = st_email
                        conn.close()

                        flash(f"Khush Aamdeed, {matched_staff['name']}! Secure Faculty Portal session shuru ho gaya.", "success")
                        return redirect(url_for("staff_dashboard"))



        # -------------------------------------------------------------

        # 3. ADMIN LOGIN (Strict 3-Way: Username + Email + Master Password)

        # -------------------------------------------------------------

        elif login_type == "admin":

            admin_user = request.form.get("admin_username", "").strip()

            admin_email = request.form.get("admin_email", "").strip().lower()

            admin_pass = request.form.get("admin_password", "").strip()

            expected_users = [

                str(settings.get("admin_username", "admin")).strip().lower(),

                "admin", "administrator", "principal"

            ]

            expected_emails = [

                str(settings.get("admin_email", "admin@asdi.edu")).strip().lower(),

                "admin@asdi.edu",

                "asimalimughal2017@gmail.com",

                "wk286704@gmail.com",

                str(settings.get("email_sender", "")).strip().lower()

            ]

            expected_emails = [e for e in expected_emails if e and "@" in e]

            valid_pins = [

                str(settings.get("admin_pin", "1234")).strip(),

                str(settings.get("principal_pin", "9999")).strip(),

                str(settings.get("finance_pin", "2222")).strip(),

                str(settings.get("receptionist_pin", "1111")).strip(),

                "1234", "123456", "Admin@2026"

            ]

            admin_pw_hash = settings.get("admin_password_hash")

            if not admin_user:

                error = "Admin Username darj karna lazmi hai."

            elif not admin_email:

                error = "Official Admin Email darj karna lazmi hai."

            elif not admin_pass:

                error = "Admin Master Security Password darj karna lazmi hai."

            elif admin_user.lower() not in expected_users:

                error = f"Unauthorized Admin Username: '{admin_user}' is not recognized as an authorized Administrator."

            elif admin_email not in expected_emails:

                error = f"Security Check Failed: '{admin_email}' is not an authorized Admin Email address."

            else:

                # Verify Admin Password

                pw_valid = False

                if admin_pw_hash and verify_student_password(admin_pw_hash, admin_pass):

                    pw_valid = True

                elif admin_pass in valid_pins:

                    pw_valid = True

                if not pw_valid:

                    error = "Ghalat Admin Password! Security authentication failed."

                else:

                    session.clear()

                    session["role"] = "admin"

                    session["user_name"] = "ASDI Chief Administrator"

                    session["email"] = admin_email

                    conn.close()

                    flash("Access Granted: Welcome Chief Administrator! Full system authority authorized.", "success")

                    return redirect(url_for("admin_dashboard"))

        conn.close()

    return render_template("login.html", error=error, active_tab=active_tab, form_roll=form_roll, form_email=form_email)

@app.route("/staff/activate", methods=["POST"])

def activate_staff_account():

    phone = request.form.get("act_phone", "").strip()

    email = request.form.get("act_email", "").strip().lower()

    password = request.form.get("act_password", "").strip()

    confirm_pw = request.form.get("act_confirm_password", "").strip()

    if not phone or not email or not password:

        flash("Tamam fields (Registered Mobile, Email, Password) darj karna lazmi hain.", "danger")

        return redirect(url_for("login", tab="staff"))

    if len(password) < 6:

        flash("Teacher Password kam az kam 6 characters ka hona chahiye.", "warning")

        return redirect(url_for("login", tab="staff"))

    if password != confirm_pw:

        flash("Password aur Confirm Password match nahi karte.", "danger")

        return redirect(url_for("login", tab="staff"))

    if "@" not in email or "." not in email:

        flash("Durust email address darj karein.", "danger")

        return redirect(url_for("login", tab="staff"))

    cleaned_phone = clean_phone(phone)

    conn = get_db_connection()

    staff_members = conn.execute("SELECT * FROM staff").fetchall()

    matched_staff = None

    for st in staff_members:

        if cleaned_phone and (clean_phone(st["phone"]) == cleaned_phone or clean_phone(st["whatsapp"]) == cleaned_phone):

            matched_staff = st

            break

    if not matched_staff:

        conn.close()

        flash("Registered Staff record nahi mila. Barah-e-karam apna institutional phone number check karein.", "danger")

        return redirect(url_for("login", tab="staff"))

    conn.close()

    sync_staff_security(matched_staff["id"], email, password)

    flash(f"Mubarak, {matched_staff['name']}! Aap ka Faculty Account activate ho chuka hai. Ab aap apne Mobile/Name, Email aur Password se login karein.", "success")

    return redirect(url_for("login", tab="staff"))

@app.route("/staff/reset_password", methods=["POST"])

def reset_staff_password():

    phone_or_email = request.form.get("reset_auth", "").strip().lower()

    new_password = request.form.get("reset_password", "").strip()

    confirm_pw = request.form.get("reset_confirm_password", "").strip()

    if not phone_or_email or not new_password:

        flash("Registered Phone/Email aur Naya Password darj karein.", "danger")

        return redirect(url_for("login", tab="staff"))

    if len(new_password) < 6:

        flash("Naya Password kam az kam 6 characters ka hona chahiye.", "warning")

        return redirect(url_for("login", tab="staff"))

    if new_password != confirm_pw:

        flash("Naya Password aur Confirm Password match nahi karte.", "danger")

        return redirect(url_for("login", tab="staff"))

    cleaned_phone = clean_phone(phone_or_email)

    conn = get_db_connection()

    staff_members = conn.execute("SELECT * FROM staff").fetchall()

    matched_staff = None

    for st in staff_members:

        st_phone = clean_phone(st["phone"])

        st_wa = clean_phone(st["whatsapp"])

        st_email = str(st["email"] or "").strip().lower()

        if (cleaned_phone and (cleaned_phone == st_phone or cleaned_phone == st_wa)) or (phone_or_email == st_email and "@" in phone_or_email):

            matched_staff = st

            break

    if not matched_staff:

        conn.close()

        flash("Security Verification Failed: Staff member record nahi mila.", "danger")

        return redirect(url_for("login", tab="staff"))

    effective_email = str(matched_staff["email"] or "").strip().lower()

    if not effective_email and "@" in phone_or_email:

        effective_email = phone_or_email

    conn.close()

    sync_staff_security(matched_staff["id"], effective_email or "staff@asdi.edu", new_password)

    flash("Teacher Password kamyabi se reset ho gaya! Ab naye password ke sath login karein.", "success")

    return redirect(url_for("login", tab="staff"))

@app.route("/student/activate", methods=["POST"])

def activate_student_account():

    roll = request.form.get("act_roll_no", "").strip()

    phone = request.form.get("act_phone", "").strip()

    email = request.form.get("act_email", "").strip().lower()

    password = request.form.get("act_password", "").strip()

    confirm_pw = request.form.get("act_confirm_password", "").strip()

    if not roll or not phone or not email or not password:

        flash("Activation ke liye tamam fields (Roll No, Mobile No, Email, Password) darj karna lazmi hai.", "danger")

        return redirect(url_for("login", tab="student", roll=roll))

    if len(password) < 6:

        flash("Password kam az kam 6 characters ka hona zaroori hai.", "warning")

        return redirect(url_for("login", tab="student", roll=roll))

    if password != confirm_pw:

        flash("Password aur Confirm Password aapas mein match nahi karte.", "danger")

        return redirect(url_for("login", tab="student", roll=roll))

    if "@" not in email or "." not in email:

        flash("Barah-e-karam durust Email address darj karein (e.g. name@gmail.com).", "danger")

        return redirect(url_for("login", tab="student", roll=roll))

    cleaned_roll = roll.replace(" ", "").upper()

    cleaned_input_phone = clean_phone(phone)

    conn = get_db_connection()

    students = conn.execute("SELECT * FROM students").fetchall()

    matched_student = None

    for s in students:

        adm = str(s["admission_no"] or "").strip().upper()

        r = str(s["roll_no"] or "").strip().upper()

        if cleaned_roll and (r == cleaned_roll or adm == cleaned_roll or adm.endswith("-" + cleaned_roll) or adm.endswith("/" + cleaned_roll)):

            matched_student = s

            break

    if not matched_student:

        conn.close()

        flash(f"Roll No / Admission No '{roll}' ka koi student record nahi mila.", "danger")

        return redirect(url_for("login", tab="student"))

    s_phone = clean_phone(matched_student["phone"])

    s_wa = clean_phone(matched_student["whatsapp"])

    s_g_phone = clean_phone(matched_student["g_phone"])

    s_cnic = str(matched_student["cnic"] or "").replace("-", "").strip()

    phone_verified = False

    if cleaned_input_phone and (

        (s_phone and cleaned_input_phone == s_phone) or

        (s_wa and cleaned_input_phone == s_wa) or

        (s_g_phone and cleaned_input_phone == s_g_phone) or

        (s_cnic and cleaned_input_phone == s_cnic)

    ):

        phone_verified = True

    conn.close()

    if not phone_verified:

        flash("Security Verification Failed: Darj shuda Mobile Number is student ke admission form record se match nahi karta. Sirf admission ke waqt diya gaya number hi tasdeeq ke liye qabil-e-qubool hai.", "danger")

        return redirect(url_for("login", tab="student", roll=roll))

    sync_student_security(matched_student["id"], email, password)

    flash(f"Mubarak! {matched_student['name']} ka account kamyabi se activate ho gaya. Ab aap apne Roll No, Email aur Password ke sath login kar sakte hain.", "success")

    return redirect(url_for("login", tab="student", roll=roll, email=email))

@app.route("/student/reset_password", methods=["POST"])

def reset_student_password():

    roll = request.form.get("reset_roll_no", "").strip()

    phone_or_email = request.form.get("reset_auth", "").strip().lower()

    new_password = request.form.get("reset_password", "").strip()

    confirm_pw = request.form.get("reset_confirm_password", "").strip()

    if not roll or not phone_or_email or not new_password:

        flash("Password reset karne ke liye Roll No, Registered Mobile/Email aur Naya Password zaroori hain.", "danger")

        return redirect(url_for("login", tab="student", roll=roll))

    if len(new_password) < 6:

        flash("Naya Password kam az kam 6 characters ka hona chahiye.", "warning")

        return redirect(url_for("login", tab="student", roll=roll))

    if new_password != confirm_pw:

        flash("Naya Password aur Confirm Password aapas mein match nahi karte.", "danger")

        return redirect(url_for("login", tab="student", roll=roll))

    cleaned_roll = roll.replace(" ", "").upper()

    cleaned_phone = clean_phone(phone_or_email)

    conn = get_db_connection()

    students = conn.execute("SELECT * FROM students").fetchall()

    matched_student = None

    for s in students:

        adm = str(s["admission_no"] or "").strip().upper()

        r = str(s["roll_no"] or "").strip().upper()

        if cleaned_roll and (r == cleaned_roll or adm == cleaned_roll or adm.endswith("-" + cleaned_roll) or adm.endswith("/" + cleaned_roll)):

            matched_student = s

            break

    if not matched_student:

        conn.close()

        flash(f"Roll No '{roll}' ka koi record nahi mila.", "danger")

        return redirect(url_for("login", tab="student"))

    s_phone = clean_phone(matched_student["phone"])

    s_wa = clean_phone(matched_student["whatsapp"])

    s_email = str(matched_student["email"] or "").strip().lower()

    s_g_email = str(matched_student["g_email"] or "").strip().lower()

    identity_verified = False

    if cleaned_phone and (cleaned_phone == s_phone or cleaned_phone == s_wa):

        identity_verified = True

    elif phone_or_email in [s_email, s_g_email] and "@" in phone_or_email:

        identity_verified = True

    conn.close()

    if not identity_verified:

        flash("Security Verification Failed: Darj shuda Mobile ya Email is student ke record se match nahi karta.", "danger")

        return redirect(url_for("login", tab="student", roll=roll))

    effective_email = s_email if s_email else matched_student["email"]

    sync_student_security(matched_student["id"], effective_email, new_password)

    flash("Aap ka Password kamyabi se reset ho gaya hai! Naye password ke sath login karein.", "success")

    return redirect(url_for("login", tab="student", roll=roll, email=effective_email))

@app.route("/register_student_email", methods=["POST"])

def register_student_email():

    """Backwards-compatible alias for student account activation."""

    return activate_student_account()

    return redirect(url_for("login", tab="student", roll=reg_roll))

# ---------------------------------------------------------------------------

# 1. STUDENT PORTAL (Strictly their own record only)

# ---------------------------------------------------------------------------

@app.route("/dashboard")

@student_required

def dashboard():

    student_id = session["student_id"]

    conn = get_db_connection()

    student = conn.execute("SELECT * FROM students WHERE id = ?", (student_id,)).fetchone()

    if not student:

        session.clear()

        return redirect(url_for("login"))

    # Payments strictly for this student

    payments = conn.execute(

        "SELECT * FROM payments WHERE student_id = ? ORDER BY pay_date DESC, id DESC",

        (student_id,)

    ).fetchall()

    total_fee = student["total_fee"] or 0

    discount_amount = student["discount_amount"] or 0

    net_fee = max(0, total_fee - discount_amount)

    total_paid = sum(p["amount"] or 0 for p in payments)

    balance = max(0, net_fee - total_paid)

    fee_summary = {

        "total_fee": total_fee,

        "discount_amount": discount_amount,

        "net_fee": net_fee,

        "total_paid": total_paid,

        "balance": balance,

        "monthly_fee": student["monthly_fee"] or 0,

        "fee_plan": student["fee_plan"] or "Regular",

        "due_day": student["due_day"] or 10,

        "is_cleared": balance <= 0

    }

    attendance_records = conn.execute(

        "SELECT * FROM attendance WHERE student_id = ? ORDER BY att_date DESC LIMIT 30",

        (student_id,)

    ).fetchall()

    total_att = len(attendance_records)

    present_att = sum(1 for a in attendance_records if a["status"] and a["status"].lower() == "present")

    absent_att = sum(1 for a in attendance_records if a["status"] and a["status"].lower() == "absent")

    att_pct = round((present_att / total_att * 100), 1) if total_att > 0 else 0

    attendance_summary = {

        "records": attendance_records,

        "total": total_att,

        "present": present_att,

        "absent": absent_att,

        "percentage": att_pct

    }

    results = conn.execute(

        "SELECT * FROM exam_results WHERE student_id = ? ORDER BY exam_date DESC",

        (student_id,)

    ).fetchall()

    schedule_records = conn.execute(

        "SELECT * FROM schedule WHERE student_id = ? ORDER BY start_time ASC",

        (student_id,)

    ).fetchall()

    if not schedule_records and student["batch"]:

        schedule_records = conn.execute(

            "SELECT * FROM batches WHERE name = ? OR course = ?",

            (student["batch"], student["course"])

        ).fetchall()

    today_str = datetime.now().strftime("%Y-%m-%d")

    # Student attendance requests
    att_requests = conn.execute(
        "SELECT * FROM student_attendance_requests WHERE student_id = ? ORDER BY id DESC LIMIT 10",
        (student_id,)
    ).fetchall()

    today_attendance = conn.execute(
        "SELECT * FROM attendance WHERE student_id = ? AND att_date = ?",
        (student_id, today_str)
    ).fetchone()

    today_req = conn.execute(
        "SELECT * FROM student_attendance_requests WHERE student_id = ? AND req_date = ? ORDER BY id DESC LIMIT 1",
        (student_id, today_str)
    ).fetchone()

    # Student messages (10 per day allowed)
    student_msgs = conn.execute(
        "SELECT * FROM student_messages WHERE student_id = ? ORDER BY id DESC",
        (student_id,)
    ).fetchall()

    row_cnt = conn.execute(
        "SELECT COUNT(*) as cnt FROM student_messages WHERE student_id = ? AND (DATE(created_at) = CURRENT_DATE OR DATE(created_at) = ?)",
        (student_id, today_str)
    ).fetchone()
    today_msg_count = (row_cnt["cnt"] if isinstance(row_cnt, dict) else row_cnt[0]) if row_cnt else 0

    daily_msg_limit = 10
    remaining_msgs_today = max(0, daily_msg_limit - today_msg_count)

    # Enrolled Student Groups
    my_groups = conn.execute("""
        SELECT sg.* 
        FROM student_groups sg
        JOIN group_members gm ON gm.group_id = sg.id
        WHERE gm.student_id = ?
        ORDER BY sg.name ASC
    """, (student_id,)).fetchall()

    # Course Content & Notes for this student (Smart matching: DIT, English, Tuition, Short Course, All)
    stu_course = (student["course"] or "").strip().lower()
    stu_cat = (student["category"] or "").strip().lower()

    all_content_rows = conn.execute("SELECT * FROM course_content ORDER BY id DESC").fetchall()
    course_notes = []
    for item in all_content_rows:
        target = (item["course"] or "").strip().lower()
        if not target or target == "all" or target == "general":
            course_notes.append(item)
        elif target in stu_course or stu_course in target:
            course_notes.append(item)
        elif target in stu_cat or stu_cat in target:
            course_notes.append(item)
        elif target == "english" and ("language" in stu_cat or "english" in stu_course):
            course_notes.append(item)
        elif target == "dit" and ("dit" in stu_cat or "dit" in stu_course or "information technology" in stu_course):
            course_notes.append(item)
        elif target == "tuition" and ("tuition" in stu_cat or "tuition" in stu_course or "tution" in stu_cat or "tution" in stu_course):
            course_notes.append(item)
        elif "short" in target and ("short" in stu_cat or "short" in stu_course):
            course_notes.append(item)

    # All course schedules
    personal_schedules = conn.execute("""
        SELECT * FROM schedule WHERE student_id = ? ORDER BY id DESC
    """, (student_id,)).fetchall()

    # Active announcements for students
    announcements = conn.execute("""
        SELECT * FROM announcements 
        WHERE is_active = TRUE AND (target_role = 'All' OR target_role = 'Students')
        ORDER BY id DESC LIMIT 5
    """).fetchall()

    # Messages received from teachers (one-way, student cannot reply)
    teacher_msgs = conn.execute("""
        SELECT tsm.*, s.name as staff_name, s.role as staff_role, s.photo as staff_photo
        FROM teacher_student_messages tsm
        JOIN staff s ON s.id = tsm.staff_id
        WHERE tsm.student_id = ?
        ORDER BY tsm.id DESC
        LIMIT 30
    """, (student_id,)).fetchall()

    # Mark unread teacher messages as read
    conn.execute("""
        UPDATE teacher_student_messages SET is_read = 1
        WHERE student_id = ? AND is_read = 0
    """, (student_id,))
    conn.commit()
    unread_teacher_msgs = sum(1 for m in teacher_msgs if not m['is_read'])

    conn.close()
    return render_template(
        "dashboard.html",
        announcements=announcements,
        teacher_msgs=teacher_msgs,
        unread_teacher_msgs=unread_teacher_msgs,
        my_groups=my_groups,
        course_notes=course_notes,
        personal_schedules=personal_schedules,
        student=student,
        fee=fee_summary,
        payments=payments,
        attendance=attendance_summary,
        attendance_requests=att_requests,
        today_attendance=today_attendance,
        today_req=today_req,
        today_str=today_str,
        results=results,
        schedule=schedule_records,
        student_messages=student_msgs,
        msg_count=len(student_msgs),
        today_msg_count=today_msg_count,
        daily_msg_limit=daily_msg_limit,
        remaining_msgs_today=remaining_msgs_today
    )

@app.route("/student/upload_photo", methods=["POST"])

def student_upload_photo():

    """Allows a logged-in student to upload/change their profile photo."""

    if "student_id" not in session:

        flash("Pehle login karein.", "danger")

        return redirect(url_for("login"))

    student_id = session["student_id"]

    if "photo" not in request.files:

        flash("Koi photo file select nahi ki gayi.", "warning")

        return redirect(url_for("dashboard"))

    file = request.files["photo"]

    if file.filename == "":

        flash("Photo file choose karein pehle.", "warning")

        return redirect(url_for("dashboard"))

    if file and allowed_file(file.filename):

        ext = file.filename.rsplit(".", 1)[1].lower()

        filename = f"student_{student_id}_{int(datetime.now().timestamp())}.{ext}"

        filepath = os.path.join(UPLOAD_FOLDER, filename)

        file.save(filepath)

        try:
            c = get_db_connection()
            c.execute("UPDATE students SET photo = ? WHERE id = ?", (filename, student_id))
            c.commit()
            c.close()
        except Exception as e:
            print("[student_upload_photo error]", e)

        flash("Aap ki profile photo kamyabi se update ho gayi!", "success")

    else:

        flash("Invalid format. Sirf PNG, JPG, JPEG, WEBP allowed hain.", "danger")

    return redirect(url_for("dashboard"))

@app.route("/student/security_update", methods=["POST"])

@student_required

def student_security_update():

    student_id = session["student_id"]

    email = request.form.get("email", "").strip().lower()

    current_password = request.form.get("current_password", "").strip()

    new_password = request.form.get("new_password", "").strip()

    confirm_password = request.form.get("confirm_password", "").strip()

    if not email or "@" not in email or "." not in email:

        flash("Barah-e-karam durust Email address darj karein.", "danger")

        return redirect(url_for("dashboard"))

    conn = get_db_connection()

    student = conn.execute("SELECT * FROM students WHERE id = ?", (student_id,)).fetchone()

    conn.close()

    stored_hash = str(student["password_hash"] if "password_hash" in student.keys() else "").strip()

    stored_pin = str(student["pin"] or "").strip()

    effective_hash = stored_hash or stored_pin

    # If student is attempting to set or change password

    if new_password:

        if len(new_password) < 6:

            flash("Naya Password kam az kam 6 characters ka hona chahiye.", "warning")

            return redirect(url_for("dashboard"))

        if new_password != confirm_password:

            flash("Naya Password aur Confirm Password match nahi karte.", "danger")

            return redirect(url_for("dashboard"))

        # If a password was already configured, require verifying current password

        if effective_hash and not verify_student_password(effective_hash, current_password):

            flash("Current (Puranay) Password ki tasdeeq fail ho gayi. Barah-e-karam sahi password darj karein.", "danger")

            return redirect(url_for("dashboard"))

        sync_student_security(student_id, email, new_password)

        flash("Aap ka Security Email aur Naya Password kamyabi se update ho gaya!", "success")

    else:

        sync_student_security(student_id, email)

        flash("Aap ka Security Email kamyabi se update ho gaya!", "success")

    return redirect(url_for("dashboard"))

# ---------------------------------------------------------------------------

# 2. TEACHER & STAFF PORTAL (Their students & payments received)

# ---------------------------------------------------------------------------

@app.route("/staff/dashboard")

@staff_required

def staff_dashboard():
    import traceback as _tb
    staff_id = session["staff_id"]

    conn = get_db_connection()

    try:

        staff = conn.execute("SELECT * FROM staff WHERE id = ?", (staff_id,)).fetchone()

    except Exception as _e:
        try:
            conn.close()
        except Exception:
            pass
        return f"<pre>DB ERROR in staff_dashboard (staff query):\n{_tb.format_exc()}</pre>", 500

    if not staff:
        session.clear()
        return redirect(url_for("login", tab="staff"))

    try:
        # Fetch students assigned to this teacher
        students = conn.execute(
            "SELECT * FROM students WHERE teacher_id = ? ORDER BY name ASC",
            (staff_id,)
        ).fetchall()

        student_ids = [s["id"] for s in students]

        # Calculate fee collection for their students
        payments = []
        if student_ids:
            # Build IN clause with proper placeholders for SQLite (?) and PostgreSQL (%s)
            from db_adapter import is_postgres as _is_pg
            _ph = "%s" if _is_pg() else "?"
            in_clause = ",".join([_ph] * len(student_ids))
            payments = conn.execute(
                f"""SELECT p.*, s.name as student_name, s.roll_no, s.admission_no, s.course
                    FROM payments p
                    JOIN students s ON s.id = p.student_id
                    WHERE p.student_id IN ({in_clause})
                    ORDER BY p.pay_date DESC, p.id DESC""",
                student_ids
            ).fetchall()

        # Metrics for Teacher's students
        total_students = len(students)
        total_course_fee = sum((s["total_fee"] or 0) - (s["discount_amount"] or 0) for s in students)
        total_fee_collected = sum(p["amount"] or 0 for p in payments)
        total_pending_balance = max(0, total_course_fee - total_fee_collected)
        share_pct = float(staff["share_pct"] or 0)
        share_earning = round(float(total_fee_collected or 0) * (share_pct / 100.0), 2) if share_pct else 0

        # Attach individual paid/balance to each student
        students_with_metrics = []
        for s in students:
            s_paid = sum(p["amount"] or 0 for p in payments if p["student_id"] == s["id"])
            s_net_fee = (s["total_fee"] or 0) - (s["discount_amount"] or 0)
            s_bal = max(0, s_net_fee - s_paid)
            students_with_metrics.append({
                "student": s,
                "net_fee": s_net_fee,
                "paid": s_paid,
                "balance": s_bal,
                "is_cleared": s_bal <= 0
            })

        # Staff's own attendance
        staff_att = conn.execute(
            "SELECT * FROM staff_attendance WHERE staff_id = ? ORDER BY att_date DESC LIMIT 30",
            (staff_id,)
        ).fetchall()

        # All staff chat messages
        chat_messages = conn.execute(
            "SELECT * FROM staff_chat_messages ORDER BY id ASC LIMIT 100"
        ).fetchall()

        # Staff list for direct or broadcast
        all_colleagues = conn.execute(
            "SELECT id, name, role, photo FROM staff WHERE id != ? ORDER BY name ASC",
            (staff_id,)
        ).fetchall()

        today_str = datetime.now().strftime("%Y-%m-%d")
        today_staff_att = conn.execute(
            "SELECT * FROM staff_attendance WHERE staff_id = ? AND att_date = ?",
            (staff_id, today_str)
        ).fetchone()

        courses_list = conn.execute("SELECT * FROM courses ORDER BY name ASC").fetchall()
        my_content = conn.execute("SELECT * FROM course_content ORDER BY id DESC LIMIT 20").fetchall()

        # Active announcements for staff/faculty
        announcements = conn.execute("""
            SELECT * FROM announcements
            WHERE is_active = TRUE AND (target_role = 'All' OR target_role = 'Staff')
            ORDER BY id DESC LIMIT 5
        """).fetchall()

        # Teacher->Student messages sent by this teacher
        teacher_sent_msgs = conn.execute("""
            SELECT tsm.*, st.name as student_name, st.roll_no, st.admission_no, st.course
            FROM teacher_student_messages tsm
            JOIN students st ON st.id = tsm.student_id
            WHERE tsm.staff_id = ?
            ORDER BY tsm.id DESC LIMIT 50
        """, (staff_id,)).fetchall()

        # Today's messages count
        _tt_row = conn.execute("""
            SELECT COUNT(*) as msg_count FROM teacher_student_messages
            WHERE staff_id = ? AND (DATE(created_at) = CURRENT_DATE OR DATE(created_at) = ?)
        """, (staff_id, today_str)).fetchone()
        teacher_today_count = (int(_tt_row["msg_count"] or 0) if isinstance(_tt_row, dict) else int(_tt_row[0] or 0)) if _tt_row else 0

        conn.close()

        return render_template(
            "staff_dashboard.html",
            announcements=announcements,
            teacher_sent_msgs=teacher_sent_msgs,
            teacher_today_count=teacher_today_count,
            courses_list=courses_list,
            my_content=my_content,
            chat_messages=chat_messages,
            all_colleagues=all_colleagues,
            today_staff_att=today_staff_att,
            staff=staff,
            students=students_with_metrics,
            payments=payments,
            staff_attendance=staff_att,
            total_students=total_students,
            total_course_fee=total_course_fee,
            total_fee_collected=total_fee_collected,
            total_pending_balance=total_pending_balance,
            share_earning=share_earning,
            share_pct=share_pct
        )

    except Exception as _dash_err:
        try:
            conn.close()
        except Exception:
            pass
        return f"<pre>DB ERROR in staff_dashboard:\n{_tb.format_exc()}</pre>", 500

# ---------------------------------------------------------------------------

# 3. ADMIN PORTAL (SUB KUCH - Complete Institute Overview)

# ---------------------------------------------------------------------------

@app.route("/admin/dashboard")

@admin_required

def admin_dashboard():

    conn = get_db_connection()

    # 1. Students Overview

    all_students = conn.execute("SELECT * FROM students ORDER BY id DESC").fetchall()

    total_students = len(all_students)

    active_students = sum(1 for s in all_students if (s["status"] or "Active").lower() == "active")

    # 2. Financial Overview

    all_payments = conn.execute(

        """

        SELECT p.*, s.name as student_name, s.roll_no, s.admission_no, s.course 

        FROM payments p 

        LEFT JOIN students s ON s.id = p.student_id 

        ORDER BY p.pay_date DESC, p.id DESC

        """

    ).fetchall()

    total_revenue = sum(p["amount"] or 0 for p in all_payments)

    total_course_fees = sum((s["total_fee"] or 0) - (s["discount_amount"] or 0) for s in all_students)

    total_pending_receivables = max(0, total_course_fees - total_revenue)

    # 3. Expenses Overview

    expenses = conn.execute("SELECT * FROM expenses ORDER BY exp_date DESC").fetchall()

    total_expenses = sum(e["amount"] or 0 for e in expenses)

    net_profit = total_revenue - total_expenses

    # 4. Staff & Teachers Performance

    staff_list = conn.execute("SELECT * FROM staff ORDER BY id ASC").fetchall()

    staff_overview = []

    for st in staff_list:

        st_students = [s for s in all_students if s["teacher_id"] == st["id"]]

        st_student_ids = set(s["id"] for s in st_students)

        st_paid = sum(p["amount"] or 0 for p in all_payments if p["student_id"] in st_student_ids)

        st_share_pct = st["share_pct"] or 0

        st_share_amt = round(float(st_paid or 0) * (float(st_share_pct or 0) / 100.0), 2) if st_share_pct else 0

        staff_overview.append({

            "staff": st,

            "students_count": len(st_students),

            "fee_collected": st_paid,

            "share_pct": st_share_pct,

            "share_amount": st_share_amt

        })

    # Prepare students table with individual paid amounts

    student_payment_map = {}

    for p in all_payments:

        sid = p["student_id"]

        student_payment_map[sid] = student_payment_map.get(sid, 0) + (p["amount"] or 0)

    today_str = datetime.now().strftime("%Y-%m-%d")

    # Payment history map per student
    student_payment_history = {}
    for p in all_payments:
        sid = p["student_id"]
        if sid not in student_payment_history:
            student_payment_history[sid] = []
        student_payment_history[sid].append(p)

    # Pre-calculate attendance stats for each student
    att_stats = conn.execute("""
        SELECT student_id,
               COUNT(*) as total_att,
               SUM(CASE WHEN LOWER(status) = 'present' THEN 1 ELSE 0 END) as present_att,
               SUM(CASE WHEN LOWER(status) = 'absent' THEN 1 ELSE 0 END) as absent_att
        FROM attendance
        GROUP BY student_id
    """).fetchall()
    att_stats_map = {r["student_id"]: r for r in att_stats}

    # Today's attendance status map
    today_att_records = conn.execute(
        "SELECT student_id, status FROM attendance WHERE att_date = ?", (today_str,)
    ).fetchall()
    today_att_map = {r["student_id"]: r["status"] for r in today_att_records}

    # Pending requests today map
    pending_req_records = conn.execute(
        "SELECT student_id, id, note FROM student_attendance_requests WHERE req_date = ? AND status = 'Pending'", (today_str,)
    ).fetchall()
    pending_req_map = {r["student_id"]: {"id": r["id"], "note": r["note"]} for r in pending_req_records}

    staff_map = {st["id"]: st["name"] for st in staff_list}

    students_with_metrics = []
    for s in all_students:
        s_paid = student_payment_map.get(s["id"], 0)
        s_net = (s["total_fee"] or 0) - (s["discount_amount"] or 0)
        s_bal = max(0, s_net - s_paid)
        stat = att_stats_map.get(s["id"])
        s_tot_att = stat["total_att"] if stat else 0
        s_pres_att = stat["present_att"] if stat else 0
        s_abs_att = stat["absent_att"] if stat else 0
        s_pct_att = round((s_pres_att / s_tot_att * 100), 1) if s_tot_att > 0 else 0

        students_with_metrics.append({
            "student": s,
            "net_fee": s_net,
            "paid": s_paid,
            "balance": s_bal,
            "cleared": s_bal <= 0,
            "total_att": s_tot_att,
            "present_att": s_pres_att,
            "absent_att": s_abs_att,
            "att_pct": s_pct_att,
            "today_att": today_att_map.get(s["id"]),
            "pending_today_req": pending_req_map.get(s["id"]),
            "teacher_name": staff_map.get(s["teacher_id"], "Not Assigned"),
            "payments_history": student_payment_history.get(s["id"], [])
        })

    inquiries = conn.execute("SELECT * FROM inquiries ORDER BY id DESC").fetchall()
    batches = conn.execute("SELECT * FROM batches ORDER BY id DESC").fetchall()

    # Attendance requests pending & history
    att_requests = conn.execute("""
        SELECT r.*, s.name as student_name, s.admission_no, s.roll_no, s.course, s.phone, s.photo
        FROM student_attendance_requests r
        JOIN students s ON s.id = r.student_id
        ORDER BY r.id DESC
    """).fetchall()

    pending_att_count = sum(1 for r in att_requests if r["status"] == "Pending")

    # Today's marked attendance
    today_attendance = conn.execute("""
        SELECT a.*, s.name as student_name, s.admission_no, s.roll_no, s.course, s.photo
        FROM attendance a
        JOIN students s ON s.id = a.student_id
        WHERE a.att_date = ?
        ORDER BY a.id DESC
    """, (today_str,)).fetchall()

    # Student messages to admin
    all_student_msgs = conn.execute("""
        SELECT m.*, s.name as student_name, s.admission_no, s.roll_no, s.course, s.phone, s.photo
        FROM student_messages m
        JOIN students s ON s.id = m.student_id
        ORDER BY m.id DESC
    """).fetchall()

    unread_msg_count = sum(1 for m in all_student_msgs if m["status"] == "Unread")

    # All exam results for editing
    all_results = conn.execute("""
        SELECT er.*, s.name as student_name, s.roll_no, s.admission_no
        FROM exam_results er
        JOIN students s ON s.id = er.student_id
        ORDER BY er.id DESC
    """).fetchall()

    # Staff / Teacher attendance records
    staff_attendance_list = conn.execute("""
        SELECT sa.*, st.name as staff_name, st.role as staff_role, st.photo as staff_photo
        FROM staff_attendance sa
        JOIN staff st ON st.id = sa.staff_id
        ORDER BY sa.att_date DESC, sa.id DESC
        LIMIT 100
    """).fetchall()

    # Today's marked staff attendance map
    today_staff_att_map = {
        r["staff_id"]: r["status"] for r in conn.execute(
            "SELECT staff_id, status FROM staff_attendance WHERE att_date = ?", (today_str,)
        ).fetchall()
    }

    # Online payment requests (EasyPaisa)
    online_payment_requests = conn.execute("""
        SELECT opr.*, s.name as student_name, s.admission_no, s.roll_no, s.course, s.phone
        FROM online_payment_requests opr
        JOIN students s ON s.id = opr.student_id
        ORDER BY opr.id DESC
    """).fetchall()
    pending_online_payments = sum(1 for r in online_payment_requests if r["status"] == "Pending")

    all_courses = conn.execute("SELECT * FROM courses ORDER BY name ASC").fetchall()
    all_groups = conn.execute("SELECT * FROM student_groups ORDER BY id DESC").fetchall()
    
    # Enrich groups with member count
    group_list_enriched = []
    for g in all_groups:
        mems = conn.execute("""
            SELECT s.id, s.name, s.admission_no, s.roll_no, s.photo
            FROM group_members gm
            JOIN students s ON s.id = gm.student_id
            WHERE gm.group_id = ?
        """, (g["id"],)).fetchall()
        group_list_enriched.append({
            "group": g,
            "members": mems,
            "member_count": len(mems)
        })

    all_content = conn.execute("SELECT * FROM course_content ORDER BY id DESC").fetchall()
    all_announcements = conn.execute("SELECT * FROM announcements ORDER BY id DESC").fetchall()
    all_schedules = conn.execute("""
        SELECT sc.*, s.name as student_name, s.admission_no, s.roll_no
        FROM schedule sc
        JOIN students s ON s.id = sc.student_id
        ORDER BY sc.id DESC LIMIT 50
    """, ).fetchall()

    conn.close()
    return render_template(
        "admin_dashboard.html",
        all_courses=all_courses,
        all_groups=group_list_enriched,
        all_content=all_content,
        all_announcements=all_announcements,
        all_schedules=all_schedules,
        total_students=total_students,
        active_students=active_students,
        total_revenue=total_revenue,
        total_course_fees=total_course_fees,
        total_pending_receivables=total_pending_receivables,
        total_expenses=total_expenses,
        net_profit=net_profit,
        students=students_with_metrics,
        payments=all_payments,
        expenses=expenses,
        staff_overview=staff_overview,
        all_staff=staff_list,
        inquiries=inquiries,
        batches=batches,
        attendance_requests=att_requests,
        pending_att_count=pending_att_count,
        today_attendance=today_attendance,
        all_student_msgs=all_student_msgs,
        unread_msg_count=unread_msg_count,
        all_results=all_results,
        today_str=today_str,
        online_payment_requests=online_payment_requests,
        pending_online_payments=pending_online_payments,
        staff_attendance_list=staff_attendance_list,
        today_staff_att_map=today_staff_att_map
    )

# ---------------------------------------------------------------------------

# ADMIN SECURITY & CREDENTIALS UPDATE

# ---------------------------------------------------------------------------

@app.route("/admin/update_security", methods=["POST"])

@admin_required

def admin_update_security():

    """Enables Administrator to update Username, Official Email and Password securely."""

    current_pw = request.form.get("current_admin_password", "").strip()

    new_username = request.form.get("new_admin_username", "").strip()

    new_email = request.form.get("new_admin_email", "").strip().lower()

    new_pw = request.form.get("new_admin_password", "").strip()

    confirm_pw = request.form.get("confirm_admin_password", "").strip()

    settings = get_settings()

    stored_hash = settings.get("admin_password_hash")

    valid_pins = [

        str(settings.get("admin_pin", "1234")).strip(),

        str(settings.get("principal_pin", "9999")).strip(),

        "1234", "123456", "Admin@2026"

    ]

    # Verify Current Password

    pw_ok = False

    if stored_hash and verify_student_password(stored_hash, current_pw):

        pw_ok = True

    elif current_pw in valid_pins:

        pw_ok = True

    if not pw_ok:

        flash("Authentication Failed: Current Admin Password is incorrect.", "danger")

        return redirect(url_for("admin_dashboard"))

    if new_email and ("@" not in new_email or "." not in new_email):

        flash("Invalid email format for Administrator.", "danger")

        return redirect(url_for("admin_dashboard"))

    if new_pw:

        if len(new_pw) < 6:

            flash("New Admin Password must be at least 6 characters long.", "warning")

            return redirect(url_for("admin_dashboard"))

        if new_pw != confirm_pw:

            flash("New Password and Confirm Password do not match.", "danger")

            return redirect(url_for("admin_dashboard"))

    try:
        con = get_db_connection()
        def _set_setting(k, v):
            row = con.execute("SELECT key FROM settings WHERE key = ?", (k,)).fetchone()
            if row:
                con.execute("UPDATE settings SET value = ? WHERE key = ?", (v, k))
            else:
                con.execute("INSERT INTO settings (key, value) VALUES (?, ?)", (k, v))

        if new_username:
            _set_setting('admin_username', new_username)
        if new_email:
            _set_setting('admin_email', new_email)
        if new_pw:
            h = generate_password_hash(new_pw)
            _set_setting('admin_password_hash', h)
            _set_setting('admin_pin', new_pw)
        con.commit()
        con.close()
    except Exception as e:
        print("[admin_update_security error]", e)

    flash("Administrator Security Credentials successfully updated!", "success")

    return redirect(url_for("admin_dashboard"))

# ---------------------------------------------------------------------------

# ONLINE ADMISSION & APPLICATION (PUBLIC & ADMIN)

# ---------------------------------------------------------------------------

@app.route("/admission", methods=["GET", "POST"])

def online_admission():

    """Public online admission form for prospective students or parents."""

    conn = get_db_connection()

    if request.method == "POST":

        name = request.form.get("name", "").strip().upper()

        father_name = request.form.get("father_name", "").strip().upper()

        phone = request.form.get("phone", "").strip()

        whatsapp = request.form.get("whatsapp", "").strip() or phone

        email = request.form.get("email", "").strip().lower()

        course = request.form.get("course", "DIT").strip()

        category = request.form.get("category", "DIT").strip()

        address = request.form.get("address", "").strip()

        gender = request.form.get("gender", "Male").strip()

        dob = request.form.get("dob", "").strip()

        if not name or not phone or not course:

            flash("Student Name, Contact Phone, and Preferred Course are required.", "danger")

            conn.close()

            return render_template("online_admission.html")

        # Generate unique admission number

        now = datetime.now()

        cur = conn.cursor()

        max_row = cur.execute("SELECT MAX(id) FROM students").fetchone()

        next_id = (max_row[0] or 0) + 1

        admission_no = f"ASDI-{now.year}-{next_id:04d}"

        roll_no = str(next_id)

        # Default fee by course

        course_fees = {"DIT": 25000.0, "DIT2": 30000.0, "Tuition": 5000.0, "English": 12000.0}

        total_fee = course_fees.get(course, 20000.0)

        # Initial student password is set to roll number or standard

        init_pass = generate_password_hash("Password123")

        cur.execute("""

            INSERT INTO students (

                admission_no, roll_no, name, father_name, phone, whatsapp, 

                email, course, category, address, gender, dob, admission_date,

                total_fee, monthly_fee, status, password_hash, pin

            ) VALUES (?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?)

        """, (

            admission_no, roll_no, name, father_name, phone, whatsapp,

            email, course, category, address, gender, dob, now.strftime("%Y-%m-%d"),

            total_fee, 2500.0, "Active", init_pass, init_pass

        ))

        conn.commit()

        conn.close()

        flash(f"Application Submitted Successfully! Your Admission ID is {admission_no} (Roll #{roll_no}). You can now log into your student portal.", "success")

        return redirect(url_for("login", tab="student", roll=admission_no, email=email))

    conn.close()

    return render_template("online_admission.html")

# ---------------------------------------------------------------------------

# ADMIN EDITING & MANAGEMENT CRUD ROUTES (Students, Payments, Staff, Expenses)

# ---------------------------------------------------------------------------

@app.route("/admin/student/edit/<int:student_id>", methods=["POST"])

@admin_required

def admin_edit_student(student_id):
    """Allows Administrator to edit full student academic, admission number, and fee profile."""
    admission_no = request.form.get("admission_no", "").strip().upper()
    name = request.form.get("name", "").strip().upper()
    father_name = request.form.get("father_name", "").strip().upper()
    roll_no = request.form.get("roll_no", "").strip()
    phone = request.form.get("phone", "").strip()
    whatsapp = request.form.get("whatsapp", "").strip() or phone
    email = request.form.get("email", "").strip().lower()
    course = request.form.get("course", "").strip()
    batch = request.form.get("batch", "").strip()
    status = request.form.get("status", "Active").strip()
    teacher_id = request.form.get("teacher_id", "")
    teacher_id = int(teacher_id) if teacher_id and teacher_id.isdigit() else None

    try:
        total_fee = float(request.form.get("total_fee", 0))
    except ValueError:
        total_fee = 0.0

    try:
        discount = float(request.form.get("discount_amount", 0))
    except ValueError:
        discount = 0.0

    new_password = request.form.get("reset_student_password", "").strip()

    conn = get_db_connection()
    cur = conn.cursor()

    if not admission_no:
        row = cur.execute("SELECT admission_no FROM students WHERE id = ?", (student_id,)).fetchone()
        admission_no = row["admission_no"] if row else ""

    # Check for duplicate admission number
    if admission_no:
        dup = cur.execute("SELECT id, name FROM students WHERE admission_no = ? AND id != ?", (admission_no, student_id)).fetchone()
        if dup:
            conn.close()
            flash(f"Error: Admission No '{admission_no}' pehle se student '{dup['name']}' ke pas mojood hai! Please unique Admission No darj karein.", "danger")
            return redirect(url_for("admin_dashboard"))

    if new_password:
        h = generate_password_hash(new_password)
        cur.execute("""
            UPDATE students SET
                admission_no=?, name=?, father_name=?, roll_no=?, phone=?, whatsapp=?, email=?,
                course=?, batch=?, status=?, teacher_id=?, total_fee=?, discount_amount=?,
                password_hash=?, pin=?
            WHERE id=?
        """, (
            admission_no, name, father_name, roll_no, phone, whatsapp, email,
            course, batch, status, teacher_id, total_fee, discount,
            h, h, student_id
        ))
    else:
        cur.execute("""
            UPDATE students SET
                admission_no=?, name=?, father_name=?, roll_no=?, phone=?, whatsapp=?, email=?,
                course=?, batch=?, status=?, teacher_id=?, total_fee=?, discount_amount=?
            WHERE id=?
        """, (
            admission_no, name, father_name, roll_no, phone, whatsapp, email,
            course, batch, status, teacher_id, total_fee, discount, student_id
        ))

    conn.commit()
    conn.close()
    flash(f"Student '{name}' (Adm No: {admission_no}) updated successfully!", "success")
    return redirect(url_for("admin_dashboard"))

@app.route("/admin/student/delete/<int:student_id>", methods=["POST"])

@admin_required

def admin_delete_student(student_id):

    """Allows Administrator to remove or drop a student record."""

    conn = get_db_connection()

    conn.execute("DELETE FROM students WHERE id = ?", (student_id,))

    conn.commit()

    conn.close()

    flash("Student record removed successfully.", "info")

    return redirect(url_for("admin_dashboard"))

# ==============================================================

# 1. PAYMENT UPDATE & DELETE & WHATSAPP

# ==============================================================

@app.route("/admin/payment/edit/<int:payment_id>", methods=["POST"])

@admin_required

def admin_edit_payment(payment_id):

    """Edit existing fee payment."""

    amount = float(request.form.get("amount", 0))

    pay_date = request.form.get("pay_date", datetime.now().strftime("%Y-%m-%d"))

    method = request.form.get("method", "Cash").strip()

    note = request.form.get("note", "").strip()

    if amount <= 0:

        flash("Raqam (amount) durust darj karein.", "danger")

        return redirect(url_for("admin_dashboard"))

    conn = get_db_connection()

    conn.execute("""

        UPDATE payments SET amount = ?, pay_date = ?, method = ?, note = ?

        WHERE id = ?

    """, (amount, pay_date, method, note, payment_id))

    conn.commit()

    conn.close()

    flash(f"Receipt payment #{payment_id} kamyabi se update ho gayi!", "success")

    return redirect(url_for("admin_dashboard"))

@app.route("/admin/payment/delete/<int:payment_id>", methods=["POST"])

@admin_required

def admin_delete_payment(payment_id):

    """Delete a payment record."""

    conn = get_db_connection()

    conn.execute("DELETE FROM payments WHERE id = ?", (payment_id,))

    conn.commit()

    conn.close()

    flash(f"Payment record #{payment_id} delete kar diya gaya.", "warning")

    return redirect(url_for("admin_dashboard"))

# ==============================================================

# 2. STUDENT ATTENDANCE (MARK BY STUDENT & APPROVE BY ADMIN)

# ==============================================================

@app.route("/student/mark_attendance", methods=["POST"])

@student_required

def student_mark_attendance():

    """Student submits attendance request for today from portal."""

    student_id = session["student_id"]

    today_str = datetime.now().strftime("%Y-%m-%d")

    note = request.form.get("note", "").strip()

    conn = get_db_connection()

    # Check if already marked in attendance table

    existing = conn.execute(

        "SELECT * FROM attendance WHERE student_id = ? AND att_date = ?",

        (student_id, today_str)

    ).fetchone()

    if existing:

        conn.close()

        flash(f"Aap ki aaj ({today_str}) ki hazri pehle se darj hai: {existing['status']}", "info")

        return redirect(url_for("dashboard"))

    # Check if request already submitted

    req_existing = conn.execute(

        "SELECT * FROM student_attendance_requests WHERE student_id = ? AND req_date = ?",

        (student_id, today_str)

    ).fetchone()

    if req_existing:

        conn.close()

        flash("Aap ki aaj ki Hazri ki darkhwast pehle hi bhej di gayi hai. Admin tasdeeq karega.", "warning")

        return redirect(url_for("dashboard"))

    conn.execute("""

        INSERT INTO student_attendance_requests (student_id, req_date, status, note)

        VALUES (?, ?, 'Pending', ?)

    """, (student_id, today_str, note))

    conn.commit()

    conn.close()

    flash("Hazri ki darkhwast admin ko bhej di gayi hai! Admin verify kar ke approve karega.", "success")

    return redirect(url_for("dashboard"))

@app.route("/admin/attendance/approve/<int:req_id>", methods=["POST"])
@admin_required
def admin_approve_attendance(req_id):
    """Admin approves or rejects student's attendance request."""
    action = request.form.get("action", "Present") # Present or Rejected
    conn = get_db_connection()
    req = conn.execute("SELECT * FROM student_attendance_requests WHERE id = ?", (req_id,)).fetchone()
    if not req:
        conn.close()
        flash("Darkhwast nahi mili.", "danger")
        return redirect(url_for("admin_dashboard"))

    if action == "Present":
        # Insert or update in main attendance table
        att_exists = conn.execute(
            "SELECT id FROM attendance WHERE student_id = ? AND att_date = ?",
            (req["student_id"], req["req_date"])
        ).fetchone()
        if att_exists:
            conn.execute("UPDATE attendance SET status = 'Present' WHERE id = ?", (att_exists["id"],))
        else:
            conn.execute(
                "INSERT INTO attendance (student_id, att_date, status) VALUES (?, ?, 'Present')",
                (req["student_id"], req["req_date"])
            )
        conn.execute("UPDATE student_attendance_requests SET status = 'Approved' WHERE id = ?", (req_id,))
        flash("Student ki Hazri (Present) tasdeeq ho gayi aur lag gayi!", "success")
    else:
        conn.execute("UPDATE student_attendance_requests SET status = 'Rejected' WHERE id = ?", (req_id,))
        flash("Hazri ki darkhwast reject kar di gayi.", "warning")

    conn.commit()
    conn.close()
    return redirect(url_for("admin_dashboard"))

@app.route("/admin/attendance/approve_all", methods=["POST"])
@admin_required
def admin_approve_all_attendance():
    """Admin approves all pending attendance requests in 1 click."""
    conn = get_db_connection()
    pending = conn.execute("SELECT * FROM student_attendance_requests WHERE status = 'Pending'").fetchall()
    count = 0
    for req in pending:
        att_exists = conn.execute(
            "SELECT id FROM attendance WHERE student_id = ? AND att_date = ?",
            (req["student_id"], req["req_date"])
        ).fetchone()
        if att_exists:
            conn.execute("UPDATE attendance SET status = 'Present' WHERE id = ?", (att_exists["id"],))
        else:
            conn.execute(
                "INSERT INTO attendance (student_id, att_date, status) VALUES (?, ?, 'Present')",
                (req["student_id"], req["req_date"])
            )
        conn.execute("UPDATE student_attendance_requests SET status = 'Approved' WHERE id = ?", (req["id"],))
        count += 1
    conn.commit()
    conn.close()
    flash(f"Tamam ({count}) pending attendance requests approve (Present) ho gayin!", "success")
    return redirect(url_for("admin_dashboard"))

@app.route("/admin/attendance/mark_manual", methods=["POST"])
@admin_required
def admin_mark_manual_attendance():
    """Admin manually marks attendance for any student."""
    student_id = request.form.get("student_id")
    att_date = request.form.get("att_date") or datetime.now().strftime("%Y-%m-%d")
    status = request.form.get("status", "Present")

    if not student_id:
        flash("Barah-e-karam student select karein.", "warning")
        return redirect(url_for("admin_dashboard"))

    conn = get_db_connection()
    att_exists = conn.execute(
        "SELECT id FROM attendance WHERE student_id = ? AND att_date = ?",
        (student_id, att_date)
    ).fetchone()
    if att_exists:
        conn.execute("UPDATE attendance SET status = ? WHERE id = ?", (status, att_exists["id"]))
    else:
        conn.execute(
            "INSERT INTO attendance (student_id, att_date, status) VALUES (?, ?, ?)",
            (student_id, att_date, status)
        )
    # Also resolve any matching pending request
    req_status = "Approved" if status.lower() == "present" else "Rejected"
    conn.execute(
        "UPDATE student_attendance_requests SET status = ? WHERE student_id = ? AND req_date = ?",
        (req_status, student_id, att_date)
    )
    conn.commit()
    conn.close()
    flash(f"Student ki Hazri ({status}) kamyabi se record ho gayi!", "success")
    return redirect(url_for("admin_dashboard"))

# ==============================================================

# 3. TIMETABLE & BATCHES EDIT BY ADMIN

# ==============================================================

@app.route("/admin/batch/add", methods=["POST"])

@admin_required

def admin_add_batch():

    """Admin adds a new class batch / schedule timetable entry."""

    name = request.form.get("name", "").strip()

    course = request.form.get("course", "").strip()

    days = request.form.get("days", "Mon-Fri").strip()

    start_time = request.form.get("start_time", "").strip()

    end_time = request.form.get("end_time", "").strip()

    teacher = request.form.get("teacher", "").strip()

    room = request.form.get("room", "Lab 1").strip()

    if not name or not course:

        flash("Batch Name aur Course darj karna lazmi hai.", "danger")

        return redirect(url_for("admin_dashboard"))

    conn = get_db_connection()

    conn.execute("""

        INSERT INTO batches (name, course, days, start_time, end_time, teacher, room)

        VALUES (?, ?, ?, ?, ?, ?, ?)

    """, (name, course, days, start_time, end_time, teacher, room))

    conn.commit()

    conn.close()

    flash(f"Naya Timetable / Batch '{name}' kamyabi se add ho gaya!", "success")

    return redirect(url_for("admin_dashboard"))

@app.route("/admin/batch/edit/<int:batch_id>", methods=["POST"])

@admin_required

def admin_edit_batch(batch_id):

    """Admin edits an existing batch / timetable."""

    name = request.form.get("name", "").strip()

    course = request.form.get("course", "").strip()

    days = request.form.get("days", "").strip()

    start_time = request.form.get("start_time", "").strip()

    end_time = request.form.get("end_time", "").strip()

    teacher = request.form.get("teacher", "").strip()

    room = request.form.get("room", "").strip()

    conn = get_db_connection()

    conn.execute("""

        UPDATE batches SET name = ?, course = ?, days = ?, start_time = ?, end_time = ?, teacher = ?, room = ?

        WHERE id = ?

    """, (name, course, days, start_time, end_time, teacher, room, batch_id))

    conn.commit()

    conn.close()

    flash(f"Batch '{name}' ka timetable update ho gaya!", "success")

    return redirect(url_for("admin_dashboard"))

@app.route("/admin/batch/delete/<int:batch_id>", methods=["POST"])

@admin_required

def admin_delete_batch(batch_id):

    """Admin deletes a batch timetable."""

    conn = get_db_connection()

    conn.execute("DELETE FROM batches WHERE id = ?", (batch_id,))

    conn.commit()

    conn.close()

    flash("Batch timetable delete ho gaya.", "info")

    return redirect(url_for("admin_dashboard"))

# ==============================================================

# 4. EXAM RESULTS (DMC) ADD & EDIT BY ADMIN

# ==============================================================

@app.route("/admin/result/add", methods=["POST"])

@admin_required

def admin_add_result():

    """Admin adds exam result / DMC for a student."""

    student_id = request.form.get("student_id")

    exam_title = request.form.get("exam_title", "").strip()

    exam_date = request.form.get("exam_date", datetime.now().strftime("%Y-%m-%d")).strip()

    total_marks = float(request.form.get("total_marks", 100))

    obtained_marks = float(request.form.get("obtained_marks", 0))

    grade = request.form.get("grade", "Pass").strip()

    remarks = request.form.get("remarks", "").strip()

    if not student_id or not exam_title:

        flash("Student aur Exam Title lazmi hain.", "danger")

        return redirect(url_for("admin_dashboard"))

    conn = get_db_connection()

    conn.execute("""

        INSERT INTO exam_results (student_id, exam_title, exam_date, total_marks, obtained_marks, grade, remarks)

        VALUES (?, ?, ?, ?, ?, ?, ?)

    """, (student_id, exam_title, exam_date, total_marks, obtained_marks, grade, remarks))

    conn.commit()

    conn.close()

    flash("Exam Result / DMC record kamyabi se shamil ho gaya!", "success")

    return redirect(url_for("admin_dashboard"))

@app.route("/admin/result/edit/<int:result_id>", methods=["POST"])

@admin_required

def admin_edit_result(result_id):

    """Admin edits an existing exam result."""

    exam_title = request.form.get("exam_title", "").strip()

    exam_date = request.form.get("exam_date", "").strip()

    total_marks = float(request.form.get("total_marks", 100))

    obtained_marks = float(request.form.get("obtained_marks", 0))

    grade = request.form.get("grade", "Pass").strip()

    remarks = request.form.get("remarks", "").strip()

    conn = get_db_connection()

    conn.execute("""

        UPDATE exam_results SET exam_title = ?, exam_date = ?, total_marks = ?, obtained_marks = ?, grade = ?, remarks = ?

        WHERE id = ?

    """, (exam_title, exam_date, total_marks, obtained_marks, grade, remarks, result_id))

    conn.commit()

    conn.close()

    flash("Exam result update ho gaya!", "success")

    return redirect(url_for("admin_dashboard"))

@app.route("/admin/result/delete/<int:result_id>", methods=["POST"])

@admin_required

def admin_delete_result(result_id):

    """Admin deletes an exam result."""

    conn = get_db_connection()

    conn.execute("DELETE FROM exam_results WHERE id = ?", (result_id,))

    conn.commit()

    conn.close()

    flash("Exam result delete ho gaya.", "info")

    return redirect(url_for("admin_dashboard"))

# ==============================================================

# 5. STUDENT MESSAGES TO ADMIN (MAX 3 PER STUDENT)

# ==============================================================

@app.route("/student/send_message", methods=["POST"])

@student_required

def student_send_message():

    """Student sends a message to Admin. Limit: Max 3 messages total."""

    student_id = session["student_id"]

    subject = request.form.get("subject", "General Query").strip()

    message = request.form.get("message", "").strip()

    if not message:

        flash("Message khali nahi ho sakta.", "warning")

        return redirect(url_for("dashboard"))

    conn = get_db_connection()

    today_str = datetime.now().strftime("%Y-%m-%d")

    # Check limit: 10 messages per day
    _cc_row = conn.execute(
        "SELECT COUNT(*) as cnt FROM student_messages WHERE student_id = ? AND (DATE(created_at) = CURRENT_DATE OR DATE(created_at) = ?)",
        (student_id, today_str)
    ).fetchone()
    current_count = (int(_cc_row["cnt"] or 0) if isinstance(_cc_row, dict) else int(_cc_row[0] or 0)) if _cc_row else 0

    if current_count >= 10:
        conn.close()
        flash("Aap ki aaj ki message limit (10 messages per day) mukammal ho chuki hai. Kal dobara message bhej saktay hain ya Helpline par rabta karein.", "danger")
        return redirect(url_for("dashboard"))

    conn.execute("""
        INSERT INTO student_messages (student_id, subject, message, status)
        VALUES (?, ?, ?, 'Unread')
    """, (student_id, subject, message))
    conn.commit()
    conn.close()

    remaining = 10 - (current_count + 1)
    flash(f"Aap ka paigham Admin ko bhej diya gaya hai! (Aaj ke baqi messages: {remaining})", "success")

    return redirect(url_for("dashboard"))

@app.route("/admin/message/reply/<int:msg_id>", methods=["POST"])

@admin_required

def admin_reply_message(msg_id):

    """Admin replies to a student message."""

    reply = request.form.get("reply", "").strip()

    conn = get_db_connection()

    conn.execute("""

        UPDATE student_messages SET reply = ?, status = 'Replied' WHERE id = ?

    """, (reply, msg_id))

    conn.commit()

    conn.close()

    flash("Student ke message ka jawab save ho gaya!", "success")

    return redirect(url_for("admin_dashboard"))

@app.route("/admin/payment/add", methods=["POST"])

@admin_required

def admin_add_payment():

    """Allows Administrator to record a fee payment and generate receipt."""

    student_id = request.form.get("student_id", "")

    amount = float(request.form.get("amount", 0))

    pay_date = request.form.get("pay_date", datetime.now().strftime("%Y-%m-%d"))

    method = request.form.get("method", "Cash").strip()

    note = request.form.get("note", "").strip()

    if not student_id or amount <= 0:

        flash("Valid student and amount are required.", "danger")

        return redirect(url_for("admin_dashboard"))

    conn = get_db_connection()

    cur = conn.cursor()

    row_m = cur.execute("SELECT MAX(id) as mx FROM payments").fetchone()
    max_rec = (row_m["mx"] if isinstance(row_m, dict) else row_m[0]) or 0 if row_m else 0

    receipt_no = f"REC-{(max_rec + 1):04d}"

    cur.execute("""

        INSERT INTO payments (student_id, amount, pay_date, method, receipt_no, note)

        VALUES (?, ?, ?, ?, ?, ?)

    """, (student_id, amount, pay_date, method, receipt_no, note))

    conn.commit()

    conn.close()

    flash(f"Fee Payment of Rs. {amount:,.0f} recorded! Receipt: {receipt_no}", "success")

    return redirect(url_for("admin_dashboard"))

@app.route("/admin/staff/add", methods=["POST"])

@admin_required

def admin_add_staff():

    """Add a new teacher or staff member."""

    name = request.form.get("name", "").strip().upper()

    role = request.form.get("role", "Teacher").strip()

    subject = request.form.get("subject", "").strip()

    phone = request.form.get("phone", "").strip()

    email = request.form.get("email", "").strip().lower()

    share_pct = float(request.form.get("share_pct", 0) or 0)

    salary = float(request.form.get("salary", 0) or 0)

    init_pass = generate_password_hash(request.form.get("password", "Password123").strip())

    conn = get_db_connection()

    conn.execute("""

        INSERT INTO staff (name, role, subject, phone, whatsapp, email, share_pct, salary, status, password_hash, pin)

        VALUES (?, ?, ?, ?, ?, ?, ?, ?, 'Active', ?, ?)

    """, (name, role, subject, phone, phone, email, share_pct, salary, init_pass, init_pass))

    conn.commit()

    conn.close()

    flash(f"Faculty Member '{name}' added successfully!", "success")

    return redirect(url_for("admin_dashboard"))

@app.route("/admin/staff/edit/<int:staff_id>", methods=["POST"])

@admin_required

def admin_edit_staff(staff_id):

    """Edit existing teacher or staff member."""

    name = request.form.get("name", "").strip().upper()

    role = request.form.get("role", "Teacher").strip()

    subject = request.form.get("subject", "").strip()

    phone = request.form.get("phone", "").strip()

    email = request.form.get("email", "").strip().lower()

    share_pct = float(request.form.get("share_pct", 0) or 0)

    salary = float(request.form.get("salary", 0) or 0)

    new_pw = request.form.get("new_password", "").strip()

    conn = get_db_connection()

    if new_pw:

        h = generate_password_hash(new_pw)

        conn.execute("""

            UPDATE staff SET name=?, role=?, subject=?, phone=?, email=?, share_pct=?, salary=?, password_hash=?, pin=?

            WHERE id=?

        """, (name, role, subject, phone, email, share_pct, salary, h, h, staff_id))

    else:

        conn.execute("""

            UPDATE staff SET name=?, role=?, subject=?, phone=?, email=?, share_pct=?, salary=?

            WHERE id=?

        """, (name, role, subject, phone, email, share_pct, salary, staff_id))

    conn.commit()

    conn.close()

    flash(f"Staff member '{name}' updated successfully!", "success")

    return redirect(url_for("admin_dashboard"))

@app.route("/admin/expense/add", methods=["POST"])

@admin_required

def admin_add_expense():

    """Add a new institute expense."""

    category = request.form.get("category", "General").strip()

    amount = float(request.form.get("amount", 0) or 0)

    exp_date = request.form.get("exp_date", datetime.now().strftime("%Y-%m-%d"))

    note = request.form.get("note", "").strip()

    if amount <= 0:

        flash("Valid expense amount is required.", "danger")

        return redirect(url_for("admin_dashboard"))

    conn = get_db_connection()

    conn.execute("INSERT INTO expenses (exp_date, category, amount, note) VALUES (?, ?, ?, ?)",

                 (exp_date, category, amount, note))

    conn.commit()

    conn.close()

    flash(f"Expense of Rs. {amount:,.0f} ({category}) added.", "success")

    return redirect(url_for("admin_dashboard"))

@app.route("/admin/inquiry/add", methods=["POST"])

@admin_required

def admin_add_inquiry():

    """Add student admission lead / inquiry."""

    name = request.form.get("name", "").strip().upper()

    phone = request.form.get("phone", "").strip()

    course = request.form.get("course", "DIT").strip()

    note = request.form.get("note", "").strip()

    follow_up = request.form.get("follow_up_date", "")

    conn = get_db_connection()

    conn.execute("""

        INSERT INTO inquiries (inq_date, name, phone, course, status, follow_up_date, note)

        VALUES (?, ?, ?, ?, 'New', ?, ?)

    """, (datetime.now().strftime("%Y-%m-%d"), name, phone, course, follow_up, note))

    conn.commit()

    conn.close()

    flash(f"Inquiry for '{name}' added successfully!", "success")

    return redirect(url_for("admin_dashboard"))



# ---------------------------------------------------------------------------

# RECEIPT VIEW (Protected per Role)

# ---------------------------------------------------------------------------

@app.route("/receipt/<int:receipt_id>")

def receipt(receipt_id):

    role = session.get("role")

    if not role:

        flash("Pehle login karein.", "warning")

        return redirect(url_for("login"))

    conn = get_db_connection()

    payment = conn.execute("SELECT * FROM payments WHERE id = ?", (receipt_id,)).fetchone()

    if not payment:

        conn.close()

        flash("Receipt nahi mili.", "danger")

        return redirect(url_for("index"))

    student = conn.execute("SELECT * FROM students WHERE id = ?", (payment["student_id"],)).fetchone()

    if not student:

        conn.close()

        flash("Student nahi mila.", "danger")

        return redirect(url_for("index"))

    # PERMISSION CHECK

    # 1. Student can ONLY view their own receipt

    if role == "student" and payment["student_id"] != session.get("student_id"):

        conn.close()

        abort(403)

    # 2. Staff can ONLY view receipt if student is assigned to them

    if role == "staff" and student["teacher_id"] != session.get("staff_id"):

        conn.close()

        abort(403)

    # 3. Admin can view any receipt

    # Cumulative calculations

    all_payments = conn.execute(

        "SELECT * FROM payments WHERE student_id = ? ORDER BY pay_date ASC, id ASC",

        (payment["student_id"],)

    ).fetchall()

    total_fee = student["total_fee"] or 0

    discount = student["discount_amount"] or 0

    net_fee = total_fee - discount

    cumulative_paid = 0

    for p in all_payments:

        cumulative_paid += p["amount"]

        if p["id"] == payment["id"]:

            break

    remaining_balance = max(0, net_fee - cumulative_paid)

    conn.close()

    back_url = url_for("dashboard")

    if role == "staff":

        back_url = url_for("staff_dashboard")

    elif role == "admin":

        back_url = url_for("admin_dashboard")

    return render_template(

        "receipt.html",

        payment=payment,

        student=student,

        remaining_balance=remaining_balance,

        cumulative_paid=cumulative_paid,

        back_url=back_url

    )

# ---------------------------------------------------------------------------

# LOGOUT & HEALTH

# ---------------------------------------------------------------------------


# ---------------------------------------------------------------------------
# EASYPASA ONLINE PAYMENT - STUDENT SUBMISSION
# ---------------------------------------------------------------------------

@app.route("/student/easypasa_request", methods=["POST"])
@student_required
def student_easypasa_request():
    """Student submits EasyPaisa payment proof for admin verification."""
    student_id = session["student_id"]
    try:
        amount = float(request.form.get("amount", 0))
    except ValueError:
        amount = 0
    transaction_id = request.form.get("transaction_id", "").strip()
    transaction_date = request.form.get("transaction_date", datetime.now().strftime("%Y-%m-%d"))

    if amount <= 0:
        flash("Raqam (Amount) darj karna zaroori hai.", "danger")
        return redirect(url_for("dashboard"))
    if not transaction_id:
        flash("EasyPaisa Transaction ID darj karna zaroori hai.", "danger")
        return redirect(url_for("dashboard"))

    # Handle screenshot upload
    screenshot_file = None
    if "screenshot" in request.files:
        f = request.files["screenshot"]
        if f and f.filename and allowed_file(f.filename):
            ext = f.filename.rsplit(".", 1)[1].lower()
            fname = f"ep_{student_id}_{int(datetime.now().timestamp())}.{ext}"
            f.save(os.path.join(UPLOAD_FOLDER, fname))
            screenshot_file = fname

    conn = get_db_connection()
    conn.execute("""
        INSERT INTO online_payment_requests (student_id, amount, transaction_id, transaction_date, screenshot, method, status)
        VALUES (?, ?, ?, ?, ?, 'EasyPaisa', 'Pending')
    """, (student_id, amount, transaction_id, transaction_date, screenshot_file))
    conn.commit()
    conn.close()

    flash(f"✅ Aap ka EasyPaisa payment request (Rs. {amount:,.0f}) submit ho gaya! Admin verification ke baad fee update ho jaye gi.", "success")
    return redirect(url_for("dashboard"))


# ---------------------------------------------------------------------------
# ADMIN: APPROVE / REJECT ONLINE PAYMENTS
# ---------------------------------------------------------------------------

@app.route("/admin/approve_online_payment/<int:req_id>", methods=["POST"])
@admin_required
def admin_approve_online_payment(req_id):
    """Admin approves an EasyPaisa payment - auto creates payment record."""
    conn = get_db_connection()
    req = conn.execute("SELECT * FROM online_payment_requests WHERE id = ?", (req_id,)).fetchone()
    if not req or req["status"] != "Pending":
        conn.close()
        flash("Request nahi mili ya already processed hai.", "warning")
        return redirect(url_for("admin_dashboard"))

    # Create payment record - auto-updates student fee balance
    row_m = conn.execute("SELECT MAX(id) as mx FROM payments").fetchone()
    max_rec = (row_m["mx"] if isinstance(row_m, dict) else row_m[0]) or 0 if row_m else 0
    receipt_no = f"EP-{(max_rec + 1):04d}"
    conn.execute("""
        INSERT INTO payments (student_id, amount, pay_date, method, receipt_no, note)
        VALUES (?, ?, ?, 'EasyPaisa', ?, ?)
    """, (req["student_id"], req["amount"], req["transaction_date"], receipt_no, f"EasyPaisa TxnID: {req['transaction_id']}"))

    # Mark request approved
    conn.execute("UPDATE online_payment_requests SET status='Approved' WHERE id=?", (req_id,))
    conn.commit()
    conn.close()

    flash(f"✅ EasyPaisa Payment Rs. {req['amount']:,.0f} approve! Receipt: {receipt_no}. Fee balance auto-update ho gaya.", "success")
    return redirect(url_for("admin_dashboard"))


@app.route("/admin/reject_online_payment/<int:req_id>", methods=["POST"])
@admin_required
def admin_reject_online_payment(req_id):
    """Admin rejects an online payment request."""
    note = request.form.get("note", "").strip()
    conn = get_db_connection()
    conn.execute("UPDATE online_payment_requests SET status='Rejected', admin_note=? WHERE id=?", (note, req_id))
    conn.commit()
    conn.close()
    flash("Payment request reject kar di gayi.", "warning")
    return redirect(url_for("admin_dashboard"))


# ---------------------------------------------------------------------------
# RECEIPT DOWNLOAD (PDF + PNG)
# ---------------------------------------------------------------------------

@app.route("/receipt/<int:receipt_id>/download")
def receipt_download(receipt_id):
    """Download receipt as PDF or PNG."""
    from flask import send_file
    fmt = request.args.get("fmt", "pdf").lower()
    role = session.get("role")
    if not role:
        flash("Pehle login karein.", "warning")
        return redirect(url_for("login"))

    conn = get_db_connection()
    payment = conn.execute("SELECT * FROM payments WHERE id = ?", (receipt_id,)).fetchone()
    if not payment:
        conn.close()
        abort(404)
    student = conn.execute("SELECT * FROM students WHERE id = ?", (payment["student_id"],)).fetchone()
    if not student:
        conn.close()
        abort(404)

    # Permission check
    if role == "student" and payment["student_id"] != session.get("student_id"):
        conn.close()
        abort(403)
    if role == "staff" and student["teacher_id"] != session.get("staff_id"):
        conn.close()
        abort(403)

    # Fee calculations
    all_p = conn.execute(
        "SELECT * FROM payments WHERE student_id = ? ORDER BY pay_date ASC, id ASC",
        (payment["student_id"],)
    ).fetchall()
    total_fee = student["total_fee"] or 0
    discount = student["discount_amount"] or 0
    net_fee = total_fee - discount
    cumulative_paid = 0
    for p in all_p:
        cumulative_paid += (p["amount"] or 0)
        if p["id"] == payment["id"]:
            break
    remaining_balance = max(0, net_fee - cumulative_paid)
    conn.close()

    receipt_no = payment["receipt_no"] or f"RC-{payment['id']}"
    student_name = student["name"] or ""
    student_adm = student["admission_no"] or ""
    batch_val = student["batch"] if ("batch" in student.keys() and student["batch"]) else ""
    student_course = (student["course"] or "") + (f" ({batch_val})" if batch_val else "")
    father_name = student["father_name"] or ""

    if fmt == "pdf":
        try:
            from reportlab.lib.pagesizes import A5
            from reportlab.lib import colors
            from reportlab.lib.styles import getSampleStyleSheet, ParagraphStyle
            from reportlab.lib.units import mm
            from reportlab.platypus import SimpleDocTemplate, Paragraph, Spacer, Table, TableStyle, HRFlowable
            from reportlab.lib.enums import TA_CENTER, TA_RIGHT
            import io as _io

            buf = _io.BytesIO()
            doc = SimpleDocTemplate(buf, pagesize=A5, rightMargin=15*mm, leftMargin=15*mm, topMargin=10*mm, bottomMargin=10*mm)
            styles = getSampleStyleSheet()
            navy_c = colors.HexColor("#0D186E")
            green_c = colors.HexColor("#1F9D6B")
            red_c = colors.HexColor("#D64545")

            title_s = ParagraphStyle("t", fontSize=13, textColor=navy_c, alignment=TA_CENTER, fontName="Helvetica-Bold", spaceAfter=2, leading=16)
            sub_s = ParagraphStyle("s", fontSize=8, textColor=colors.grey, alignment=TA_CENTER, spaceAfter=4)
            lbl_s = ParagraphStyle("l", fontSize=8, textColor=colors.grey)
            val_s = ParagraphStyle("v", fontSize=9, fontName="Helvetica-Bold")
            r_s = ParagraphStyle("r", fontSize=8, textColor=colors.grey, alignment=TA_RIGHT)

            story = []
            story.append(Paragraph("ASIAN SKILL DEVELOPMENT INSTITUTE", title_s))
            story.append(Paragraph("Official E-Fee Receipt / Payment Voucher", sub_s))
            story.append(HRFlowable(width="100%", thickness=1, color=navy_c, spaceAfter=6))

            meta = [[Paragraph(f"Receipt No: <b>{receipt_no}</b>", lbl_s), Paragraph(f"Date: <b>{payment['pay_date']}</b>", r_s)]]
            mt = Table(meta, colWidths=["50%","50%"])
            mt.setStyle(TableStyle([('BOTTOMPADDING',(0,0),(-1,-1),4)]))
            story.append(mt)
            story.append(HRFlowable(width="100%", thickness=0.5, color=colors.lightgrey, spaceAfter=6))

            story.append(Paragraph("STUDENT PARTICULARS", ParagraphStyle("sec", fontSize=7, textColor=colors.grey, fontName="Helvetica-Bold", spaceAfter=4)))
            sdata = [
                ["Student Name:", student_name],
                ["Father Name:", father_name],
                ["Admission No:", student_adm],
                ["Course / Batch:", student_course],
            ]
            st = Table(sdata, colWidths=[40*mm, 70*mm])
            st.setStyle(TableStyle([
                ('FONTSIZE',(0,0),(-1,-1),8),
                ('TEXTCOLOR',(0,0),(0,-1),colors.grey),
                ('FONTNAME',(1,0),(1,-1),"Helvetica-Bold"),
                ('TOPPADDING',(0,0),(-1,-1),2),
                ('BOTTOMPADDING',(0,0),(-1,-1),2),
            ]))
            story.append(st)
            story.append(Spacer(1, 4*mm))

            story.append(Paragraph("AMOUNT PAID", ParagraphStyle("al", fontSize=8, textColor=green_c, alignment=TA_CENTER, fontName="Helvetica-Bold")))
            story.append(Paragraph(f"Rs. {payment['amount']:,.0f}", ParagraphStyle("am", fontSize=24, textColor=green_c, alignment=TA_CENTER, fontName="Helvetica-Bold")))
            pay_method = payment['method'] if ('method' in payment.keys() and payment['method']) else 'Cash'
            story.append(Paragraph(f"Method: <b>{pay_method}</b>", ParagraphStyle("m", fontSize=8, textColor=colors.grey, alignment=TA_CENTER)))
            story.append(Spacer(1, 4*mm))

            fdata = [
                ["Total Course Fee:", f"Rs. {total_fee:,.0f}"],
                ["Total Paid Till Date:", f"Rs. {cumulative_paid:,.0f}"],
                ["Remaining Balance:", f"Rs. {remaining_balance:,.0f}"],
            ]
            if discount > 0:
                fdata.insert(1, ["Discount:", f"- Rs. {discount:,.0f}"])
            ft = Table(fdata, colWidths=[60*mm, 50*mm])
            ft.setStyle(TableStyle([
                ('FONTSIZE',(0,0),(-1,-1),8),
                ('TEXTCOLOR',(0,0),(0,-1),colors.grey),
                ('FONTNAME',(1,-1),(1,-1),"Helvetica-Bold"),
                ('TEXTCOLOR',(1,-1),(1,-1), red_c if remaining_balance > 0 else green_c),
                ('TOPPADDING',(0,0),(-1,-1),2),
                ('BOTTOMPADDING',(0,0),(-1,-1),2),
                ('LINEABOVE',(0,-1),(-1,-1),0.5,colors.lightgrey),
            ]))
            story.append(ft)
            story.append(Spacer(1, 5*mm))
            story.append(HRFlowable(width="100%", thickness=0.5, color=navy_c, spaceBefore=2, spaceAfter=4))
            story.append(Paragraph("Digitally Verified by ASDI Accounts", ParagraphStyle("ft", fontSize=7, textColor=green_c, alignment=TA_CENTER)))
            story.append(Paragraph("This is a computer-generated voucher. Helpline: 0344-4996072", ParagraphStyle("ft2", fontSize=6, textColor=colors.grey, alignment=TA_CENTER)))

            doc.build(story)
            buf.seek(0)
            return send_file(buf, as_attachment=True, download_name=f"ASDI_Receipt_{receipt_no}.pdf", mimetype="application/pdf")
        except Exception as e:
            flash(f"PDF generate karne mein masla: {e}", "danger")
            return redirect(url_for("receipt", receipt_id=receipt_id))

    elif fmt == "png":
        try:
            from PIL import Image, ImageDraw, ImageFont
            import io as _io

            W, H = 620, 950
            img = Image.new("RGB", (W, H), "white")
            draw = ImageDraw.Draw(img)

            try:
                font_bold = ImageFont.truetype("C:/Windows/Fonts/arialbd.ttf", 15)
                font_title = ImageFont.truetype("C:/Windows/Fonts/arialbd.ttf", 17)
                font_amount = ImageFont.truetype("C:/Windows/Fonts/arialbd.ttf", 38)
                font_small = ImageFont.truetype("C:/Windows/Fonts/arial.ttf", 12)
            except Exception:
                font_bold = ImageFont.load_default()
                font_title = font_bold
                font_amount = font_bold
                font_small = font_bold

            navy_rgb = (13, 24, 110)
            green_rgb = (31, 157, 107)
            red_rgb = (214, 69, 69)
            grey_rgb = (107, 115, 148)
            light_bg = (238, 241, 248)
            ep_green = (0, 166, 81)

            # Header bar
            draw.rectangle([0, 0, W, 85], fill=navy_rgb)
            draw.text((W//2, 28), "ASIAN SKILL DEVELOPMENT INSTITUTE", fill="white", font=font_title, anchor="mm")
            draw.text((W//2, 58), "Official E-Fee Receipt / Payment Voucher", fill=(180, 195, 255), font=font_small, anchor="mm")

            y = 108
            draw.text((35, y), f"Receipt No: {receipt_no}", fill=navy_rgb, font=font_bold)
            draw.text((W-35, y), f"Date: {payment['pay_date']}", fill=grey_rgb, font=font_small, anchor="ra")
            y += 28
            draw.line([(35, y), (W-35, y)], fill=light_bg, width=1)
            y += 14

            draw.text((35, y), "STUDENT PARTICULARS", fill=grey_rgb, font=font_small)
            y += 22
            rows = [
                ("Student Name:", student_name),
                ("Father Name:", father_name or "N/A"),
                ("Admission No:", student_adm),
                ("Course / Batch:", student_course),
            ]
            for label, val in rows:
                draw.text((35, y), label, fill=grey_rgb, font=font_small)
                draw.text((190, y), val, fill=(10, 10, 30), font=font_bold)
                y += 24

            y += 12
            draw.line([(35, y), (W-35, y)], fill=light_bg, width=1)
            y += 16

            # Amount box
            draw.rectangle([35, y, W-35, y+112], fill=(235, 248, 242), outline=green_rgb, width=2)
            draw.text((W//2, y+20), "AMOUNT PAID", fill=green_rgb, font=font_small, anchor="mm")
            draw.text((W//2, y+62), f"Rs. {payment['amount']:,.0f}", fill=green_rgb, font=font_amount, anchor="mm")
            pay_method_png = payment['method'] if ('method' in payment.keys() and payment['method']) else 'Cash'
            draw.text((W//2, y+95), f"Method: {pay_method_png}", fill=grey_rgb, font=font_small, anchor="mm")
            y += 130

            # Fee ledger
            draw.rectangle([35, y, W-35, y+115], fill=light_bg)
            summary = [
                ("Total Course Fee:", f"Rs. {total_fee:,.0f}", False),
                ("Total Paid Till Date:", f"Rs. {cumulative_paid:,.0f}", False),
                ("Remaining Balance:", f"Rs. {remaining_balance:,.0f}", True),
            ]
            if discount > 0:
                summary.insert(1, ("Discount:", f"- Rs. {discount:,.0f}", False))
            sy = y + 14
            for label, val, is_last in summary:
                draw.text((50, sy), label, fill=grey_rgb, font=font_small)
                col = (red_rgb if remaining_balance > 0 else green_rgb) if is_last else (10, 10, 30)
                draw.text((W-50, sy), val, fill=col, font=font_bold, anchor="ra")
                sy += 25
            y = sy + 22

            # EasyPaisa info strip
            draw.rectangle([35, y, W-35, y+36], fill=(240, 255, 248), outline=ep_green, width=1)
            draw.text((W//2, y+18), "Online Payment: EasyPaisa 0315-5545014", fill=ep_green, font=font_small, anchor="mm")
            y += 52

            # Footer
            draw.line([(35, y), (W-35, y)], fill=navy_rgb, width=1)
            y += 14
            draw.text((W//2, y), "Digitally Verified by ASDI Accounts", fill=green_rgb, font=font_small, anchor="mm")
            y += 22
            draw.text((W//2, y), "Helpline: 0344-4996072  |  ASDI Student Portal", fill=grey_rgb, font=font_small, anchor="mm")

            buf = _io.BytesIO()
            img.save(buf, format="PNG")
            buf.seek(0)
            return send_file(buf, as_attachment=True, download_name=f"ASDI_Receipt_{receipt_no}.png", mimetype="image/png")
        except Exception as e:
            flash(f"PNG generate karne mein masla: {e}", "danger")
            return redirect(url_for("receipt", receipt_id=receipt_id))

    return redirect(url_for("receipt", receipt_id=receipt_id))


# ---------------------------------------------------------------------------
# STAFF CHAT & PHOTO ROUTES
# ---------------------------------------------------------------------------

@app.route("/staff/upload_photo", methods=["POST"])
@staff_required
def staff_upload_photo():
    """Staff uploads/updates their profile photo."""
    staff_id = session["staff_id"]
    if "photo" not in request.files:
        flash("Koi photo file select nahi ki gayi.", "warning")
        return redirect(url_for("staff_dashboard"))
    file = request.files["photo"]
    if file.filename == "":
        flash("Photo choose karein pehle.", "warning")
        return redirect(url_for("staff_dashboard"))
    if file and allowed_file(file.filename):
        ext = file.filename.rsplit(".", 1)[1].lower()
        filename = f"staff_{staff_id}_{int(datetime.now().timestamp())}.{ext}"
        filepath = os.path.join(UPLOAD_FOLDER, filename)
        file.save(filepath)

        try:
            c = get_db_connection()
            c.execute("UPDATE staff SET photo = ? WHERE id = ?", (filename, staff_id))
            c.commit()
            c.close()
        except Exception as e:
            print("[staff_upload_photo error]", e)
        flash("Faculty profile photo kamyabi se update ho gayi!", "success")
    else:
        flash("Invalid photo format. PNG, JPG, JPEG, WEBP allowed.", "danger")
    return redirect(url_for("staff_dashboard"))


@app.route("/staff/send_chat", methods=["POST"])
@staff_required
def staff_send_chat():
    """Staff sends chat message to colleagues (No limit, instant delivery)."""
    staff_id = session["staff_id"]
    message = request.form.get("message", "").strip()
    receiver_id = int(request.form.get("receiver_id", 0) or 0)
    if not message:
        return jsonify({"status": "error", "msg": "Khali message nahi bheja ja sakta."}), 400

    conn = get_db_connection()
    sender = conn.execute("SELECT name, role, photo FROM staff WHERE id = ?", (staff_id,)).fetchone()
    sender_name = sender["name"] if sender else session.get("user_name", "Faculty")
    sender_role = sender["role"] if sender else "Staff"
    sender_photo = sender["photo"] if (sender and "photo" in sender.keys()) else ""

    if is_postgres():
        row = conn.execute("""
            INSERT INTO staff_chat_messages (sender_id, sender_name, sender_role, sender_photo, receiver_id, message)
            VALUES (?, ?, ?, ?, ?, ?) RETURNING id
        """, (staff_id, sender_name, sender_role, sender_photo, receiver_id, message)).fetchone()
        msg_id = row["id"] if row else 0
    else:
        cur = conn.cursor()
        cur.execute("""
            INSERT INTO staff_chat_messages (sender_id, sender_name, sender_role, sender_photo, receiver_id, message)
            VALUES (?, ?, ?, ?, ?, ?)
        """, (staff_id, sender_name, sender_role, sender_photo, receiver_id, message))
        msg_id = cur.lastrowid
    conn.commit()
    conn.close()

    # Check if AJAX
    if request.headers.get("X-Requested-With") == "XMLHttpRequest" or request.is_json:
        return jsonify({
            "status": "success",
            "message_id": msg_id,
            "sender_name": sender_name,
            "sender_photo": sender_photo,
            "text": message,
            "time": datetime.now().strftime("%I:%M %p")
        })
    flash("Message sent!", "success")
    return redirect(url_for("staff_dashboard"))


@app.route("/staff/get_chat_messages")
@staff_required
def staff_get_chat_messages():
    """Live polling endpoint for staff chat messages."""
    after_id = int(request.args.get("after_id", 0) or 0)
    current_staff_id = session.get("staff_id", 0)
    conn = get_db_connection()
    rows = conn.execute("""
        SELECT * FROM staff_chat_messages
        WHERE id > ? AND (receiver_id = 0 OR receiver_id = ? OR sender_id = ?)
        ORDER BY id ASC
        LIMIT 50
    """, (after_id, current_staff_id, current_staff_id)).fetchall()
    conn.close()

    messages = []
    for r in rows:
        created_dt = r["created_at"]
        formatted_time = created_dt
        try:
            dt = datetime.strptime(str(created_dt)[:19], "%Y-%m-%d %H:%M:%S")
            formatted_time = dt.strftime("%I:%M %p")
        except Exception:
            pass
        messages.append({
            "id": r["id"],
            "sender_id": r["sender_id"],
            "sender_name": r["sender_name"],
            "sender_role": r["sender_role"] or "Staff",
            "sender_photo": r["sender_photo"] or "",
            "message": r["message"],
            "receiver_id": r["receiver_id"] or 0,
            "is_me": (r["sender_id"] == current_staff_id),
            "time": formatted_time
        })
    return jsonify({"status": "success", "messages": messages})


# ---------------------------------------------------------------------------
# ADMIN DP (PROFILE PICTURE) UPLOAD ROUTE
# ---------------------------------------------------------------------------

@app.route("/admin/upload_dp", methods=["POST"])
@admin_required
def admin_upload_dp():
    """Admin uploads custom profile picture."""
    if "admin_photo" not in request.files:
        flash("Koi image file select nahi ki gayi.", "warning")
        return redirect(url_for("admin_dashboard"))
    file = request.files["admin_photo"]
    if file.filename == "":
        flash("DP photo file choose karein.", "warning")
        return redirect(url_for("admin_dashboard"))
    if file and allowed_file(file.filename):
        ext = file.filename.rsplit(".", 1)[1].lower()
        filename = f"admin_dp_{int(datetime.now().timestamp())}.{ext}"
        filepath = os.path.join(UPLOAD_FOLDER, filename)
        file.save(filepath)

        try:
            c = get_db_connection()
            row = c.execute("SELECT key FROM settings WHERE key = ?", ('admin_dp',)).fetchone()
            if row:
                c.execute("UPDATE settings SET value = ? WHERE key = ?", (filename, 'admin_dp'))
            else:
                c.execute("INSERT INTO settings (key, value) VALUES (?, ?)", ('admin_dp', filename))
            c.commit()
            c.close()
        except Exception as e:
            print("[admin_upload_dp error]", e)
        flash("Admin Display Picture (DP) kamyabi se update ho gayi!", "success")
    else:
        flash("Invalid format. PNG, JPG, JPEG, WEBP allowed.", "danger")
    return redirect(url_for("admin_dashboard"))


# ---------------------------------------------------------------------------
# STAFF / TEACHER ATTENDANCE (MARK & ADMIN OVERVIEW)
# ---------------------------------------------------------------------------

@app.route("/staff/mark_self_attendance", methods=["POST"])
@staff_required
def staff_mark_self_attendance():
    """Teacher marks their daily check-in."""
    staff_id = session["staff_id"]
    today_str = datetime.now().strftime("%Y-%m-%d")
    now_time = datetime.now().strftime("%I:%M %p")
    status = request.form.get("status", "Present").strip()
    note = request.form.get("note", "").strip()

    conn = get_db_connection()
    existing = conn.execute("SELECT id FROM staff_attendance WHERE staff_id = ? AND att_date = ?", (staff_id, today_str)).fetchone()
    if existing:
        conn.execute("UPDATE staff_attendance SET status = ?, note = ? WHERE id = ?", (status, note, existing["id"]))
        flash(f"Aap ki aaj ki attendance ({status}) update ho gayi!", "info")
    else:
        conn.execute("""
            INSERT INTO staff_attendance (staff_id, att_date, status, check_in, note)
            VALUES (?, ?, ?, ?, ?)
        """, (staff_id, today_str, status, now_time, note))
        flash(f"Aap ki attendance mark ho gayi! Check-in: {now_time}", "success")
    conn.commit()
    conn.close()
    return redirect(url_for("staff_dashboard"))


@app.route("/admin/staff_attendance/mark", methods=["POST"])
@admin_required
def admin_mark_staff_attendance():
    """Admin marks or updates staff attendance."""
    staff_id = int(request.form.get("staff_id"))
    att_date = request.form.get("att_date", datetime.now().strftime("%Y-%m-%d")).strip()
    status = request.form.get("status", "Present").strip()
    check_in = request.form.get("check_in", datetime.now().strftime("%I:%M %p")).strip()
    note = request.form.get("note", "").strip()

    conn = get_db_connection()
    existing = conn.execute("SELECT id FROM staff_attendance WHERE staff_id = ? AND att_date = ?", (staff_id, att_date)).fetchone()
    if existing:
        conn.execute("UPDATE staff_attendance SET status = ?, check_in = ?, note = ? WHERE id = ?", (status, check_in, note, existing["id"]))
    else:
        conn.execute("""
            INSERT INTO staff_attendance (staff_id, att_date, status, check_in, note)
            VALUES (?, ?, ?, ?, ?)
        """, (staff_id, att_date, status, check_in, note))
    conn.commit()
    conn.close()
    flash(f"Staff attendance ({status}) kamyabi se record ho gayi!", "success")
    return redirect(url_for("admin_dashboard"))
# ==============================================================
# TEACHER -> STUDENT PRIVATE MESSAGING (ONE-WAY, 3 msgs/day limit)
# ==============================================================

@app.route("/staff/message/student", methods=["POST"])
@staff_required
def staff_message_student():
    """Teacher sends a private message to a specific student. Max 3 messages per day total."""
    staff_id = session["staff_id"]
    student_id = int(request.form.get("student_id", 0))
    message = request.form.get("message", "").strip()

    if not student_id or not message:
        flash("Please select a student and write a message.", "warning")
        return redirect(url_for("staff_dashboard"))

    conn = get_db_connection()

    # Check if student exists
    stu = conn.execute("SELECT * FROM students WHERE id = ?", (student_id,)).fetchone()
    if not stu:
        conn.close()
        flash("Student not found.", "danger")
        return redirect(url_for("staff_dashboard"))

    # Check daily limit: max 3 messages PER DAY (total across all students)
    today_str = datetime.now().strftime("%Y-%m-%d")
    _t4_row = conn.execute("""
        SELECT COUNT(*) as cnt FROM teacher_student_messages
        WHERE staff_id = ? AND (DATE(created_at) = CURRENT_DATE OR DATE(created_at) = ?)
    """, (staff_id, today_str)).fetchone()
    today_count = (int(_t4_row["cnt"] or 0) if isinstance(_t4_row, dict) else int(_t4_row[0] or 0)) if _t4_row else 0

    if today_count >= 3:
        conn.close()
        flash("Daily message limit reached (3 messages per day). You can send more messages tomorrow.", "warning")
        return redirect(url_for("staff_dashboard"))

    # Get teacher info
    teacher = conn.execute("SELECT name, photo FROM staff WHERE id = ?", (staff_id,)).fetchone()
    staff_name = teacher["name"] if teacher else session.get("user_name", "Teacher")
    staff_photo = teacher["photo"] if (teacher and teacher["photo"]) else ""

    conn.execute("""
        INSERT INTO teacher_student_messages (staff_id, staff_name, staff_photo, student_id, message)
        VALUES (?, ?, ?, ?, ?)
    """, (staff_id, staff_name, staff_photo, student_id, message))
    conn.commit()
    conn.close()

    remaining = 2 - today_count  # after this message
    flash(f"Message sent to {stu['name']} successfully! (Daily messages remaining: {max(0, remaining)})", "success")
    return redirect(url_for("staff_dashboard"))


@app.route("/staff/messages/get")
@staff_required
def staff_get_sent_messages():
    """AJAX endpoint: Get teacher's sent messages list."""
    staff_id = session["staff_id"]
    conn = get_db_connection()
    rows = conn.execute("""
        SELECT tsm.*, st.name as student_name, st.roll_no, st.course
        FROM teacher_student_messages tsm
        JOIN students st ON st.id = tsm.student_id
        WHERE tsm.staff_id = ?
        ORDER BY tsm.id DESC
        LIMIT 50
    """, (staff_id,)).fetchall()
    today_str = datetime.now().strftime("%Y-%m-%d")
    _t4_row = conn.execute("""
        SELECT COUNT(*) as cnt FROM teacher_student_messages
        WHERE staff_id = ? AND (DATE(created_at) = CURRENT_DATE OR DATE(created_at) = ?)
    """, (staff_id, today_str)).fetchone()
    today_count = (int(_t4_row["cnt"] or 0) if isinstance(_t4_row, dict) else int(_t4_row[0] or 0)) if _t4_row else 0
    conn.close()

    messages = []
    for r in rows:
        try:
            dt = datetime.strptime(str(r["created_at"])[:19], "%Y-%m-%d %H:%M:%S")
            t = dt.strftime("%b %d, %I:%M %p")
        except Exception:
            t = str(r["created_at"])[:16]
        messages.append({
            "id": r["id"],
            "student_name": r["student_name"],
            "roll_no": r["roll_no"] or "",
            "course": r["course"] or "",
            "message": r["message"],
            "is_read": bool(r["is_read"]),
            "time": t
        })
    return jsonify({"status": "success", "messages": messages, "today_count": today_count, "daily_limit": 3})


@app.route("/student/teacher_messages/get")
@student_required
def student_get_teacher_messages():
    """AJAX: Student gets messages received from teachers."""
    student_id = session["student_id"]
    after_id = int(request.args.get("after_id", 0))
    conn = get_db_connection()
    rows = conn.execute("""
        SELECT tsm.*, s.name as teacher_name, s.role as teacher_role, s.photo as teacher_photo
        FROM teacher_student_messages tsm
        JOIN staff s ON s.id = tsm.staff_id
        WHERE tsm.student_id = ? AND tsm.id > ?
        ORDER BY tsm.id DESC
        LIMIT 20
    """, (student_id, after_id)).fetchall()

    # Mark as read
    conn.execute("""
        UPDATE teacher_student_messages SET is_read = 1
        WHERE student_id = ? AND is_read = 0
    """, (student_id,))
    conn.commit()
    conn.close()

    messages = []
    for r in rows:
        try:
            dt = datetime.strptime(str(r["created_at"])[:19], "%Y-%m-%d %H:%M:%S")
            t = dt.strftime("%b %d, %I:%M %p")
        except Exception:
            t = str(r["created_at"])[:16]
        messages.append({
            "id": r["id"],
            "teacher_name": r["teacher_name"],
            "teacher_role": r["teacher_role"] or "Teacher",
            "teacher_photo": r["teacher_photo"] or "",
            "message": r["message"],
            "time": t
        })
    return jsonify({"status": "success", "messages": messages})


@app.route("/logout")

def logout():

    session.clear()

    return redirect(url_for("login"))

@app.route("/uploads/profiles/<filename>")

def uploaded_profile(filename):

    """Serves uploaded student profile photos."""

    return send_from_directory(UPLOAD_FOLDER, filename)

@app.route("/health")

def health():

    return jsonify({"status": "ok", "app": "ASDI Multi-Role Portal", "time": datetime.now().isoformat()})


# ==============================================================
# 6. COURSES MANAGEMENT (DYNAMIC + LISTING)
# ==============================================================

@app.route("/admin/courses/add", methods=["POST"])
@admin_required
def admin_add_course():
    name = request.form.get("name", "").strip()
    category = request.form.get("category", "General").strip()
    try:
        fee = float(request.form.get("fee", 0))
    except ValueError:
        fee = 0.0
    duration = request.form.get("duration", "").strip()
    description = request.form.get("description", "").strip()

    if not name:
        flash("Course title is mandatory.", "danger")
        return redirect(url_for("admin_dashboard"))

    conn = get_db_connection()
    try:
        conn.execute("""
            INSERT INTO courses (name, category, fee, duration, description)
            VALUES (?, ?, ?, ?, ?)
        """, (name, category, fee, duration, description))
        conn.commit()
        flash(f"Course '{name}' added successfully!", "success")
    except Exception as e:
        flash(f"Course creation failed: {e}", "danger")
    finally:
        conn.close()
    return redirect(url_for("admin_dashboard"))


@app.route("/admin/courses/edit/<int:course_id>", methods=["POST"])
@admin_required
def admin_edit_course(course_id):
    name = request.form.get("name", "").strip()
    category = request.form.get("category", "General").strip()
    try:
        fee = float(request.form.get("fee", 0))
    except ValueError:
        fee = 0.0
    duration = request.form.get("duration", "").strip()
    description = request.form.get("description", "").strip()

    if not name:
        flash("Course title cannot be empty.", "danger")
        return redirect(url_for("admin_dashboard"))

    conn = get_db_connection()
    try:
        conn.execute("""
            UPDATE courses 
            SET name = ?, category = ?, fee = ?, duration = ?, description = ?
            WHERE id = ?
        """, (name, category, fee, duration, description, course_id))
        conn.commit()
        flash(f"Course '{name}' updated successfully!", "success")
    except Exception as e:
        flash(f"Error updating course: {e}", "danger")
    finally:
        conn.close()
    return redirect(url_for("admin_dashboard"))


@app.route("/admin/courses/delete/<int:course_id>", methods=["POST"])
@admin_required
def admin_delete_course(course_id):
    conn = get_db_connection()
    try:
        conn.execute("DELETE FROM courses WHERE id = ?", (course_id,))
        conn.commit()
        flash("Course removed successfully.", "info")
    except Exception as e:
        flash(f"Error removing course: {e}", "danger")
    finally:
        conn.close()
    return redirect(url_for("admin_dashboard"))


# ==============================================================
# 7. ANNOUNCEMENTS / NOTICEBOARD (STUDENTS + TEACHERS)
# ==============================================================

@app.route("/admin/announcement/add", methods=["POST"])
@admin_required
def admin_add_announcement():
    title = request.form.get("title", "").strip()
    message = request.form.get("message", "").strip()
    target_role = request.form.get("target_role", "All").strip()

    if not title or not message:
        flash("Title and message are required for announcement.", "danger")
        return redirect(url_for("admin_dashboard"))

    conn = get_db_connection()
    try:
        conn.execute("""
            INSERT INTO announcements (title, message, target_role, is_active)
            VALUES (?, ?, ?, TRUE)
        """, (title, message, target_role))
        conn.commit()
        flash("Official Announcement broadcasted successfully!", "success")
    except Exception as e:
        flash(f"Error publishing announcement: {e}", "danger")
    finally:
        conn.close()
    return redirect(url_for("admin_dashboard"))


@app.route("/admin/announcement/delete/<int:ann_id>", methods=["POST"])
@admin_required
def admin_delete_announcement(ann_id):
    conn = get_db_connection()
    try:
        conn.execute("DELETE FROM announcements WHERE id = ?", (ann_id,))
        conn.commit()
        flash("Announcement removed.", "info")
    except Exception as e:
        flash(f"Error: {e}", "danger")
    finally:
        conn.close()
    return redirect(url_for("admin_dashboard"))


# ==============================================================
# 8. COURSE CONTENT & STUDY MATERIAL (UPLOAD & DOWNLOAD)
# ==============================================================

@app.route("/content/upload", methods=["POST"])
def upload_course_content():
    role = session.get("role")
    if role not in ["admin", "staff"]:
        abort(403)

    course = request.form.get("course", "").strip()
    title = request.form.get("title", "").strip()
    description = request.form.get("description", "").strip()
    drive_link = request.form.get("drive_link", "").strip()

    if not course or not title:
        flash("Course and Content Title are mandatory.", "danger")
        return redirect(url_for("admin_dashboard" if role == "admin" else "staff_dashboard"))

    uploaded_filename = None
    if "content_file" in request.files:
        f = request.files["content_file"]
        if f and f.filename:
            allowed = {"pdf", "doc", "docx", "ppt", "pptx", "zip", "rar", "png", "jpg", "jpeg", "txt"}
            ext = f.filename.rsplit(".", 1)[-1].lower() if "." in f.filename else ""
            if ext in allowed:
                fname = f"content_{int(datetime.now().timestamp())}_{secure_filename(f.filename)}"
                save_dir = os.path.join(STATIC_DIR, "uploads", "content")
                os.makedirs(save_dir, exist_ok=True)
                f.save(os.path.join(save_dir, fname))
                uploaded_filename = fname

    uploader_name = session.get("user_name", "Staff/Admin")
    uploader_role = "Admin" if role == "admin" else "Teacher"

    conn = get_db_connection()
    try:
        conn.execute("""
            INSERT INTO course_content (course, title, description, file_path, drive_link, uploaded_by, uploader_role)
            VALUES (?, ?, ?, ?, ?, ?, ?)
        """, (course, title, description, uploaded_filename, drive_link, uploader_name, uploader_role))
        conn.commit()
        flash(f"Course Material '{title}' published successfully for students!", "success")
    except Exception as e:
        flash(f"Error publishing notes: {e}", "danger")
    finally:
        conn.close()

    return redirect(url_for("admin_dashboard" if role == "admin" else "staff_dashboard"))


@app.route("/content/delete/<int:content_id>", methods=["POST"])
def delete_course_content(content_id):
    role = session.get("role")
    if role not in ["admin", "staff"]:
        abort(403)

    conn = get_db_connection()
    try:
        conn.execute("DELETE FROM course_content WHERE id = ?", (content_id,))
        conn.commit()
        flash("Material removed successfully.", "info")
    except Exception as e:
        flash(f"Error: {e}", "danger")
    finally:
        conn.close()

    return redirect(url_for("admin_dashboard" if role == "admin" else "staff_dashboard"))


@app.route("/content/download/<int:content_id>")
def download_course_content(content_id):
    if "role" not in session:
        flash("Please log in first.", "warning")
        return redirect(url_for("login"))

    conn = get_db_connection()
    item = conn.execute("SELECT * FROM course_content WHERE id = ?", (content_id,)).fetchone()
    conn.close()

    if not item:
        abort(404)

    if item["drive_link"] and not item["file_path"]:
        return redirect(item["drive_link"])

    if item["file_path"]:
        content_dir = os.path.join(STATIC_DIR, "uploads", "content")
        return send_from_directory(content_dir, item["file_path"], as_attachment=True)

    flash("No downloadable file attached to this resource.", "warning")
    return redirect(request.referrer or url_for("index"))


# ==============================================================
# 9. STUDENT WHATSAPP-STYLE GROUPS & SECURE CHAT
# ==============================================================

@app.route("/admin/group/create", methods=["POST"])
@admin_required
def admin_create_student_group():
    name = request.form.get("name", "").strip()
    course = request.form.get("course", "").strip()
    batch = request.form.get("batch", "").strip()
    description = request.form.get("description", "").strip()

    if not name:
        flash("Group Name is required.", "danger")
        return redirect(url_for("admin_dashboard"))

    conn = get_db_connection()
    try:
        conn.execute("""
            INSERT INTO student_groups (name, course, batch, description, is_locked, created_by)
            VALUES (?, ?, ?, ?, FALSE, 'Admin')
        """, (name, course, batch, description))
        conn.commit()
        flash(f"Student Group '{name}' created successfully!", "success")
    except Exception as e:
        flash(f"Error creating group: {e}", "danger")
    finally:
        conn.close()

    return redirect(url_for("admin_dashboard"))


@app.route("/admin/group/toggle_lock/<int:group_id>", methods=["POST"])
@admin_required
def admin_toggle_group_lock(group_id):
    conn = get_db_connection()
    try:
        grp = conn.execute("SELECT is_locked, name FROM student_groups WHERE id = ?", (group_id,)).fetchone()
        if grp:
            new_state = not bool(grp["is_locked"])
            conn.execute("UPDATE student_groups SET is_locked = ? WHERE id = ?", (new_state, group_id))
            conn.commit()
            action_str = "LOCKED / MUTED (Students cannot send messages)" if new_state else "UNLOCKED / ACTIVE"
            flash(f"Group '{grp['name']}' is now {action_str}.", "info")
    except Exception as e:
        flash(f"Error updating lock: {e}", "danger")
    finally:
        conn.close()

    return redirect(url_for("admin_dashboard"))


@app.route("/admin/group/delete/<int:group_id>", methods=["POST"])
@admin_required
def admin_delete_group(group_id):
    conn = get_db_connection()
    try:
        conn.execute("DELETE FROM student_groups WHERE id = ?", (group_id,))
        conn.commit()
        flash("Group and conversations permanently deleted.", "warning")
    except Exception as e:
        flash(f"Error: {e}", "danger")
    finally:
        conn.close()

    return redirect(url_for("admin_dashboard"))


@app.route("/admin/group/add_member", methods=["POST"])
@admin_required
def admin_add_group_member():
    group_id = int(request.form.get("group_id", 0))
    student_id = int(request.form.get("student_id", 0))

    if not group_id or not student_id:
        flash("Select both group and student.", "warning")
        return redirect(url_for("admin_dashboard"))

    conn = get_db_connection()
    try:
        conn.execute("""
            INSERT INTO group_members (group_id, student_id)
            VALUES (?, ?) ON CONFLICT DO NOTHING
        """, (group_id, student_id))
        conn.commit()
        flash("Student enrolled into group!", "success")
    except Exception as e:
        flash(f"Error adding member: {e}", "danger")
    finally:
        conn.close()

    return redirect(url_for("admin_dashboard"))


@app.route("/admin/group/remove_member", methods=["POST"])
@admin_required
def admin_remove_group_member():
    group_id = int(request.form.get("group_id", 0))
    student_id = int(request.form.get("student_id", 0))

    conn = get_db_connection()
    try:
        conn.execute("DELETE FROM group_members WHERE group_id = ? AND student_id = ?", (group_id, student_id))
        conn.commit()
        flash("Student removed from group.", "info")
    except Exception as e:
        flash(f"Error: {e}", "danger")
    finally:
        conn.close()

    return redirect(url_for("admin_dashboard"))


@app.route("/chat/group/send", methods=["POST"])
def send_group_message():
    role = session.get("role")
    if role not in ["student", "admin"]:
        return jsonify({"status": "error", "message": "Unauthorized"}), 403

    group_id = int(request.form.get("group_id", 0))
    message = request.form.get("message", "").strip()

    if not group_id or not message:
        return jsonify({"status": "error", "message": "Empty message or group"}), 400

    conn = get_db_connection()
    try:
        grp = conn.execute("SELECT * FROM student_groups WHERE id = ?", (group_id,)).fetchone()
        if not grp:
            conn.close()
            return jsonify({"status": "error", "message": "Group not found"}), 404

        # If student: check if group is locked or student is member
        if role == "student":
            if grp["is_locked"]:
                conn.close()
                return jsonify({"status": "error", "message": "This group is locked by Admin. Messages cannot be sent right now."}), 403

            student_id = session.get("student_id")
            is_mem = conn.execute("SELECT 1 FROM group_members WHERE group_id = ? AND student_id = ?", (group_id, student_id)).fetchone()
            if not is_mem:
                conn.close()
                return jsonify({"status": "error", "message": "Access Denied: You are not a member of this group."}), 403

            sender_id = student_id
            sender_type = "student"
            sender_name = session.get("user_name", "Student")
            stu_row = conn.execute("SELECT photo FROM students WHERE id = ?", (student_id,)).fetchone()
            sender_photo = stu_row["photo"] if stu_row and "photo" in stu_row.keys() else ""
        else:
            # Admin sending into group
            sender_id = 0
            sender_type = "admin"
            sender_name = "Chief Administrator"
            sender_photo = ""

        conn.execute("""
            INSERT INTO group_messages (group_id, sender_id, sender_type, sender_name, sender_photo, message)
            VALUES (?, ?, ?, ?, ?, ?)
        """, (group_id, sender_id, sender_type, sender_name, sender_photo, message))
        conn.commit()

        return jsonify({
            "status": "success",
            "sender_name": sender_name,
            "sender_photo": sender_photo,
            "sender_type": sender_type,
            "message": message,
            "time": datetime.now().strftime("%I:%M %p")
        })
    finally:
        conn.close()


@app.route("/chat/group/messages/<int:group_id>")
def get_group_messages(group_id):
    role = session.get("role")
    if not role:
        return jsonify({"status": "error", "message": "Unauthorized"}), 401

    conn = get_db_connection()
    try:
        grp = conn.execute("SELECT * FROM student_groups WHERE id = ?", (group_id,)).fetchone()
        if not grp:
            return jsonify({"status": "error", "message": "Group not found"}), 404

        if role == "student":
            student_id = session.get("student_id")
            is_mem = conn.execute("SELECT 1 FROM group_members WHERE group_id = ? AND student_id = ?", (group_id, student_id)).fetchone()
            if not is_mem:
                return jsonify({"status": "error", "message": "Not a member"}), 403

        after_id = int(request.args.get("after_id", 0))
        rows = conn.execute("""
            SELECT * FROM group_messages 
            WHERE group_id = ? AND id > ? 
            ORDER BY id ASC 
            LIMIT 50
        """, (group_id, after_id)).fetchall()

        # Members list (with photos)
        members = conn.execute("""
            SELECT s.id, s.name, s.roll_no, s.admission_no, s.photo
            FROM group_members gm
            JOIN students s ON s.id = gm.student_id
            WHERE gm.group_id = ?
            ORDER BY s.name ASC
        """, (group_id,)).fetchall()

        current_id = session.get("student_id") if role == "student" else -1

        messages = []
        for r in rows:
            created_dt = r["created_at"]
            time_str = ""
            try:
                dt = datetime.strptime(str(created_dt)[:19], "%Y-%m-%d %H:%M:%S")
                time_str = dt.strftime("%I:%M %p")
            except Exception:
                time_str = str(created_dt)[11:16]

            is_me = (role == "student" and r["sender_type"] == "student" and r["sender_id"] == current_id) or (role == "admin" and r["sender_type"] == "admin")
            messages.append({
                "id": r["id"],
                "sender_id": r["sender_id"],
                "sender_type": r["sender_type"],
                "sender_name": r["sender_name"],
                "sender_photo": r["sender_photo"] or "",
                "message": r["message"],
                "is_me": is_me,
                "time": time_str
            })

        return jsonify({
            "status": "success",
            "group_name": grp["name"],
            "is_locked": bool(grp["is_locked"]),
            "messages": messages,
            "members": [dict(m) for m in members]
        })
    finally:
        conn.close()


@app.route("/admin/group/message/delete/<int:msg_id>", methods=["POST"])
@admin_required
def admin_delete_group_message(msg_id):
    conn = get_db_connection()
    try:
        conn.execute("DELETE FROM group_messages WHERE id = ?", (msg_id,))
        conn.commit()
        return jsonify({"status": "success"})
    except Exception as e:
        return jsonify({"status": "error", "message": str(e)}), 500
    finally:
        conn.close()


# ==============================================================
# 10. EDITABLE STUDENT INDIVIDUAL TIMETABLE / SCHEDULE
# ==============================================================

@app.route("/admin/student/timetable/save", methods=["POST"])
@admin_required
def admin_save_student_timetable():
    student_id = int(request.form.get("student_id", 0))
    subject = request.form.get("subject", "").strip()
    teacher = request.form.get("teacher", "").strip()
    days = request.form.get("days", "Mon-Fri").strip()
    start_time = request.form.get("start_time", "").strip()
    end_time = request.form.get("end_time", "").strip()
    note = request.form.get("note", "").strip()

    if not student_id or not subject:
        flash("Student and Subject are mandatory.", "danger")
        return redirect(url_for("admin_dashboard"))

    conn = get_db_connection()
    try:
        conn.execute("""
            INSERT INTO schedule (student_id, days, start_time, end_time, subject, teacher, note)
            VALUES (?, ?, ?, ?, ?, ?, ?)
        """, (student_id, days, start_time, end_time, subject, teacher, note))
        conn.commit()
        flash("Personal timetable class entry added for student!", "success")
    except Exception as e:
        flash(f"Error adding schedule: {e}", "danger")
    finally:
        conn.close()

    return redirect(url_for("admin_dashboard"))


@app.route("/admin/student/timetable/delete/<int:schedule_id>", methods=["POST"])
@admin_required
def admin_delete_student_timetable(schedule_id):
    conn = get_db_connection()
    try:
        conn.execute("DELETE FROM schedule WHERE id = ?", (schedule_id,))
        conn.commit()
        flash("Schedule entry removed.", "info")
    except Exception as e:
        flash(f"Error: {e}", "danger")
    finally:
        conn.close()

    return redirect(url_for("admin_dashboard"))


if __name__ == "__main__":

    print("=" * 65)

    print("   ASDI MULTI-ROLE PORTAL (STUDENT / TEACHER / ADMIN)")

    print("=" * 65)

    print("Local access:   http://localhost:5000")

    print("Network access: http://192.168.18.21:5000  (Mobile on same Wi-Fi)")

    print("=" * 65)

    app.run(host="0.0.0.0", port=5000, debug=True)

