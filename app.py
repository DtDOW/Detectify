# app.py
import os
import uuid
from flask import Flask, request, render_template, jsonify, redirect, url_for, flash
from werkzeug.utils import secure_filename
from werkzeug.security import generate_password_hash, check_password_hash

from models1 import db, User
from flask_login import LoginManager, login_user, logout_user, login_required, current_user

from detect1 import predict_video_file   # your existing joblib-based detect.py

# CONFIG
BASE_DIR = os.path.dirname(__file__)
UPLOAD_FOLDER = os.path.join(BASE_DIR, "uploads")
os.makedirs(UPLOAD_FOLDER, exist_ok=True)
ALLOWED_EXTENSIONS = {".mp4", ".mov", ".avi", ".mkv", ".gif", ".jpeg", ".jpg", ".png"}
MAX_CONTENT_LENGTH = 500 * 1024 * 1024  # 500 MB upload limit, adjust as needed

app = Flask(__name__, static_folder="static", template_folder="templates")
app.config["UPLOAD_FOLDER"] = UPLOAD_FOLDER
app.config["MAX_CONTENT_LENGTH"] = MAX_CONTENT_LENGTH
app.config["SQLALCHEMY_DATABASE_URI"] = "sqlite:///" + os.path.join(BASE_DIR, "users.db")
app.config["SQLALCHEMY_TRACK_MODIFICATIONS"] = False
app.config["SECRET_KEY"] = os.environ.get("DETECTIFY_SECRET") or "change-this-secret-in-prod"

# initialize extensions
db.init_app(app)
login_manager = LoginManager()
login_manager.init_app(app)
login_manager.login_view = "login"

@login_manager.user_loader
def load_user(user_id):
    try:
        return User.query.get(int(user_id))
    except Exception:
        return None

#def allowed_file(filename):
   # _, ext = os.path.splitext(filename.lower())
   # return ext in ALLOWED_EXTENSIONS

#@app.before_first_request
#def create_tables():
   # db.create_all()

def allowed_file(filename):
    """Return True if filename has an allowed extension."""
    if not filename:
        return False
    _, ext = os.path.splitext(filename.lower())
    return ext in ALLOWED_EXTENSIONS

with app.app_context():
    try:
        User.__table__.create(db.engine, checkfirst=True)
        Prediction.__table__.create(db.engine, checkfirst=True)
    except Exception:
        pass


# --- Pages & API ---
@app.route("/")
def index():
    # render index with authentication context
    return render_template("index.html")

@app.route("/upload", methods=["POST"])
def upload_and_predict():
    if "file" not in request.files:
        return jsonify({"success": False, "error": "No file part"}), 400

    f = request.files["file"]
    if f.filename == "":
        return jsonify({"success": False, "error": "No selected file"}), 400

    if not allowed_file(f.filename):
        return jsonify({"success": False, "error": "Invalid file type"}), 400

    # Save file
    filename = secure_filename(f.filename)
    unique_name = f"{uuid.uuid4().hex}_{filename}"
    save_path = os.path.join(app.config["UPLOAD_FOLDER"], unique_name)
    f.save(save_path)

    try:
        label, prob = predict_video_file(save_path)
        result = {
            "success": True,
            "label": label,
            "confidence": round(prob * 100, 2)
        }
        # optional: remove file after prediction to save space
        try:
            os.remove(save_path)
        except Exception:
            pass
        return jsonify(result)
    except Exception as e:
        # Clean up and return error
        try:
            os.remove(save_path)
        except Exception:
            pass
        return jsonify({"success": False, "error": str(e)}), 500

# --- Authentication routes ---
@app.route("/signup", methods=["GET", "POST"])
def signup():
    if request.method == "POST":
        email = request.form.get("email", "").strip().lower()
        password = request.form.get("password", "")

        if not email or not password:
            flash("Email and password required.", "error")
            return redirect(url_for("signup"))

        # check duplicate
        if User.query.filter_by(email=email).first():
            flash("User already exists. Please login.", "error")
            return redirect(url_for("login"))

        hashed_pw = generate_password_hash(password)
        new_user = User(email=email, password=hashed_pw)
        db.session.add(new_user)
        db.session.commit()

        flash("Signup successful — please login.", "success")
        return redirect(url_for("login"))

    return render_template("signup.html")

@app.route("/login", methods=["GET", "POST"])
def login():
    if request.method == "POST":
        email = request.form.get("email", "").strip().lower()
        password = request.form.get("password", "")

        user = User.query.filter_by(email=email).first()
        if not user or not check_password_hash(user.password, password):
            flash("Invalid credentials.", "error")
            return redirect(url_for("login"))

        login_user(user)
        flash("Logged in successfully.", "success")
        next_page = request.args.get("next")
        return redirect(next_page or url_for("index"))

    return render_template("login.html")

@app.route("/logout")
@login_required
def logout():
    logout_user()
    flash("Logged out.", "info")
    return redirect(url_for("index"))

# health check
@app.route("/ping")
def ping():
    return "pong", 200

if __name__ == "__main__":
    # local dev only
    app.run(host="0.0.0.0", port=5000, threaded=True, debug=True)
