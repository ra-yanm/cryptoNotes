import os
from functools import wraps
from flask import Flask, jsonify, request


app = Flask(__name__)


def get_db():
    import mysql.connector

    return mysql.connector.connect(
        host=os.getenv("DB_HOST", "localhost"),
        user=os.getenv("DB_USER", "db447"),
        password=os.getenv("DB_PASSWORD", "db447"),
        database=os.getenv("DB_NAME", "flaskDB447"),
    )


def query(sql, params=(), many=False):
    db = get_db()
    cursor = db.cursor(dictionary=True)
    try:
        cursor.execute(sql, params)
        result = cursor.fetchall() if many else cursor.fetchone()
        db.commit()
        return result
    finally:
        cursor.close()
        db.close()


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
    user = query(
        "SELECT user_ID, user_type, name, email, department, bio, personal_phn, discord_id FROM user "
        "WHERE (user_ID = %s OR email = %s) AND password = %s",
        (identity, identity, password),
    )
    if not user:
        return jsonify(error="Incorrect User ID or Password"), 401
    return jsonify(user=user)


@app.get("/api/me")
@authenticated_user
def me(user):
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
        (phone or None, data.get("discord_id", "").strip() or None, data.get("bio", "").strip() or None, user["user_ID"]),
    )
    updated = query(
        "SELECT user_ID, user_type, name, email, department, bio, personal_phn, discord_id "
        "FROM user WHERE user_ID = %s",
        (user["user_ID"],),
    )
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
    return jsonify(course_info=course, notes=notes)


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
    return jsonify(note=result)


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
    if not suggestion or suggestion == original["note"]:
        return jsonify(message="No changes, [Not submitted]"), 200
    if action == "saving" and user["user_type"] in ("faculty", "st"):
        query("UPDATE notes SET note = %s WHERE noteID = %s", (suggestion, note_id))
        return jsonify(message="Saved!")
    if action == "suggesting" and user["user_type"] != "alumni":
        query(
            "INSERT INTO note_suggestions (courseID, noteID, suggestion, suggested_by) "
            "VALUES (%s, %s, %s, %s)",
            (original["courseID"], note_id, suggestion, user["user_ID"]),
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
            (data.get("courseID"), data.get("title"), data.get("note"), int(data.get("student_view", 0))),
        )
        return jsonify(message="Note added successfully!")
    query(
        "INSERT INTO note_pending (courseID, title, note, post_by) VALUES (%s, %s, %s, %s)",
        (data.get("courseID"), data.get("title"), data.get("note"), user["user_ID"]),
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
        (str(data.get("courseID", "")).upper(), data.get("title"), data.get("description")),
    )
    return jsonify(message="Course added successfully!")


if __name__ == "__main__":
    app.run(host="127.0.0.1", port=int(os.getenv("API_PORT", "5000")), debug=True)
