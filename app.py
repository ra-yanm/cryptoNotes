import os
import hashlib
import json
import secrets
from datetime import datetime, timedelta
from functools import wraps
from dotenv import load_dotenv
from flask import Flask, jsonify, request
import bcrypt
from flask_mailman import EmailMessage, Mail
from key_management import decrypt_bulk, decrypt_login, encrypt_bulk, encrypt_login
from ecc import ECC, decrypt_with, encrypt_for


load_dotenv()
app = Flask(__name__)
app.config.update(
    MAIL_SERVER=os.getenv("MAIL_SERVER"),
    MAIL_PORT=int(os.getenv("MAIL_PORT", "587")),
    MAIL_USE_TLS=os.getenv("MAIL_USE_TLS", "true").lower() == "true",
    MAIL_USERNAME=os.getenv("MAIL_USERNAME"),
    MAIL_PASSWORD=os.getenv("MAIL_PASSWORD"),
    MAIL_DEFAULT_SENDER=os.getenv("MAIL_DEFAULT_SENDER"),
)
mail = Mail(app)
_secure_storage_ready = False


def get_db():
    import mysql.connector

    return mysql.connector.connect(
        host=os.getenv("DB_HOST"),
        user=os.getenv("DB_USER"),
        password=os.getenv("DB_PASSWORD"),
        database=os.getenv("DB_NAME"),
    )


def ensure_secure_storage(db):
    global _secure_storage_ready
    if _secure_storage_ready:
        return
    cursor = db.cursor()
    cursor.execute("""
        CREATE TABLE IF NOT EXISTS secure_login (
            identity_hash CHAR(64) PRIMARY KEY,
            encrypted_credentials TEXT NOT NULL
        )
    """)
    cursor.execute("""
        CREATE TABLE IF NOT EXISTS account_otp (
            challenge_id CHAR(64) PRIMARY KEY,
            user_ID VARCHAR(20) NULL,
            email VARCHAR(254) NOT NULL,
            purpose VARCHAR(20) NOT NULL,
            otp_hash CHAR(64) NOT NULL,
            payload TEXT NULL,
            expires_at DATETIME NOT NULL,
            used_at DATETIME NULL
        )
    """)
    cursor.execute("""
        CREATE TABLE IF NOT EXISTS user_ecc_keys (
            user_ID VARCHAR(20) PRIMARY KEY,
            public_key TEXT NOT NULL,
            encrypted_private_key TEXT NOT NULL
        )
    """)
    cursor.execute("""
        CREATE TABLE IF NOT EXISTS note_messages (
            message_id BIGINT AUTO_INCREMENT PRIMARY KEY,
            noteID INT NOT NULL,
            student_ID VARCHAR(20) NOT NULL,
            faculty_ID VARCHAR(20) NOT NULL,
            sender_ID VARCHAR(20) NOT NULL,
            ciphertext_for_student TEXT NOT NULL,
            ciphertext_for_faculty TEXT NOT NULL,
            created_at DATETIME NOT NULL DEFAULT CURRENT_TIMESTAMP,
            INDEX note_message_lookup (noteID, student_ID, created_at)
        )
    """)
    cursor.execute("ALTER TABLE user ADD COLUMN IF NOT EXISTS email_verified BOOLEAN NOT NULL DEFAULT TRUE")
    for table, columns in {
        "user": "MODIFY email VARCHAR(254), MODIFY password TEXT, MODIFY bio TEXT, MODIFY discord_id TEXT",
        "notes": "MODIFY title TEXT, MODIFY note TEXT",
        "note_pending": "MODIFY title TEXT, MODIFY note TEXT",
        "note_suggestions": "MODIFY suggestion TEXT",
        "courses": "MODIFY title TEXT, MODIFY description TEXT",
    }.items():
        cursor.execute(f"ALTER TABLE {table} {columns}")
    db.commit()
    cursor.close()
    _secure_storage_ready = True


def query(sql, params=(), many=False):
    db = get_db()
    ensure_secure_storage(db)
    cursor = db.cursor(dictionary=True)
    try:
        cursor.execute(sql, params)
        result = cursor.fetchall() if many else cursor.fetchone()
        db.commit()
        return result
    finally:
        cursor.close()
        db.close()


def protected_fields(row, fields):
    if not row:
        return row
    for field in fields:
        if field in row:
            row[field] = decrypt_bulk(row[field])
    return row


def protected_rows(rows, fields):
    return [protected_fields(row, fields) for row in rows]


def user_ecc_key(user_id):
    """Load or create the user's ECC key pair used for message encryption."""
    record = query("SELECT public_key, encrypted_private_key FROM user_ecc_keys WHERE user_ID = %s", (user_id,))
    if not record:
        key = ECC()
        query(
            "INSERT INTO user_ecc_keys (user_ID, public_key, encrypted_private_key) VALUES (%s, %s, %s)",
            (user_id, json.dumps(list(key.public_key)), encrypt_bulk(str(key.private_key))),
        )
        return key
    private_key = int(decrypt_bulk(record["encrypted_private_key"]))
    return ECC(private_key=private_key)


def message_context(note_id, user, student_id=None):
    context = query(
        "SELECT n.courseID, c.coordinator, n.student_view "
        "FROM notes n JOIN courses c ON c.courseID = n.courseID WHERE n.noteID = %s",
        (note_id,),
    )
    if not context:
        return None, (jsonify(error="Note not found"), 404)
    if user["user_type"] == "faculty":
        if context["coordinator"] != user["user_ID"]:
            return None, (jsonify(error="Only the course coordinator may access these messages"), 403)
        if not student_id:
            return context, None
    elif user["user_type"] == "student":
        if not context["student_view"]:
            return None, (jsonify(error="This note is not available to students"), 403)
        student_id = user["user_ID"]
    else:
        return None, (jsonify(error="Only students and the course coordinator may use messages"), 403)
    student = query("SELECT user_ID FROM user WHERE user_ID = %s AND user_type = 'student'", (student_id,))
    if not student:
        return None, (jsonify(error="Student not found"), 404)
    context["student_ID"] = student_id
    context["faculty_ID"] = context["coordinator"]
    return context, None


def identity_digest(identity):
    return hashlib.sha256(identity.strip().lower().encode("utf-8")).hexdigest()


def hash_password(password):
    return bcrypt.hashpw(password.encode("utf-8"), bcrypt.gensalt()).decode("utf-8")


def check_password(password, password_hash):
    return bcrypt.checkpw(password.encode("utf-8"), password_hash.encode("utf-8"))


def create_otp(email, purpose, user_id=None, payload=None):
    challenge_id = secrets.token_hex(32)
    otp = f"{secrets.randbelow(1000000):06d}"
    query(
        "INSERT INTO account_otp (challenge_id, user_ID, email, purpose, otp_hash, payload, expires_at) "
        "VALUES (%s, %s, %s, %s, %s, %s, %s)",
        (challenge_id, user_id, email, purpose, hashlib.sha256(otp.encode()).hexdigest(), payload,
         datetime.utcnow() + timedelta(minutes=5)),
    )
    subject = "Your CampusLink verification code"
    message = EmailMessage(
        subject=subject,
        body=f"Your {purpose} verification code is {otp}. It expires in 5 minutes.",
        to=[email],
    )
    message.send()
    return challenge_id


def resend_otp(challenge_id, purpose):
    record = query(
        "SELECT email, user_ID, payload FROM account_otp "
        "WHERE challenge_id = %s AND purpose = %s AND used_at IS NULL",
        (challenge_id, purpose),
    )
    if not record:
        return None
    new_challenge_id = create_otp(
        record["email"], purpose, record["user_ID"], record["payload"]
    )
    query(
        "UPDATE account_otp SET used_at = %s WHERE challenge_id = %s",
        (datetime.utcnow(), challenge_id),
    )
    return new_challenge_id


def valid_otp(challenge_id, otp, purpose):
    record = query(
        "SELECT * FROM account_otp WHERE challenge_id = %s AND purpose = %s AND used_at IS NULL",
        (challenge_id, purpose),
    )
    if not record or record["expires_at"] < datetime.utcnow():
        return None
    if not secrets.compare_digest(record["otp_hash"], hashlib.sha256(otp.encode()).hexdigest()):
        return None
    query("UPDATE account_otp SET used_at = %s WHERE challenge_id = %s", (datetime.utcnow(), challenge_id))
    return record


def save_login(identity, password):
    save_login_hash(identity, hash_password(password))


def save_login_hash(identity, password_hash):
    query(
        "REPLACE INTO secure_login (identity_hash, encrypted_credentials) VALUES (%s, %s)",
        (identity_digest(identity), encrypt_login(json.dumps({"identity": identity, "password_hash": password_hash}))),
    )


def authenticated_user(view):
    @wraps(view)
    def wrapped(*args, **kwargs):
        user_id = request.headers.get("X-User-ID")
        if not user_id:
            return jsonify(error="Authentication required"), 401
        user = query(
            "SELECT user_ID, user_type, name, email, department, bio, personal_phn, discord_id "
            "FROM user WHERE user_ID = %s",
            (user_id,),
        )
        if not user:
            return jsonify(error="User not found"), 401
        return view(user, *args, **kwargs)

    return wrapped


@app.post("/api/login")
def login():
    data = request.get_json(silent=True) or {}
    identity = data.get("userID", "")
    password = data.get("password", "")
    encrypted = query("SELECT encrypted_credentials FROM secure_login WHERE identity_hash = %s", (identity_digest(identity),))
    user = None
    if encrypted:
        credentials = json.loads(decrypt_login(encrypted["encrypted_credentials"]))
        password_matches = (
            check_password(password, credentials["password_hash"])
            if "password_hash" in credentials
            else credentials.get("password") == password
        )
        if password_matches:
            identity = credentials["identity"]
            user = query("SELECT user_ID, user_type, name, email, department, bio, personal_phn, discord_id, email_verified FROM user WHERE user_ID = %s OR email = %s", (identity, identity))
            if user:
                password_hash = credentials.get("password_hash", hash_password(password))
                save_login_hash(user["user_ID"], password_hash)
                save_login_hash(user["email"], password_hash)
    else:
        user = query(
            "SELECT user_ID, user_type, name, email, department, bio, personal_phn, discord_id, email_verified FROM user "
            "WHERE (user_ID = %s OR email = %s) AND password = %s",
            (identity, identity, password),
        )
        if user:
            save_login(user["user_ID"], password)
            save_login(user["email"], password)
            query("UPDATE user SET password = %s WHERE user_ID = %s", ("", user["user_ID"]))
    if not user:
        return jsonify(error="Incorrect User ID or Password"), 401
    if not user.get("email_verified", True):
        return jsonify(error="Email address is not verified"), 403
    challenge_id = create_otp(user["email"], "login", user["user_ID"])
    return jsonify(message="A verification code was sent to your email", challenge_id=challenge_id)


@app.post("/api/verify-login")
def verify_login():
    data = request.get_json(silent=True) or {}
    record = valid_otp(data.get("challenge_id", ""), data.get("otp", ""), "login")
    if not record:
        return jsonify(error="Invalid or expired verification code"), 401
    user = query(
        "SELECT user_ID, user_type, name, email, department, bio, personal_phn, discord_id "
        "FROM user WHERE user_ID = %s", (record["user_ID"],),
    )
    protected_fields(user, ("bio", "discord_id"))
    return jsonify(user=user)


@app.post("/api/resend-otp")
def resend_otp_api():
    data = request.get_json(silent=True) or {}
    purpose = data.get("purpose")
    if purpose not in ("login", "registration"):
        return jsonify(error="Invalid OTP purpose"), 400
    new_challenge_id = resend_otp(str(data.get("challenge_id", "")), purpose)
    if not new_challenge_id:
        return jsonify(error="This OTP request is no longer available"), 400
    return jsonify(message="A new verification code was sent to your email", challenge_id=new_challenge_id)


@app.post("/api/register")
def register():
    data = request.get_json(silent=True) or {}
    user_id = str(data.get("user_ID", "")).strip()
    email = str(data.get("email", "")).strip().lower()
    if not user_id or not email or not data.get("password"):
        return jsonify(error="All registration fields are required"), 400
    if query("SELECT user_ID FROM user WHERE user_ID = %s OR email = %s", (user_id, email)):
        return jsonify(error="User ID or email is already registered"), 409
    payload = json.dumps({
        "user_ID": user_id,
        "email": email,
        "password_hash": hash_password(data["password"]),
        "name": str(data.get("name", "")).strip(),
        "department": str(data.get("department", "")).strip().upper(),
    })
    challenge_id = create_otp(email, "registration", payload=payload)
    return jsonify(message="A verification code was sent to your email", challenge_id=challenge_id), 201


@app.post("/api/verify-registration")
def verify_registration():
    data = request.get_json(silent=True) or {}
    record = valid_otp(data.get("challenge_id", ""), data.get("otp", ""), "registration")
    if not record:
        return jsonify(error="Invalid or expired verification code"), 401
    registration = json.loads(record["payload"])
    if query("SELECT user_ID FROM user WHERE user_ID = %s OR email = %s", (registration["user_ID"], registration["email"])):
        return jsonify(error="User ID or email is already registered"), 409
    query(
        "INSERT INTO user (user_ID, email, password, name, department, user_type, email_verified) "
        "VALUES (%s, %s, %s, %s, %s, %s, %s)",
        (registration["user_ID"], registration["email"], registration["password_hash"], registration["name"], registration["department"], "student", 1),
    )
    save_login_hash(registration["user_ID"], registration["password_hash"])
    save_login_hash(registration["email"], registration["password_hash"])
    return jsonify(message="Registration complete. You can now log in.")


@app.get("/api/me")
@authenticated_user
def me(user):
    protected_fields(user, ("bio", "discord_id"))
    return jsonify(user=user)


@app.put("/api/profile")
@authenticated_user
def update_profile(user):
    data = request.get_json(silent=True) or {}
    phone = str(data.get("personal_phn", "")).strip()
    if phone and (not phone.isdigit() or len(phone) != 11):
        return jsonify(error="Phone number must contain exactly 11 digits"), 400
    query(
        "UPDATE user SET personal_phn = %s, discord_id = %s, bio = %s WHERE user_ID = %s",
        (phone or None, encrypt_bulk(data.get("discord_id", "").strip() or None), encrypt_bulk(data.get("bio", "").strip() or None), user["user_ID"]),
    )
    updated = query(
        "SELECT user_ID, user_type, name, email, department, bio, personal_phn, discord_id "
        "FROM user WHERE user_ID = %s",
        (user["user_ID"],),
    )
    protected_fields(updated, ("bio", "discord_id"))
    return jsonify(message="Profile updated successfully!", user=updated)


@app.get("/api/courses")
@authenticated_user
def courses(user):
    return jsonify(courses=query("SELECT courseID FROM courses ORDER BY courseID", many=True))


@app.get("/api/courses/<course_id>")
@authenticated_user
def course_notes(user, course_id):
    course = query(
        "SELECT courseID, title, description FROM courses WHERE courseID = %s",
        (course_id,),
    )
    if not course:
        return jsonify(error="Course not found"), 404
    notes = query(
        "SELECT courseID, noteID, title, student_view FROM notes "
        "WHERE courseID = %s ORDER BY noteID",
        (course_id,),
        many=True,
    )
    protected_fields(course, ("title", "description"))
    return jsonify(course_info=course, notes=protected_rows(notes, ("title", "note")))


@app.get("/api/notes/<int:note_id>")
@authenticated_user
def note(user, note_id):
    result = query(
        "SELECT noteID, courseID, note, title, student_view FROM notes WHERE noteID = %s",
        (note_id,),
    )
    if not result:
        return jsonify(error="Note not found"), 404
    suggestion = query("SELECT noteID FROM note_suggestions WHERE noteID = %s", (note_id,))
    result["have_suggestion"] = bool(suggestion)
    protected_fields(result, ("title", "note"))
    return jsonify(note=result)


@app.get("/api/notes/<int:note_id>/messages")
@authenticated_user
def note_messages(user, note_id):
    context, error = message_context(note_id, user, request.args.get("student_id"))
    if error:
        return error
    if user["user_type"] == "faculty" and "student_ID" not in context:
        participants = query(
            "SELECT DISTINCT m.student_ID AS user_ID, u.name "
            "FROM note_messages m JOIN user u ON u.user_ID = m.student_ID "
            "WHERE m.noteID = %s ORDER BY u.name",
            (note_id,), many=True,
        )
        return jsonify(participants=participants, messages=[])
    rows = query(
        "SELECT m.message_id, m.sender_ID, u.name, m.created_at, "
        "m.ciphertext_for_student, m.ciphertext_for_faculty "
        "FROM note_messages m JOIN user u ON u.user_ID = m.sender_ID "
        "WHERE m.noteID = %s AND m.student_ID = %s ORDER BY m.message_id",
        (note_id, context["student_ID"]), many=True,
    )
    key = user_ecc_key(user["user_ID"])
    ciphertext_field = "ciphertext_for_student" if user["user_type"] == "student" else "ciphertext_for_faculty"
    messages = []
    for row in rows:
        messages.append({
            "message_id": row["message_id"],
            "sender_ID": row["sender_ID"],
            "sender_name": row["name"],
            "created_at": row["created_at"].isoformat(),
            "message": decrypt_with(key.private_key, row[ciphertext_field]),
        })
    return jsonify(participants=[], messages=messages, student_ID=context["student_ID"], faculty_ID=context["faculty_ID"])


@app.post("/api/notes/<int:note_id>/messages")
@authenticated_user
def send_note_message(user, note_id):
    data = request.get_json(silent=True) or {}
    message = str(data.get("message", "")).strip()
    if not message or len(message) > 4000:
        return jsonify(error="Message must contain between 1 and 4000 characters"), 400
    context, error = message_context(note_id, user, data.get("student_id"))
    if error:
        return error
    if "student_ID" not in context:
        return jsonify(error="Select a student conversation first"), 400
    sender_id = user["user_ID"]
    recipient_id = context["faculty_ID"] if user["user_type"] == "student" else context["student_ID"]
    sender_key = user_ecc_key(sender_id)
    recipient_key = user_ecc_key(recipient_id)
    query(
        "INSERT INTO note_messages "
        "(noteID, student_ID, faculty_ID, sender_ID, ciphertext_for_student, ciphertext_for_faculty) "
        "VALUES (%s, %s, %s, %s, %s, %s)",
        (
            note_id, context["student_ID"], context["faculty_ID"], sender_id,
            encrypt_for(sender_key.public_key, message),
            encrypt_for(recipient_key.public_key, message),
        ),
    )
    return jsonify(message="Message sent")


@app.get("/api/notes/<int:note_id>/suggestions/status")
@authenticated_user
def suggestion_status(user, note_id):
    return jsonify(has_suggestion=bool(query("SELECT noteID FROM note_suggestions WHERE noteID = %s", (note_id,))))


@app.get("/api/courses/<course_id>/pending/status")
@authenticated_user
def pending_status(user, course_id):
    return jsonify(has_pending=bool(query("SELECT courseID FROM note_pending WHERE courseID = %s", (course_id,))))


@app.post("/api/notes/<int:note_id>/suggestions")
@authenticated_user
def submit_suggestion(user, note_id):
    data = request.get_json(silent=True) or {}
    suggestion = data.get("suggestion_note", "")
    action = data.get("action")
    original = query("SELECT note, courseID FROM notes WHERE noteID = %s", (note_id,))
    if not original:
        return jsonify(error="Note not found"), 404
    original["note"] = decrypt_bulk(original["note"])
    if not suggestion or suggestion == original["note"]:
        return jsonify(message="No changes, [Not submitted]"), 200
    if action == "saving" and user["user_type"] in ("faculty", "st"):
        query("UPDATE notes SET note = %s WHERE noteID = %s", (encrypt_bulk(suggestion), note_id))
        return jsonify(message="Saved!")
    if action == "suggesting" and user["user_type"] != "alumni":
        query(
            "INSERT INTO note_suggestions (courseID, noteID, suggestion, suggested_by) "
            "VALUES (%s, %s, %s, %s)",
            (original["courseID"], note_id, encrypt_bulk(suggestion), user["user_ID"]),
        )
        return jsonify(message="Suggestion submitted!")
    return jsonify(error="Permission denied"), 403


@app.post("/api/notes/<int:note_id>/visibility")
@authenticated_user
def update_visibility(user, note_id):
    if user["user_type"] != "faculty":
        return jsonify(error="Permission denied"), 403
    visible = int((request.get_json(silent=True) or {}).get("student_view", 0))
    query("UPDATE notes SET student_view = %s WHERE noteID = %s", (visible, note_id))
    return jsonify(message="Status Updated!")


@app.post("/api/notes")
@authenticated_user
def add_note(user):
    data = request.get_json(silent=True) or {}
    if user["user_type"] == "alumni":
        return jsonify(error="Permission denied"), 403
    if user["user_type"] == "faculty":
        query(
            "INSERT INTO notes (courseID, title, note, student_view) VALUES (%s, %s, %s, %s)",
            (data.get("courseID"), encrypt_bulk(data.get("title")), encrypt_bulk(data.get("note")), int(data.get("student_view", 0))),
        )
        return jsonify(message="Note added successfully!")
    query(
        "INSERT INTO note_pending (courseID, title, note, post_by) VALUES (%s, %s, %s, %s)",
        (data.get("courseID"), encrypt_bulk(data.get("title")), encrypt_bulk(data.get("note")), user["user_ID"]),
    )
    return jsonify(message="Note has been submitted for approval.")


@app.post("/api/courses")
@authenticated_user
def add_course(user):
    if user["user_type"] != "faculty":
        return jsonify(error="Permission denied"), 403
    data = request.get_json(silent=True) or {}
    query(
        "INSERT INTO courses (courseID, title, description) VALUES (%s, %s, %s)",
        (str(data.get("courseID", "")).upper(), encrypt_bulk(data.get("title")), encrypt_bulk(data.get("description"))),
    )
    return jsonify(message="Course added successfully!")


if __name__ == "__main__":
    app.run(host="127.0.0.1", port=int(os.getenv("API_PORT", "5000")), debug=True)
