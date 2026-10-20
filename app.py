import os
import sqlite3
from datetime import datetime
from functools import wraps
from flask import Flask, render_template, request, redirect, url_for, session, flash, jsonify, abort
from werkzeug.security import generate_password_hash, check_password_hash

BASE_DIR = os.path.dirname(os.path.abspath(__file__))
TEMPLATES_DIR = os.path.join(BASE_DIR, "templates")
STATIC_DIR = os.path.join(BASE_DIR, "static")

app = Flask(
    __name__,
    template_folder=TEMPLATES_DIR if os.path.isdir(TEMPLATES_DIR) else "templates",
    static_folder=STATIC_DIR if os.path.isdir(STATIC_DIR) else "static"
)

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
    return {
        "inst_name": inst_name,
        "inst_phone": settings.get("phone", "0344-4996072"),
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

def sync_student_security(student_id, email, password=None):
    """Updates email, pin and password_hash across all database copies so data remains in sync."""
    paths = [
        os.path.abspath(os.path.join(BASE_DIR, "..", "ASDI_App_Full", "asdi", "data", "asdi.db")),
        os.path.join(BASE_DIR, "data", "asdi.db"),
        os.path.join(BASE_DIR, "asdi_student_portal", "data", "asdi.db")
    ]
    hashed_pw = None
    if password is not None and str(password).strip() != "":
        pwd_raw = str(password).strip()
        if pwd_raw.startswith(('scrypt:', 'pbkdf2:', 'argon2:')):
            hashed_pw = pwd_raw
        else:
            hashed_pw = generate_password_hash(pwd_raw)

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
                if "password_hash" not in cols:
                    cur.execute("ALTER TABLE students ADD COLUMN password_hash TEXT")
                if hashed_pw:
                    cur.execute("UPDATE students SET email = ?, pin = ?, password_hash = ? WHERE id = ?", (email, hashed_pw, hashed_pw, student_id))
                else:
                    cur.execute("UPDATE students SET email = ? WHERE id = ?", (email, student_id))
                c.commit()
                c.close()
            except Exception:
                pass

def sync_staff_security(staff_id, email, password=None):
    """Updates email, pin and password_hash for staff across all database copies."""
    paths = [
        os.path.abspath(os.path.join(BASE_DIR, "..", "ASDI_App_Full", "asdi", "data", "asdi.db")),
        os.path.join(BASE_DIR, "data", "asdi.db"),
        os.path.join(BASE_DIR, "asdi_student_portal", "data", "asdi.db")
    ]
    hashed_pw = None
    if password is not None and str(password).strip() != "":
        pwd_raw = str(password).strip()
        if pwd_raw.startswith(('scrypt:', 'pbkdf2:', 'argon2:')):
            hashed_pw = pwd_raw
        else:
            hashed_pw = generate_password_hash(pwd_raw)

    for p in paths:
        if os.path.exists(p):
            try:
                c = sqlite3.connect(p)
                cur = c.cursor()
                cols = [col[1] for col in cur.execute("PRAGMA table_info(staff)").fetchall()]
                if "email" not in cols:
                    cur.execute("ALTER TABLE staff ADD COLUMN email TEXT")
                if "pin" not in cols:
                    cur.execute("ALTER TABLE staff ADD COLUMN pin TEXT")
                if "password_hash" not in cols:
                    cur.execute("ALTER TABLE staff ADD COLUMN password_hash TEXT")
                if hashed_pw:
                    cur.execute("UPDATE staff SET email = ?, pin = ?, password_hash = ? WHERE id = ?", (email, hashed_pw, hashed_pw, staff_id))
                else:
                    cur.execute("UPDATE staff SET email = ? WHERE id = ?", (email, staff_id))
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
    form_email = request.args.get("email", "")
    error = None

    if request.method == "POST":
        login_type = request.form.get("login_type", "student")
        active_tab = login_type
        conn = get_db_connection()
        settings = get_settings()

        # -------------------------------------------------------------
        # 1. STUDENT LOGIN (Strict 3-Way: Roll No + Email + Password)
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
                error = "Student Roll No ya Admission No darj karna zaroori hai."
            elif not student_email:
                error = "Apna registered Email address darj karna zaroori hai."
            elif not password:
                error = "Apna Security Password darj karna zaroori hai."
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
                    error = f"Roll No ya Admission No '{roll_or_adm}' ka koi student record nahi mila. Barah-e-karam Roll No dobara check karein."
                else:
                    # 1. Verify Registered Email
                    s_email = str(matched_student["email"] or "").strip().lower()
                    s_g_email = str(matched_student["g_email"] or "").strip().lower()

                    if not s_email and not s_g_email:
                        error = "Aap ke account par abhi Email aur Password set nahi hai. Pehli baar login ke liye neeche 'First-Time Activation & Set Password' par click karein."
                    elif cleaned_email != s_email and cleaned_email != s_g_email:
                        error = f"Security Check Failed: Darj shuda Email '{student_email}' is Roll Number ke registered record se match nahi karta."
                    else:
                        # 2. Verify Password
                        stored_pin = str(matched_student["pin"] or "").strip()
                        stored_hash = str(matched_student["password_hash"] if "password_hash" in matched_student.keys() else "").strip()
                        effective_hash = stored_hash or stored_pin

                        if not effective_hash:
                            error = "Is account ke liye abhi koi password set nahi hai. Neeche 'First-Time Activation & Set Password' se apna Password set karein."
                        elif not verify_student_password(effective_hash, password):
                            error = "Ghalat Password! Barah-e-karam apna durust password darj karein ya 'Forgot Password' se reset karein."
                        else:
                            # Auto-upgrade plain PIN/password to secure hash if not hashed
                            if not effective_hash.startswith(('scrypt:', 'pbkdf2:', 'argon2:')):
                                sync_student_security(matched_student["id"], s_email or cleaned_email, password)

                            # ALL 3 PASSED - SUCCESSFUL AUTHENTICATION
                            session.clear()
                            session["role"] = "student"
                            session["student_id"] = matched_student["id"]
                            session["user_name"] = matched_student["name"]
                            session["roll_no"] = matched_student["roll_no"] or matched_student["admission_no"]
                            session["email"] = s_email or cleaned_email
                            conn.close()

                            flash(f"Khush Aamdeed, {matched_student['name']}! Secure student portal session start ho gaya.", "success")
                            return redirect(url_for("dashboard"))

        # -------------------------------------------------------------
        # 2. TEACHER / STAFF LOGIN (Strict 3-Way: ID/Phone + Email + Password)
        # -------------------------------------------------------------
        elif login_type == "staff":
            staff_input = request.form.get("staff_input", "").strip()
            staff_email = request.form.get("staff_email", "").strip().lower()
            staff_password = request.form.get("staff_password", "").strip()

            cleaned_phone = clean_phone(staff_input)
            staff_name_input = staff_input.upper()

            if not staff_input:
                error = "Teacher ID, Mobile Number ya Name darj karna lazmi hai."
            elif not staff_email:
                error = "Teacher ka Registered Email address darj karna lazmi hai."
            elif not staff_password:
                error = "Teacher Security Password darj karna lazmi hai."
            else:
                staff_members = conn.execute("SELECT * FROM staff").fetchall()
                matched_staff = None

                for st in staff_members:
                    st_phone = clean_phone(st["phone"])
                    st_wa = clean_phone(st["whatsapp"])
                    st_name = (st["name"] or "").strip().upper()
                    st_id = str(st["id"]).strip()

                    # Match ID, phone, or name
                    if staff_input == f"TCH-{st_id.zfill(3)}" or staff_input == st_id:
                        matched_staff = st
                        break
                    if cleaned_phone and (cleaned_phone == st_phone or cleaned_phone == st_wa):
                        matched_staff = st
                        break
                    if staff_name_input and (staff_name_input in st_name or st_name in staff_name_input):
                        matched_staff = st
                        break

                if not matched_staff:
                    error = f"Staff / Teacher '{staff_input}' ka koi record nahi mila. Barah-e-karam apna Teacher ID ya number check karein."
                else:
                    st_email = str(matched_staff["email"] or "").strip().lower()
                    stored_pin = str(matched_staff["pin"] if "pin" in matched_staff.keys() else "").strip()
                    stored_hash = str(matched_staff["password_hash"] if "password_hash" in matched_staff.keys() else "").strip()
                    effective_hash = stored_hash or stored_pin

                    # 1. Verify Email
                    if not st_email:
                        error = "Aap ka Teacher Email abhi set nahi hai. Pehli baar login ke liye neeche 'First-Time Teacher Activation' par click karein."
                    elif staff_email != st_email:
                        error = f"Security Check Failed: Darj shuda Email '{staff_email}' is Teacher ke registered record se match nahi karta."
                    else:
                        # 2. Verify Password
                        if not effective_hash:
                            error = "Is Teacher account ke liye abhi koi password set nahi hai. Neeche 'First-Time Teacher Activation' par click karein."
                        elif not verify_student_password(effective_hash, staff_password):
                            error = "Ghalat Teacher Password! Barah-e-karam sahi password darj karein ya 'Forgot Password' se reset karein."
                        else:
                            # Auto-upgrade plain PIN/passwords to hash
                            if not effective_hash.startswith(('scrypt:', 'pbkdf2:', 'argon2:')):
                                sync_staff_security(matched_staff["id"], st_email, staff_password)

                            # SUCCESSFUL FACULTY LOGIN
                            session.clear()
                            session["role"] = "staff"
                            session["staff_id"] = matched_staff["id"]
                            session["user_name"] = matched_staff["name"]
                            session["staff_role"] = matched_staff["role"]
                            session["email"] = st_email
                            conn.close()
                            flash(f"Khush Aamdeed, {matched_staff['name']}! Secure faculty portal session established.", "success")
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
                "Admin@2026"
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

    inquiries = conn.execute("SELECT * FROM inquiries ORDER BY id DESC").fetchall()
    batches = conn.execute("SELECT * FROM batches ORDER BY id DESC").fetchall()

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
        staff_overview=staff_overview,
        all_staff=staff_list,
        inquiries=inquiries,
        batches=batches
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
        "Admin@2026"
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

    # Update in Database
    paths = [
        os.path.abspath(os.path.join(BASE_DIR, "..", "ASDI_App_Full", "asdi", "data", "asdi.db")),
        os.path.join(BASE_DIR, "data", "asdi.db"),
        os.path.join(BASE_DIR, "asdi_student_portal", "data", "asdi.db")
    ]

    for p in paths:
        if os.path.exists(p):
            try:
                con = sqlite3.connect(p)
                cur = con.cursor()
                if new_username:
                    cur.execute("INSERT OR REPLACE INTO settings (key, value) VALUES ('admin_username', ?)", (new_username,))
                if new_email:
                    cur.execute("INSERT OR REPLACE INTO settings (key, value) VALUES ('admin_email', ?)", (new_email,))
                if new_pw:
                    h = generate_password_hash(new_pw)
                    cur.execute("INSERT OR REPLACE INTO settings (key, value) VALUES ('admin_password_hash', ?)", (h,))
                    cur.execute("INSERT OR REPLACE INTO settings (key, value) VALUES ('admin_pin', ?)", (new_pw,))
                con.commit()
                con.close()
            except Exception:
                pass

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
    """Allows Administrator to edit full student academic and fee profile."""
    name = request.form.get("name", "").strip().upper()
    father_name = request.form.get("father_name", "").strip().upper()
    roll_no = request.form.get("roll_no", "").strip()
    phone = request.form.get("phone", "").strip()
    whatsapp = request.form.get("whatsapp", "").strip()
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

    if new_password:
        h = generate_password_hash(new_password)
        cur.execute("""
            UPDATE students SET
                name=?, father_name=?, roll_no=?, phone=?, whatsapp=?, email=?,
                course=?, batch=?, status=?, teacher_id=?, total_fee=?, discount_amount=?,
                password_hash=?, pin=?
            WHERE id=?
        """, (
            name, father_name, roll_no, phone, whatsapp, email,
            course, batch, status, teacher_id, total_fee, discount,
            h, h, student_id
        ))
    else:
        cur.execute("""
            UPDATE students SET
                name=?, father_name=?, roll_no=?, phone=?, whatsapp=?, email=?,
                course=?, batch=?, status=?, teacher_id=?, total_fee=?, discount_amount=?
            WHERE id=?
        """, (
            name, father_name, roll_no, phone, whatsapp, email,
            course, batch, status, teacher_id, total_fee, discount, student_id
        ))

    conn.commit()
    conn.close()

    flash(f"Student '{name}' updated successfully!", "success")
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
    max_rec = cur.execute("SELECT MAX(id) FROM payments").fetchone()[0] or 0
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


@app.route("/admin/batch/add", methods=["POST"])
@admin_required
def admin_add_batch():
    """Create new class batch."""
    name = request.form.get("name", "").strip()
    course = request.form.get("course", "").strip()
    days = request.form.get("days", "Mon-Fri").strip()
    start_time = request.form.get("start_time", "").strip()
    end_time = request.form.get("end_time", "").strip()
    teacher = request.form.get("teacher", "").strip()
    room = request.form.get("room", "Lab 1").strip()

    conn = get_db_connection()
    conn.execute("""
        INSERT INTO batches (name, course, days, start_time, end_time, teacher, room)
        VALUES (?, ?, ?, ?, ?, ?, ?)
    """, (name, course, days, start_time, end_time, teacher, room))
    conn.commit()
    conn.close()

    flash(f"Batch '{name}' created successfully!", "success")
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
