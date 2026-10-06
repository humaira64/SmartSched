from flask import Flask, render_template, request, redirect, url_for, flash, session, jsonify
import mysql.connector
import pandas as pd
import os
import random
import bcrypt
from dotenv import load_dotenv
import smtplib
import secrets
from werkzeug.utils import secure_filename
from email.message import EmailMessage
from datetime import datetime, timedelta
from google.oauth2 import id_token
from google.auth.transport import requests as google_requests

load_dotenv()


app = Flask(__name__)
def flash_for(endpoint, message, category="success"):
    flash({
        "endpoint": endpoint,
        "message": message
    }, category)
app.secret_key = "smartsched-secret-key"
app.secret_key = "smartsched-secret-key"

# Profile image upload configuration
PROFILE_UPLOAD_FOLDER = os.path.join(
    app.root_path,
    "static",
    "uploads",
    "profile"
)

ALLOWED_IMAGE_EXTENSIONS = {
    "png",
    "jpg",
    "jpeg",
    "webp"
}

app.config["PROFILE_UPLOAD_FOLDER"] = PROFILE_UPLOAD_FOLDER

os.makedirs(
    PROFILE_UPLOAD_FOLDER,
    exist_ok=True
)

def allowed_image(filename):

    return (
        "." in filename
        and filename.rsplit(".", 1)[1].lower()
        in ALLOWED_IMAGE_EXTENSIONS
    )

# =====================================
# ADMIN OTP EMAIL CONFIGURATION
# =====================================

MAIL_USERNAME = os.getenv("MAIL_USERNAME")
MAIL_PASSWORD = os.getenv("MAIL_PASSWORD")

SMTP_SERVER = "smtp.gmail.com"
SMTP_PORT = 465

def send_admin_otp(admin_email, otp_code):
    try:
        message = EmailMessage()

        message["Subject"] = "SmartSched Admin Verification Code"
        message["From"] = MAIL_USERNAME
        message["To"] = admin_email

        message.set_content(f"""
Hello,

Your SmartSched administrator verification code is:

{otp_code}

This verification code will expire in 5 minutes.

If you did not attempt to log in to SmartSched, please ignore this email.

Regards,
SmartSched
Universiti Poly-Tech Malaysia
""")

        with smtplib.SMTP_SSL(SMTP_SERVER, SMTP_PORT) as server:
            server.login(MAIL_USERNAME, MAIL_PASSWORD)
            server.send_message(message)

        return True

    except Exception as e:
        print("Email sending error:", e)
        return False

# =====================================
# STUDENT
# =====================================
GOOGLE_CLIENT_ID = "279290701698-iebfmdop4c22302rm9n7dpc3nikmcpbf.apps.googleusercontent.com"

@app.before_request
def protect_admin_pages():

    if request.path.startswith("/admin/"):

        if session.get("role") != "admin":
            return redirect(url_for("login"))

    if request.path == "/admin-change-password":

        if session.get("role") != "admin":
            return redirect(url_for("admin_login"))


def log_admin_activity(
    module,
    action,
    description,
    record_id=None
):

    admin_id = session.get("admin_id")

    if not admin_id:
        return

    cursor = db.cursor()

    cursor.execute("""
        INSERT INTO admin_activity_logs
        (
            admin_id,
            module,
            action,
            description,
            record_id
        )
        VALUES (%s, %s, %s, %s, %s)
    """, (
        admin_id,
        module,
        action,
        description,
        record_id
    ))

    db.commit()

    cursor.close()

@app.after_request
def auto_log_admin_activity(response):

    # Only log successful admin actions
    if response.status_code not in [200, 201, 302]:
        return response

    # Only logged-in admins
    if session.get("role") != "admin":
        return response

    # Only POST requests
    if request.method != "POST":
        return response

    endpoint = request.endpoint or ""

    # Do not log authentication-related actions
    excluded_endpoints = {
        "admin_login",
        "admin_verify",
        "admin_change_password"
    }

    if endpoint in excluded_endpoints:
        return response

    admin_id = session.get("admin_id")

    if not admin_id:
        return response

    # ------------------------------------------
    # Determine module
    # ------------------------------------------

    endpoint_lower = endpoint.lower()

    if "subject" in endpoint_lower:
        module = "Subject"

    elif "lecturer" in endpoint_lower:
        module = "Lecturer"

    elif "classroom" in endpoint_lower:
        module = "Classroom"

    elif "programme" in endpoint_lower:
        module = "Programme"

    elif "session" in endpoint_lower:
        module = "Academic Session"

    elif "curriculum" in endpoint_lower:
        module = "Curriculum"

    elif "offering" in endpoint_lower:
        module = "Subject Offering"

    elif "timetable" in endpoint_lower:
        module = "Timetable"

    elif "generate" in endpoint_lower:
        module = "Timetable Generation"

    elif "admin" in endpoint_lower:
        module = "Admin Management"

    else:
        module = "Administration"

    # ------------------------------------------
    # Determine action
    # ------------------------------------------

    if any(word in endpoint_lower for word in [
        "delete",
        "remove"
    ]):

        action = "Deleted"

    elif any(word in endpoint_lower for word in [
        "add",
        "create"
    ]):

        action = "Added"

    elif any(word in endpoint_lower for word in [
        "edit",
        "update"
    ]):

        action = "Updated"

    elif any(word in endpoint_lower for word in [
        "generate"
    ]):

        action = "Generated"

    elif any(word in endpoint_lower for word in [
        "import",
        "upload"
    ]):

        action = "Imported"

    elif any(word in endpoint_lower for word in [
        "save",
        "assign"
    ]):

        action = "Updated"

    else:

        action = "Updated"

    # ------------------------------------------
    # Description
    # ------------------------------------------

    description_map = {

        "add_lecturer": "Added a new lecturer",
        "edit_lecturer": "Updated lecturer information",
        "delete_lecturer": "Deleted a lecturer",

        "add_classroom": "Added a new classroom",
        "edit_classroom": "Updated classroom information",
        "delete_classroom": "Deleted a classroom",

        "add_subject": "Added a new subject",
        "edit_subject": "Updated subject information",
        "delete_subject": "Deleted a subject",

        "add_programme": "Added a new programme",
        "edit_programme": "Updated programme information",
        "delete_programme": "Deleted a programme",

        "add_session": "Added a new academic session",
        "edit_session": "Updated academic session information",
        "delete_session": "Deleted an academic session",

        "import_curriculum": "Imported curriculum data",
        "save_timetable": "Saved timetable changes",
        "generate_timetable": "Generated timetable automatically",
    }

    description = description_map.get(
        endpoint,
        f"{action} {module.lower()} record"
    )

    cursor = None

    try:

        cursor = db.cursor()

        cursor.execute("""
            INSERT INTO admin_activity_logs
            (
                admin_id,
                module,
                action,
                description
            )
            VALUES (%s, %s, %s, %s)
        """, (
            admin_id,
            module,
            action,
            description
        ))

        db.commit()

    except Exception as e:

        print(
            "Activity log error:",
            e
        )

    finally:

        if cursor:
            cursor.close()

    return response

db = mysql.connector.connect(
    host=os.getenv("DB_HOST"),
    user=os.getenv("DB_USER"),
    password=os.getenv("DB_PASSWORD"),
    database=os.getenv("DB_NAME"),
    buffered=True
)

# ==========================
# SUBJECT COLOR PALETTE
# ==========================

SUBJECT_COLORS = [
    "#DCEEFF",
    "#E5F4E1",
    "#FFF0CC",
    "#EDE2FF",
    "#FFE1E1",
    "#DFF7F2",
    "#FBE5D6",
    "#E3E8FF",
    "#F0E6D6",
    "#E7F0D5",

    "#D9EAF7",
    "#E2F0D9",
    "#FFF2CC",
    "#E4DFEC",
    "#F4CCCC",
    "#D9EAD3",
    "#FCE5CD",
    "#D0E0E3",
    "#D9D2E9",
    "#EAD1DC",

    "#CFE2F3",
    "#D9EAD3",
    "#FCE8B2",
    "#D9D2E9",
    "#F4CCCC",
    "#CFE8E5",
    "#F9CB9C",
    "#C9DAF8",
    "#EADCF8",
    "#F4D7D7",

    "#D6EAF8",
    "#D5F5E3",
    "#FCF3CF",
    "#E8DAEF",
    "#FADBD8",
    "#D1F2EB",
    "#FAE5D3",
    "#D4E6F1",
    "#E8DAEF",
    "#F5D6E6",

    "#E1F0FF",
    "#E8F5E9",
    "#FFF5D6",
    "#F0E6FF",
    "#FFE8E8",
    "#E0F7F4",
    "#FBEBDD",
    "#E5EBFF",
    "#F2E8D5",
    "#EAF2D7"
]

def assign_missing_subject_colors():
    cursor = db.cursor(dictionary=True)

    # Get colours already used
    cursor.execute("""
        SELECT color
        FROM subjects
        WHERE color IS NOT NULL
    """)

    used_colors = {
        row["color"]
        for row in cursor.fetchall()
    }

    # Get subjects without colour
    cursor.execute("""
        SELECT id
        FROM subjects
        WHERE color IS NULL
        ORDER BY id
    """)

    subjects_without_color = cursor.fetchall()

    for subject in subjects_without_color:

        # Find first unused colour
        available_color = None

        for color in SUBJECT_COLORS:
            if color not in used_colors:
                available_color = color
                break

        # If all 50 colours are already used,
        # start reusing colours
        if available_color is None:
            available_color = SUBJECT_COLORS[
                len(used_colors) % len(SUBJECT_COLORS)
            ]

        cursor.execute("""
            UPDATE subjects
            SET color = %s
            WHERE id = %s
        """, (
            available_color,
            subject["id"]
        ))

        used_colors.add(available_color)

    db.commit()
    cursor.close()

assign_missing_subject_colors()

# ==========================
# AUTH
# ==========================

@app.route("/")
def login():
    return render_template("login.html")

@app.route("/admin-login", methods=["GET", "POST"])
def admin_login():

    if request.method == "GET":
        return render_template("admin_login.html")

    email = request.form.get("email", "").strip().lower()
    password = request.form.get("password", "")

    if not email or not password:
        return render_template(
            "admin_login.html",
            error="Please enter your email and password."
        )

    cursor = db.cursor(dictionary=True)

    cursor.execute("""
        SELECT *
        FROM admin_users
        WHERE email = %s
          AND role = 'admin'
          AND is_active = 1
        LIMIT 1
    """, (email,))

    admin = cursor.fetchone()
    cursor.close()

    # =====================================
    # CHECK ADMIN ACCOUNT
    # =====================================

    if not admin:
        return render_template(
            "admin_login.html",
            error="Invalid email or password."
        )

    # =====================================
    # CHECK PASSWORD
    # =====================================

    if not bcrypt.checkpw(
        password.encode("utf-8"),
        admin["password_hash"].encode("utf-8")
    ):
        return render_template(
            "admin_login.html",
            error="Invalid email or password."
        )

    # =====================================
    # GENERATE OTP
    # =====================================

    otp_code = f"{secrets.randbelow(1000000):06d}"

    expires_at = datetime.now() + timedelta(minutes=5)

    cursor = db.cursor()

    # Remove previous OTPs for this admin

    cursor.execute("""
        DELETE FROM admin_otp
        WHERE admin_id = %s
    """, (admin["id"],))

    # Insert new OTP

    cursor.execute("""
        INSERT INTO admin_otp
        (
            admin_id,
            otp_code,
            expires_at
        )
        VALUES (%s, %s, %s)
    """, (
        admin["id"],
        otp_code,
        expires_at
    ))

    db.commit()
    cursor.close()

    # =====================================
    # SEND OTP EMAIL
    # =====================================

    email_sent = send_admin_otp(
        admin["email"],
        otp_code
    )

    if not email_sent:

        # Remove OTP if email failed

        cursor = db.cursor()

        cursor.execute("""
            DELETE FROM admin_otp
            WHERE admin_id = %s
        """, (admin["id"],))

        db.commit()
        cursor.close()

        return render_template(
            "admin_login.html",
            error="Unable to send verification email. Please try again."
        )

    # =====================================
    # TEMPORARY SESSION
    # =====================================

    session["pending_admin_id"] = admin["id"]
    session["pending_admin_email"] = admin["email"]

    return redirect(url_for("admin_verify"))

@app.route("/admin-verify", methods=["GET", "POST"])
def admin_verify():

    pending_admin_id = session.get("pending_admin_id")

    if not pending_admin_id:
        return redirect(url_for("admin_login"))

    if request.method == "GET":

        email = session.get("pending_admin_email")

        return render_template(
            "admin_verify.html",
            email=email
        )

    otp = request.form.get("otp", "").strip()

    if not otp:
        return render_template(
            "admin_verify.html",
            email=session.get("pending_admin_email"),
            error="Please enter the verification code."
        )

    cursor = db.cursor(dictionary=True)

    cursor.execute("""
        SELECT *
        FROM admin_otp
        WHERE admin_id = %s
          AND otp_code = %s
        ORDER BY id DESC
        LIMIT 1
    """, (
        pending_admin_id,
        otp
    ))

    otp_record = cursor.fetchone()

    if not otp_record:
        cursor.close()

        return render_template(
            "admin_verify.html",
            email=session.get("pending_admin_email"),
            error="Invalid verification code."
        )

    # =====================================
    # CHECK EXPIRATION
    # =====================================

    if datetime.now() > otp_record["expires_at"]:

        cursor.close()

        return render_template(
            "admin_verify.html",
            email=session.get("pending_admin_email"),
            error="Verification code has expired. Please login again."
        )

    # =====================================
    # OTP SUCCESS
    # =====================================

    cursor.execute("""
        DELETE FROM admin_otp
        WHERE admin_id = %s
    """, (pending_admin_id,))

    db.commit()

    # Get admin information

    cursor.execute("""
        SELECT *
        FROM admin_users
        WHERE id = %s
          AND role = 'admin'
          AND is_active = 1
        LIMIT 1
    """, (pending_admin_id,))

    admin = cursor.fetchone()

    cursor.close()

    if not admin:

        session.clear()

        return redirect(url_for("admin_login"))

    # =====================================
    # CREATE VERIFIED ADMIN SESSION
    # =====================================

    session.pop("pending_admin_id", None)
    session.pop("pending_admin_email", None)

    session["admin_id"] = admin["id"]
    session["admin_email"] = admin["email"]
    session["role"] = "admin"

    # =====================================
    # FIRST LOGIN
    # =====================================

    if admin["must_change_password"] == 1:

        return redirect(
            url_for("admin_change_password")
        )

    # =====================================
    # NORMAL LOGIN
    # =====================================

    return redirect("/admin/dashboard")

@app.route("/admin-change-password", methods=["GET", "POST"])
def admin_change_password():

    if session.get("role") != "admin":
        return redirect(url_for("admin_login"))

    admin_id = session.get("admin_id")

    if not admin_id:
        return redirect(url_for("admin_login"))

    if request.method == "GET":
        return render_template("admin_change_password.html")

    new_password = request.form.get("new_password", "")
    confirm_password = request.form.get("confirm_password", "")

    # =====================================
    # VALIDATION
    # =====================================

    if not new_password or not confirm_password:

        return render_template(
            "admin_change_password.html",
            error="Please fill in all fields."
        )

    if new_password != confirm_password:

        return render_template(
            "admin_change_password.html",
            error="Passwords do not match."
        )

    if len(new_password) < 8:

        return render_template(
            "admin_change_password.html",
            error="Password must contain at least 8 characters."
        )

    # Prevent keeping default password

    if new_password == "1234":

        return render_template(
            "admin_change_password.html",
            error="Please choose a new password."
        )

    # =====================================
    # HASH PASSWORD
    # =====================================

    password_hash = bcrypt.hashpw(
        new_password.encode("utf-8"),
        bcrypt.gensalt()
    ).decode("utf-8")

    cursor = db.cursor()

    cursor.execute("""
        UPDATE admin_users
        SET password_hash = %s,
            must_change_password = 0
        WHERE id = %s
          AND role = 'admin'
    """, (
        password_hash,
        admin_id
    ))

    db.commit()
    cursor.close()

    flash(
        "Your password has been changed successfully.",
        "success"
    )

    return redirect("/admin/dashboard")

@app.route("/student-login")
def student_login():
    return render_template("student_login.html", google_client_id=GOOGLE_CLIENT_ID)

@app.route("/student-login/google", methods=["POST"])
def google_login():

    try:
        data = request.get_json()

        if not data or "credential" not in data:
            return {
                "success": False,
                "message": "Google credential is missing."
            }, 400

        credential = data["credential"]

        # Verify Google ID token
        google_user = id_token.verify_oauth2_token(
            credential,
            google_requests.Request(),
            GOOGLE_CLIENT_ID
        )

        email = google_user.get("email")
        email_verified = google_user.get("email_verified")
        google_sub = google_user.get("sub")
        full_name = google_user.get("name")

        # Check email verification
        if not email_verified:
            return {
                "success": False,
                "message": "Your Google email is not verified."
            }, 403

        # Only UPTM student email allowed
        if not email or not email.lower().endswith("@student.uptm.edu.my"):
            return {
                "success": False,
                "message": "Only UPTM student accounts are allowed."
            }, 403

        cursor = db.cursor(dictionary=True)

        # Check whether student already exists
        cursor.execute("""
            SELECT *
            FROM students
            WHERE google_sub = %s
               OR email = %s
            LIMIT 1
        """, (google_sub, email))

        student = cursor.fetchone()

        if student:

            # Existing student
            session["student_id"] = student["id"]
            session["student_email"] = student["email"]
            session["student_name"] = student["full_name"]
            session["role"] = "student"

            cursor.close()

            # Profile not completed yet
            if student["faculty_id"] is None or student["current_semester"] is None:

                return {
                    "success": True,
                    "redirect": url_for("complete_student_profile")
                }

            # Profile already completed
            return {
                "success": True,
                "redirect": url_for("dashboard")
            }

        # First-time student
        cursor.execute("""
            INSERT INTO students
            (google_sub, email, full_name)
            VALUES (%s, %s, %s)
        """, (google_sub, email, full_name))

        db.commit()

        student_id = cursor.lastrowid
        cursor.close()

        session["student_id"] = student_id
        session["student_email"] = email
        session["student_name"] = full_name
        session["role"] = "student"

        return {
            "success": True,
            "redirect": url_for("complete_student_profile")
        }

    except Exception as e:

        print("Google login error:", e)

        return {
            "success": False,
            "message": "Google login failed. Please try again."
        }, 500

@app.route("/complete-student-profile", methods=["GET", "POST"])
def complete_student_profile():

    # Make sure student is logged in
    if session.get("role") != "student":
        return redirect(url_for("student_login"))

    student_id = session.get("student_id")

    cursor = db.cursor(dictionary=True)

    # --------------------------------------------------
    # GET AVAILABLE FACULTIES
    # --------------------------------------------------

    cursor.execute("""
        SELECT
            id,
            faculty_code,
            faculty_name
        FROM faculties
        ORDER BY faculty_code
    """)

    faculties = cursor.fetchall()

    # --------------------------------------------------
    # SAVE PROFILE
    # --------------------------------------------------

    if request.method == "POST":

        faculty_id = request.form.get("faculty_id")
        current_semester = request.form.get("current_semester")

        # Check required fields
        if not faculty_id or not current_semester:

            cursor.close()

            return render_template(
                "complete_student_profile.html",
                faculties=faculties,
                error="Please select your faculty and current semester."
            )

        # --------------------------------------------------
        # UPDATE STUDENT PROFILE
        # --------------------------------------------------

        cursor.execute("""
            UPDATE students

            SET faculty_id = %s,
                current_semester = %s

            WHERE id = %s
        """, (
            faculty_id,
            current_semester,
            student_id
        ))

        db.commit()

        cursor.close()

        return redirect(url_for("dashboard"))

    # --------------------------------------------------
    # DISPLAY PROFILE PAGE
    # --------------------------------------------------

    cursor.close()

    return render_template(
        "complete_student_profile.html",
        faculties=faculties
    )

@app.route("/logout")
def logout():

    session.clear()

    return redirect(url_for("login"))

# ==========================
# STUDENT
# ==========================

@app.route("/dashboard")
def dashboard():

    # Make sure student is logged in
    if session.get("role") != "student":
        return redirect(url_for("student_login"))

    student_id = session.get("student_id")

    cursor = db.cursor(dictionary=True)

    # Get logged-in student's academic information
    cursor.execute("""
        SELECT
            s.id,
            s.full_name,
            s.email,
            s.faculty_id,
            s.current_semester,

            f.faculty_code,
            f.faculty_name

        FROM students s

        LEFT JOIN faculties f
            ON s.faculty_id = f.id

        WHERE s.id = %s

        LIMIT 1
    """, (student_id,))

    student = cursor.fetchone()

    # Student record not found
    if not student:
        cursor.close()
        session.clear()
        return redirect(url_for("student_login"))

    # Get the active academic session
    cursor.execute("""
        SELECT session_code, session_type
        FROM academic_sessions
        WHERE is_active = 1
        ORDER BY id DESC
        LIMIT 1
    """)

    academic_session = cursor.fetchone()

    cursor.close()

    return render_template(
        "student_dashboard.html",
        student=student,
        academic_session=academic_session
    )

@app.route("/profile")
def profile():

    # Student login protection
    if session.get("role") != "student":
        return redirect(url_for("student_login"))

    student_id = session.get("student_id")

    cursor = db.cursor(dictionary=True)

    cursor.execute("""
        SELECT
            s.id,
            s.full_name,
            s.email,
            s.current_semester,
            s.profile_image,

            f.faculty_code,
            f.faculty_name

        FROM students s

        LEFT JOIN faculties f
            ON s.faculty_id = f.id

        WHERE s.id = %s

        LIMIT 1
    """, (student_id,))

    student = cursor.fetchone()

    cursor.close()

    if not student:
        session.clear()
        return redirect(url_for("student_login"))

    return render_template(
        "profile.html",
        student=student
    )

@app.route("/profile/upload-image", methods=["POST"])
def upload_profile_image():

    if session.get("role") != "student":
        return redirect(url_for("student_login"))

    student_id = session.get("student_id")

    image = request.files.get("profile_image")

    if not image or image.filename == "":
        flash("Please select an image.", "danger")
        return redirect(url_for("profile"))

    if not allowed_image(image.filename):
        flash(
            "Only JPG, JPEG, PNG and WEBP images are allowed.",
            "danger"
        )
        return redirect(url_for("profile"))

    cursor = db.cursor(dictionary=True)

    # Get current image
    cursor.execute("""
        SELECT profile_image
        FROM students
        WHERE id = %s
        LIMIT 1
    """, (student_id,))

    student = cursor.fetchone()

    # Create unique filename
    original_name = secure_filename(image.filename)

    extension = original_name.rsplit(".", 1)[1].lower()

    filename = f"student_{student_id}.{extension}"

    filepath = os.path.join(
        app.config["PROFILE_UPLOAD_FOLDER"],
        filename
    )

    # Delete old image if it exists
    if student and student["profile_image"]:

        old_path = os.path.join(
            app.config["PROFILE_UPLOAD_FOLDER"],
            student["profile_image"]
        )

        if os.path.exists(old_path):
            os.remove(old_path)

    # Save new image
    image.save(filepath)

    # Save filename in database
    cursor.execute("""
        UPDATE students
        SET profile_image = %s
        WHERE id = %s
    """, (
        filename,
        student_id
    ))

    db.commit()

    cursor.close()

    flash(
        "Profile picture updated successfully.",
        "success"
    )

    return redirect(url_for("profile"))

@app.route("/profile/delete-image", methods=["POST"])
def delete_profile_image():

    if session.get("role") != "student":
        return redirect(url_for("student_login"))

    student_id = session.get("student_id")

    cursor = db.cursor(dictionary=True)

    cursor.execute("""
        SELECT profile_image
        FROM students
        WHERE id = %s
        LIMIT 1
    """, (student_id,))

    student = cursor.fetchone()

    if student and student["profile_image"]:

        filepath = os.path.join(
            app.config["PROFILE_UPLOAD_FOLDER"],
            student["profile_image"]
        )

        if os.path.exists(filepath):
            os.remove(filepath)

        cursor.execute("""
            UPDATE students
            SET profile_image = NULL
            WHERE id = %s
        """, (student_id,))

        db.commit()

    cursor.close()

    flash(
        "Profile picture deleted successfully.",
        "success"
    )

    return redirect(url_for("profile"))

@app.route("/profile/update-semester", methods=["POST"])
def update_profile_semester():

    if session.get("role") != "student":
        return redirect(url_for("student_login"))

    student_id = session.get("student_id")

    semester = request.form.get("current_semester")

    if not semester:
        flash(
            "Please select a semester.",
            "danger"
        )

        return redirect(url_for("profile"))

    try:

        semester = int(semester)

    except ValueError:

        flash(
            "Invalid semester.",
            "danger"
        )

        return redirect(url_for("profile"))

    if semester < 1 or semester > 8:

        flash(
            "Invalid semester.",
            "danger"
        )

        return redirect(url_for("profile"))

    cursor = db.cursor()

    cursor.execute("""
        UPDATE students
        SET current_semester = %s
        WHERE id = %s
    """, (
        semester,
        student_id
    ))

    db.commit()

    cursor.close()

    flash(
        "Semester updated successfully.",
        "success"
    )

    return redirect(url_for("profile"))

@app.route("/find-subjects")
def find_subjects():

    # --------------------------------------------------
    # STUDENT LOGIN PROTECTION
    # --------------------------------------------------

    if session.get("role") != "student":
        return redirect(url_for("student_login"))

    student_id = session.get("student_id")

    cursor = db.cursor(dictionary=True)


    # --------------------------------------------------
    # GET STUDENT INFORMATION
    # --------------------------------------------------

    cursor.execute("""
        SELECT
            s.id,
            s.full_name,
            s.email,
            s.faculty_id,
            s.programme_id,
            s.current_semester,

            f.faculty_code,
            f.faculty_name

        FROM students s

        LEFT JOIN faculties f
            ON s.faculty_id = f.id

        WHERE s.id = %s

        LIMIT 1
    """, (student_id,))

    student = cursor.fetchone()


    # --------------------------------------------------
    # STUDENT NOT FOUND
    # --------------------------------------------------

    if not student:

        cursor.close()

        session.clear()

        return redirect(url_for("student_login"))


    # --------------------------------------------------
    # GET PROGRAMMES BELONGING TO STUDENT'S FACULTY
    # --------------------------------------------------

    faculty_programmes = []

    # --------------------------------------------------
    # GET FCOM PROGRAMMES
    # --------------------------------------------------

    cursor.execute("""
        SELECT
            id,
            programme_code,
            programme_name

        FROM programmes

        WHERE faculty_id = (
            SELECT id
            FROM faculties
            WHERE faculty_code = 'FCOM'
            LIMIT 1
        )

        AND is_active = 1

        ORDER BY programme_name
    """)

    faculty_programmes = cursor.fetchall()


    # --------------------------------------------------
    # GET SELECTED PROGRAMME
    # --------------------------------------------------

    selected_programme = request.args.get(
        "programme",
        type=int
    )


    # --------------------------------------------------
    # DEFAULT PROGRAMME
    # --------------------------------------------------

    if not selected_programme:

        # If old student data already has a programme
        # and that programme belongs to the student's faculty,
        # use it as the default.

        if student["programme_id"]:

            valid_programme = False

            for programme in faculty_programmes:

                if programme["id"] == student["programme_id"]:

                    valid_programme = True

                    break

            if valid_programme:

                selected_programme = student["programme_id"]


        # If no valid previous programme,
        # select the first programme in the faculty.

        if not selected_programme and faculty_programmes:

            selected_programme = faculty_programmes[0]["id"]


    # --------------------------------------------------
    # GET ACTIVE ACADEMIC SESSION
    # --------------------------------------------------

    cursor.execute("""
        SELECT
            id,
            session_code,
            session_type

        FROM academic_sessions

        WHERE is_active = 1

        ORDER BY id DESC

        LIMIT 1
    """)

    academic_session = cursor.fetchone()


    # --------------------------------------------------
    # GET SELECTED SEMESTER
    # --------------------------------------------------

    selected_semester = request.args.get(
        "semester",
        "all"
    )


    # --------------------------------------------------
    # AVAILABLE SUBJECTS
    # --------------------------------------------------

    subjects = []


    if academic_session and selected_programme:

        query = """
            SELECT

                so.id AS offering_id,

                sub.id AS subject_id,
                sub.subject_code,
                sub.subject_name,
                sub.credit_hour,
                sub.color,

                so.semester,

                sos.id AS section_id,
                sos.section_code,

                ts.id AS schedule_id,
                ts.day_of_week,
                ts.start_time,
                ts.end_time,
                ts.delivery_mode,

                l.lecturer_name,

                c.classroom_code,

                CASE
                    WHEN sss.id IS NOT NULL THEN 1
                    ELSE 0
                END AS is_selected


            FROM subject_offerings so


            INNER JOIN subjects sub
                ON so.subject_id = sub.id


            INNER JOIN subject_offering_sections sos
                ON sos.offering_id = so.id


            INNER JOIN timetable_schedules ts
                ON ts.section_id = sos.id


            LEFT JOIN lecturers l
                ON ts.lecturer_id = l.id


            LEFT JOIN classrooms c
                ON ts.classroom_id = c.id


            LEFT JOIN student_selected_subjects sss
                ON sss.section_id = sos.id

                AND sss.student_id = %s

                AND sss.session_id = so.session_id


            WHERE so.programme_id = %s

              AND so.session_id = %s

              AND sub.is_active = 1
        """


        params = [

            student_id,

            selected_programme,

            academic_session["id"]

        ]


        # --------------------------------------------------
        # SEMESTER FILTER
        # --------------------------------------------------

        if selected_semester != "all":

            query += """
                AND so.semester = %s
            """

            params.append(
                int(selected_semester)
            )


        # --------------------------------------------------
        # ORDER SUBJECTS
        # --------------------------------------------------

        query += """
            ORDER BY

                so.semester,

                sub.subject_code,

                sos.section_code,

                ts.day_of_week,

                ts.start_time
        """


        # --------------------------------------------------
        # EXECUTE SUBJECT QUERY
        # --------------------------------------------------

        cursor.execute(
            query,
            tuple(params)
        )

        raw_subjects = cursor.fetchall()

        # --------------------------------------------------
        # GROUP SUBJECTS BY SECTION
        # One section = one selectable subject
        # All timetable periods belong to that section
        # --------------------------------------------------

        subjects = []

        section_map = {}

        for row in raw_subjects:

            section_id = row["section_id"]

            if section_id not in section_map:

                section_map[section_id] = {
                    "offering_id": row["offering_id"],
                    "subject_id": row["subject_id"],
                    "subject_code": row["subject_code"],
                    "subject_name": row["subject_name"],
                    "credit_hour": row["credit_hour"],
                    "color": row["color"],
                    "semester": row["semester"],
                    "section_id": row["section_id"],
                    "section_code": row["section_code"],
                    "is_selected": row["is_selected"],
                    "schedules": []
                }

                subjects.append(
                    section_map[section_id]
                )

            # Add ALL timetable periods belonging to this section

            section_map[section_id]["schedules"].append({
                "schedule_id": row["schedule_id"],
                "day_of_week": row["day_of_week"],
                "start_time": row["start_time"],
                "end_time": row["end_time"],
                "delivery_mode": row["delivery_mode"],
                "lecturer_name": row["lecturer_name"],
                "classroom_code": row["classroom_code"]
            })


    # --------------------------------------------------
    # GET SELECTED SUBJECTS
    # --------------------------------------------------

    selected_subjects = []


    if academic_session:

        cursor.execute("""
            SELECT DISTINCT

                sss.id AS selection_id,

                sub.subject_code,
                sub.subject_name,

                so.semester,

                sos.id AS section_id,
                sos.section_code


            FROM student_selected_subjects sss


            INNER JOIN subject_offerings so
                ON sss.offering_id = so.id


            INNER JOIN subjects sub
                ON so.subject_id = sub.id


            INNER JOIN subject_offering_sections sos
                ON sss.section_id = sos.id


            WHERE sss.student_id = %s

              AND sss.session_id = %s


            ORDER BY

                so.semester,

                sub.subject_code
        """, (

            student_id,

            academic_session["id"]

        ))


        selected_subjects = cursor.fetchall()


    # --------------------------------------------------
    # CLOSE DATABASE CURSOR
    # --------------------------------------------------

    cursor.close()


    # --------------------------------------------------
    # DISPLAY FIND SUBJECTS PAGE
    # --------------------------------------------------

    return render_template(

        "find_subjects.html",

        student=student,

        faculty_programmes=faculty_programmes,

        selected_programme=selected_programme,

        academic_session=academic_session,

        subjects=subjects,

        selected_subjects=selected_subjects,

        selected_semester=selected_semester

    )


@app.route("/student/select-subject", methods=["POST"])
def select_subject():

    # Student login protection
    if session.get("role") != "student":
        return redirect(url_for("student_login"))

    student_id = session.get("student_id")

    section_id = request.form.get("section_id")
    offering_id = request.form.get("offering_id")

    if not section_id or not offering_id:
        flash("Invalid subject selection.", "danger")
        return redirect(url_for("find_subjects"))


    cursor = db.cursor(dictionary=True)


    try:

        # --------------------------------------------------
        # GET ACTIVE SESSION
        # --------------------------------------------------

        cursor.execute("""
            SELECT id
            FROM academic_sessions
            WHERE is_active = 1
            ORDER BY id DESC
            LIMIT 1
        """)

        academic_session = cursor.fetchone()


        if not academic_session:

            cursor.close()

            flash(
                "No active academic session is available.",
                "danger"
            )

            return redirect(url_for("find_subjects"))


        session_id = academic_session["id"]


        # --------------------------------------------------
        # CHECK WHETHER ALREADY SELECTED
        # --------------------------------------------------

        cursor.execute("""
            SELECT id
            FROM student_selected_subjects
            WHERE student_id = %s
              AND section_id = %s
              AND session_id = %s
            LIMIT 1
        """, (
            student_id,
            section_id,
            session_id
        ))

        existing = cursor.fetchone()


        if existing:

            cursor.close()

            flash(
                "This subject section is already selected.",
                "warning"
            )

            return redirect(url_for("find_subjects"))


        # --------------------------------------------------
        # CHECK TIMETABLE CONFLICT
        # --------------------------------------------------

        cursor.execute("""
            SELECT
                new_ts.day_of_week,
                new_ts.start_time,
                new_ts.end_time,

                existing_sub.subject_code,
                existing_sub.subject_name,
                existing_sos.section_code

            FROM timetable_schedules new_ts

            INNER JOIN timetable_schedules existing_ts
                ON existing_ts.day_of_week = new_ts.day_of_week

            INNER JOIN student_selected_subjects selected
                ON selected.section_id = existing_ts.section_id

            INNER JOIN subject_offering_sections existing_sos
                ON existing_sos.id = existing_ts.section_id

            INNER JOIN subject_offerings existing_so
                ON existing_so.id = existing_sos.offering_id

            INNER JOIN subjects existing_sub
                ON existing_sub.id = existing_so.subject_id

            WHERE new_ts.section_id = %s

              AND selected.student_id = %s

              AND selected.session_id = %s

              AND new_ts.start_time < existing_ts.end_time

              AND new_ts.end_time > existing_ts.start_time

            LIMIT 1
        """, (
            section_id,
            student_id,
            session_id
        ))

        conflict = cursor.fetchone()


        # --------------------------------------------------
        # ADD SELECTED SUBJECT
        # --------------------------------------------------

        cursor.execute("""
            INSERT INTO student_selected_subjects
            (
                student_id,
                offering_id,
                section_id,
                session_id
            )
            VALUES (%s, %s, %s, %s)
        """, (
            student_id,
            offering_id,
            section_id,
            session_id
        ))


        db.commit()


    except Exception as e:

                db.rollback()

                cursor.close()

                print("Select subject error:", e)

                flash(
                    "Unable to add subject. Please try again.",
                    "danger"
                )

                return redirect(url_for("find_subjects"))

@app.route("/student/save-selected-subjects", methods=["POST"])
def save_selected_subjects():

    # ==========================================
    # STUDENT LOGIN PROTECTION
    # ==========================================

    if session.get("role") != "student":
        return redirect(url_for("student_login"))

    student_id = session.get("student_id")

    section_ids = request.form.getlist("section_ids")
    offering_ids = request.form.getlist("offering_ids")


    # ==========================================
    # NO SUBJECT SELECTED
    # ==========================================

    if not section_ids:

        flash(
            "Please select at least one subject.",
            "warning"
        )

        return redirect(
            url_for("find_subjects")
        )


    cursor = db.cursor(dictionary=True)


    try:

        # ==========================================
        # GET ACTIVE ACADEMIC SESSION
        # ==========================================

        cursor.execute("""
            SELECT
                id,
                session_code,
                session_type
            FROM academic_sessions
            WHERE is_active = 1
            ORDER BY id DESC
            LIMIT 1
        """)

        academic_session = cursor.fetchone()


        if not academic_session:

            cursor.close()

            flash(
                "No active academic session is available.",
                "danger"
            )

            return redirect(
                url_for("find_subjects")
            )


        session_id = academic_session["id"]


        # ==========================================
        # CONVERT IDS TO INTEGER
        # ==========================================

        try:

            section_ids = [
                int(section_id)
                for section_id in section_ids
            ]

            offering_ids = [
                int(offering_id)
                for offering_id in offering_ids
            ]

        except ValueError:

            cursor.close()

            flash(
                "Invalid subject selection.",
                "danger"
            )

            return redirect(
                url_for("find_subjects")
            )


        # ==========================================
        # REMOVE DUPLICATES
        # ==========================================

        section_ids = list(
            dict.fromkeys(section_ids)
        )


        # ==========================================
        # VERIFY SUBJECTS ARE ACTUALLY SCHEDULED
        # ==========================================

        placeholders = ",".join(
            ["%s"] * len(section_ids)
        )


        cursor.execute(
            f"""
                SELECT DISTINCT

                    sos.id AS section_id,

                    sos.section_code,

                    so.id AS offering_id,

                    sub.subject_code,

                    sub.subject_name

                FROM subject_offering_sections sos

                INNER JOIN subject_offerings so
                    ON sos.offering_id = so.id

                INNER JOIN subjects sub
                    ON so.subject_id = sub.id

                INNER JOIN timetable_schedules ts
                    ON ts.section_id = sos.id

                WHERE sos.id IN ({placeholders})

                  AND so.session_id = %s

                  AND sub.is_active = 1

            """,
            tuple(section_ids) + (
                session_id,
            )
        )


        valid_subjects = cursor.fetchall()


        valid_section_ids = [
            row["section_id"]
            for row in valid_subjects
        ]


        # ==========================================
        # INVALID SUBJECT
        # ==========================================

        if len(valid_section_ids) != len(section_ids):

            cursor.close()

            flash(
                "One or more selected subjects are not available.",
                "danger"
            )

            return redirect(
                url_for("find_subjects")
            )


        # ==========================================
        # GET ALL TIMETABLE SCHEDULES
        # FOR SELECTED SUBJECTS
        # ==========================================

        placeholders = ",".join(
            ["%s"] * len(section_ids)
        )


        cursor.execute(
            f"""
                SELECT

                    ts.section_id,

                    ts.day_of_week,

                    ts.start_time,

                    ts.end_time,

                    sub.subject_code,

                    sub.subject_name,

                    sos.section_code

                FROM timetable_schedules ts

                INNER JOIN subject_offering_sections sos
                    ON ts.section_id = sos.id

                INNER JOIN subject_offerings so
                    ON sos.offering_id = so.id

                INNER JOIN subjects sub
                    ON so.subject_id = sub.id

                WHERE ts.section_id IN ({placeholders})

                  AND so.session_id = %s

                ORDER BY
                    ts.day_of_week,
                    ts.start_time

            """,
            tuple(section_ids) + (
                session_id,
            )
        )


        schedules = cursor.fetchall()


        # ==========================================
        # CONFLICT DETECTION
        # ==========================================

        conflict = None


        for i in range(
            len(schedules)
        ):

            current = schedules[i]


            for j in range(
                i + 1,
                len(schedules)
            ):

                other = schedules[j]


                # Same section = same subject
                if (
                    current["section_id"]
                    ==
                    other["section_id"]
                ):
                    continue


                # Different day = no conflict
                if (
                    current["day_of_week"]
                    !=
                    other["day_of_week"]
                ):
                    continue


                # Time overlap
                if (
                    current["start_time"]
                    <
                    other["end_time"]
                    and
                    current["end_time"]
                    >
                    other["start_time"]
                ):

                    conflict = (
                        current,
                        other
                    )

                    break


            if conflict:
                break


        # ==========================================
        # CONFLICT FOUND
        # ==========================================

        if conflict:

            first = conflict[0]
            second = conflict[1]

            cursor.close()

            flash(
                "Timetable conflict detected: "
                + first["subject_code"]
                + " (Section "
                + first["section_code"]
                + ") conflicts with "
                + second["subject_code"]
                + " (Section "
                + second["section_code"]
                + ") on "
                + first["day_of_week"]
                + ".",
                "danger"
            )

            return redirect(
                url_for("find_subjects")
            )


        # ==========================================
        # SAVE SELECTIONS
        # ==========================================

        cursor.execute("""
            DELETE FROM student_selected_subjects

            WHERE student_id = %s

              AND session_id = %s
        """, (
            student_id,
            session_id
        ))


        # ==========================================
        # INSERT SELECTED SUBJECTS
        # ==========================================

        for index, section_id in enumerate(
            section_ids
        ):

            # Find correct offering
            cursor.execute("""
                SELECT
                    offering_id

                FROM subject_offering_sections

                WHERE id = %s

                LIMIT 1
            """, (
                section_id,
            ))

            section_data = cursor.fetchone()


            if not section_data:
                continue


            cursor.execute("""
                INSERT INTO student_selected_subjects
                (
                    student_id,
                    offering_id,
                    section_id,
                    session_id
                )

                VALUES
                (
                    %s,
                    %s,
                    %s,
                    %s
                )
            """, (
                student_id,
                section_data["offering_id"],
                section_id,
                session_id
            ))


        db.commit()

        cursor.close()


        # ==========================================
        # GO DIRECTLY TO MY TIMETABLE
        # ==========================================

        return redirect(
            url_for("my_timetable")
        )


    except Exception as e:

        db.rollback()

        cursor.close()

        print(
            "Save selected subjects error:",
            e
        )

        flash(
            "Unable to save selected subjects.",
            "danger"
        )

        return redirect(
            url_for("find_subjects")
        )

@app.route("/student/clear-timetable", methods=["POST"])
def clear_student_timetable():

    if session.get("role") != "student":
        return jsonify({
            "success": False,
            "message": "Unauthorized."
        }), 401

    student_id = session.get("student_id")

    cursor = db.cursor(dictionary=True)

    try:

        # Get current academic session
        cursor.execute("""
            SELECT id
            FROM academic_sessions
            WHERE is_active = 1
            ORDER BY id DESC
            LIMIT 1
        """)

        academic_session = cursor.fetchone()

        if not academic_session:
            cursor.close()

            return jsonify({
                "success": False,
                "message": "No active academic session."
            })

        # Clear only this student's current-session selections
        cursor.execute("""
            DELETE FROM student_selected_subjects
            WHERE student_id = %s
              AND session_id = %s
        """, (
            student_id,
            academic_session["id"]
        ))

        db.commit()

        cursor.close()

        return jsonify({
            "success": True
        })

    except Exception as e:

        db.rollback()
        cursor.close()

        print("Clear timetable error:", e)

        return jsonify({
            "success": False,
            "message": "Unable to clear timetable."
        }), 500

@app.route("/my-timetable")
def my_timetable():

    # ==========================================
    # STUDENT LOGIN PROTECTION
    # ==========================================

    if session.get("role") != "student":
        return redirect(url_for("student_login"))

    student_id = session.get("student_id")

    cursor = db.cursor(dictionary=True)

    # GET STUDENT CURRENT SEMESTER
    cursor.execute("""
        SELECT current_semester
        FROM students
        WHERE id = %s
        LIMIT 1
    """, (student_id,))

    student = cursor.fetchone()

    try:

        # ==========================================
        # GET ACTIVE ACADEMIC SESSION
        # ==========================================

        cursor.execute("""
            SELECT
                id,
                session_code,
                session_type
            FROM academic_sessions
            WHERE is_active = 1
            ORDER BY id DESC
            LIMIT 1
        """)

        academic_session = cursor.fetchone()

        timetable = []

        # ==========================================
        # GET STUDENT SELECTED SUBJECTS
        # + THEIR TIMETABLE SCHEDULE
        # ==========================================

        if academic_session:

            cursor.execute("""
                SELECT

                    sss.id AS selection_id,

                    sub.subject_code,
                    sub.subject_name,
                    sub.credit_hour,

                    sos.section_code,

                    ts.id AS schedule_id,
                    ts.day_of_week,

                    TIME_FORMAT(
                        ts.start_time,
                        '%H:%i'
                    ) AS start_time,

                    TIME_FORMAT(
                        ts.end_time,
                        '%H:%i'
                    ) AS end_time,

                    ts.delivery_mode,

                    l.lecturer_name,

                    c.classroom_code AS classroom,

                    sub.color

                FROM student_selected_subjects sss

                INNER JOIN subject_offering_sections sos
                    ON sss.section_id = sos.id

                INNER JOIN subject_offerings so
                    ON sos.offering_id = so.id

                INNER JOIN subjects sub
                    ON so.subject_id = sub.id

                INNER JOIN timetable_schedules ts
                    ON ts.section_id = sos.id

                LEFT JOIN lecturers l
                    ON ts.lecturer_id = l.id

                LEFT JOIN classrooms c
                    ON ts.classroom_id = c.id

                WHERE sss.student_id = %s
                  AND sss.session_id = %s

                ORDER BY
                    FIELD(
                        ts.day_of_week,
                        'Monday',
                        'Tuesday',
                        'Wednesday',
                        'Thursday',
                        'Friday'
                    ),
                    ts.start_time

            """, (
                student_id,
                academic_session["id"]
            ))

            timetable = cursor.fetchall()

        cursor.close()

        return render_template(
            "my_timetable.html",
            timetable=timetable,
            academic_session=academic_session,
            current_semester=student["current_semester"] if student else None
        )

    except Exception as e:

        cursor.close()

        print("MY TIMETABLE ERROR:", e)

        return render_template(
            "my_timetable.html",
            timetable=[],
            academic_session=academic_session,
            error="Unable to load timetable."
        )

@app.route("/student/save-current-timetable", methods=["POST"])
def save_current_timetable():

    # Student login protection
    if session.get("role") != "student":
        return {
            "success": False,
            "message": "Please login as a student."
        }, 401

    student_id = session.get("student_id")
    cursor = None

    try:
        # Make sure MySQL connection is still alive
        db.ping(reconnect=True, attempts=3, delay=1)

        # Use buffered cursor to avoid "Commands out of sync"
        cursor = db.cursor(dictionary=True, buffered=True)

        # Get active academic session
        cursor.execute("""
            SELECT
                id,
                session_code,
                session_type
            FROM academic_sessions
            WHERE is_active = 1
            ORDER BY id DESC
            LIMIT 1
        """)

        academic_session = cursor.fetchone()

        if not academic_session:
            return {
                "success": False,
                "message": "No active academic session."
            }, 400

        # Check whether student has selected subjects
        cursor.execute("""
            SELECT COUNT(*) AS total
            FROM student_selected_subjects
            WHERE student_id = %s
              AND session_id = %s
        """, (
            student_id,
            academic_session["id"]
        ))

        result = cursor.fetchone()

        if not result or result["total"] == 0:
            return {
                "success": False,
                "message": "You have not selected any subjects yet."
            }, 400

        return {
            "success": True,
            "message": "Current semester timetable saved successfully."
        }, 200

    except Exception as e:

        print("Save current timetable error:", e)

        return {
            "success": False,
            "message": "Unable to save current semester timetable."
        }, 500

    finally:
        if cursor:
            cursor.close()



# ==========================
# ADMIN
# ==========================

@app.route("/admin/dashboard")
def admin_dashboard():

    # --------------------------------------------------
    # ADMIN LOGIN PROTECTION
    # --------------------------------------------------

    if session.get("role") != "admin":
        return redirect(url_for("admin_login"))


    cursor = db.cursor(dictionary=True)


    # ==================================================
    # CURRENT ACADEMIC SESSION
    # ==================================================

    cursor.execute("""
        SELECT
            id,
            session_code,
            session_type
        FROM academic_sessions
        WHERE is_active = 1
        ORDER BY id DESC
        LIMIT 1
    """)

    current_session = cursor.fetchone()


    # ==================================================
    # SCHEDULED CLASSES
    # ==================================================

    scheduled_classes = 0

    if current_session:

        cursor.execute("""
            SELECT COUNT(*) AS total

            FROM timetable_schedules ts

            INNER JOIN subject_offering_sections sos
                ON ts.section_id = sos.id

            INNER JOIN subject_offerings so
                ON sos.offering_id = so.id

            WHERE so.session_id = %s
        """, (
            current_session["id"],
        ))

        result = cursor.fetchone()

        scheduled_classes = result["total"] or 0


    # ==================================================
    # UNSCHEDULED RESOURCES
    # ==================================================

    unscheduled_resources = 0

    if current_session:

        cursor.execute("""
            SELECT COUNT(*) AS total

            FROM timetable_resources tr

            INNER JOIN subject_offering_sections sos
                ON tr.section_id = sos.id

            INNER JOIN subject_offerings so
                ON sos.offering_id = so.id

            LEFT JOIN timetable_schedules ts
                ON ts.section_id = tr.section_id

            WHERE so.session_id = %s

            AND ts.id IS NULL
        """, (
            current_session["id"],
        ))

        result = cursor.fetchone()

        unscheduled_resources = result["total"] or 0


    # ==================================================
    # LECTURER CONFLICTS
    # ==================================================

    lecturer_conflicts = 0

    if current_session:

        cursor.execute("""
            SELECT COUNT(*) AS total

            FROM (
                SELECT
                    ts.lecturer_id,
                    ts.day_of_week,
                    ts.start_time,
                    ts.end_time

                FROM timetable_schedules ts

                INNER JOIN subject_offering_sections sos
                    ON ts.section_id = sos.id

                INNER JOIN subject_offerings so
                    ON sos.offering_id = so.id

                WHERE so.session_id = %s

                AND ts.lecturer_id IS NOT NULL

                GROUP BY
                    ts.lecturer_id,
                    ts.day_of_week,
                    ts.start_time,
                    ts.end_time

                HAVING COUNT(*) > 1

            ) AS conflicts
        """, (
            current_session["id"],
        ))

        result = cursor.fetchone()

        lecturer_conflicts = result["total"] or 0


    # ==================================================
    # CLASSROOM CONFLICTS
    # ==================================================

    classroom_conflicts = 0

    if current_session:

        cursor.execute("""
            SELECT COUNT(*) AS total

            FROM (
                SELECT
                    ts.classroom_id,
                    ts.day_of_week,
                    ts.start_time,
                    ts.end_time

                FROM timetable_schedules ts

                INNER JOIN subject_offering_sections sos
                    ON ts.section_id = sos.id

                INNER JOIN subject_offerings so
                    ON sos.offering_id = so.id

                WHERE so.session_id = %s

                AND ts.classroom_id IS NOT NULL

                GROUP BY
                    ts.classroom_id,
                    ts.day_of_week,
                    ts.start_time,
                    ts.end_time

                HAVING COUNT(*) > 1

            ) AS conflicts
        """, (
            current_session["id"],
        ))

        result = cursor.fetchone()

        classroom_conflicts = result["total"] or 0


    # ==================================================
    # RECENT ADMIN ACTIVITY
    # ==================================================

    cursor.execute("""
        SELECT
            aal.created_at,
            au.full_name,
            au.email,
            aal.module,
            aal.action,
            aal.description

        FROM admin_activity_logs aal

        INNER JOIN admin_users au
            ON aal.admin_id = au.id

        ORDER BY aal.created_at DESC

        LIMIT 2
    """)

    recent_activities = cursor.fetchall()


    # ==================================================
    # CLOSE CURSOR
    # ==================================================

    cursor.close()


    # ==================================================
    # DASHBOARD
    # ==================================================

    return render_template(
        "admin/admin_dashboard.html",

        current_session=current_session,

        scheduled_classes=scheduled_classes,

        unscheduled_resources=unscheduled_resources,

        lecturer_conflicts=lecturer_conflicts,

        classroom_conflicts=classroom_conflicts,

        recent_activities=recent_activities
    )


@app.route("/admin/manage-subjects")
def manage_subjects():

    search = request.args.get("search", "").strip()

    cursor = db.cursor(dictionary=True)

    sql = """
        SELECT
            s.id,
            s.subject_code,
            s.subject_name,
            s.credit_hour,
            s.contact_hour,
            s.is_active,
            f.faculty_code,
            f.faculty_name
        FROM subjects s
        LEFT JOIN faculties f
            ON s.faculty_id = f.id
        WHERE 1=1
    """

    values = []

    # Search subject code or name
    if search:
        sql += """
            AND (
                s.subject_code LIKE %s
                OR s.subject_name LIKE %s
            )
        """

        values.append(f"%{search}%")
        values.append(f"%{search}%")

    sql += " ORDER BY s.subject_code"

    cursor.execute(sql, values)

    subjects = cursor.fetchall()

    cursor.close()

    return render_template(
        "admin/manage_subjects.html",
        subjects=subjects,
        search=search
    )


@app.route("/admin/manage-lecturers")
def manage_lecturers():
    return render_template("admin/manage_lecturers.html")


@app.route("/admin/manage-classrooms")
def manage_classrooms():
    return render_template("admin/manage_classrooms.html")


@app.route("/admin/manage-timetable")
def manage_timetable():

    if session.get("role") != "admin":
        return redirect(url_for("admin_login"))

    cursor = db.cursor(dictionary=True, buffered=True)

    # =====================================================
    # SELECTED FILTERS
    # =====================================================

    selected_session = request.args.get(
        "session",
        ""
    )

    selected_programme = request.args.get(
        "programme",
        ""
    )

    selected_semester = request.args.get(
        "semester",
        ""
    )

    # =====================================================
    # ACADEMIC SESSIONS
    # =====================================================

    cursor.execute("""
        SELECT
            id,
            session_code,
            session_type
        FROM academic_sessions
        ORDER BY id ASC
    """)

    sessions = cursor.fetchall()

    # =====================================================
    # PROGRAMMES
    # =====================================================

    cursor.execute("""
        SELECT
            id,
            programme_code,
            programme_name
        FROM programmes
        ORDER BY programme_name ASC
    """)

    programmes = cursor.fetchall()

    # =====================================================
    # SEMESTERS
    # =====================================================

    cursor.execute("""
        SELECT DISTINCT
            semester
        FROM subject_offerings
        WHERE semester IS NOT NULL
        ORDER BY semester ASC
    """)

    semesters = cursor.fetchall()

    # =====================================================
    # DEFAULT EMPTY DATA
    # =====================================================

    subject_sections = []
    timetable_resources = []
    schedules = []

    # =====================================================
    # LOAD TIMETABLE DATA ONLY AFTER FILTERS SELECTED
    # =====================================================

    if (
        selected_session
        and selected_programme
        and selected_semester
    ):

        # -------------------------------------------------
        # SUBJECT SECTIONS
        # -------------------------------------------------

        cursor.execute("""
            SELECT

                sos.id AS section_id,
                sos.section_code,

                s.subject_code,
                s.subject_name,
                s.credit_hour,
                s.color,

                so.id AS offering_id,
                so.semester,

                p.id AS programme_id,
                p.programme_name,

                a.id AS session_id,
                a.session_code

            FROM subject_offering_sections sos

            INNER JOIN subject_offerings so
                ON sos.offering_id = so.id

            INNER JOIN subjects s
                ON so.subject_id = s.id

            LEFT JOIN programmes p
                ON so.programme_id = p.id

            LEFT JOIN academic_sessions a
                ON so.session_id = a.id

            WHERE so.session_id = %s
              AND so.programme_id = %s
              AND so.semester = %s

            ORDER BY
                s.subject_code,
                sos.section_code
        """, (
            selected_session,
            selected_programme,
            selected_semester
        ))

        subject_sections = cursor.fetchall()

        # -------------------------------------------------
        # TIMETABLE RESOURCES
        # -------------------------------------------------

        cursor.execute("""
            SELECT

                tr.id AS resource_id,
                tr.section_id,

                tr.lecturer_id,
                tr.classroom_id,
                tr.delivery_mode,
                tr.duration_periods,

                sos.section_code,

                s.subject_code,
                s.subject_name,
                s.color,

                l.lecturer_name,

                c.classroom_code

            FROM timetable_resources tr

            INNER JOIN subject_offering_sections sos
                ON tr.section_id = sos.id

            INNER JOIN subject_offerings so
                ON sos.offering_id = so.id

            INNER JOIN subjects s
                ON so.subject_id = s.id

            LEFT JOIN lecturers l
                ON tr.lecturer_id = l.id

            LEFT JOIN classrooms c
                ON tr.classroom_id = c.id

            WHERE so.session_id = %s
              AND so.programme_id = %s
              AND so.semester = %s

            ORDER BY
                s.subject_code,
                sos.section_code
        """, (
            selected_session,
            selected_programme,
            selected_semester
        ))

        timetable_resources = cursor.fetchall()

        # -------------------------------------------------
        # EXISTING TIMETABLE
        # -------------------------------------------------

        cursor.execute("""
            SELECT

                ts.id,

                ts.section_id,

                ts.lecturer_id,
                ts.classroom_id,

                ts.day_of_week,
                ts.start_time,
                ts.end_time,

                ts.delivery_mode,

                s.subject_code,
                s.subject_name,

                sos.section_code,

                s.color,

                p.programme_name,

                so.semester,

                a.session_code,

                l.lecturer_name,

                c.classroom_code

            FROM timetable_schedules ts

            INNER JOIN subject_offering_sections sos
                ON ts.section_id = sos.id

            INNER JOIN subject_offerings so
                ON sos.offering_id = so.id

            INNER JOIN subjects s
                ON so.subject_id = s.id

            LEFT JOIN programmes p
                ON so.programme_id = p.id

            LEFT JOIN academic_sessions a
                ON so.session_id = a.id

            LEFT JOIN lecturers l
                ON ts.lecturer_id = l.id

            LEFT JOIN classrooms c
                ON ts.classroom_id = c.id

            WHERE so.session_id = %s
              AND so.programme_id = %s
              AND so.semester = %s

            ORDER BY
                ts.day_of_week,
                ts.start_time
        """, (
            selected_session,
            selected_programme,
            selected_semester
        ))

        schedules = cursor.fetchall()

    # =====================================================
    # LECTURERS
    # =====================================================

    cursor.execute("""
        SELECT
            id,
            lecturer_name
        FROM lecturers
        ORDER BY lecturer_name ASC
    """)

    lecturers = cursor.fetchall()

    # =====================================================
    # CLASSROOMS
    # =====================================================

    cursor.execute("""
        SELECT
            id,
            classroom_code
        FROM classrooms
        ORDER BY classroom_code ASC
    """)

    classrooms = cursor.fetchall()

    cursor.close()

    # =====================================================
    # RENDER
    # =====================================================

    return render_template(
        "admin/manage_timetable.html",
        subject_sections=subject_sections,
        timetable_resources=timetable_resources,
        schedules=schedules,
        sessions=sessions,
        programmes=programmes,
        semesters=semesters,
        lecturers=lecturers,
        classrooms=classrooms,
        selected_session=selected_session,
        selected_programme=selected_programme,
        selected_semester=selected_semester
    )

@app.route("/admin/auto-generate", methods=["GET", "POST"])
def auto_generate():

    cursor = db.cursor(dictionary=True)

    # =========================
    # FILTER OPTIONS
    # =========================

    cursor.execute("""
        SELECT id, session_code, session_type
        FROM academic_sessions
        WHERE is_active = 1
        ORDER BY session_code DESC
    """)
    sessions = cursor.fetchall()

    cursor.execute("""
        SELECT id, programme_code, programme_name
        FROM programmes
        WHERE is_active = 1
        ORDER BY programme_code
    """)
    programmes = cursor.fetchall()

    cursor.execute("""
        SELECT DISTINCT semester
        FROM subject_offerings
        WHERE semester IS NOT NULL
        ORDER BY semester
    """)
    semesters = cursor.fetchall()

    cursor.close()

    return render_template(
        "admin/auto_generate.html",
        sessions=sessions,
        programmes=programmes,
        semesters=semesters
    )

@app.route("/admin/manage-timetable/save", methods=["POST"])
def save_timetable_schedule():

    data = request.get_json()

    schedule_id = data.get("schedule_id")
    section_id = data.get("section_id")
    lecturer_id = data.get("lecturer_id")
    classroom_id = data.get("classroom_id")
    delivery_mode = data.get("delivery_mode")
    day = data.get("day")
    start_time = data.get("start_time")
    end_time = data.get("end_time")

    # =========================
    # REQUIRED FIELDS
    # =========================

    if not section_id or not lecturer_id or not delivery_mode \
            or not day or not start_time or not end_time:

        return {
            "success": False,
            "message": "Missing required timetable information."
        }, 400

    # =========================
    # PHYSICAL REQUIRES CLASSROOM
    # =========================

    if delivery_mode == "Physical" and not classroom_id:

        return {
            "success": False,
            "message": "Physical class requires a classroom."
        }, 400

    # Online does not use classroom
    if delivery_mode == "Online":
        classroom_id = None

    cursor = db.cursor(dictionary=True)

    try:

        # =========================
        # CHECK LECTURER CLASH
        # =========================

        cursor.execute("""
            SELECT id
            FROM timetable_schedules
            WHERE lecturer_id = %s
              AND day_of_week = %s
              AND start_time < %s
              AND end_time > %s
              AND (%s IS NULL OR id != %s)
            LIMIT 1
        """, (
            lecturer_id,
            day,
            end_time,
            start_time,
            schedule_id,
            schedule_id
        ))

        lecturer_clash = cursor.fetchone()

        if lecturer_clash:

            cursor.close()

            return {
                "success": False,
                "message": "Clash detected: This lecturer is already scheduled at this time."
            }, 409

        # =========================
        # CHECK CLASSROOM CLASH
        # =========================

        if delivery_mode == "Physical":

            cursor.execute("""
                SELECT id
                FROM timetable_schedules
                WHERE classroom_id = %s
                  AND day_of_week = %s
                  AND start_time < %s
                  AND end_time > %s
                  AND (%s IS NULL OR id != %s)
                LIMIT 1
            """, (
                classroom_id,
                day,
                end_time,
                start_time,
                schedule_id,
                schedule_id
            ))

            classroom_clash = cursor.fetchone()

            if classroom_clash:

                cursor.close()

                return {
                    "success": False,
                    "message": "Clash detected: This classroom is already booked at this time."
                }, 409

        # =========================
        # UPDATE EXISTING SCHEDULE
        # =========================

        if schedule_id:

            cursor.execute("""
                UPDATE timetable_schedules
                SET
                    section_id = %s,
                    lecturer_id = %s,
                    classroom_id = %s,
                    day_of_week = %s,
                    start_time = %s,
                    end_time = %s,
                    delivery_mode = %s
                WHERE id = %s
            """, (
                section_id,
                lecturer_id,
                classroom_id,
                day,
                start_time,
                end_time,
                delivery_mode,
                schedule_id
            ))

            db.commit()

            cursor.close()

            return {
                "success": True,
                "schedule_id": schedule_id,
                "message": "Timetable updated successfully."
            }

        # =========================
        # INSERT NEW SCHEDULE
        # =========================

        cursor.execute("""
            INSERT INTO timetable_schedules
            (
                section_id,
                lecturer_id,
                classroom_id,
                day_of_week,
                start_time,
                end_time,
                delivery_mode
            )
            VALUES (%s, %s, %s, %s, %s, %s, %s)
        """, (
            section_id,
            lecturer_id,
            classroom_id,
            day,
            start_time,
            end_time,
            delivery_mode
        ))

        db.commit()

        new_schedule_id = cursor.lastrowid

        cursor.close()

        return {
            "success": True,
            "schedule_id": new_schedule_id,
            "message": "Timetable saved successfully."
        }

    except Exception as e:

        db.rollback()
        cursor.close()

        return {
            "success": False,
            "message": str(e)
        }, 500
    

@app.route("/admin/generate-timetable", methods=["POST"])
def generate_timetable():

    cursor = db.cursor(dictionary=True)

    session_id = request.form.get("session_id")
    programme_id = request.form.get("programme_id")
    semester = request.form.get("semester")

    if not session_id or not programme_id or not semester:
        cursor.close()
        flash("Please select Academic Session, Programme and Semester.", "warning")
        return redirect(url_for("auto_generate"))

    try:

        # =========================
        # GET TIMETABLE RESOURCES
        # =========================

        cursor.execute("""
            SELECT
                tr.section_id,
                tr.lecturer_id,
                tr.classroom_id,
                tr.delivery_mode,
                tr.duration_periods
            FROM timetable_resources tr

            JOIN subject_offering_sections sos
                ON tr.section_id = sos.id

            JOIN subject_offerings so
                ON sos.offering_id = so.id

            WHERE so.session_id = %s
            AND so.programme_id = %s
            AND so.semester = %s

        """, (
            session_id,
            programme_id,
            semester
        ))

        resources = cursor.fetchall()
        random.shuffle(resources)

        if not resources:

            cursor.close()

            flash(
                "No timetable resources found. "
                "Please assign lecturers, mode and duration first.",
                "warning"
            )

            return redirect(url_for("auto_generate"))


        # =========================
        # CLEAR OLD GENERATED DATA
        # =========================

        cursor.execute("""
            DELETE ts
            FROM timetable_schedules ts

            JOIN subject_offering_sections sos
                ON ts.section_id = sos.id

            JOIN subject_offerings so
                ON sos.offering_id = so.id

            WHERE so.session_id = %s
            AND so.programme_id = %s
            AND so.semester = %s
        """, (
            session_id,
            programme_id,
            semester
        ))


        # =========================
        # AVAILABLE DAYS
        # =========================

        days = [
            "Monday",
            "Tuesday",
            "Wednesday",
            "Thursday",
            "Friday"
        ]


        # =========================
        # AVAILABLE PERIODS
        # =========================

        period_times = {
            1: ("08:00:00", "09:00:00"),
            2: ("09:00:00", "10:00:00"),
            3: ("10:00:00", "11:00:00"),
            4: ("11:00:00", "12:00:00"),
            5: ("12:00:00", "13:00:00"),
            6: ("13:00:00", "14:00:00"),
            7: ("14:00:00", "15:00:00"),
            8: ("15:00:00", "16:00:00"),
            9: ("16:00:00", "17:00:00"),
            10: ("17:00:00", "18:00:00")
        }


        generated = 0


        # =========================
        # SIMPLE RANDOM SCHEDULING
        # =========================

        for resource in resources:

            duration = resource["duration_periods"]

            placed = False

            # Create random order of days
            shuffled_days = days.copy()
            random.shuffle(shuffled_days)

            # Create random order of periods
            period_numbers = list(period_times.keys())
            random.shuffle(period_numbers)


            for day in shuffled_days:

                if placed:
                    break


                for start_period in period_numbers:

                    end_period = start_period + duration - 1

                    if end_period not in period_times:
                        continue


                    start_time = period_times[start_period][0]
                    end_time = period_times[end_period][1]


                    # =========================
                    # CHECK CONFLICT
                    # =========================

                    cursor.execute("""
                        SELECT id
                        FROM timetable_schedules

                        WHERE day_of_week = %s

                        AND (
                            lecturer_id = %s

                            OR (
                                classroom_id IS NOT NULL
                                AND classroom_id = %s
                                AND %s = 'Physical'
                                AND delivery_mode = 'Physical'
                            )

                            OR section_id = %s
                        )

                        AND start_time < %s
                        AND end_time > %s

                        LIMIT 1
                    """, (
                        day,
                        resource["lecturer_id"],
                        resource["classroom_id"],
                        resource["delivery_mode"],
                        resource["section_id"],
                        end_time,
                        start_time
                    ))

                    conflict = cursor.fetchone()


                    if conflict:
                        continue


                    # =========================
                    # INSERT TIMETABLE
                    # =========================

                    cursor.execute("""
                        INSERT INTO timetable_schedules
                        (
                            section_id,
                            lecturer_id,
                            classroom_id,
                            day_of_week,
                            start_time,
                            end_time,
                            delivery_mode
                        )

                        VALUES
                        (
                            %s, %s, %s, %s, %s, %s, %s
                        )
                    """, (
                        resource["section_id"],
                        resource["lecturer_id"],

                        resource["classroom_id"]
                        if resource["delivery_mode"] == "Physical"
                        else None,

                        day,
                        start_time,
                        end_time,
                        resource["delivery_mode"]
                    ))

                    generated += 1
                    placed = True

                    break


            # =========================
            # IF CANNOT SCHEDULE
            # =========================

            if not placed:

                db.rollback()
                cursor.close()

                flash(
                    "Unable to generate timetable because some "
                    "classes cannot be scheduled without conflicts.",
                    "danger"
                )

                return redirect(url_for("auto_generate"))


        db.commit()
        cursor.close()


        flash(
            f"Timetable generated successfully. "
            f"{generated} classes scheduled.",
            "success"
        )

        return redirect(
            url_for(
                "manage_timetable",
                session_id=session_id,
                programme_id=programme_id,
                semester=semester
            )
        )


    except Exception as e:

        db.rollback()
        cursor.close()

        flash(
            f"Failed to generate timetable: {str(e)}",
            "danger"
        )

        return redirect(url_for("auto_generate"))

@app.route("/admin/manage-timetable/delete/<int:schedule_id>", methods=["POST"])
def delete_timetable_schedule(schedule_id):

    cursor = db.cursor()

    cursor.execute("""
        DELETE FROM timetable_schedules
        WHERE id = %s
    """, (schedule_id,))

    db.commit()
    cursor.close()

    return {
        "success": True
    }


@app.route("/admin/manage-admins")
def manage_admins():
    return render_template("admin/manage_admins.html")


@app.route("/admin/reports")
def reports():
    return render_template("admin/reports.html")

@app.route("/admin/add-subject", methods=["GET", "POST"])
def add_subject():

    cursor = db.cursor(dictionary=True)

    # Get all faculties / units
    cursor.execute("""
        SELECT
            id,
            faculty_code,
            faculty_name
        FROM faculties
        ORDER BY faculty_code
    """)

    faculties = cursor.fetchall()

    if request.method == "POST":

        subject_code = request.form["subject_code"].strip()
        subject_name = request.form["subject_name"].strip()
        credit_hour = request.form["credit_hour"]
        contact_hour = request.form["contact_hour"]
        faculty_id = request.form["faculty_id"]
        is_active = request.form.get("is_active", "1")

        # Check duplicate subject code
        cursor.execute("""
            SELECT id
            FROM subjects
            WHERE subject_code = %s
        """, (subject_code,))

        existing = cursor.fetchone()

        if existing:

            cursor.close()

            flash(
                f"Subject code {subject_code} already exists.",
                "warning"
            )

            return redirect(url_for("add_subject"))

        # Insert new subject
        cursor.execute("""
            INSERT INTO subjects
            (
                subject_code,
                subject_name,
                credit_hour,
                contact_hour,
                faculty_id,
                is_active
            )
            VALUES (%s, %s, %s, %s, %s, %s)
        """, (
            subject_code,
            subject_name,
            credit_hour,
            contact_hour,
            faculty_id,
            is_active
        ))

        db.commit()

        cursor.close()

        flash(
            f"{subject_code} has been added successfully.",
            "success"
        )

        return redirect(url_for("manage_subjects"))

    cursor.close()

    return render_template(
        "admin/add_subject.html",
        faculties=faculties
    )

@app.route("/admin/delete-subject/<int:subject_id>")
def delete_subject(subject_id):

    cursor = db.cursor()

    cursor.execute(
        "DELETE FROM subjects WHERE id = %s",
        (subject_id,)
    )

    db.commit()

    cursor.close()

    return redirect(url_for("manage_subjects"))


@app.route("/admin/import-subjects", methods=["GET", "POST"])
def import_subjects():

    cursor = db.cursor(dictionary=True)

    if request.method == "POST":

        file = request.files.get("file")
        programme_id = request.form.get("programme_id")

        if not programme_id:
            cursor.close()
            flash("Please select a programme.", "warning")
            return redirect(url_for("import_subjects"))

        if not file or file.filename == "":
            cursor.close()
            flash("Please select an Excel file.", "warning")
            return redirect(url_for("import_subjects"))

        filepath = os.path.join("uploads", file.filename)
        file.save(filepath)

        try:

            df = pd.read_excel(filepath)

            required_columns = [
                "Year",
                "Semester",
                "Course Code",
                "Course Name",
                "Status",
                "Credit",
                "Contact Hour"
            ]

            for column in required_columns:

                if column not in df.columns:
                    flash(
                        f"Missing column: {column}",
                        "danger"
                    )

                    os.remove(filepath)
                    cursor.close()

                    return redirect(
                        url_for("import_subjects")
                    )

            added = 0
            skipped = 0
            curriculum_added = 0
            failed = 0

            for _, row in df.iterrows():

                subject_code = str(
                    row["Course Code"]
                ).strip()

                subject_name = str(
                    row["Course Name"]
                ).strip()

                status = str(
                    row["Status"]
                ).strip()

                year = row["Year"]
                semester = row["Semester"]
                credit = row["Credit"]
                contact_hour = row["Contact Hour"]

                # Skip invalid rows
                if (
                    not subject_code
                    or subject_code.lower() == "nan"
                    or pd.isna(year)
                    or pd.isna(semester)
                    or pd.isna(credit)
                ):
                    failed += 1
                    continue

                # Contact Hour can be empty
                if pd.isna(contact_hour):
                    contact_hour = None

                # =========================
                # SUBJECT MASTER
                # =========================

                cursor.execute("""
                    SELECT id
                    FROM subjects
                    WHERE subject_code = %s
                """, (subject_code,))

                existing_subject = cursor.fetchone()

                if existing_subject:

                    subject_id = existing_subject["id"]
                    skipped += 1

                else:

                    cursor.execute("""
                        INSERT INTO subjects
                        (
                            subject_code,
                            subject_name,
                            credit_hour,
                            contact_hour,
                            faculty_id,
                            is_active
                        )
                        VALUES
                        (
                            %s, %s, %s, %s, NULL, 1
                        )
                    """, (
                        subject_code,
                        subject_name,
                        int(credit),
                        contact_hour
                    ))

                    subject_id = cursor.lastrowid
                    added += 1

                # =========================
                # CURRICULUM
                # =========================

                cursor.execute("""
                    SELECT id
                    FROM curriculum
                    WHERE subject_id = %s
                    AND programme_id = %s
                    AND year = %s
                    AND semester = %s
                """, (
                    subject_id,
                    programme_id,
                    int(year),
                    int(semester)
                ))

                existing_curriculum = cursor.fetchone()

                if not existing_curriculum:

                    cursor.execute("""
                        INSERT INTO curriculum
                        (
                            subject_id,
                            programme_id,
                            year,
                            semester,
                            curriculum_status
                        )
                        VALUES
                        (
                            %s, %s, %s, %s, %s
                        )
                    """, (
                        subject_id,
                        programme_id,
                        int(year),
                        int(semester),
                        status
                    ))

                    curriculum_added += 1

            db.commit()

            cursor.close()
            os.remove(filepath)

            flash(
                f"Import completed: "
                f"{added} new subjects added, "
                f"{skipped} existing subjects skipped, "
                f"{curriculum_added} curriculum records added, "
                f"{failed} rows failed.",
                "success"
            )

            return redirect(
                url_for("manage_subjects")
            )

        except Exception as e:

            db.rollback()

            cursor.close()

            if os.path.exists(filepath):
                os.remove(filepath)

            flash(
                f"Import failed: {str(e)}",
                "danger"
            )

            return redirect(
                url_for("import_subjects")
            )

    # Programmes
    cursor.execute("""
        SELECT
            id,
            programme_code,
            programme_name
        FROM programmes
        WHERE is_active = 1
        ORDER BY programme_code
    """)

    programmes = cursor.fetchall()

    cursor.close()

    return render_template(
        "admin/import_subjects.html",
        programmes=programmes
    )


@app.route("/admin/assign-curriculum", methods=["GET", "POST"])
def assign_curriculum():

    cursor = db.cursor(dictionary=True)

    if request.method == "POST":

        session_id = request.form.get("session_id")
        programme_id = request.form.get("programme_id")
        curriculum_ids = request.form.getlist("curriculum_id")

        if not session_id or not programme_id:
            cursor.close()
            flash(
                "Please select an academic session and programme.",
                "warning"
            )
            return redirect(url_for("assign_curriculum"))

        if not curriculum_ids:
            cursor.close()
            flash(
                "Please select at least one subject.",
                "warning"
            )
            return redirect(
                url_for(
                    "assign_curriculum",
                    session_id=session_id,
                    programme_id=programme_id
                )
            )

        try:

            added = 0
            skipped = 0

            for curriculum_id in curriculum_ids:

                # Get curriculum record
                cursor.execute("""
                    SELECT
                        subject_id,
                        year,
                        semester,
                        curriculum_status
                    FROM curriculum
                    WHERE id = %s
                    AND programme_id = %s
                """, (
                    curriculum_id,
                    programme_id
                ))

                item = cursor.fetchone()

                if not item:
                    continue

                # Check if already assigned to this session
                cursor.execute("""
                    SELECT id
                    FROM subject_offerings
                    WHERE subject_id = %s
                    AND programme_id = %s
                    AND session_id = %s
                """, (
                    item["subject_id"],
                    programme_id,
                    session_id
                ))

                existing = cursor.fetchone()

                if existing:
                    skipped += 1
                    continue

                # Create subject offering
                cursor.execute("""
                    INSERT INTO subject_offerings
                    (
                        subject_id,
                        programme_id,
                        session_id,
                        year,
                        semester,
                        curriculum_status
                    )
                    VALUES
                    (
                        %s, %s, %s, %s, %s, %s
                    )
                """, (
                    item["subject_id"],
                    programme_id,
                    session_id,
                    item["year"],
                    item["semester"],
                    item["curriculum_status"]
                ))

                added += 1

            db.commit()
            cursor.close()

            flash(
                f"{added} subjects assigned successfully. "
                f"{skipped} already assigned.",
                "success"
            )

            return redirect(url_for("subject_offerings"))

        except Exception as e:

            db.rollback()
            cursor.close()

            flash(
                f"Failed to assign curriculum: {str(e)}",
                "danger"
            )

            return redirect(
                url_for(
                    "assign_curriculum",
                    session_id=session_id,
                    programme_id=programme_id
                )
            )

    # =========================
    # GET
    # =========================

    session_id = request.args.get("session_id")
    programme_id = request.args.get("programme_id")

    # Academic Sessions
    cursor.execute("""
        SELECT
            id,
            session_code,
            session_type
        FROM academic_sessions
        WHERE is_active = 1
        ORDER BY session_code DESC
    """)

    sessions = cursor.fetchall()

    # Programmes
    cursor.execute("""
        SELECT
            id,
            programme_code,
            programme_name
        FROM programmes
        WHERE is_active = 1
        ORDER BY programme_code
    """)

    programmes = cursor.fetchall()

    # Curriculum
    curriculum = []

    if programme_id:

        cursor.execute("""
            SELECT
                c.id AS curriculum_id,
                c.subject_id,
                c.year,
                c.semester,
                c.curriculum_status,
                s.subject_code,
                s.subject_name,
                s.credit_hour
            FROM curriculum c
            JOIN subjects s
                ON c.subject_id = s.id
            WHERE c.programme_id = %s
            ORDER BY
                c.year,
                c.semester,
                s.subject_code
        """, (programme_id,))

        curriculum = cursor.fetchall()

    # Subjects already assigned to selected session
    offered_subject_ids = []

    if session_id and programme_id:

        cursor.execute("""
            SELECT subject_id
            FROM subject_offerings
            WHERE session_id = %s
            AND programme_id = %s
        """, (
            session_id,
            programme_id
        ))

        offered_subject_ids = [
            row["subject_id"]
            for row in cursor.fetchall()
        ]

    cursor.close()

    return render_template(
        "admin/assign_curriculum.html",
        sessions=sessions,
        programmes=programmes,
        curriculum=curriculum,
        offered_subject_ids=offered_subject_ids,
        selected_session_id=session_id,
        selected_programme_id=programme_id
    )


@app.route("/admin/subject-offerings")
def subject_offerings():

    cursor = db.cursor(dictionary=True)

    cursor.execute("""
        SELECT
            so.id,
            so.year,
            so.semester,
            so.curriculum_status,
            s.subject_code,
            s.subject_name,
            p.programme_code,
            p.programme_name,
            a.session_code,

            (SELECT GROUP_CONCAT(
                    sos.section_code
                    ORDER BY sos.section_code
                    SEPARATOR ', '
                )
                FROM subject_offering_sections sos
                WHERE sos.offering_id = so.id
            ) AS section_codes

        FROM subject_offerings so

        JOIN subjects s
            ON so.subject_id = s.id

        JOIN programmes p
            ON so.programme_id = p.id

        JOIN academic_sessions a
            ON so.session_id = a.id

        ORDER BY
            a.session_code DESC,
            p.programme_code,
            so.year,
            so.semester,
            s.subject_code
    """)

    offerings = cursor.fetchall()

    # Get sections for each subject offering
    for offering in offerings:

        cursor.execute("""
            SELECT
                id,
                section_code
            FROM subject_offering_sections
            WHERE offering_id = %s
            ORDER BY section_code
        """, (offering["id"],))

        offering["sections"] = cursor.fetchall()

    cursor.close()

    return render_template(
        "admin/subject_offerings.html",
        offerings=offerings
    )

@app.route("/admin/subject-offerings/<int:offering_id>/sections/add", methods=["POST"])
def add_section(offering_id):

    section_code = request.form.get("section_code", "").strip()

    if not section_code:
        flash("Please enter a section code.", "warning")
        return redirect(url_for("subject_offerings"))

    cursor = db.cursor(dictionary=True)

    # Check if section already exists
    cursor.execute("""
        SELECT id
        FROM subject_offering_sections
        WHERE offering_id = %s
        AND section_code = %s
    """, (offering_id, section_code))

    existing_section = cursor.fetchone()

    if existing_section:

        cursor.close()

        flash_for(
            "subject_offerings",
            f"Section {section_code} already exists for this subject offering.",
            "warning"
        )

        return redirect(url_for("subject_offerings"))

    # Add new section
    cursor.execute("""
        INSERT INTO subject_offering_sections
        (offering_id, section_code)
        VALUES (%s, %s)
    """, (offering_id, section_code))

    db.commit()

    cursor.close()

    flash_for(
        "subject_offerings",
        f"Section {section_code} has been added successfully.",
        "success"
    )

    return redirect(url_for("subject_offerings"))

@app.route("/admin/subject-offerings/sections/<int:section_id>/delete", methods=["POST"])
def delete_section(section_id):

    cursor = db.cursor(dictionary=True)

    # Get section information
    cursor.execute("""
        SELECT section_code, offering_id
        FROM subject_offering_sections
        WHERE id = %s
    """, (section_id,))

    section = cursor.fetchone()

    if not section:

        cursor.close()

        flash(
            "Section not found.",
            "warning"
        )

        return redirect(url_for("subject_offerings"))

    section_code = section["section_code"]

    # Delete section
    cursor.execute("""
        DELETE FROM subject_offering_sections
        WHERE id = %s
    """, (section_id,))

    db.commit()

    cursor.close()

    flash_for(
        "subject_offerings",
        f"Section {section_code} has been deleted successfully.",
        "success"
    )

    return redirect(url_for("subject_offerings"))

@app.route("/admin/add-subject-offering", methods=["GET", "POST"])
def add_subject_offering():

    cursor = db.cursor(dictionary=True)

    if request.method == "POST":

        session_id = request.form.get("session_id")
        programme_id = request.form.get("programme_id")
        curriculum_ids = request.form.getlist("curriculum_id")

        if not session_id or not programme_id:
            cursor.close()
            flash("Please select an academic session and programme.", "warning")
            return redirect(url_for("add_subject_offering"))

        if not curriculum_ids:
            cursor.close()
            flash("Please select at least one subject.", "warning")
            return redirect(
                url_for(
                    "add_subject_offering",
                    session_id=session_id,
                    programme_id=programme_id
                )
            )

        try:

            added = 0
            skipped = 0

            for curriculum_id in curriculum_ids:

                # Get curriculum record
                cursor.execute("""
                    SELECT
                        subject_id,
                        programme_id,
                        year,
                        semester,
                        curriculum_status
                    FROM subject_offerings
                    WHERE id = %s
                    AND programme_id = %s
                    AND session_id IS NULL
                """, (
                    curriculum_id,
                    programme_id
                ))

                curriculum = cursor.fetchone()

                if not curriculum:
                    continue

                # Check if already offered in this session
                cursor.execute("""
                    SELECT id
                    FROM subject_offerings
                    WHERE subject_id = %s
                    AND programme_id = %s
                    AND session_id = %s
                    AND year = %s
                    AND semester = %s
                """, (
                    curriculum["subject_id"],
                    programme_id,
                    session_id,
                    curriculum["year"],
                    curriculum["semester"]
                ))

                existing = cursor.fetchone()

                if existing:
                    skipped += 1
                    continue

                # Create session-specific offering
                cursor.execute("""
                    INSERT INTO subject_offerings
                    (
                        subject_id,
                        programme_id,
                        session_id,
                        year,
                        semester,
                        curriculum_status
                    )
                    VALUES
                    (
                        %s, %s, %s, %s, %s, %s
                    )
                """, (
                    curriculum["subject_id"],
                    programme_id,
                    session_id,
                    curriculum["year"],
                    curriculum["semester"],
                    curriculum["curriculum_status"]
                ))

                added += 1

            db.commit()
            cursor.close()

            flash(
                f"{added} subjects assigned successfully. "
                f"{skipped} already assigned subjects skipped.",
                "success"
            )

            return redirect(url_for("subject_offerings"))

        except Exception as e:

            db.rollback()
            cursor.close()

            flash(
                f"Failed to assign subjects: {str(e)}",
                "danger"
            )

            return redirect(url_for("add_subject_offering"))

    # -------------------------
    # GET
    # -------------------------

    session_id = request.args.get("session_id")
    programme_id = request.args.get("programme_id")

    # Academic Sessions
    cursor.execute("""
        SELECT
            id,
            session_code,
            session_type
        FROM academic_sessions
        WHERE is_active = 1
        ORDER BY session_code DESC
    """)

    sessions = cursor.fetchall()

    # Programmes
    cursor.execute("""
        SELECT
            id,
            programme_code,
            programme_name
        FROM programmes
        WHERE is_active = 1
        ORDER BY programme_code
    """)

    programmes = cursor.fetchall()

    curriculum = []

    # Load curriculum only when programme is selected
    if programme_id:

        cursor.execute("""
            SELECT
                so.id AS curriculum_id,
                so.subject_id,
                so.year,
                so.semester,
                so.curriculum_status,
                s.subject_code,
                s.subject_name,
                s.credit_hour
            FROM subject_offerings so
            JOIN subjects s
                ON so.subject_id = s.id
            WHERE so.programme_id = %s
            AND so.session_id IS NULL
            ORDER BY
                so.year,
                so.semester,
                s.subject_code
        """, (programme_id,))

        curriculum = cursor.fetchall()

    # Existing offerings for selected session
    offered_subject_ids = []

    if session_id and programme_id:

        cursor.execute("""
            SELECT subject_id
            FROM subject_offerings
            WHERE session_id = %s
            AND programme_id = %s
        """, (
            session_id,
            programme_id
        ))

        offered_subject_ids = [
            row["subject_id"]
            for row in cursor.fetchall()
        ]

    cursor.close()

    return render_template(
        "admin/add_subject_offering.html",
        sessions=sessions,
        programmes=programmes,
        curriculum=curriculum,
        offered_subject_ids=offered_subject_ids,
        selected_session_id=session_id,
        selected_programme_id=programme_id
    )

@app.route("/admin/academic-sessions")
def academic_sessions():

    cursor = db.cursor(dictionary=True)

    cursor.execute("""
        SELECT *
        FROM academic_sessions
        ORDER BY id ASC
    """)

    sessions = cursor.fetchall()

    cursor.close()

    return render_template(
        "admin/academic_sessions.html",
        sessions=sessions
    )

@app.route("/admin/add-session", methods=["GET", "POST"])
def add_session():

    if request.method == "POST":

        session_code = request.form["session_code"].strip()
        session_type = request.form["session_type"].strip()

        cursor = db.cursor()

        cursor.execute("""
            SELECT id
            FROM academic_sessions
            WHERE session_code = %s
        """, (session_code,))

        existing = cursor.fetchone()

        if existing:

            cursor.close()

            flash_for(
                "academic_sessions",
                f"Academic session {session_code} already exists.",
                "warning"
            )

            return redirect(url_for("add_session"))


        cursor.execute("""
            INSERT INTO academic_sessions
            (session_code, session_type, is_active)
            VALUES (%s, %s, TRUE)
        """, (session_code, session_type))

        db.commit()

        cursor.close()

        flash_for(
            "academic_sessions",
            f"Academic session {session_code} has been added successfully.",
            "success"
        )

        return redirect(
            url_for("academic_sessions")
        )

    return render_template(
        "admin/add_session.html"
    )

@app.route("/admin/toggle-session/<int:session_id>")
def toggle_session(session_id):

    cursor = db.cursor()

    cursor.execute("""
        SELECT is_active
        FROM academic_sessions
        WHERE id = %s
    """, (session_id,))

    session = cursor.fetchone()

    if not session:
        cursor.close()

        flash_for(
            "academic_sessions",
            "Academic session not found.",
            "warning"
        )

        return redirect(url_for("academic_sessions"))

    current_status = session[0]

    new_status = not current_status

    cursor.execute("""
        UPDATE academic_sessions
        SET is_active = %s
        WHERE id = %s
    """, (new_status, session_id))

    db.commit()

    cursor.close()

    flash_for(
        "academic_sessions",
        "Academic session status has been updated.",
        "success"
    )

    return redirect(url_for("academic_sessions"))

@app.route("/admin/programmes")
def programmes():

    cursor = db.cursor(dictionary=True)

    cursor.execute("""
        SELECT
            p.id,
            p.programme_code,
            p.programme_level,
            p.programme_name,
            p.faculty_id,
            p.is_active,
            f.faculty_code,
            f.faculty_name
        FROM programmes p
        JOIN faculties f
            ON p.faculty_id = f.id
        ORDER BY
            f.faculty_code,
            p.programme_level,
            p.programme_code
    """)

    programmes = cursor.fetchall()

    cursor.close()

    return render_template(
        "admin/programmes.html",
        programmes=programmes
    )

@app.route("/admin/add-programme", methods=["GET", "POST"])
def add_programme():

    cursor = db.cursor(dictionary=True)

    # Get faculties for dropdown
    cursor.execute("""
        SELECT id, faculty_code, faculty_name
        FROM faculties
        ORDER BY faculty_code
    """)

    faculties = cursor.fetchall()

    if request.method == "POST":

        programme_code = request.form["programme_code"].strip()
        programme_level = request.form["programme_level"]
        programme_name = request.form["programme_name"].strip()
        faculty_id = request.form["faculty_id"]

        # Check duplicate programme code
        cursor.execute("""
            SELECT id
            FROM programmes
            WHERE programme_code = %s
        """, (programme_code,))

        existing = cursor.fetchone()

        if existing:

            cursor.close()

            flash(
                f"Programme code {programme_code} already exists.",
                "warning"
            )

            return redirect(url_for("add_programme"))

        # Insert programme
        cursor.execute("""
            INSERT INTO programmes
            (
                faculty_id,
                programme_code,
                programme_level,
                programme_name
            )
            VALUES (%s, %s, %s, %s)
        """, (
            faculty_id,
            programme_code,
            programme_level,
            programme_name
        ))

        db.commit()

        cursor.close()

        flash(
            f"{programme_code} has been added successfully.",
            "success"
        )

        return redirect(url_for("programmes"))

    cursor.close()

    return render_template(
        "admin/add_programme.html",
        faculties=faculties
    )

@app.route("/admin/toggle-programme/<int:programme_id>")
def toggle_programme(programme_id):

    cursor = db.cursor()

    cursor.execute("""
        SELECT is_active
        FROM programmes
        WHERE id = %s
    """, (programme_id,))

    programme = cursor.fetchone()

    if not programme:

        cursor.close()

        flash(
            "Programme not found.",
            "warning"
        )

        return redirect(url_for("programmes"))

    current_status = programme[0]

    new_status = not current_status

    cursor.execute("""
        UPDATE programmes
        SET is_active = %s
        WHERE id = %s
    """, (new_status, programme_id))

    db.commit()

    cursor.close()

    flash(
        "Programme status has been updated.",
        "success"
    )

    return redirect(url_for("programmes"))

@app.route("/admin/lecturers")
def lecturers():

    cursor = db.cursor(dictionary=True)

    cursor.execute("""
        SELECT
            l.id,
            l.lecturer_name,
            l.is_active,
            f.faculty_code,
            f.faculty_name
        FROM lecturers l
        LEFT JOIN faculties f
            ON l.faculty_id = f.id
        ORDER BY l.lecturer_name
    """)

    lecturers = cursor.fetchall()

    cursor.close()

    return render_template(
        "admin/lecturers.html",
        lecturers=lecturers
    )

@app.route("/admin/lecturers/add", methods=["GET", "POST"])
def add_lecturer():

    cursor = db.cursor(dictionary=True)

    # Get faculties
    cursor.execute("""
        SELECT id, faculty_code, faculty_name
        FROM faculties
        ORDER BY faculty_code
    """)

    faculties = cursor.fetchall()

    cursor.close()

    if request.method == "POST":

        lecturer_name = request.form.get("lecturer_name", "").strip()
        faculty_id = request.form.get("faculty_id")
        is_active = request.form.get("is_active", "1")

        if not lecturer_name or not faculty_id:

            flash_for(
                "lecturers",
                "Lecturer Name and Faculty / Unit are required.",
                "warning"
            )

            return render_template(
                "admin/add_lecturer.html",
                faculties=faculties
            )

        cursor = db.cursor()

        try:

            cursor.execute("""
                INSERT INTO lecturers
                (
                    lecturer_name,
                    faculty_id,
                    is_active
                )
                VALUES (%s, %s, %s)
            """, (
                lecturer_name,
                faculty_id,
                is_active
            ))

            db.commit()

        except Exception as e:

            db.rollback()

            if "Duplicate entry" in str(e):

                flash_for(
                    "lecturers",
                    f"Lecturer {lecturer_name} already exists.",
                    "warning"
                )

            else:

                flash_for(
                    "lecturers",
                    "Unable to add lecturer. Please try again.",
                    "danger"
                )

            cursor.close()

            return render_template(
                "admin/add_lecturer.html",
                faculties=faculties
            )

        cursor.close()

        flash_for(
            "lecturers",
            f"Lecturer {lecturer_name} has been added successfully.",
            "success"
        )

        return redirect(url_for("lecturers"))

    # GET request
    return render_template(
        "admin/add_lecturer.html",
        faculties=faculties
    )

@app.route("/admin/lecturers/edit/<int:lecturer_id>", methods=["GET", "POST"])
def edit_lecturer(lecturer_id):

    cursor = db.cursor(dictionary=True)

    # Get lecturer
    cursor.execute("""
        SELECT *
        FROM lecturers
        WHERE id = %s
    """, (lecturer_id,))

    lecturer = cursor.fetchone()

    if not lecturer:
        cursor.close()

        flash_for(
            "lecturers",
            "Lecturer not found.",
            "danger"
        )

        return redirect(url_for("lecturers"))

    # Get faculties
    cursor.execute("""
        SELECT
            id,
            faculty_code,
            faculty_name
        FROM faculties
        ORDER BY faculty_code
    """)

    faculties = cursor.fetchall()

    if request.method == "POST":

        lecturer_name = request.form.get(
            "lecturer_name", ""
        ).strip()

        faculty_id = request.form.get("faculty_id")
        is_active = request.form.get("is_active", "1")

        if not lecturer_name or not faculty_id:

            flash_for(
                "lecturers",
                "Lecturer Name and Faculty / Unit are required.",
                "warning"
            )

            cursor.close()

            return render_template(
                "admin/edit_lecturer.html",
                lecturer=lecturer,
                faculties=faculties
            )

        try:

            cursor.execute("""
                UPDATE lecturers
                SET
                    lecturer_name = %s,
                    faculty_id = %s,
                    is_active = %s
                WHERE id = %s
            """, (
                lecturer_name,
                faculty_id,
                is_active,
                lecturer_id
            ))

            db.commit()

        except Exception as e:

            db.rollback()

            flash_for(
                "lecturers",
                "Unable to update lecturer. Please try again.",
                "danger"
            )

            cursor.close()

            return render_template(
                "admin/edit_lecturer.html",
                lecturer=lecturer,
                faculties=faculties
            )

        cursor.close()

        flash_for(
            "lecturers",
            f"Lecturer {lecturer_name} has been updated successfully.",
            "success"
        )

        return redirect(url_for("lecturers"))

    # GET request
    cursor.close()

    return render_template(
        "admin/edit_lecturer.html",
        lecturer=lecturer,
        faculties=faculties
    )

@app.route("/admin/classrooms")
def classrooms():

    cursor = db.cursor(dictionary=True)

    cursor.execute("""
        SELECT
            id,
            classroom_code,
            room_type
        FROM classrooms
        ORDER BY classroom_code
    """)

    classrooms = cursor.fetchall()

    cursor.close()

    return render_template(
        "admin/classrooms.html",
        classrooms=classrooms
    )

@app.route("/admin/classrooms/add", methods=["GET", "POST"])
def add_classroom():

    if request.method == "POST":

        classroom_code = request.form.get("classroom_code", "").strip()
        room_type = request.form.get("room_type", "").strip()

        if not classroom_code or not room_type:

            flash_for(
                "classrooms",
                "Classroom Code is required.",
                "warning"
            )

            return render_template(
                "admin/add_classroom.html"
            )

        cursor = db.cursor()

        try:

            cursor.execute("""
                INSERT INTO classrooms
                (
                    classroom_code,
                    room_type
                )
                VALUES (%s, %s)
            """, (
                classroom_code,
                room_type if room_type else None
            ))

            db.commit()

        except Exception as e:

            db.rollback()

            if "Duplicate entry" in str(e):

                flash_for(
                    "classrooms",
                    f"Classroom Code {classroom_code} already exists.",
                    "warning"
                )

            else:

                flash_for(
                    "classrooms",
                    "Unable to add classroom. Please try again.",
                    "danger"
                )

            cursor.close()

            return render_template(
                "admin/add_classroom.html"
            )

        cursor.close()

        flash_for(
            "classrooms",
            f"Classroom {classroom_code} has been added successfully.",
            "success"
        )

        return redirect(url_for("classrooms"))

    return render_template(
        "admin/add_classroom.html"
    )

@app.route("/admin/classrooms/edit/<int:classroom_id>", methods=["GET", "POST"])
def edit_classroom(classroom_id):

    cursor = db.cursor(dictionary=True)

    cursor.execute("""
        SELECT *
        FROM classrooms
        WHERE id = %s
    """, (classroom_id,))

    classroom = cursor.fetchone()

    if not classroom:
        cursor.close()

        flash_for("classrooms", "Classroom not found.", "danger")

        return redirect(url_for("classrooms"))

    if request.method == "POST":

        classroom_code = request.form.get("classroom_code", "").strip()
        room_type = request.form.get("room_type", "").strip()

        if not classroom_code or not room_type:

            flash_for(
                "classrooms",
                "Classroom Code is required.",
                "warning"
            )

            cursor.close()

            return render_template(
                "admin/edit_classroom.html",
                classroom=classroom
            )

        try:

            cursor.execute("""
                UPDATE classrooms
                SET
                    classroom_code = %s,
                    room_type = %s
                WHERE id = %s
            """, (
                classroom_code,
                room_type if room_type else None,
                classroom_id
            ))

            db.commit()

        except Exception as e:

            db.rollback()

            if "Duplicate entry" in str(e):

                flash_for(
                    "classrooms",
                    f"Classroom Code {classroom_code} already exists.",
                    "warning"
                )

            else:

                flash_for(
                    "classrooms",
                    "Unable to update classroom. Please try again.",
                    "danger"
                )

            cursor.close()

            return render_template(
                "admin/edit_classroom.html",
                classroom=classroom
            )

        cursor.close()

        flash_for(
            "classrooms",
            f"Classroom {classroom_code} has been updated successfully.",
            "success"
        )

        return redirect(url_for("classrooms"))

    cursor.close()

    return render_template(
        "admin/edit_classroom.html",
        classroom=classroom
    )

@app.route("/admin/timetable-resources", methods=["GET", "POST"])
def timetable_resources():

    cursor = db.cursor(dictionary=True)

    # =========================
    # FILTER VALUES
    # =========================

    session_id = request.args.get("session_id")
    programme_id = request.args.get("programme_id")
    semester = request.args.get("semester")

    # =========================
    # SAVE RESOURCE
    # =========================

    if request.method == "POST":

        section_id = request.form.get("section_id")
        lecturer_id = request.form.get("lecturer_id")
        delivery_mode = request.form.get("delivery_mode")
        classroom_id = request.form.get("classroom_id")
        duration_periods = request.form.get("duration_periods")

        if not section_id or not lecturer_id or not delivery_mode or not duration_periods:
            cursor.close()

            flash(
                "Please complete all required fields.",
                "warning"
            )

            return redirect(request.referrer or url_for("timetable_resources"))

        # Classroom required for Physical
        if delivery_mode == "Physical" and not classroom_id:

            cursor.close()

            flash(
                "Please select a classroom for Physical class.",
                "warning"
            )

            return redirect(request.referrer or url_for("timetable_resources"))

        # Online = no classroom
        if delivery_mode == "Online":
            classroom_id = None

        try:

            # Check if resource already exists
            cursor.execute("""
                SELECT id
                FROM timetable_resources
                WHERE section_id = %s
            """, (section_id,))

            existing = cursor.fetchone()

            if existing:

                cursor.execute("""
                    UPDATE timetable_resources
                    SET
                        lecturer_id = %s,
                        delivery_mode = %s,
                        classroom_id = %s,
                        duration_periods = %s
                    WHERE section_id = %s
                """, (
                    lecturer_id,
                    delivery_mode,
                    classroom_id,
                    duration_periods,
                    section_id
                ))

            else:

                cursor.execute("""
                    INSERT INTO timetable_resources
                    (
                        section_id,
                        lecturer_id,
                        delivery_mode,
                        classroom_id,
                        duration_periods
                    )
                    VALUES
                    (
                        %s, %s, %s, %s, %s
                    )
                """, (
                    section_id,
                    lecturer_id,
                    delivery_mode,
                    classroom_id,
                    duration_periods
                ))

            db.commit()

            cursor.close()

            flash(
                "Timetable resource saved successfully.",
                "success"
            )

            return redirect(request.referrer or url_for("timetable_resources"))

        except Exception as e:

            db.rollback()
            cursor.close()

            flash(
                f"Failed to save timetable resource: {str(e)}",
                "danger"
            )

            return redirect(request.referrer or url_for("timetable_resources"))

    # =========================
    # FILTER OPTIONS
    # =========================

    cursor.execute("""
        SELECT
            id,
            session_code,
            session_type
        FROM academic_sessions
        WHERE is_active = 1
        ORDER BY session_code DESC
    """)

    sessions = cursor.fetchall()


    cursor.execute("""
        SELECT
            id,
            programme_code,
            programme_name
        FROM programmes
        WHERE is_active = 1
        ORDER BY programme_code
    """)

    programmes = cursor.fetchall()


    cursor.execute("""
        SELECT DISTINCT semester
        FROM subject_offerings
        WHERE semester IS NOT NULL
        ORDER BY semester
    """)

    semesters = cursor.fetchall()


    # =========================
    # LECTURERS
    # =========================

    cursor.execute("""
        SELECT
            id,
            lecturer_name
        FROM lecturers
        WHERE is_active = 1
        ORDER BY lecturer_name
    """)

    lecturers = cursor.fetchall()


    # =========================
    # CLASSROOMS
    # =========================

    cursor.execute("""
        SELECT
            id,
            classroom_code
        FROM classrooms
        ORDER BY classroom_code
    """)

    classrooms = cursor.fetchall()


    # =========================
    # RESOURCES
    # =========================

    resources = []

    if session_id and programme_id and semester:

        cursor.execute("""
            SELECT

                sos.id AS section_id,
                sos.section_code,

                s.id AS subject_id,
                s.subject_code,
                s.subject_name,

                so.id AS offering_id,
                so.year,
                so.semester,

                p.programme_code,
                p.programme_name,

                a.session_code,

                tr.id AS resource_id,
                tr.lecturer_id,
                tr.classroom_id,
                tr.delivery_mode,
                tr.duration_periods

            FROM subject_offering_sections sos

            JOIN subject_offerings so
                ON sos.offering_id = so.id

            JOIN subjects s
                ON so.subject_id = s.id

            JOIN programmes p
                ON so.programme_id = p.id

            JOIN academic_sessions a
                ON so.session_id = a.id

            LEFT JOIN timetable_resources tr
                ON tr.section_id = sos.id

            WHERE so.session_id = %s
            AND so.programme_id = %s
            AND so.semester = %s

            ORDER BY
                s.subject_code,
                sos.section_code
        """, (
            session_id,
            programme_id,
            semester
        ))

        resources = cursor.fetchall()


    cursor.close()


    return render_template(
        "admin/timetable_resources.html",
        resources=resources,
        sessions=sessions,
        programmes=programmes,
        semesters=semesters,
        lecturers=lecturers,
        classrooms=classrooms,
        selected_session_id=session_id,
        selected_programme_id=programme_id,
        selected_semester=semester
    )

@app.route("/admin/timetable-resources/save", methods=["POST"])
def save_timetable_resource():

    cursor = db.cursor(dictionary=True)

    section_id = request.form.get("section_id")
    session_id = request.form.get("session_id")
    programme_id = request.form.get("programme_id")
    semester = request.form.get("semester")

    lecturer_id = request.form.get("lecturer_id")
    delivery_mode = request.form.get("delivery_mode")
    classroom_id = request.form.get("classroom_id")
    duration_periods = request.form.get("duration_periods")

    if not section_id or not lecturer_id or not delivery_mode or not duration_periods:
        cursor.close()

        flash(
            "Please complete lecturer, delivery mode and duration.",
            "warning"
        )

        return redirect(
            url_for(
                "timetable_resources",
                session_id=session_id,
                programme_id=programme_id,
                semester=semester
            )
        )

    # Classroom only required for Physical
    if delivery_mode == "Physical" and not classroom_id:

        cursor.close()

        flash(
            "Please select a classroom for physical class.",
            "warning"
        )

        return redirect(
            url_for(
                "timetable_resources",
                session_id=session_id,
                programme_id=programme_id,
                semester=semester
            )
        )

    try:

        # Check whether resource already exists
        cursor.execute("""
            SELECT id
            FROM timetable_resources
            WHERE section_id = %s
        """, (section_id,))

        existing = cursor.fetchone()

        if existing:

            # UPDATE existing resource
            cursor.execute("""
                UPDATE timetable_resources
                SET
                    lecturer_id = %s,
                    delivery_mode = %s,
                    classroom_id = %s,
                    duration_periods = %s
                WHERE section_id = %s
            """, (
                lecturer_id,
                delivery_mode,
                classroom_id if delivery_mode == "Physical" else None,
                duration_periods,
                section_id
            ))

            message = "Timetable resource updated successfully."
            message_type = "info"

        else:

            # ADD new resource
            cursor.execute("""
                INSERT INTO timetable_resources
                (
                    section_id,
                    lecturer_id,
                    delivery_mode,
                    classroom_id,
                    duration_periods
                )
                VALUES
                (%s, %s, %s, %s, %s)
            """, (
                section_id,
                lecturer_id,
                delivery_mode,
                classroom_id if delivery_mode == "Physical" else None,
                duration_periods
            ))

            message = "Timetable resource added successfully."
            message_type = "success"

        db.commit()
        cursor.close()

        flash(message, message_type)

    except Exception as e:

        db.rollback()
        cursor.close()

        flash(
            f"Failed to save timetable resource: {str(e)}",
            "danger"
        )

    return redirect(
        url_for(
            "timetable_resources",
            session_id=session_id,
            programme_id=programme_id,
            semester=semester
        )
    )

@app.route("/admin/activity-log")
def admin_activity_log():

    if session.get("role") != "admin":
        return redirect(url_for("admin_login"))

    cursor = db.cursor(dictionary=True)

    cursor.execute("""
        SELECT
            aal.id,
            aal.created_at,
            au.full_name,
            aal.module,
            aal.action,
            aal.description

        FROM admin_activity_logs aal

        INNER JOIN admin_users au
            ON aal.admin_id = au.id

        ORDER BY aal.created_at DESC

        LIMIT 200
    """)

    activities = cursor.fetchall()

    cursor.close()

    return render_template(
        "admin/activity_log.html",
        activities=activities
    )

if __name__ == "__main__":
    app.run(debug=True)