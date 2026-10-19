import os
import sqlite3
from datetime import datetime
from functools import wraps
from flask import Flask, render_template, request, redirect, url_for, session, flash, jsonify, abort

import jinja2

BASE_DIR = os.path.dirname(os.path.abspath(__file__))

# Configure flexible template loader so it finds templates regardless of folder naming
template_candidates = [
    os.path.join(BASE_DIR, "templates"),
    os.path.join(BASE_DIR, "template"),
    os.path.join(BASE_DIR, "asdi_student_portal", "templates"),
    os.path.join(BASE_DIR, "asdi_student_portal", "template"),
    BASE_DIR,
]
valid_template_dirs = [d for d in template_candidates if os.path.isdir(d)]

app = Flask(
    __name__,
    template_folder=valid_template_dirs[0] if valid_template_dirs else "templates",
    static_folder=os.path.join(BASE_DIR, "static") if os.path.isdir(os.path.join(BASE_DIR, "static")) else "static"
)
if valid_template_dirs:
    app.jinja_loader = jinja2.ChoiceLoader([jinja2.FileSystemLoader(d) for d in valid_template_dirs])

app.secret_key = os.environ.get("SECRET_KEY", "asdi_portal_secret_key_2026_x92_multi_role")

# Flexible Database Path Resolver
def get_db_path():
    """Returns the most up-to-date database path available across environments."""
    candidates = [
        os.path.abspath(os.path.join(BASE_DIR, "..", "ASDI_App_Full", "asdi", "data", "asdi.db")),
        os.path.join(BASE_DIR, "data", "asdi.db"),
        os.path.join(BASE_DIR, "asdi_student_portal", "data", "asdi.db"),
        os.path.join(BASE_DIR, "asdi.db"),
        os.path.join(BASE_DIR, "data", "asdi.sqlite"),
        "data/asdi.db",
        "asdi.db"
    ]
    for p in candidates:
        if os.path.exists(p):
            return p
    return os.path.join(BASE_DIR, "data", "asdi.db")

def get_db_connection():
    db_path = get_db_path()
    conn = sqlite3.connect(db_path)
    conn.row_factory = sqlite3.Row
    return conn

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
            "phone": "0311-8386393",
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
    return {
        "inst_name": inst_name,
        "inst_phone": settings.get("email_sender", "0311-8386393"),
        "current_user_role": session.get("role"),
        "current_user_name": session.get("user_name"),
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

def sync_student_security(student_id, email, pin=None):
    """Updates email and pin across all database copies so data remains in sync."""
    paths = [
        os.path.abspath(os.path.join(BASE_DIR, "..", "ASDI_App_Full", "asdi", "data", "asdi.db")),
        os.path.join(BASE_DIR, "data", "asdi.db"),
        os.path.join(BASE_DIR, "asdi_student_portal", "data", "asdi.db")
    ]
    for p in paths:
        if os.path.exists(p):
            try:
                c = sqlite3.connect(p)
                cur = c.cursor()
                cols = [col[1] for col in cur.execute("PRAGMA table_info(students)").fetchall()]
                if "email" not in cols:
                    cur.execute("ALTER TABLE students ADD COLUMN email TEXT")
                if "pin" not in cols:
                    cur.execute("ALTER TABLE students ADD COLUMN pin TEXT")
                if pin is not None and str(pin).strip() != "":
                    cur.execute("UPDATE students SET email = ?, pin = ? WHERE id = ?", (email, str(pin).strip(), student_id))
                else:
                    cur.execute("UPDATE students SET email = ? WHERE id = ?", (email, student_id))
                c.commit()
                c.close()
            except Exception:
                pass

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
    error = None

    if request.method == "POST":
        login_type = request.form.get("login_type", "student")
        active_tab = login_type
        conn = get_db_connection()
        settings = get_settings()

        # -------------------------------------------------------------
        # 1. STUDENT LOGIN (Strict 2-Factor: Roll No + Email/Mobile/PIN)
        # -------------------------------------------------------------
        if login_type == "student":
            roll_or_adm = (request.form.get("roll_no") or request.form.get("identifier") or "").strip()
            auth_val = (request.form.get("student_auth") or request.form.get("email") or "").strip()
            form_roll = roll_or_adm

            cleaned_id = roll_or_adm.replace(" ", "").upper()
            cleaned_auth_phone = clean_phone(auth_val)
            cleaned_auth_email = auth_val.lower().strip()

            if not roll_or_adm:
                error = "Barah-e-karam apna Roll No ya Admission No darj karein."
            elif not auth_val:
                error = "Security Check: Kisi dusre ka Roll No daal kar koi record nahi dekh sakta. Roll No ke sath apna Email ya Mobile Number zaroor darj karein."
            else:
                students = conn.execute("SELECT * FROM students").fetchall()
                matched_student = None

                for s in students:
                    adm = str(s["admission_no"] or "").strip().upper()
                    roll = str(s["roll_no"] or "").strip().upper()

                    # Match Admission No or Roll No
                    if cleaned_id and (roll == cleaned_id or adm == cleaned_id or adm.endswith("-" + cleaned_id) or adm.endswith("/" + cleaned_id)):
                        matched_student = s
                        break

                if not matched_student:
                    error = f"Roll No ya Admission No '{roll_or_adm}' ka koi student record nahi mila."
                else:
                    # VERIFY credentials strictly against THIS matched student
                    s_email = str(matched_student["email"] or "").strip().lower()
                    s_g_email = str(matched_student["g_email"] or "").strip().lower()
                    s_phone = clean_phone(matched_student["phone"])
                    s_wa = clean_phone(matched_student["whatsapp"])
                    s_cnic = str(matched_student["cnic"] or "").replace("-", "").strip()
                    s_pin = str(matched_student["pin"] or "").strip()

                    auth_verified = False

                    # Check 1: Email matching
                    if "@" in cleaned_auth_email:
                        if s_email and cleaned_auth_email == s_email:
                            auth_verified = True
                        elif s_g_email and cleaned_auth_email == s_g_email:
                            auth_verified = True
                        elif not s_email and not s_g_email:
                            error = "Aap ka Email abhi register nahi hai. Pehli baar login ke liye apna Admission Form wala Mobile Number darj karein, ya neeche 'Register Email' se apna Email save karein."
                        else:
                            error = "Security Check Fail: Yeh Email is Roll Number ke registered record se match nahi karta."

                    # Check 2: PIN matching
                    elif s_pin and auth_val == s_pin:
                        auth_verified = True

                    # Check 3: Phone / WhatsApp / CNIC matching
                    elif cleaned_auth_phone and (
                        (s_phone and cleaned_auth_phone == s_phone) or
                        (s_wa and cleaned_auth_phone == s_wa) or
                        (s_cnic and cleaned_auth_phone == s_cnic)
                    ):
                        auth_verified = True
                    else:
                        if not error:
                            error = "Security Check Fail: Darj shuda Email ya Mobile Number is Roll Number ke record se match nahi karta! Sirf verified student hi login kar sakta hai."

                    if auth_verified:
                        session.clear()
                        session["role"] = "student"
                        session["student_id"] = matched_student["id"]
                        session["user_name"] = matched_student["name"]
                        conn.close()

                        # Advise student to set email if missing
                        if not s_email:
                            flash("Khush Aamdeed! Apne account ko mazeed mehfooz karne ke liye Profile tab mein ja kar apna Email zaroor save karein.", "info")

                        return redirect(url_for("dashboard"))

        # -------------------------------------------------------------
        # 2. TEACHER / STAFF LOGIN
        # -------------------------------------------------------------
        elif login_type == "staff":
            staff_input = request.form.get("staff_input", "").strip()
            cleaned_phone = clean_phone(staff_input)
            staff_name_input = staff_input.upper()

            if not staff_input:
                error = "Barah-e-karam apna Registered Mobile Number ya Naam darj karein."
            else:
                staff_members = conn.execute("SELECT * FROM staff").fetchall()
                matched_staff = None

                for st in staff_members:
                    st_phone = clean_phone(st["phone"])
                    st_wa = clean_phone(st["whatsapp"])
                    st_name = (st["name"] or "").strip().upper()

                    # Match phone
                    if cleaned_phone and (cleaned_phone == st_phone or cleaned_phone == st_wa):
                        matched_staff = st
                        break
                    # Match name
                    if staff_name_input and (staff_name_input in st_name or st_name in staff_name_input):
                        matched_staff = st
                        break

                if matched_staff:
                    session.clear()
                    session["role"] = "staff"
                    session["staff_id"] = matched_staff["id"]
                    session["user_name"] = matched_staff["name"]
                    session["staff_role"] = matched_staff["role"]
                    conn.close()
                    return redirect(url_for("staff_dashboard"))
                else:
                    error = "Staff / Teacher record nahi mila. Barah-e-karam apna registered number check karein."

        # -------------------------------------------------------------
        # 3. ADMIN LOGIN
        # -------------------------------------------------------------
        elif login_type == "admin":
            pin = request.form.get("admin_pin", "").strip()
            valid_pins = [
                str(settings.get("admin_pin", "1234")).strip(),
                str(settings.get("principal_pin", "9999")).strip(),
                str(settings.get("finance_pin", "2222")).strip(),
                str(settings.get("receptionist_pin", "1111")).strip()
            ]

            if not pin:
                error = "Barah-e-karam Admin PIN code darj karein."
            elif pin in valid_pins:
                session.clear()
                session["role"] = "admin"
                session["user_name"] = "ASDI Administrator"
                conn.close()
                return redirect(url_for("admin_dashboard"))
            else:
                error = "Ghalat Admin PIN code! Barah-e-karam sahi security PIN darj karein."

        conn.close()

    return render_template("login.html", error=error, active_tab=active_tab, form_roll=form_roll)


@app.route("/register_student_email", methods=["POST"])
def register_student_email():
    reg_roll = request.form.get("reg_roll_no", "").strip()
    reg_phone = request.form.get("reg_phone", "").strip()
    reg_email = request.form.get("reg_email", "").strip().lower()
    reg_pin = request.form.get("reg_pin", "").strip()

    cleaned_roll = reg_roll.replace(" ", "").upper()
    cleaned_input_phone = clean_phone(reg_phone)

    if not reg_roll or not reg_phone or not reg_email:
        flash("Barah-e-karam Roll No, Mobile No aur Email tamam fields darj karein.", "danger")
        return redirect(url_for("login", tab="student"))

    if "@" not in reg_email or "." not in reg_email:
        flash("Barah-e-karam durust Email address darj karein (e.g. name@gmail.com).", "danger")
        return redirect(url_for("login", tab="student"))

    conn = get_db_connection()
    students = conn.execute("SELECT * FROM students").fetchall()
    matched_student = None

    for s in students:
        adm = str(s["admission_no"] or "").strip().upper()
        roll = str(s["roll_no"] or "").strip().upper()
        if cleaned_roll and (roll == cleaned_roll or adm == cleaned_roll or adm.endswith("-" + cleaned_roll) or adm.endswith("/" + cleaned_roll)):
            matched_student = s
            break

    if not matched_student:
        conn.close()
        flash(f"Roll No / Admission No '{reg_roll}' ka koi student record nahi mila.", "danger")
        return redirect(url_for("login", tab="student"))

    # Security verification: Phone must match student's admission record
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
        flash("Security Check Fail: Darj shuda Mobile Number is Roll Number ke admission record se match nahi hua! Sirf wahi number darj karein jo admission ke waqt diya tha.", "danger")
        return redirect(url_for("login", tab="student"))

    # Verified! Save email and PIN
    sync_student_security(matched_student["id"], reg_email, reg_pin)
    flash(f"Shabash {matched_student['name']}! Aap ka Email ({reg_email}) kamyabi se link ho gaya hai. Ab aap apne Roll No aur Email se login karein.", "success")
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

    conn.close()

    return render_template(
        "dashboard.html",
        student=student,
        fee=fee_summary,
        payments=payments,
        attendance=attendance_summary,
        results=results,
        schedule=schedule_records
    )


@app.route("/student/security_update", methods=["POST"])
@student_required
def student_security_update():
    student_id = session["student_id"]
    email = request.form.get("email", "").strip().lower()
    pin = request.form.get("pin", "").strip()

    if not email or "@" not in email or "." not in email:
        flash("Barah-e-karam durust Email address darj karein.", "danger")
        return redirect(url_for("dashboard"))

    sync_student_security(student_id, email, pin)
    flash("Aap ka Security Email aur PIN kamyabi se update ho gaya! Agli baar aap is Email se login kar saken gay.", "success")
    return redirect(url_for("dashboard"))


# ---------------------------------------------------------------------------
# 2. TEACHER & STAFF PORTAL (Their students & payments received)
# ---------------------------------------------------------------------------

@app.route("/staff/dashboard")
@staff_required
def staff_dashboard():
    staff_id = session["staff_id"]
    conn = get_db_connection()

    staff = conn.execute("SELECT * FROM staff WHERE id = ?", (staff_id,)).fetchone()
    if not staff:
        session.clear()
        return redirect(url_for("login", tab="staff"))

    # Fetch students assigned to this teacher
    # Criteria: teacher_id matches this staff id OR if teacher has a specific subject/course
    students = conn.execute(
        "SELECT * FROM students WHERE teacher_id = ? ORDER BY name ASC",
        (staff_id,)
    ).fetchall()

    student_ids = [s["id"] for s in students]

    # Calculate fee collection for their students
    payments = []
    if student_ids:
        in_clause = ",".join("?" * len(student_ids))
        payments = conn.execute(
            f"""
            SELECT p.*, s.name as student_name, s.roll_no, s.admission_no, s.course
            FROM payments p 
            JOIN students s ON s.id = p.student_id 
            WHERE p.student_id IN ({in_clause}) 
            ORDER BY p.pay_date DESC, p.id DESC
            """,
            student_ids
        ).fetchall()

    # Metrics for Teacher's students
    total_students = len(students)
    total_course_fee = sum((s["total_fee"] or 0) - (s["discount_amount"] or 0) for s in students)
    total_fee_collected = sum(p["amount"] or 0 for p in payments)
    total_pending_balance = max(0, total_course_fee - total_fee_collected)

    share_pct = staff["share_pct"] or 0
    share_earning = round(total_fee_collected * (share_pct / 100.0), 2) if share_pct else 0

    # Attach individual paid/balance to each student for the teacher's student table
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

    conn.close()

    return render_template(
        "staff_dashboard.html",
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
        st_share_amt = round(st_paid * (st_share_pct / 100.0), 2) if st_share_pct else 0

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

    students_with_metrics = []
    for s in all_students:
        s_paid = student_payment_map.get(s["id"], 0)
        s_net = (s["total_fee"] or 0) - (s["discount_amount"] or 0)
        students_with_metrics.append({
            "student": s,
            "net_fee": s_net,
            "paid": s_paid,
            "balance": max(0, s_net - s_paid)
        })

    conn.close()

    return render_template(
        "admin_dashboard.html",
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
        staff_overview=staff_overview
    )


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

@app.route("/logout")
def logout():
    session.clear()
    return redirect(url_for("login"))

@app.route("/health")
def health():
    return jsonify({"status": "ok", "app": "ASDI Multi-Role Portal", "time": datetime.now().isoformat()})

if __name__ == "__main__":
    print("=" * 65)
    print("   ASDI MULTI-ROLE PORTAL (STUDENT / TEACHER / ADMIN)")
    print("=" * 65)
    print("Local access:   http://localhost:5000")
    print("Network access: http://192.168.18.21:5000  (Mobile on same Wi-Fi)")
    print("=" * 65)
    app.run(host="0.0.0.0", port=5000, debug=True)
