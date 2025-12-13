import os
import sqlite3
import sys
from flask import Flask, render_template, request, jsonify, g, redirect, url_for, flash
from werkzeug.utils import secure_filename
from werkzeug.security import generate_password_hash, check_password_hash

from flask_login import LoginManager, login_user, logout_user, login_required, UserMixin

# YOLO detection
sys.path.append(os.path.join(os.path.dirname(__file__), "utils"))
from detection import average_people_in_video

BASE_DIR = os.path.dirname(__file__)
DATABASE = os.path.join(BASE_DIR, "data.sqlite")

IMAGE_UPLOAD_FOLDER = os.path.join(BASE_DIR, "static", "uploads", "images")
VIDEO_UPLOAD_FOLDER = os.path.join(BASE_DIR, "static", "uploads", "videos")
os.makedirs(IMAGE_UPLOAD_FOLDER, exist_ok=True)
os.makedirs(VIDEO_UPLOAD_FOLDER, exist_ok=True)

ALLOWED_IMAGE_EXT = {"png", "jpg", "jpeg", "gif"}
ALLOWED_VIDEO_EXT = {"mp4", "mov", "avi", "mkv"}

app = Flask(__name__, static_url_path="/static")
app.secret_key = "dev-secret-change-this"

login_manager = LoginManager(app)
login_manager.login_view = "admin_login"


# -------------------------
# DB HELPERS
# -------------------------
def get_db():
    if "_db" not in g:
        g._db = sqlite3.connect(DATABASE)
        g._db.row_factory = sqlite3.Row
    return g._db


@app.teardown_appcontext
def close_db(exc):
    db = g.pop("_db", None)
    if db:
        db.close()


# -------------------------
# INIT + MIGRATION
# -------------------------
def init_db():
    db = get_db()

    db.execute("""
        CREATE TABLE IF NOT EXISTS main_locations (
            id INTEGER PRIMARY KEY AUTOINCREMENT,
            name TEXT,
            capacity INTEGER,
            image TEXT,
            address TEXT
        )
    """)

    db.execute("""
        CREATE TABLE IF NOT EXISTS sub_locations (
            id INTEGER PRIMARY KEY AUTOINCREMENT,
            main_location_id INTEGER,
            name TEXT,
            capacity INTEGER,
            image TEXT,
            video TEXT,
            FOREIGN KEY (main_location_id) REFERENCES main_locations(id)
        )
    """)

    db.execute("""
        CREATE TABLE IF NOT EXISTS status (
            id INTEGER PRIMARY KEY,
            location_name TEXT,
            average_people INTEGER,
            capacity INTEGER,
            percent REAL,
            level TEXT,
            updated_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP
        )
    """)

    db.execute("""
        CREATE TABLE IF NOT EXISTS admin_users (
            username TEXT PRIMARY KEY,
            password_hash TEXT
        )
    """)

    db.commit()

    # seed admin user once
    if not db.execute("SELECT 1 FROM admin_users").fetchone():
        db.execute(
            "INSERT INTO admin_users VALUES (?, ?)",
            ("Admin195B", generate_password_hash("admin1"))
        )
        db.commit()


def migrate_locations():
    """
    One-time migration:
      legacy locations -> main_locations + sub_locations (one sub per legacy)
    """
    db = get_db()

    try:
        legacy = db.execute("SELECT * FROM locations").fetchall()
    except sqlite3.OperationalError:
        legacy = []

    # if already have main locations, don't re-migrate
    if db.execute("SELECT COUNT(*) FROM main_locations").fetchone()[0] > 0:
        return

    for loc in legacy:
        cur = db.execute("""
            INSERT INTO main_locations (name, capacity, image, address)
            VALUES (?, ?, ?, ?)
        """, (loc["name"], loc["capacity"], loc["image"], loc["address"]))

        main_id = cur.lastrowid

        db.execute("""
            INSERT INTO sub_locations
            (main_location_id, name, capacity, image, video)
            VALUES (?, ?, ?, ?, ?)
        """, (
            main_id,
            f"{loc['name']} - Main Area",
            loc["capacity"],
            loc["image"],
            loc["video"]
        ))

    db.commit()


def seed_demo_if_empty():
    """
    If there's literally nothing in main_locations after migration,
    add 1 demo main + 1 demo sub so /spaces isn't empty.
    """
    db = get_db()
    count = db.execute("SELECT COUNT(*) FROM main_locations").fetchone()[0]
    if count > 0:
        return

    cur = db.execute("""
        INSERT INTO main_locations (name, capacity, image, address)
        VALUES (?, ?, ?, ?)
    """, (
        "SJSU Demo Campus",
        0,
        "uploads/images/library.jpg",
        "San Jose State University"
    ))
    main_id = cur.lastrowid

    db.execute("""
        INSERT INTO sub_locations (main_location_id, name, capacity, image, video)
        VALUES (?, ?, ?, ?, ?)
    """, (
        main_id,
        "Student Union - Demo",
        60,
        "uploads/images/library.jpg",
        "uploads/videos/lotsofpeoplewalking.mp4"
    ))

    db.commit()


with app.app_context():
    init_db()
    migrate_locations()
    seed_demo_if_empty()


# -------------------------
# AUTH
# -------------------------
class AdminUser(UserMixin):
    def __init__(self, username):
        self.id = username


@login_manager.user_loader
def load_user(username):
    row = get_db().execute(
        "SELECT username FROM admin_users WHERE username = ?", (username,)
    ).fetchone()
    return AdminUser(row["username"]) if row else None


# -------------------------
# PUBLIC ROUTES
# -------------------------
@app.route("/")
def home():
    return render_template("home.html")


@app.route("/spaces")
def spaces():
    db = get_db()

    rows = db.execute("""
        SELECT m.*,
               COALESCE(SUM(s.capacity), 0) AS total_capacity,
               COALESCE(SUM(st.average_people), 0) AS total_people
        FROM main_locations m
        LEFT JOIN sub_locations s ON s.main_location_id = m.id
        LEFT JOIN status st ON st.id = s.id
        GROUP BY m.id
        ORDER BY m.name
    """).fetchall()

    locations = []
    for r in rows:
        total_capacity = r["total_capacity"] or 0
        total_people = r["total_people"] or 0

        percent = (total_people / total_capacity) * 100 if total_capacity else 0
        level = "High" if percent > 60 else "Medium" if percent >= 40 else "Low"

        locations.append({
            **dict(r),
            "percent": round(percent, 1),
            "level": level
        })

    return render_template("spaces.html", main_locations=locations)


@app.route("/spaces/<int:location_id>")
def view_sub_locations(location_id):
    db = get_db()

    main = db.execute(
        "SELECT * FROM main_locations WHERE id = ?", (location_id,)
    ).fetchone()

    if not main:
        return "Not found", 404

    subs = db.execute("""
        SELECT s.*,
               st.average_people,
               st.level,
               st.percent,
               st.updated_at
        FROM sub_locations s
        LEFT JOIN status st ON st.id = s.id
        WHERE s.main_location_id = ?
        ORDER BY s.name
    """, (location_id,)).fetchall()

    return render_template(
        "sub_locations.html",
        main_location=dict(main),
        sub_locations=[dict(s) for s in subs]
    )


@app.route("/help")
def help_page():
    return render_template("help.html")


# -------------------------
# ADMIN
# -------------------------
@app.route("/admin")
def admin_root():
    return redirect(url_for("admin_login"))

@app.route("/admin/main_locations/update_image", methods=["POST"])
@login_required
def admin_update_main_location_image():
    db = get_db()

    location_id = int(request.form["location_id"])
    image = request.files.get("image")

    if not image or not image.filename:
        flash("No image selected", "error")
        return redirect(url_for("admin_dashboard"))

    if not allowed_file(image.filename, ALLOWED_IMAGE_EXT):
        flash("Invalid image type", "error")
        return redirect(url_for("admin_dashboard"))

    filename = secure_filename(image.filename)
    image.save(os.path.join(IMAGE_UPLOAD_FOLDER, filename))

    image_path = f"uploads/images/{filename}"

    db.execute(
        "UPDATE main_locations SET image = ? WHERE id = ?",
        (image_path, location_id)
    )
    db.commit()

    flash("Main location image updated", "success")
    return redirect(url_for("admin_dashboard"))


@app.route("/admin/login", methods=["GET", "POST"])
def admin_login():
    error = None
    if request.method == "POST":
        u = request.form["username"]
        p = request.form["password"]
        row = get_db().execute(
            "SELECT * FROM admin_users WHERE username = ?", (u,)
        ).fetchone()

        if row and check_password_hash(row["password_hash"], p):
            login_user(AdminUser(u))
            return redirect(url_for("admin_dashboard"))

        error = "Invalid credentials"

    return render_template("admin_login.html", error=error)


@app.route("/admin/logout")
@login_required
def admin_logout():
    logout_user()
    return redirect(url_for("admin_login"))


@app.route("/admin/dashboard")
@login_required
def admin_dashboard():
    db = get_db()

    main_locations = db.execute("SELECT * FROM main_locations ORDER BY name").fetchall()

    sub_locations = db.execute("""
        SELECT s.*, m.name AS parent_name
        FROM sub_locations s
        JOIN main_locations m ON m.id = s.main_location_id
        ORDER BY m.name, s.name
    """).fetchall()

    statuses = db.execute(
        "SELECT * FROM status ORDER BY updated_at DESC LIMIT 50"
    ).fetchall()

    return render_template(
        "admin_dashboard.html",
        main_locations=[dict(m) for m in main_locations],
        locations=[dict(s) for s in sub_locations],
        statuses=[dict(s) for s in statuses]
    )


# -------------------------
# ADMIN ADD ROUTES
# -------------------------
def allowed_file(filename, allowed_set):
    return "." in filename and filename.rsplit(".", 1)[1].lower() in allowed_set


@app.route("/admin/main_locations/add", methods=["POST"])
@login_required
def admin_add_main_location():
    db = get_db()

    image_file = request.files.get("image")
    image_path = "uploads/images/default.jpg"

    if image_file and image_file.filename and allowed_file(image_file.filename, ALLOWED_IMAGE_EXT):
        img_name = secure_filename(image_file.filename)
        image_file.save(os.path.join(IMAGE_UPLOAD_FOLDER, img_name))
        image_path = f"uploads/images/{img_name}"

    db.execute("""
        INSERT INTO main_locations (name, capacity, address, image)
        VALUES (?, ?, ?, ?)
    """, (
        request.form["name"].strip(),
        int(request.form.get("capacity") or 0),
        (request.form.get("address") or "").strip(),
        image_path
    ))
    db.commit()
    return redirect(url_for("admin_dashboard"))


@app.route("/admin/sub_locations/add", methods=["POST"])
@login_required
def admin_add_sub_location():
    db = get_db()

    img = request.files.get("image")
    vid = request.files.get("video")

    img_path = "uploads/images/default.jpg"
    vid_path = ""

    if img and img.filename and allowed_file(img.filename, ALLOWED_IMAGE_EXT):
        img_name = secure_filename(img.filename)
        img.save(os.path.join(IMAGE_UPLOAD_FOLDER, img_name))
        img_path = f"uploads/images/{img_name}"

    if vid and vid.filename and allowed_file(vid.filename, ALLOWED_VIDEO_EXT):
        vid_name = secure_filename(vid.filename)
        vid.save(os.path.join(VIDEO_UPLOAD_FOLDER, vid_name))
        vid_path = f"uploads/videos/{vid_name}"

    db.execute("""
        INSERT INTO sub_locations
        (main_location_id, name, capacity, image, video)
        VALUES (?, ?, ?, ?, ?)
    """, (
        int(request.form["main_location_id"]),
        request.form["name"].strip(),
        int(request.form.get("capacity") or 0),
        img_path,
        vid_path
    ))

    db.commit()
    return redirect(url_for("admin_dashboard"))


# -------------------------
# API (YOLO)
# -------------------------
@app.route("/api/analyze", methods=["POST"])
def api_analyze():
    loc_id = request.json.get("location")
    db = get_db()

    loc = db.execute(
        "SELECT * FROM sub_locations WHERE id = ?", (loc_id,)
    ).fetchone()

    if not loc:
        return jsonify({"error": "Unknown location"}), 400

    video_rel = (loc["video"] or "").replace("\\", "/")
    if not video_rel:
        return jsonify({"error": "No video set for this sub-location"}), 400

    video_path = os.path.join(BASE_DIR, "static", *video_rel.split("/"))
    if not os.path.exists(video_path):
        return jsonify({"error": f"Video file not found: {video_rel}"}), 404

    avg = average_people_in_video(video_path)

    cap = loc["capacity"] or 0
    percent = (avg / cap) * 100 if cap else 0
    level = "High" if percent > 60 else "Medium" if percent >= 40 else "Low"

    db.execute("""
        INSERT OR REPLACE INTO status
        (id, location_name, average_people, capacity, percent, level, updated_at)
        VALUES (?, ?, ?, ?, ?, ?, CURRENT_TIMESTAMP)
    """, (loc_id, loc["name"], int(avg), cap, round(percent, 1), level))

    db.commit()

    return jsonify({
        "id": loc_id,
        "location": loc["name"],
        "average_people": int(avg),
        "capacity": cap,
        "percent": round(percent, 1),
        "level": level
    })


@app.route("/api/get_last_status", methods=["POST"])
def get_last_status():
    row = get_db().execute(
        "SELECT * FROM status WHERE id = ?", (request.json["location"],)
    ).fetchone()
    return jsonify(dict(row)) if row else (jsonify({"error": "No data"}), 404)


if __name__ == "__main__":
    app.run(debug=True)
