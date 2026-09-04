import os
import hashlib
import json
import secrets
import threading
from datetime import datetime, timedelta
from functools import wraps
from dotenv import load_dotenv
from flask import Flask, jsonify, request
import bcrypt
from flask_mailman import EmailMessage, Mail
from key_management import (
    decrypt_bulk,
    decrypt_user_field,
    encrypt_bulk,
    encrypt_bulk_with_key,
    encrypt_user_field,
    rotate_ecc_key,
)
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
_ecc_rotation_lock = threading.Lock()
ADMIN_USER_ID = "admin"
ADMIN_PASSWORD = "admin12345"
ADMIN_EMAIL = "admin@cryptonotes.local"


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
    cursor = db.cursor(dictionary=True, buffered=True)
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
        CREATE TABLE IF NOT EXISTS admins (
            admin_ID VARCHAR(20) PRIMARY KEY,
            email VARCHAR(254) NOT NULL UNIQUE,
            password TEXT NOT NULL,
            name VARCHAR(100) NOT NULL,
            created_at DATETIME NOT NULL DEFAULT CURRENT_TIMESTAMP
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
    cursor.execute("ALTER TABLE user MODIFY name TEXT NOT NULL, MODIFY department TEXT NOT NULL")
    admin_hash = hash_password(ADMIN_PASSWORD)
    cursor.execute(
        "INSERT INTO admins (admin_ID, email, password, name) VALUES (%s, %s, %s, %s) "
        "ON DUPLICATE KEY UPDATE email = VALUES(email), password = VALUES(password), name = VALUES(name)",
        (ADMIN_USER_ID, ADMIN_EMAIL, admin_hash, "Administrator"),
    )
    cursor.execute("DELETE FROM user WHERE user_ID = %s", (ADMIN_USER_ID,))
    cursor.execute("SELECT user_ID, name, department, bio, personal_phn, discord_id FROM user")
    fields = ("name", "department", "bio", "personal_phn", "discord_id")
    for row in cursor.fetchall():
        encrypted_values = []
        for field in fields:
            raw_value = row[field]
            if isinstance(raw_value, str) and raw_value.startswith('{"version":2'):
                encrypted_values.append(raw_value)
            else:
                encrypted_values.append(encrypt_user_field(decrypt_user_field(raw_value)))
        if any(row[field] != value for field, value in zip(fields, encrypted_values)):
            cursor.execute(
                "UPDATE user SET name = %s, department = %s, bio = %s, personal_phn = %s, discord_id = %s WHERE user_ID = %s",
                (*encrypted_values, row["user_ID"]),
            )
    content_fields = (
        ("courses", "courseID", ("title", "description")),
        ("notes", "noteID", ("title", "note")),
        ("note_pending", "ID", ("title", "note")),
        ("note_suggestions", "suggestionID", ("suggestion",)),
    )
    for table, key_field, fields in content_fields:
        cursor.execute(f"SELECT {key_field}, {', '.join(fields)} FROM {table}")
        for row in cursor.fetchall():
            encrypted_values = []
            changed = False
            for field in fields:
                raw_value = row[field]
                if raw_value is None or (isinstance(raw_value, str) and raw_value.startswith('{"ephemeral":')):
                    encrypted_values.append(raw_value)
                else:
                    encrypted_values.append(encrypt_bulk(raw_value))
                    changed = True
            if changed:
                assignments = ", ".join(f"{field} = %s" for field in fields)
                cursor.execute(
                    f"UPDATE {table} SET {assignments} WHERE {key_field} = %s",
                    (*encrypted_values, row[key_field]),
                )
    db.commit()
    cursor.close()
    _secure_storage_ready = True


def query(sql, params=(), many=False):
    db = get_db()
    ensure_secure_storage(db)
    cursor = db.cursor(dictionary=True, buffered=True)
    try:
        cursor.execute(sql, params)
        statement = sql.lstrip().upper()
        is_read = statement.startswith(("SELECT", "SHOW", "DESCRIBE", "EXPLAIN"))
        result = (cursor.fetchall() if many else cursor.fetchone()) if is_read else None
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
            row[field] = decrypt_user_field(row[field])
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
    try:
        private_key = int(decrypt_bulk(record["encrypted_private_key"]))
        return ECC(private_key=private_key)
    except (ValueError, TypeError):
        # Imported databases may contain keys encrypted with another local key set.
        key = ECC()
        query(
            "UPDATE user_ecc_keys SET public_key = %s, encrypted_private_key = %s WHERE user_ID = %s",
            (json.dumps(list(key.public_key)), encrypt_bulk(str(key.private_key)), user_id),
        )
        return key


def message_context(note_id, user, student_id=None):
    context = query(
        "SELECT n.courseID, c.coordinator, coordinator.name AS coordinator_name, n.student_view "
        "FROM notes n JOIN courses c ON c.courseID = n.courseID "
        "JOIN user coordinator ON coordinator.user_ID = c.coordinator "
        "WHERE n.noteID = %s",
        (note_id,),
    )
    if not context:
        return None, (jsonify(error="Note not found"), 404)
    context["coordinator_name"] = decrypt_user_field(context["coordinator_name"])
    if user["user_type"] in ("faculty", "admin"):
        if context["coordinator"] != user["user_ID"]:
            return None, (jsonify(error="Only the course coordinator may access these messages"), 403)
        if not student_id:
            return context, None
    elif user["user_type"] in ("student", "st"):
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


def purge_expired_otps():
    query("DELETE FROM account_otp WHERE expires_at <= %s", (datetime.utcnow(),))


def create_otp(email, purpose, user_id=None, payload=None):
    purge_expired_otps()
    challenge_id = secrets.token_hex(32)
    otp = f"{secrets.randbelow(1000000):06d}"
    query(
        "INSERT INTO account_otp (challenge_id, user_ID, email, purpose, otp_hash, payload, expires_at) "
        "VALUES (%s, %s, %s, %s, %s, %s, %s)",
        (challenge_id, user_id, email, purpose, hashlib.sha256(otp.encode()).hexdigest(), payload,
         datetime.utcnow() + timedelta(minutes=5)),
    )
    subject = "Your CrytoNotes verification code"
    message = EmailMessage(
        subject=subject,
        body=f"Your {purpose} verification code is {otp}. It expires in 5 minutes.",
        to=[email],
    )
    message.send()
    return challenge_id


def resend_otp(challenge_id, purpose):
    purge_expired_otps()
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
    query("DELETE FROM account_otp WHERE challenge_id = %s", (challenge_id,))
    return new_challenge_id


def valid_otp(challenge_id, otp, purpose):
    purge_expired_otps()
    record = query(
        "SELECT * FROM account_otp WHERE challenge_id = %s AND purpose = %s AND used_at IS NULL",
        (challenge_id, purpose),
    )
    if not record:
        return None
    if not secrets.compare_digest(record["otp_hash"], hashlib.sha256(otp.encode()).hexdigest()):
        return None
    query("DELETE FROM account_otp WHERE challenge_id = %s", (challenge_id,))
    return record


def password_hash_from_storage(value):
    return value


def authenticated_user(view):
    @wraps(view)
    def wrapped(*args, **kwargs):
        user_id = request.headers.get("X-User-ID")
        if not user_id:
            return jsonify(error="Authentication required"), 401
        user = query(
            "SELECT admin_ID AS user_ID, 'admin' AS user_type, name, email, "
            "NULL AS department, NULL AS bio, NULL AS personal_phn, NULL AS discord_id "
            "FROM admins WHERE admin_ID = %s",
            (user_id,),
        )
        if not user:
            user = query(
                "SELECT user_ID, user_type, name, email, department, bio, personal_phn, discord_id "
                "FROM user WHERE user_ID = %s",
                (user_id,),
            )
        if not user:
            return jsonify(error="User not found"), 401
        protected_fields(user, ("name", "department", "bio", "personal_phn", "discord_id"))
        return view(user, *args, **kwargs)

    return wrapped


def admin_only(view):
    @wraps(view)
    @authenticated_user
    def wrapped(user, *args, **kwargs):
        if user["user_type"] != "admin":
            return jsonify(error="Administrator access required"), 403
        return view(user, *args, **kwargs)

    return wrapped


def faculty_access(user):
    return user["user_type"] in ("faculty", "admin")


@app.post("/api/login")
def login():
    data = request.get_json(silent=True) or {}
    identity = data.get("userID", "")
    password = data.get("password", "")
    admin_record = query(
        "SELECT admin_ID AS user_ID, 'admin' AS user_type, name, email, password, "
        "NULL AS department, NULL AS bio, NULL AS personal_phn, NULL AS discord_id "
        "FROM admins WHERE admin_ID = %s OR email = %s",
        (identity, identity),
    )
    if admin_record and check_password(password, admin_record.pop("password")):
        admin = admin_record
        return jsonify(user=admin, message="Administrator login successful")
    user = query(
        "SELECT user_ID, user_type, name, email, department, bio, personal_phn, discord_id, email_verified, password "
        "FROM user WHERE user_ID = %s OR email = %s",
        (identity, identity),
    )
    if user:
        try:
            stored_password = user["password"]
            password_hash = password_hash_from_storage(stored_password)
            user_matches = bool(password_hash and password_hash.startswith("$2") and check_password(password, password_hash))
        except (ValueError, TypeError):
            user_matches = False
        if not user_matches:
            user = None
        else:
            user.pop("password", None)
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
    protected_fields(user, ("name", "department", "bio", "personal_phn", "discord_id"))
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
        (registration["user_ID"], registration["email"], registration["password_hash"], encrypt_user_field(registration["name"]), encrypt_user_field(registration["department"]), "student", 1),
    )
    return jsonify(message="Registration complete. You can now log in.")


@app.get("/api/me")
@authenticated_user
def me(user):
    protected_fields(user, ("name", "department", "bio", "personal_phn", "discord_id"))
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
        (encrypt_user_field(phone or None), encrypt_user_field(data.get("discord_id", "").strip() or None), encrypt_user_field(data.get("bio", "").strip() or None), user["user_ID"]),
    )
    updated = query(
        "SELECT user_ID, user_type, name, email, department, bio, personal_phn, discord_id "
        "FROM user WHERE user_ID = %s",
        (user["user_ID"],),
    )
    protected_fields(updated, ("name", "department", "bio", "personal_phn", "discord_id"))
    return jsonify(message="Profile updated successfully!", user=updated)


@app.get("/api/admin/users")
@admin_only
def admin_users(user):
    users = query(
        "SELECT user_ID, name, email, department, user_type, created_at FROM user ORDER BY created_at DESC, user_ID",
        many=True,
    )
    protected_rows(users, ("name", "department"))
    return jsonify(users=users, roles=["student", "faculty", "alumni", "st"])


@app.put("/api/admin/users/<user_id>/role")
@admin_only
def admin_update_role(admin, user_id):
    data = request.get_json(silent=True) or {}
    role = str(data.get("user_type", "")).strip().lower()
    if role not in ("student", "faculty", "alumni", "st"):
        return jsonify(error="Invalid user type"), 400
    if user_id == ADMIN_USER_ID:
        return jsonify(error="The administrator role cannot be changed"), 400
    if not query("SELECT user_ID FROM user WHERE user_ID = %s", (user_id,)):
        return jsonify(error="User not found"), 404
    query("UPDATE user SET user_type = %s WHERE user_ID = %s", (role, user_id))
    return jsonify(message="User type updated successfully")


@app.put("/api/admin/courses/<course_id>/coordinator")
@admin_only
def admin_assign_coordinator(admin, course_id):
    data = request.get_json(silent=True) or {}
    coordinator = str(data.get("user_ID", "")).strip()
    if not query("SELECT courseID FROM courses WHERE courseID = %s", (course_id,)):
        return jsonify(error="Course not found"), 404
    if not query("SELECT user_ID FROM user WHERE user_ID = %s AND user_type = 'faculty'", (coordinator,)):
        return jsonify(error="A faculty user must be selected as coordinator"), 400
    query("UPDATE courses SET coordinator = %s WHERE courseID = %s", (coordinator, course_id))
    return jsonify(message="Course coordinator updated successfully")


@app.post("/api/admin/rotate-ecc")
@admin_only
def admin_rotate_ecc(admin):
    """Rotate the application ECC key and migrate all bulk ciphertext."""
    if not _ecc_rotation_lock.acquire(blocking=False):
        return jsonify(error="An ECC key rotation is already in progress"), 409
    try:
        new_key_id = rotate_ecc_key()
        migrated = 0
        content_fields = (
            ("courses", "courseID", ("title", "description")),
            ("notes", "noteID", ("title", "note")),
            ("note_pending", "ID", ("title", "note")),
            ("note_suggestions", "suggestionID", ("suggestion",)),
        )
        for table, key_field, fields in content_fields:
            rows = query(
                f"SELECT {key_field}, {', '.join(fields)} FROM {table}",
                many=True,
            )
            for row in rows:
                for field in fields:
                    if row[field] is None:
                        continue
                    plaintext = decrypt_bulk(row[field])
                    query(
                        f"UPDATE {table} SET {field} = %s WHERE {key_field} = %s",
                        (encrypt_bulk_with_key(plaintext, new_key_id), row[key_field]),
                    )
                    migrated += 1

        user_keys = query(
            "SELECT user_ID, encrypted_private_key FROM user_ecc_keys",
            many=True,
        )
        for row in user_keys:
            private_key = decrypt_bulk(row["encrypted_private_key"])
            query(
                "UPDATE user_ecc_keys SET encrypted_private_key = %s WHERE user_ID = %s",
                (encrypt_bulk_with_key(private_key, new_key_id), row["user_ID"]),
            )
            migrated += 1
        return jsonify(message="ECC key rotation completed", key_id=new_key_id, migrated=migrated)
    except Exception:
        app.logger.exception("ECC key rotation did not complete")
        return jsonify(error="ECC key rotation did not complete; both key versions were retained"), 500
    finally:
        _ecc_rotation_lock.release()


@app.get("/api/courses")
@authenticated_user
def courses(user):
    return jsonify(courses=query("SELECT courseID, coordinator FROM courses ORDER BY courseID", many=True))


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
        "SELECT n.noteID, n.courseID, n.note, n.title, n.student_view, c.coordinator "
        "FROM notes n JOIN courses c ON c.courseID = n.courseID WHERE n.noteID = %s",
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
    if faculty_access(user) and "student_ID" not in context:
        participants = query(
            "SELECT DISTINCT m.student_ID AS user_ID, u.name "
            "FROM note_messages m JOIN user u ON u.user_ID = m.student_ID "
            "WHERE m.noteID = %s ORDER BY u.name",
            (note_id,), many=True,
        )
        protected_rows(participants, ("name",))
        return jsonify(
            participants=participants,
            messages=[],
            coordinator_name=context["coordinator_name"],
            can_message=True,
        )
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
            "sender_name": decrypt_user_field(row["name"]),
            "created_at": row["created_at"].isoformat(),
            "message": decrypt_with(key.private_key, row[ciphertext_field]),
        })
    return jsonify(
        participants=[],
        messages=messages,
        student_ID=context["student_ID"],
        faculty_ID=context["faculty_ID"],
        coordinator_name=context["coordinator_name"],
        can_message=True,
    )


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


@app.get("/api/notes/<int:note_id>/suggestions")
@authenticated_user
def note_suggestions(user, note_id):
    note = query("SELECT noteID, courseID, title, note FROM notes WHERE noteID = %s", (note_id,))
    if not note:
        return jsonify(error="Note not found"), 404
    suggestions = query(
        "SELECT suggestionID, suggestion, suggested_by FROM note_suggestions "
        "WHERE noteID = %s ORDER BY suggestionID",
        (note_id,), many=True,
    )
    protected_fields(note, ("title", "note"))
    protected_rows(suggestions, ("suggestion",))
    return jsonify(note=note, suggestions=suggestions)


@app.post("/api/notes/<int:note_id>/suggestions/review")
@authenticated_user
def review_suggestion(user, note_id):
    if not faculty_access(user):
        return jsonify(error="Only faculty may review suggestions"), 403
    data = request.get_json(silent=True) or {}
    action = data.get("action")
    if action not in ("approve", "reject"):
        return jsonify(error="Invalid suggestion action"), 400
    suggestion = query(
        "SELECT suggestionID, suggestion FROM note_suggestions WHERE suggestionID = %s AND noteID = %s",
        (data.get("suggestionID"), note_id),
    )
    if not suggestion:
        return jsonify(error="Suggestion not found"), 404
    if action == "approve":
        query("UPDATE notes SET note = %s WHERE noteID = %s", (decrypt_bulk(suggestion["suggestion"]), note_id))
    query("DELETE FROM note_suggestions WHERE suggestionID = %s", (suggestion["suggestionID"],))
    return jsonify(message="Suggestion approved" if action == "approve" else "Suggestion rejected")


@app.get("/api/courses/<course_id>/pending/status")
@authenticated_user
def pending_status(user, course_id):
    return jsonify(has_pending=bool(query("SELECT courseID FROM note_pending WHERE courseID = %s", (course_id,))))


@app.get("/api/courses/<course_id>/pending")
@authenticated_user
def pending_notes(user, course_id):
    if user["user_type"] != "faculty":
        return jsonify(error="Only faculty may review pending notes"), 403
    pending = query(
        "SELECT ID, courseID, title, note, post_by FROM note_pending "
        "WHERE courseID = %s ORDER BY ID",
        (course_id,), many=True,
    )
    protected_rows(pending, ("title", "note"))
    return jsonify(pending=pending)


@app.post("/api/courses/<course_id>/pending/review")
@authenticated_user
def review_pending_note(user, course_id):
    if user["user_type"] != "faculty":
        return jsonify(error="Only faculty may review pending notes"), 403
    data = request.get_json(silent=True) or {}
    action = data.get("action")
    if action not in ("approve", "reject"):
        return jsonify(error="Invalid pending-note action"), 400
    pending = query(
        "SELECT ID, courseID, title, note FROM note_pending "
        "WHERE ID = %s AND courseID = %s",
        (data.get("pending_ID"), course_id),
    )
    if not pending:
        return jsonify(error="Pending note not found"), 404
    if action == "approve":
        query(
            "INSERT INTO notes (courseID, title, note, student_view) VALUES (%s, %s, %s, %s)",
            (course_id, pending["title"], pending["note"], 1),
        )
    query("DELETE FROM note_pending WHERE ID = %s", (pending["ID"],))
    return jsonify(message="Note approved" if action == "approve" else "Note rejected")


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
    if action == "saving" and faculty_access(user):
        query("UPDATE notes SET note = %s WHERE noteID = %s", (encrypt_bulk(suggestion), note_id))
        return jsonify(message="Saved!")
    if action == "suggesting" and user["user_type"] in ("student", "st", "faculty"):
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
    if not faculty_access(user):
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
    if faculty_access(user):
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
    if not faculty_access(user):
        return jsonify(error="Permission denied"), 403
    data = request.get_json(silent=True) or {}
    query(
        "INSERT INTO courses (courseID, title, description) VALUES (%s, %s, %s)",
        (str(data.get("courseID", "")).upper(), encrypt_bulk(data.get("title")), encrypt_bulk(data.get("description"))),
    )
    return jsonify(message="Course added successfully!")


if __name__ == "__main__":
    app.run(host="127.0.0.1", port=int(os.getenv("API_PORT", "5000")), debug=True)
