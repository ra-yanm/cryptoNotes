import os
from functools import wraps

import requests
from flask import Flask, flash, redirect, render_template, request, session, url_for


app = Flask(__name__, template_folder="templates", static_folder="static")
app.secret_key = os.getenv("WEB_SECRET_KEY", "change-this-secret")
API_URL = os.getenv("API_URL", "http://127.0.0.1:5000/api")


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
    session["user"] = result["user"]
    flash("Logged in successfully!")
    return redirect(url_for("home"))


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
        return render_template("note.html", notes=result["note"] if result else None, have_suggestion=result["note"].get("have_suggestion", False) if result else False, course=course_id, noteID=note_id)
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
