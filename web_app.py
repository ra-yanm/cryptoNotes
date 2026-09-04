import os
import time
from functools import wraps

import requests
from dotenv import load_dotenv
from flask import Flask, flash, redirect, render_template, request, session, url_for
from flask_wtf.csrf import CSRFProtect
from datetime import timedelta
from forms import OTPForm, RegistrationForm


load_dotenv()
app = Flask(__name__, template_folder="templates", static_folder="static")
app.secret_key = os.getenv("WEB_SECRET_KEY")
if not app.secret_key:
    raise RuntimeError("WEB_SECRET_KEY must be set in .env or the environment")
app.config.update(
    SESSION_COOKIE_HTTPONLY=True,
    SESSION_COOKIE_SECURE=os.getenv("SESSION_COOKIE_SECURE", "false").lower() == "true",
    SESSION_COOKIE_SAMESITE="Lax",
    PERMANENT_SESSION_LIFETIME=timedelta(minutes=30),
    WTF_CSRF_TIME_LIMIT=3600,
)
csrf = CSRFProtect(app)
API_URL = os.getenv("API_URL", "http://127.0.0.1:5000/api")


@app.before_request
def enforce_idle_timeout():
    if not session.get("user"):
        return None
    last_activity = session.get("last_activity", 0)
    now = time.time()
    if now - last_activity > app.permanent_session_lifetime.total_seconds():
        session.clear()
        flash("Your session expired. Please log in again.")
        return redirect(url_for("login"))
    session["last_activity"] = now
    session.permanent = True
    return None


@app.after_request
def add_security_headers(response):
    response.headers.setdefault("X-Content-Type-Options", "nosniff")
    response.headers.setdefault("X-Frame-Options", "DENY")
    response.headers.setdefault("Referrer-Policy", "strict-origin-when-cross-origin")
    response.headers.setdefault("Content-Security-Policy", "default-src 'self'; script-src 'self'; style-src 'self' 'unsafe-inline'; object-src 'none'; base-uri 'self'; frame-ancestors 'none'")
    return response


class User:
    def __init__(self, data):
        self.userID = data["user_ID"]
        self.user_type = data["user_type"]

    @property
    def is_authenticated(self):
        return bool(session.get("user"))


@app.context_processor
def inject_user():
    def check_suggestion(note_id):
        result = api_request("GET", f"/notes/{note_id}/suggestions/status")
        return result["has_suggestion"] if result else False

    def check_pending_note(course_id):
        result = api_request("GET", f"/courses/{course_id}/pending/status")
        return result["has_pending"] if result else False

    return {
        "current_user": User(session["user"]) if session.get("user") else User({"user_ID": "", "user_type": ""}),
        "check_suggestion": check_suggestion,
        "check_pending_note": check_pending_note,
    }


def api_request(method, path, **kwargs):
    headers = kwargs.pop("headers", {})
    if session.get("user"):
        headers["X-User-ID"] = session["user"]["user_ID"]
    try:
        response = requests.request(method, f"{API_URL}{path}", headers=headers, timeout=5, **kwargs)
    except requests.RequestException:
        flash("The data server is unavailable.")
        return None
    if response.status_code >= 400:
        flash(response.json().get("error", "Request failed."))
        return None
    return response.json()


def login_required(view):
    @wraps(view)
    def wrapped(*args, **kwargs):
        if not session.get("user"):
            return redirect(url_for("login"))
        return view(*args, **kwargs)

    return wrapped


@app.route("/")
def first_page():
    return redirect(url_for("home" if session.get("user") else "login"))


@app.route("/login", methods=["GET", "POST"])
def login():
    if session.get("user"):
        return redirect(url_for("home"))
    if request.method == "GET":
        return render_template("login.html")
    result = api_request("POST", "/login", json={"userID": request.form["userID"], "password": request.form["password"]})
    if not result:
        return redirect(url_for("login"))
    session["login_challenge"] = result["challenge_id"]
    return redirect(url_for("verify_login"))


@app.route("/register", methods=["GET", "POST"])
def register():
    if session.get("user"):
        return redirect(url_for("home"))
    form = RegistrationForm()
    if form.validate_on_submit():
        result = api_request("POST", "/register", json={
            "user_ID": form.user_id.data,
            "email": form.email.data,
            "name": form.name.data,
            "department": form.department.data,
            "password": form.password.data,
        })
        if result:
            session["registration_challenge"] = result["challenge_id"]
            return redirect(url_for("verify_registration"))
    return render_template("register.html", form=form)


@app.route("/verify-registration", methods=["GET", "POST"])
def verify_registration():
    form = OTPForm()
    if not session.get("registration_challenge"):
        return redirect(url_for("register"))
    if form.validate_on_submit():
        result = api_request("POST", "/verify-registration", json={
            "challenge_id": session["registration_challenge"], "otp": form.otp.data,
        })
        if result:
            session.pop("registration_challenge", None)
            flash(result["message"])
            return redirect(url_for("login"))
    return render_template("verify_otp.html", form=form, title="Verify your email")


@app.post("/resend-otp")
def resend_otp():
    if session.get("login_challenge"):
        session_key = "login_challenge"
        purpose = "login"
        destination = "verify_login"
    elif session.get("registration_challenge"):
        session_key = "registration_challenge"
        purpose = "registration"
        destination = "verify_registration"
    else:
        return redirect(url_for("login"))
    result = api_request("POST", "/resend-otp", json={
        "challenge_id": session[session_key], "purpose": purpose,
    })
    if result:
        session[session_key] = result["challenge_id"]
        flash(result["message"])
    return redirect(url_for(destination))


@app.route("/verify-login", methods=["GET", "POST"])
def verify_login():
    form = OTPForm()
    if not session.get("login_challenge"):
        return redirect(url_for("login"))
    if form.validate_on_submit():
        result = api_request("POST", "/verify-login", json={
            "challenge_id": session["login_challenge"], "otp": form.otp.data,
        })
        if result:
            session.pop("login_challenge", None)
            session.clear()
            session.permanent = True
            session["last_activity"] = time.time()
            session["user"] = result["user"]
            flash("Logged in successfully!")
            return redirect(url_for("home"))
    return render_template("verify_otp.html", form=form, title="Verify login")


@app.get("/logout")
def logout():
    session.clear()
    flash("Logged out.")
    return redirect(url_for("login"))


@app.get("/home")
@login_required
def home():
    return render_template("home.html", user_name=session["user"].get("name", session["user"]["user_ID"]))


@app.route("/profile", methods=["GET", "POST"])
@login_required
def profile():
    if request.method == "POST":
        result = api_request("PUT", "/profile", json={
            "personal_phn": request.form.get("personal_phn", ""),
            "discord_id": request.form.get("discord_id", ""),
            "bio": request.form.get("bio", ""),
        })
        if result:
            session["user"] = result["user"]
            flash(result["message"])
        return redirect(url_for("profile"))
    result = api_request("GET", "/me")
    return render_template("profile.html", profile=result["user"] if result else session["user"])


@app.get("/notes")
@login_required
def notes():
    course_id = request.args.get("course")
    note_id = request.args.get("L")
    if note_id:
        result = api_request("GET", f"/notes/{note_id}")
        message_result = api_request(
            "GET", f"/notes/{note_id}/messages",
            params={"student_id": request.args.get("student")} if request.args.get("student") else {},
        ) if result else None
        return render_template(
            "note.html",
            notes=result["note"] if result else None,
            have_suggestion=result["note"].get("have_suggestion", False) if result else False,
            course=course_id,
            noteID=note_id,
            message_data=message_result or {"messages": [], "participants": []},
            selected_student=request.args.get("student", ""),
        )
    if course_id:
        result = api_request("GET", f"/courses/{course_id}")
        if not result:
            return redirect(url_for("notes"))
        return render_template("all_note.html", **result, course=course_id)
    result = api_request("GET", "/courses")
    return render_template("all_note.html", courses=result["courses"] if result else [])


@app.route("/add_note", methods=["GET", "POST"])
@login_required
def add_note():
    if request.method == "GET":
        result = api_request("GET", "/courses")
        return render_template("add_note.html", courses=result["courses"] if result else [])
    result = api_request("POST", "/notes", json={"courseID": request.form["courseID"], "title": request.form["title"], "note": request.form["note"], "student_view": request.form.get("student_view", 0)})
    if result:
        flash(result["message"])
    return redirect(url_for("notes", course=request.form["courseID"]))


@app.post("/submit_suggestion")
@login_required
def submit_suggestion():
    result = api_request("POST", f"/notes/{request.form['noteID']}/suggestions", json={"suggestion_note": request.form["suggestion_note"], "action": request.form["buttton"]})
    if result:
        flash(result.get("message", "Request complete."))
    return redirect(url_for("notes", course=request.form["course"], L=request.form["noteID"]))


@app.post("/send_message")
@login_required
def send_message():
    note_id = request.form["noteID"]
    result = api_request(
        "POST", f"/notes/{note_id}/messages",
        json={"message": request.form["message"], "student_id": request.form.get("student_id")},
    )
    if result:
        flash(result["message"])
    return redirect(url_for("notes", course=request.form["course"], L=note_id, student=request.form.get("student_id", "")))


@app.post("/hide_note")
@login_required
def hide_note():
    result = api_request("POST", f"/notes/{request.form['noteID']}/visibility", json={"student_view": request.form["hide"]})
    if result:
        flash(result["message"])
    return redirect(url_for("notes", course=request.form["course"], L=request.form["noteID"]))


@app.route("/add_course", methods=["GET", "POST"])
@login_required
def add_course():
    if request.method == "GET":
        return render_template("add_course.html")
    result = api_request("POST", "/courses", json={"courseID": request.form["courseID"], "title": request.form["title"], "description": request.form["descriptons"]})
    if result:
        flash(result["message"])
    return redirect(url_for("notes"))


if __name__ == "__main__":
    app.run(host="127.0.0.1", port=int(os.getenv("WEB_PORT", "5001")), debug=True)
