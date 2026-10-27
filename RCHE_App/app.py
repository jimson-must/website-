# -*- coding: utf-8 -*-
"""RCHE Staff App - Ryakasinga CHE.

Teacher attendance over school Wi-Fi, live lessons, timetables, announcements,
cover and an end-of-day PDF for the Head of Academics.
Run:  python app.py   then open http://localhost:5000
"""
import csv
import datetime as dt
import hmac
import io
import os
import secrets
import socket
import threading
import webbrowser
from functools import wraps

from flask import (Flask, Response, abort, flash, g, jsonify, redirect, render_template, request,
                   send_file, send_from_directory, session, url_for)
from werkzeug.security import check_password_hash, generate_password_hash

import database as dbm
import logic as L
import reports as R
import scheduler

BASE_DIR = os.path.dirname(os.path.abspath(__file__))
INSTANCE = os.path.join(BASE_DIR, "instance")
os.makedirs(INSTANCE, exist_ok=True)
DB_PATH = os.path.join(INSTANCE, "rche.db")
REPORT_DIR = os.path.join(INSTANCE, "reports")
os.makedirs(REPORT_DIR, exist_ok=True)


def _secret_key():
    p = os.path.join(INSTANCE, "secret.key")
    if not os.path.exists(p):
        with open(p, "w") as f:
            f.write(secrets.token_hex(32))
    with open(p) as f:
        return f.read().strip()


app = Flask(__name__)
app.config.update(
    SECRET_KEY=_secret_key(),
    SESSION_COOKIE_HTTPONLY=True,
    SESSION_COOKIE_SAMESITE="Lax",
    PERMANENT_SESSION_LIFETIME=dt.timedelta(hours=12),
    MAX_CONTENT_LENGTH=1024 * 1024,
)

ROLE_LABELS = {
    "admin": "System Administrator", "principal": "Principal", "hoa": "Head of Academics",
    "dos": "Director of Studies", "teacher": "Teacher", "staff": "Non-teaching staff",
}
LEADERS = ("admin", "principal", "hoa", "dos")
APPROVERS = ("admin", "principal", "hoa")
POSTERS = ("admin", "principal", "hoa", "dos")

ICONS = {
    "home": '<path d="M3 9l9-7 9 7v11a2 2 0 0 1-2 2H5a2 2 0 0 1-2-2z"/><polyline points="9 22 9 12 15 12 15 22"/>',
    "calendar": '<rect x="3" y="4" width="18" height="18" rx="2"/><line x1="16" y1="2" x2="16" y2="6"/><line x1="8" y1="2" x2="8" y2="6"/><line x1="3" y1="10" x2="21" y2="10"/>',
    "bell": '<path d="M18 8A6 6 0 0 0 6 8c0 7-3 9-3 9h18s-3-2-3-9"/><path d="M13.73 21a2 2 0 0 1-3.46 0"/>',
    "users": '<path d="M17 21v-2a4 4 0 0 0-4-4H5a4 4 0 0 0-4 4v2"/><circle cx="9" cy="7" r="4"/><path d="M23 21v-2a4 4 0 0 0-3-3.87"/><path d="M16 3.13a4 4 0 0 1 0 7.75"/>',
    "user": '<path d="M20 21v-2a4 4 0 0 0-4-4H8a4 4 0 0 0-4 4v2"/><circle cx="12" cy="7" r="4"/>',
    "clock": '<circle cx="12" cy="12" r="10"/><polyline points="12 6 12 12 16 14"/>',
    "check": '<path d="M22 11.08V12a10 10 0 1 1-5.93-9.14"/><polyline points="22 4 12 14.01 9 11.01"/>',
    "message": '<path d="M21 15a2 2 0 0 1-2 2H7l-4 4V5a2 2 0 0 1 2-2h14a2 2 0 0 1 2 2z"/>',
    "file": '<path d="M14 2H6a2 2 0 0 0-2 2v16a2 2 0 0 0 2 2h12a2 2 0 0 0 2-2V8z"/><polyline points="14 2 14 8 20 8"/><line x1="16" y1="13" x2="8" y2="13"/><line x1="16" y1="17" x2="8" y2="17"/>',
    "sliders": '<line x1="4" y1="21" x2="4" y2="14"/><line x1="4" y1="10" x2="4" y2="3"/><line x1="12" y1="21" x2="12" y2="12"/><line x1="12" y1="8" x2="12" y2="3"/><line x1="20" y1="21" x2="20" y2="16"/><line x1="20" y1="12" x2="20" y2="3"/><line x1="1" y1="14" x2="7" y2="14"/><line x1="9" y1="8" x2="15" y2="8"/><line x1="17" y1="16" x2="23" y2="16"/>',
    "logout": '<path d="M9 21H5a2 2 0 0 1-2-2V5a2 2 0 0 1 2-2h4"/><polyline points="16 17 21 12 16 7"/><line x1="21" y1="12" x2="9" y2="12"/>',
    "bar": '<line x1="18" y1="20" x2="18" y2="10"/><line x1="12" y1="20" x2="12" y2="4"/><line x1="6" y1="20" x2="6" y2="14"/>',
    "wifi": '<path d="M5 12.55a11 11 0 0 1 14.08 0"/><path d="M1.42 9a16 16 0 0 1 21.16 0"/><path d="M8.53 16.11a6 6 0 0 1 6.95 0"/><line x1="12" y1="20" x2="12.01" y2="20"/>',
    "alert": '<path d="M10.29 3.86L1.82 18a2 2 0 0 0 1.71 3h16.94a2 2 0 0 0 1.71-3L13.71 3.86a2 2 0 0 0-3.42 0z"/><line x1="12" y1="9" x2="12" y2="13"/><line x1="12" y1="17" x2="12.01" y2="17"/>',
    "shield": '<path d="M12 22s8-4 8-10V5l-8-3-8 3v7c0 6 8 10 8 10z"/>',
    "download": '<path d="M21 15v4a2 2 0 0 1-2 2H5a2 2 0 0 1-2-2v-4"/><polyline points="7 10 12 15 17 10"/><line x1="12" y1="15" x2="12" y2="3"/>',
    "plus": '<line x1="12" y1="5" x2="12" y2="19"/><line x1="5" y1="12" x2="19" y2="12"/>',
    "edit": '<path d="M11 4H4a2 2 0 0 0-2 2v14a2 2 0 0 0 2 2h14a2 2 0 0 0 2-2v-7"/><path d="M18.5 2.5a2.121 2.121 0 0 1 3 3L12 15l-4 1 1-4 9.5-9.5z"/>',
    "trash": '<polyline points="3 6 5 6 21 6"/><path d="M19 6l-1 14a2 2 0 0 1-2 2H8a2 2 0 0 1-2-2L5 6"/><path d="M10 11v6"/><path d="M14 11v6"/><path d="M9 6V4a1 1 0 0 1 1-1h4a1 1 0 0 1 1 1v2"/>',
    "sun": '<circle cx="12" cy="12" r="5"/><line x1="12" y1="1" x2="12" y2="3"/><line x1="12" y1="21" x2="12" y2="23"/><line x1="4.22" y1="4.22" x2="5.64" y2="5.64"/><line x1="18.36" y1="18.36" x2="19.78" y2="19.78"/><line x1="1" y1="12" x2="3" y2="12"/><line x1="21" y1="12" x2="23" y2="12"/><line x1="4.22" y1="19.78" x2="5.64" y2="18.36"/><line x1="18.36" y1="5.64" x2="19.78" y2="4.22"/>',
    "moon": '<path d="M21 12.79A9 9 0 1 1 11.21 3 7 7 0 0 0 21 12.79z"/>',
    "lock": '<rect x="3" y="11" width="18" height="11" rx="2"/><path d="M7 11V7a5 5 0 0 1 10 0v4"/>',
    "activity": '<polyline points="22 12 18 12 15 21 9 3 6 12 2 12"/>',
    "grid": '<rect x="3" y="3" width="7" height="7"/><rect x="14" y="3" width="7" height="7"/><rect x="14" y="14" width="7" height="7"/><rect x="3" y="14" width="7" height="7"/>',
    "briefcase": '<rect x="2" y="7" width="20" height="14" rx="2"/><path d="M16 21V5a2 2 0 0 0-2-2h-4a2 2 0 0 0-2 2v16"/>',
    "list": '<line x1="8" y1="6" x2="21" y2="6"/><line x1="8" y1="12" x2="21" y2="12"/><line x1="8" y1="18" x2="21" y2="18"/><line x1="3" y1="6" x2="3.01" y2="6"/><line x1="3" y1="12" x2="3.01" y2="12"/><line x1="3" y1="18" x2="3.01" y2="18"/>',
    "x": '<line x1="18" y1="6" x2="6" y2="18"/><line x1="6" y1="6" x2="18" y2="18"/>',
    "menu": '<line x1="3" y1="12" x2="21" y2="12"/><line x1="3" y1="6" x2="21" y2="6"/><line x1="3" y1="18" x2="21" y2="18"/>',
    "repeat": '<polyline points="17 1 21 5 17 9"/><path d="M3 11V9a4 4 0 0 1 4-4h14"/><polyline points="7 23 3 19 7 15"/><path d="M21 13v2a4 4 0 0 1-4 4H3"/>',
}
app.jinja_env.globals["ICONS"] = ICONS
app.jinja_env.globals["ROLE_LABELS"] = ROLE_LABELS
app.jinja_env.globals["DAYS"] = L.DAYS

NAV = {
    "teacher": [("dashboard", "Dashboard", "home"), ("timetable", "My timetable", "calendar"),
                ("announcements", "Announcements", "message"), ("my_attendance", "My attendance", "check"),
                ],
    "staff": [("dashboard", "Dashboard", "home"), ("announcements", "Announcements", "message"),
              ("my_attendance", "My attendance", "check")],
    "dos": [("dashboard", "Dashboard", "home"), ("live", "Live lessons", "activity"),
            ("dos_timetable", "Timetable editor", "grid"), ("dos_cover", "Cover and substitutions", "repeat"),
            ("timetable", "Timetables", "calendar"), ("announcements", "Announcements", "message"),
            ("directory", "Staff directory", "users"), ("my_attendance", "My attendance", "check")],
    "hoa": [("dashboard", "Dashboard", "home"), ("live", "Live lessons", "activity"),
            ("overview", "Attendance", "bar"), ("reports", "Daily reports", "file"),
            ("timetable", "Timetables", "calendar"), ("announcements", "Announcements", "message"),
            ("directory", "Staff directory", "users")],
    "principal": [("dashboard", "Dashboard", "home"), ("live", "Live lessons", "activity"),
                  ("overview", "Attendance", "bar"), ("reports", "Daily reports", "file"),
                  ("timetable", "Timetables", "calendar"), ("announcements", "Announcements", "message"),
                  ("directory", "Staff directory", "users"),
                  ("audit", "Audit log", "list")],
    "admin": [("dashboard", "Dashboard", "home"), ("live", "Live lessons", "activity"),
              ("overview", "Attendance", "bar"), ("dos_timetable", "Timetable editor", "grid"),
              ("dos_cover", "Cover and substitutions", "repeat"), ("reports", "Daily reports", "file"),
              ("announcements", "Announcements", "message"),
              ("directory", "Staff directory", "users"), ("admin_users", "Users", "user"),
              ("admin_settings", "Settings", "sliders"), ("audit", "Audit log", "list")],
}


# ------------------------------------------------------------------ plumbing
def db():
    if "db" not in g:
        g.db = dbm.connect(DB_PATH)
    return g.db


@app.teardown_appcontext
def close_db(_exc):
    conn = g.pop("db", None)
    if conn is not None:
        conn.close()


def now():
    return L.app_now(db())


def client_ip():
    return request.remote_addr or ""


def audit(action, detail=""):
    u = g.get("user")
    db().execute(
        "INSERT INTO audit_log(user_id,username,action,detail,ip,created_at) VALUES(?,?,?,?,?,?)",
        (u["id"] if u else None, u["username"] if u else "", action, detail, client_ip(), L.ts(L.real_now())))
    db().commit()


def csrf():
    if "csrf" not in session:
        session["csrf"] = secrets.token_hex(16)
    return session["csrf"]


app.jinja_env.globals["csrf"] = csrf


@app.before_request
def load_user():
    g.user = None
    if request.endpoint == "static":
        return
    uid = session.get("uid")
    if uid:
        u = db().execute("SELECT * FROM users WHERE id=? AND active=1", (uid,)).fetchone()
        if u:
            g.user = u
        else:
            session.clear()
    if request.method in ("POST", "PUT", "PATCH", "DELETE"):
        sent = request.form.get("_csrf") or request.headers.get("X-CSRF-Token", "")
        token = session.get("csrf", "")
        if not token or not hmac.compare_digest(token, sent):
            abort(400, "Your session expired. Reload the page and try again.")
    if g.user and g.user["must_change"] and request.endpoint not in (
            "profile", "logout", "manifest", "service_worker", "static"):
        flash("Set a new password before you continue.", "warn")
        return redirect(url_for("profile"))


@app.after_request
def secure(resp):
    resp.headers["X-Content-Type-Options"] = "nosniff"
    resp.headers["X-Frame-Options"] = "DENY"
    resp.headers["Referrer-Policy"] = "same-origin"
    if request.endpoint not in ("static", "service_worker", "manifest"):
        resp.headers["Cache-Control"] = "no-store"
    return resp


def login_required(f):
    @wraps(f)
    def wrapper(*a, **kw):
        if not g.user:
            if request.path.startswith("/api/"):
                return jsonify(error="Please sign in again."), 401
            return redirect(url_for("login", next=request.path))
        return f(*a, **kw)
    return wrapper


def roles_required(*roles):
    def deco(f):
        @wraps(f)
        @login_required
        def wrapper(*a, **kw):
            if g.user["role"] not in roles:
                if request.path.startswith("/api/"):
                    return jsonify(error="You do not have access to this."), 403
                abort(403)
            return f(*a, **kw)
        return wrapper
    return deco


@app.template_filter("hm")
def f_hm(v):
    return L.hm(v)


@app.template_filter("dlabel")
def f_dlabel(v):
    try:
        return L.date_label(dt.datetime.strptime(v, "%Y-%m-%d").date())
    except (TypeError, ValueError):
        return v


@app.template_filter("dtlabel")
def f_dtlabel(v):
    try:
        d = dt.datetime.strptime(v, "%Y-%m-%d %H:%M:%S")
        return "%d %s, %s" % (d.day, d.strftime("%b"), d.strftime("%H:%M"))
    except (TypeError, ValueError):
        return v


@app.template_filter("initials")
def f_initials(name):
    parts = [p for p in str(name).replace(".", " ").split() if p and p.lower() not in ("mr", "mrs", "ms", "dr", "rev")]
    return "".join(p[0] for p in parts[:2]).upper() or "?"


@app.template_filter("firstname")
def f_firstname(name):
    parts = [p for p in str(name).split() if p.lower().strip(".") not in ("mr", "mrs", "ms", "dr", "rev", "prof")]
    return parts[0] if parts else str(name)


@app.context_processor
def inject():
    ctx = {"user": g.get("user")}
    if g.get("user"):
        conn = db()
        n = now()
        nav = []
        for ep, label, icon in NAV.get(g.user["role"], []):
            nav.append({"url": url_for(ep), "label": label, "icon": icon, "active": request.endpoint == ep})
        ctx.update(
            nav=nav, now_s=L.sod(n), now_label=L.long_date(n),
            school_name=L.setting(conn, "school_name"), school_short=L.setting(conn, "school_short"),
            unread=conn.execute("SELECT COUNT(*) FROM notifications WHERE user_id=? AND read_at IS NULL",
                                (g.user["id"],)).fetchone()[0],
            demo_active=int(L.setting(conn, "demo_offset", "0") or 0) != 0,
            demo_time=n.strftime("%a %d %b, %H:%M"),
        )
    else:
        ctx.update(school_name=L.setting(db(), "school_name"), school_short=L.setting(db(), "school_short"),
                   now_s=0, nav=[], unread=0, demo_active=False)
    return ctx


@app.errorhandler(400)
@app.errorhandler(403)
@app.errorhandler(404)
def http_error(e):
    code = getattr(e, "code", 500)
    msgs = {400: "That request could not be processed.", 403: "Your account does not have access to this page.",
            404: "We could not find that page."}
    desc = getattr(e, "description", "") if code == 400 else ""
    if request.path.startswith("/api/"):
        return jsonify(error=desc or msgs.get(code, "Error")), code
    return render_template("error.html", code=code, message=desc or msgs.get(code, "Something went wrong.")), code


# ---------------------------------------------------------------------- PWA
@app.route("/manifest.webmanifest")
def manifest():
    conn = db()
    data = {
        "name": L.setting(conn, "school_name") + " Staff", "short_name": L.setting(conn, "school_short"),
        "start_url": "/", "display": "standalone", "background_color": "#0B1F44", "theme_color": "#0B1F44",
        "icons": [{"src": "/static/icons/icon-192.png", "sizes": "192x192", "type": "image/png"},
                  {"src": "/static/icons/icon-512.png", "sizes": "512x512", "type": "image/png"}],
    }
    return Response(jsonify(data).get_data(), mimetype="application/manifest+json")


@app.route("/sw.js")
def service_worker():
    resp = send_from_directory(os.path.join(BASE_DIR, "static", "js"), "sw.js", mimetype="application/javascript")
    resp.headers["Service-Worker-Allowed"] = "/"
    return resp


# --------------------------------------------------------------------- auth
@app.route("/login", methods=["GET", "POST"])
def login():
    if g.user:
        return redirect(url_for("dashboard"))
    conn = db()
    if request.method == "POST":
        username = request.form.get("username", "").strip()
        password = request.form.get("password", "")
        u = conn.execute("SELECT * FROM users WHERE username=?", (username,)).fetchone()
        n = now()
        if u and u["locked_until"] and u["locked_until"] > L.ts(n):
            flash("Too many attempts. Try again in a few minutes.", "err")
        elif u and u["active"] and check_password_hash(u["password_hash"], password):
            session.clear()
            session.permanent = True
            session["uid"] = u["id"]
            session["csrf"] = secrets.token_hex(16)
            conn.execute("UPDATE users SET failed_count=0, locked_until=NULL, last_login=? WHERE id=?",
                         (L.ts(n), u["id"]))
            conn.commit()
            g.user = u
            audit("login", "Signed in")
            nxt = request.args.get("next", "")
            return redirect(nxt if nxt.startswith("/") and not nxt.startswith("//") else url_for("dashboard"))
        else:
            if u:
                fails = u["failed_count"] + 1
                lock = L.ts(n + dt.timedelta(minutes=5)) if fails >= 5 else None
                conn.execute("UPDATE users SET failed_count=?, locked_until=? WHERE id=?",
                             (0 if lock else fails, lock, u["id"]))
                conn.commit()
            audit("login_failed", "Username: %s" % username[:40])
            flash("Incorrect username or password.", "err")
    return render_template("login.html")


@app.route("/logout", methods=["POST"])
@login_required
def logout():
    audit("logout")
    session.clear()
    return redirect(url_for("login"))


# ------------------------------------------------------------ announcements
def visible_announcements(conn, user, limit=None):
    role = user["role"]
    aud = ("all", "teachers") if role == "teacher" else ("all", "staff") if role == "staff" \
        else ("all", "teachers", "staff")
    sql = ("SELECT a.*, u.full_name AS author, "
           "(SELECT COUNT(*) FROM announcement_reads r WHERE r.announcement_id=a.id AND r.user_id=?) AS is_read "
           "FROM announcements a LEFT JOIN users u ON u.id=a.author_id "
           "WHERE a.audience IN (%s) ORDER BY a.pinned DESC, a.id DESC" % ",".join("?" * len(aud)))
    params = [user["id"]] + list(aud)
    if limit:
        sql += " LIMIT ?"
        params.append(limit)
    return conn.execute(sql, params).fetchall()


@app.route("/announcements")
@login_required
def announcements():
    conn = db()
    items = visible_announcements(conn, g.user)
    stats = {}
    if g.user["role"] in POSTERS:
        for a in items:
            roles = {"all": ("teacher", "staff", "dos", "hoa", "principal", "admin"),
                     "teachers": ("teacher",), "staff": ("staff",)}[a["audience"]]
            size = conn.execute("SELECT COUNT(*) FROM users WHERE active=1 AND role IN (%s)"
                                % ",".join("?" * len(roles)), roles).fetchone()[0]
            seen = conn.execute("SELECT COUNT(*) FROM announcement_reads WHERE announcement_id=?",
                                (a["id"],)).fetchone()[0]
            stats[a["id"]] = (seen, size)
    rendered = render_template("announcements.html", items=items, stats=stats, can_post=g.user["role"] in POSTERS)
    n = now()
    for a in items:
        if not a["is_read"]:
            conn.execute("INSERT OR IGNORE INTO announcement_reads(announcement_id,user_id,read_at) VALUES(?,?,?)",
                         (a["id"], g.user["id"], L.ts(n)))
    conn.execute("UPDATE notifications SET read_at=? WHERE user_id=? AND kind='announcement' AND read_at IS NULL",
                 (L.ts(n), g.user["id"]))
    conn.commit()
    return rendered


@app.route("/announcements/new", methods=["POST"])
@roles_required(*POSTERS)
def announcement_new():
    conn = db()
    title = request.form.get("title", "").strip()[:140]
    body = request.form.get("body", "").strip()[:4000]
    audience = request.form.get("audience", "all")
    priority = "urgent" if request.form.get("priority") == "urgent" else "normal"
    pinned = 1 if request.form.get("pinned") else 0
    if not title or not body or audience not in ("all", "teachers", "staff"):
        flash("Add a title and a message.", "err")
        return redirect(url_for("announcements"))
    n = now()
    cur = conn.execute(
        "INSERT INTO announcements(title,body,audience,priority,pinned,author_id,created_at) VALUES(?,?,?,?,?,?,?)",
        (title, body, audience, priority, pinned, g.user["id"], L.ts(n)))
    roles = {"all": ("teacher", "staff", "dos", "hoa", "principal", "admin"),
             "teachers": ("teacher",), "staff": ("staff",)}[audience]
    L.notify_roles(conn, roles, "announcement", ("Urgent: " if priority == "urgent" else "") + title,
                   body[:140], "/announcements", n, exclude=g.user["id"])
    conn.commit()
    audit("announcement", "Posted #%d (%s)" % (cur.lastrowid, audience))
    flash("Announcement published.", "ok")
    return redirect(url_for("announcements"))


@app.route("/announcements/<int:aid>/delete", methods=["POST"])
@roles_required(*POSTERS)
def announcement_delete(aid):
    db().execute("DELETE FROM announcements WHERE id=?", (aid,))
    db().commit()
    audit("announcement_delete", "#%d" % aid)
    flash("Announcement removed.", "ok")
    return redirect(url_for("announcements"))


@app.route("/announcements/<int:aid>/pin", methods=["POST"])
@roles_required(*POSTERS)
def announcement_pin(aid):
    db().execute("UPDATE announcements SET pinned = 1 - pinned WHERE id=?", (aid,))
    db().commit()
    return redirect(url_for("announcements"))


# ---------------------------------------------------------------- dashboards
@app.route("/")
@login_required
def dashboard():
    conn = db()
    n = now()
    role = g.user["role"]
    anns = visible_announcements(conn, g.user, limit=4)
    if role == "teacher":
        _, stats = L.personal_history(conn, g.user["id"], n, 30)
        return render_template("dashboard_teacher.html", anns=anns, stats=stats)
    if role == "staff":
        rows, stats = L.personal_history(conn, g.user["id"], n, 30)
        return render_template("dashboard_staff.html", anns=anns, stats=stats, recent=rows[:5])
    rows, summary = L.attendance_for_date(conn, n.date(), n, "teacher")
    return render_template(
        "dashboard_leader.html", anns=anns, rows=rows, summary=summary, live=L.live_snapshot(conn, n),
        series=L.daily_series(conn, n, 14),
        cover=L.needs_cover(conn, n) if role in ("dos", "admin", "hoa", "principal") else [],
        latest_report=conn.execute("SELECT * FROM reports ORDER BY report_date DESC LIMIT 1").fetchone())


@app.route("/live")
@roles_required(*LEADERS)
def live():
    return render_template("live.html", live=L.live_snapshot(db(), now()))


@app.route("/live/fragment")
@roles_required(*LEADERS)
def live_fragment():
    return render_template("_live_board.html", live=L.live_snapshot(db(), now()))


# ---------------------------------------------------------------------- API
@app.route("/api/me/now")
@login_required
def api_now():
    return jsonify(L.now_payload(db(), g.user, now(), client_ip()))


@app.route("/api/checkin", methods=["POST"])
@login_required
def api_checkin():
    conn = db()
    n = now()
    if n.date().weekday() > 4:
        return jsonify(error="There is no school today."), 400
    net = L.network_status(conn, client_ip())
    if not net["ok"]:
        return jsonify(error="Connect to the school Wi-Fi to check in."), 403
    data = request.get_json(silent=True) or {}
    method = ("wifi-auto" if data.get("auto") else "wifi-button") if net["enforced"] else "demo-button"
    row, created = L.do_checkin(conn, g.user["id"], n, client_ip(), method)
    if created:
        audit("checkin", "%s at %s" % (row["status"], row["check_in"]))
    return jsonify(ok=True, created=created, status=row["status"], time=L.hm(row["check_in"]))


@app.route("/api/checkout", methods=["POST"])
@login_required
def api_checkout():
    conn = db()
    n = now()
    r = conn.execute("SELECT * FROM day_attendance WHERE user_id=? AND date=?",
                     (g.user["id"], L.dstr(n.date()))).fetchone()
    if not r:
        return jsonify(error="Check in first."), 400
    conn.execute("UPDATE day_attendance SET check_out=? WHERE id=?", (n.strftime("%H:%M:%S"), r["id"]))
    conn.commit()
    audit("checkout", n.strftime("%H:%M"))
    return jsonify(ok=True, time=L.hm(n))


@app.route("/api/lesson/confirm", methods=["POST"])
@roles_required("teacher")
def api_confirm():
    conn = db()
    n = now()
    data = request.get_json(silent=True) or {}
    try:
        eid = int(data.get("entry_id"))
    except (TypeError, ValueError):
        return jsonify(error="Unknown lesson."), 400
    net = L.network_status(conn, client_ip())
    if not net["ok"]:
        return jsonify(error="Connect to the school Wi-Fi to confirm your lesson."), 403
    lesson = next((l for l in L.my_lessons(conn, g.user["id"], n.date(), n) if l["entry_id"] == eid), None)
    if not lesson:
        return jsonify(error="That lesson is not on your timetable today."), 404
    early = int(L.setting(conn, "confirm_early_minutes", "5"))
    if n < lesson["start"] - dt.timedelta(minutes=early) or n >= lesson["end"]:
        return jsonify(error="You can confirm from %d minutes before the lesson until it ends." % early), 400
    conn.execute("INSERT OR IGNORE INTO lesson_attendance(timetable_id,date,teacher_id,confirmed_at,ip) VALUES(?,?,?,?,?)",
                 (eid, L.dstr(n.date()), g.user["id"], n.strftime("%H:%M:%S"), client_ip()))
    if not conn.execute("SELECT 1 FROM day_attendance WHERE user_id=? AND date=?", (g.user["id"], L.dstr(n.date()))).fetchone():
        L.do_checkin(conn, g.user["id"], n, client_ip(), "lesson")
    conn.commit()
    audit("lesson_confirm", "%s %s" % (lesson["class_name"], lesson["subject"]))
    return jsonify(ok=True, time=L.hm(n))


@app.route("/api/notifications")
@login_required
def api_notifications():
    conn = db()
    n = now()
    rows = conn.execute("SELECT * FROM notifications WHERE user_id=? ORDER BY id DESC LIMIT 15",
                        (g.user["id"],)).fetchall()
    unread = conn.execute("SELECT COUNT(*) FROM notifications WHERE user_id=? AND read_at IS NULL",
                          (g.user["id"],)).fetchone()[0]
    return jsonify(unread=unread, items=[{
        "id": r["id"], "kind": r["kind"], "title": r["title"], "body": r["body"], "link": r["link"],
        "ago": L.ago(r["created_at"], n), "read": bool(r["read_at"])} for r in rows])


@app.route("/api/notifications/read", methods=["POST"])
@login_required
def api_notifications_read():
    conn = db()
    data = request.get_json(silent=True) or {}
    n = L.ts(now())
    if data.get("id"):
        conn.execute("UPDATE notifications SET read_at=? WHERE id=? AND user_id=? AND read_at IS NULL",
                     (n, int(data["id"]), g.user["id"]))
    else:
        conn.execute("UPDATE notifications SET read_at=? WHERE user_id=? AND read_at IS NULL", (n, g.user["id"]))
    conn.commit()
    return jsonify(ok=True)


# --------------------------------------------------------------- timetables
def _monday(n):
    return n.date() - dt.timedelta(days=n.date().weekday())


def build_grid(conn, mode, key, n):
    """Weekly grid for the current week, honouring cover arrangements."""
    cells = {}
    monday = _monday(n)
    for d in range(5):
        for l in L.lessons_for_date(conn, monday + dt.timedelta(days=d)):
            tag = other = None
            if mode == "teacher":
                if l["eff_id"] == key and l["sub_id"] == key:
                    tag, other = "cover", l["teacher"]
                elif l["teacher_id"] == key and l["sub_id"]:
                    tag, other = "covered", l["sub"]
                elif l["teacher_id"] == key:
                    pass
                else:
                    continue
                cells[(l["period_id"], d)] = {"title": l["class_name"], "sub": l["subject"], "room": l["room"],
                                              "tag": tag, "other": other}
            else:
                if l["class_name"] != key:
                    continue
                cells[(l["period_id"], d)] = {"title": l["eff_name"], "sub": l["subject"], "room": l["room"],
                                              "tag": "cover" if l["sub_id"] else None, "other": l["teacher"]}
    return cells


@app.route("/timetable")
@roles_required("teacher", "dos", "hoa", "principal", "admin")
def timetable():
    conn = db()
    n = now()
    role = g.user["role"]
    teachers = L.teachers(conn)
    classes = [c.strip() for c in L.setting(conn, "classes").split(",") if c.strip()]
    if role == "teacher":
        mode, key, title = "teacher", g.user["id"], "My timetable"
    else:
        cls = request.args.get("class")
        if cls in classes:
            mode, key, title = "class", cls, "Class %s" % cls
        else:
            try:
                tid = int(request.args.get("teacher", teachers[0]["id"]))
            except (ValueError, IndexError):
                tid = teachers[0]["id"] if teachers else 0
            t = next((t for t in teachers if t["id"] == tid), None)
            mode, key, title = "teacher", tid, (t["full_name"] if t else "Timetable")
    cells = build_grid(conn, mode, key, n)
    cur = L.live_snapshot(conn, n)
    cur_periods = {l["period_id"] for l in cur["current"]}
    return render_template("timetable.html", mode=mode, key=key, title=title, cells=cells,
                           periods=L.periods(conn), teachers=teachers, classes=classes,
                           today=n.date().weekday(), cur_periods=cur_periods,
                           monday=_monday(n))


# ------------------------------------------------------- DOS: timetable editor
@app.route("/dos/timetable")
@roles_required("dos", "admin")
def dos_timetable():
    conn = db()
    classes = [c.strip() for c in L.setting(conn, "classes").split(",") if c.strip()]
    cls = request.args.get("class", classes[0] if classes else "")
    rows = conn.execute(
        "SELECT t.*, u.full_name FROM timetable t JOIN users u ON u.id=t.teacher_id WHERE t.class_name=?",
        (cls,)).fetchall()
    cells = {(r["period_id"], r["day"]): r for r in rows}
    return render_template("dos_timetable.html", classes=classes, cls=cls, cells=cells,
                           periods=L.periods(conn), teachers=L.teachers(conn))


@app.route("/dos/timetable/cell", methods=["POST"])
@roles_required("dos", "admin")
def dos_cell():
    conn = db()
    n = now()
    cls = request.form.get("class_name", "")
    try:
        day = int(request.form["day"])
        pid = int(request.form["period_id"])
    except (KeyError, ValueError):
        abort(400)
    back = redirect(url_for("dos_timetable", **{"class": cls}))
    old = conn.execute("SELECT * FROM timetable WHERE day=? AND period_id=? AND class_name=?",
                       (day, pid, cls)).fetchone()
    if request.form.get("action") == "clear":
        if old:
            conn.execute("DELETE FROM timetable WHERE id=?", (old["id"],))
            L.notify_timetable(conn, old["teacher_id"], n)
            conn.commit()
            audit("timetable_clear", "%s %s period %d" % (cls, L.DAYS[day], pid))
            flash("Lesson removed.", "ok")
        return back
    try:
        tid = int(request.form["teacher_id"])
    except (KeyError, ValueError):
        flash("Choose a teacher.", "err")
        return back
    teacher = conn.execute("SELECT * FROM users WHERE id=? AND role='teacher' AND active=1", (tid,)).fetchone()
    if not teacher:
        flash("Choose a teacher.", "err")
        return back
    subject = request.form.get("subject", "").strip()[:60] or teacher["department"] or "Lesson"
    room = request.form.get("room", "").strip()[:30]
    clash = conn.execute("SELECT class_name FROM timetable WHERE day=? AND period_id=? AND teacher_id=? AND class_name<>?",
                         (day, pid, tid, cls)).fetchone()
    if clash:
        flash("%s already teaches %s in that period. Pick another teacher or time." %
              (teacher["full_name"], clash["class_name"]), "err")
        return back
    if room:
        rc = conn.execute("SELECT class_name FROM timetable WHERE day=? AND period_id=? AND room=? AND class_name<>?",
                          (day, pid, room, cls)).fetchone()
        if rc:
            flash("%s is already used by %s in that period." % (room, rc["class_name"]), "err")
            return back
    if old:
        conn.execute("UPDATE timetable SET teacher_id=?, subject=?, room=? WHERE id=?", (tid, subject, room, old["id"]))
        if old["teacher_id"] != tid:
            L.notify_timetable(conn, old["teacher_id"], n)
    else:
        conn.execute("INSERT INTO timetable(day,period_id,teacher_id,class_name,subject,room) VALUES(?,?,?,?,?,?)",
                     (day, pid, tid, cls, subject, room))
    L.notify_timetable(conn, tid, n)
    conn.commit()
    audit("timetable_set", "%s %s period %d -> %s" % (cls, L.DAYS[day], pid, teacher["full_name"]))
    flash("Lesson saved. %s has been notified." % teacher["full_name"], "ok")
    return back


def _valid_hm(s):
    try:
        h, m = [int(x) for x in s.split(":")]
        return 0 <= h < 24 and 0 <= m < 60
    except Exception:
        return False


@app.route("/dos/periods", methods=["GET", "POST"])
@roles_required("dos", "admin")
def dos_periods():
    conn = db()
    if request.method == "POST":
        ok = True
        for p in L.periods(conn):
            label = request.form.get("label_%d" % p["id"], "").strip()[:30]
            s = request.form.get("start_%d" % p["id"], "")
            e = request.form.get("end_%d" % p["id"], "")
            brk = 1 if request.form.get("break_%d" % p["id"]) else 0
            if label and _valid_hm(s) and _valid_hm(e) and s < e:
                conn.execute("UPDATE periods SET label=?, start_time=?, end_time=?, is_break=? WHERE id=?",
                             (label, s.zfill(5), e.zfill(5), brk, p["id"]))
            else:
                ok = False
        nl, ns, ne = (request.form.get(k, "").strip() for k in ("new_label", "new_start", "new_end"))
        if nl or ns or ne:
            if nl and _valid_hm(ns) and _valid_hm(ne) and ns < ne:
                conn.execute("INSERT INTO periods(label,start_time,end_time,is_break) VALUES(?,?,?,?)",
                             (nl[:30], ns.zfill(5), ne.zfill(5), 1 if request.form.get("new_break") else 0))
            else:
                ok = False
        conn.commit()
        audit("periods_update")
        flash("Periods saved." if ok else "Some rows were skipped: check the labels and times (HH:MM).",
              "ok" if ok else "warn")
        return redirect(url_for("dos_periods"))
    return render_template("dos_periods.html", periods=L.periods(conn))


@app.route("/dos/periods/<int:pid>/delete", methods=["POST"])
@roles_required("dos", "admin")
def dos_period_delete(pid):
    db().execute("DELETE FROM periods WHERE id=?", (pid,))
    db().commit()
    audit("period_delete", "#%d" % pid)
    flash("Period removed along with its lessons.", "ok")
    return redirect(url_for("dos_periods"))


@app.route("/dos/cover", methods=["GET", "POST"])
@roles_required("dos", "admin")
def dos_cover():
    conn = db()
    n = now()
    if request.method == "POST":
        date = L.parse_date(request.form.get("date"), n.date())
        try:
            eid = int(request.form["entry_id"])
        except (KeyError, ValueError):
            abort(400)
        entry = conn.execute("SELECT t.*, p.label FROM timetable t JOIN periods p ON p.id=t.period_id WHERE t.id=?",
                             (eid,)).fetchone()
        if request.form.get("action") == "remove":
            conn.execute("DELETE FROM substitutions WHERE timetable_id=? AND date=?", (eid, L.dstr(date)))
            conn.commit()
            flash("Cover removed.", "ok")
            return redirect(url_for("dos_cover", date=L.dstr(date)))
        try:
            sub = int(request.form["sub_id"])
        except (KeyError, ValueError):
            flash("Choose a teacher to cover.", "err")
            return redirect(url_for("dos_cover", date=L.dstr(date)))
        if not entry or sub not in {t["id"] for t in L.free_teachers(conn, date, entry["period_id"])}:
            flash("That teacher is not free for this period.", "err")
            return redirect(url_for("dos_cover", date=L.dstr(date)))
        conn.execute(
            "INSERT INTO substitutions(timetable_id,date,sub_teacher_id,note,created_by,created_at) VALUES(?,?,?,?,?,?) "
            "ON CONFLICT(timetable_id,date) DO UPDATE SET sub_teacher_id=excluded.sub_teacher_id",
            (eid, L.dstr(date), sub, request.form.get("note", "")[:120], g.user["id"], L.ts(n)))
        what = "%s %s (%s)" % (entry["class_name"], entry["subject"], entry["label"])
        L.notify(conn, sub, "cover", "You are covering %s" % what, "On %s." % L.date_label(date), "/timetable", n)
        L.notify(conn, entry["teacher_id"], "cover", "Cover arranged for %s" % what,
                 "Someone will take your class on %s." % L.date_label(date), "/timetable", n)
        conn.commit()
        audit("cover_set", "%s on %s" % (what, L.dstr(date)))
        flash("Cover assigned and both teachers notified.", "ok")
        return redirect(url_for("dos_cover", date=L.dstr(date)))
    date = L.parse_date(request.args.get("date"), n.date())
    lessons = L.annotate(L.lessons_for_date(conn, date), L.status_clock(date, n), L.threshold(conn))
    free = {pid: L.free_teachers(conn, date, pid) for pid in {l["period_id"] for l in lessons}}
    only = request.args.get("filter", "attention")
    if only == "attention":
        lessons = [l for l in lessons if l["sub_id"] or l["status"] == "unattended"]
    return render_template("dos_cover.html", date=date, lessons=lessons, free=free, only=only,
                           prev=L.dstr(date - dt.timedelta(days=1)), nxt=L.dstr(date + dt.timedelta(days=1)))


# --------------------------------------------------------------- attendance
@app.route("/attendance")
@login_required
def my_attendance():
    rows, stats = L.personal_history(db(), g.user["id"], now(), 30)
    return render_template("my_attendance.html", rows=rows, stats=stats)


@app.route("/attendance/overview")
@roles_required("admin", "principal", "hoa", "dos")
def overview():
    conn = db()
    n = now()
    date = L.parse_date(request.args.get("date"), n.date())
    group = request.args.get("group", "teacher")
    if group == "staff" and g.user["role"] not in ("admin", "principal"):
        group = "teacher"
    rows, summary = L.attendance_for_date(conn, date, n, group)
    if request.args.get("export") == "csv":
        out = io.StringIO()
        w = csv.writer(out)
        w.writerow(["Name", "Department", "Status", "Check-in", "Check-out", "Lessons scheduled", "Lessons confirmed"])
        for r in rows:
            w.writerow([r["user"]["full_name"], r["user"]["department"], r["status"], r["check_in"], r["check_out"],
                        r["scheduled"], r["attended"]])
        return Response(out.getvalue(), mimetype="text/csv", headers={
            "Content-Disposition": "attachment; filename=attendance_%s_%s.csv" % (group, L.dstr(date))})
    return render_template("overview.html", rows=rows, summary=summary, date=date, group=group,
                           prev=L.dstr(date - dt.timedelta(days=1)), nxt=L.dstr(date + dt.timedelta(days=1)),
                           alerts=L.alerts_for_date(conn, date) if group == "teacher" else [])


@app.route("/directory")
@roles_required(*LEADERS)
def directory():
    conn = db()
    n = now()
    q = request.args.get("q", "").strip().lower()
    att = {r["user_id"]: r for r in conn.execute("SELECT * FROM day_attendance WHERE date=?", (L.dstr(n.date()),))}
    people = []
    for u in conn.execute("SELECT * FROM users WHERE active=1 ORDER BY full_name"):
        if g.user["role"] == "hoa" and u["role"] == "staff":
            continue  # non-teaching records stay with admin and the principal
        if q and q not in (u["full_name"] + u["department"] + u["username"]).lower():
            continue
        a = att.get(u["id"])
        people.append({"u": u, "status": a["status"] if a else "not_in",
                       "check_in": L.hm(a["check_in"]) if a else ""})
    return render_template("directory.html", people=people, q=q)


# ------------------------------------------------------------------ reports
@app.route("/reports")
@roles_required("hoa", "principal", "admin")
def reports():
    rows = db().execute("SELECT * FROM reports ORDER BY report_date DESC LIMIT 60").fetchall()
    return render_template("reports.html", rows=rows, today=L.dstr(now().date()))


@app.route("/reports/generate", methods=["POST"])
@roles_required("hoa", "principal", "admin")
def reports_generate():
    conn = db()
    n = now()
    date = L.parse_date(request.form.get("date"), n.date())
    if date > n.date() or date.weekday() > 4:
        flash("Pick a school day that is not in the future.", "err")
        return redirect(url_for("reports"))
    rid = R.generate_and_publish(conn, date, n, REPORT_DIR, by=g.user["full_name"])
    audit("report_generate", L.dstr(date))
    flash("Report generated.", "ok")
    return redirect(url_for("report_file", rid=rid, mode="view"))


@app.route("/reports/<int:rid>/<mode>")
@roles_required("hoa", "principal", "admin")
def report_file(rid, mode):
    r = db().execute("SELECT * FROM reports WHERE id=?", (rid,)).fetchone()
    if not r:
        abort(404)
    path = os.path.join(REPORT_DIR, os.path.basename(r["filename"]))
    if not os.path.exists(path):
        abort(404)
    return send_file(path, mimetype="application/pdf", as_attachment=(mode == "download"),
                     download_name=r["filename"])


# -------------------------------------------------------------------- admin
def _temp_password():
    return "Rche-" + secrets.token_hex(3)


@app.route("/admin/users", methods=["GET", "POST"])
@roles_required("admin")
def admin_users():
    conn = db()
    if request.method == "POST":
        username = request.form.get("username", "").strip().lower()
        name = request.form.get("full_name", "").strip()
        role = request.form.get("role", "teacher")
        if not username or not name or role not in ROLE_LABELS or " " in username:
            flash("Enter a username (no spaces), a full name and a role.", "err")
            return redirect(url_for("admin_users"))
        if conn.execute("SELECT 1 FROM users WHERE username=?", (username,)).fetchone():
            flash("That username is taken.", "err")
            return redirect(url_for("admin_users"))
        temp = _temp_password()
        conn.execute(
            "INSERT INTO users(username,full_name,role,department,phone,email,password_hash,must_change,created_at) "
            "VALUES(?,?,?,?,?,?,?,1,?)",
            (username, name[:80], role, request.form.get("department", "")[:60], request.form.get("phone", "")[:30],
             request.form.get("email", "")[:80], generate_password_hash(temp), L.ts(now())))
        conn.commit()
        audit("user_create", "%s (%s)" % (username, role))
        flash("Account created. Username: %s. Temporary password: %s. It must be changed at first sign-in." %
              (username, temp), "ok")
        return redirect(url_for("admin_users"))
    users = conn.execute("SELECT * FROM users ORDER BY active DESC, role, full_name").fetchall()
    return render_template("admin_users.html", users=users)


@app.route("/admin/users/<int:uid>", methods=["GET", "POST"])
@roles_required("admin")
def admin_user_edit(uid):
    conn = db()
    u = conn.execute("SELECT * FROM users WHERE id=?", (uid,)).fetchone()
    if not u:
        abort(404)
    if request.method == "POST":
        action = request.form.get("action", "save")
        if action == "reset":
            temp = _temp_password()
            conn.execute("UPDATE users SET password_hash=?, must_change=1, failed_count=0, locked_until=NULL WHERE id=?",
                         (generate_password_hash(temp), uid))
            conn.commit()
            audit("user_reset", u["username"])
            flash("New temporary password for %s: %s" % (u["username"], temp), "ok")
            return redirect(url_for("admin_user_edit", uid=uid))
        role = request.form.get("role", u["role"])
        active = 1 if request.form.get("active") else 0
        if uid == g.user["id"] and (not active or role != "admin"):
            flash("You cannot deactivate or demote your own account.", "err")
            return redirect(url_for("admin_user_edit", uid=uid))
        if role not in ROLE_LABELS:
            abort(400)
        conn.execute("UPDATE users SET full_name=?, role=?, department=?, phone=?, email=?, active=? WHERE id=?",
                     (request.form.get("full_name", u["full_name"]).strip()[:80], role,
                      request.form.get("department", "")[:60], request.form.get("phone", "")[:30],
                      request.form.get("email", "")[:80], active, uid))
        conn.commit()
        audit("user_edit", u["username"])
        flash("Changes saved.", "ok")
        return redirect(url_for("admin_users"))
    return render_template("admin_user_edit.html", u=u)


@app.route("/admin/settings", methods=["GET", "POST"])
@roles_required("admin")
def admin_settings():
    conn = db()
    if request.method == "POST":
        f = request.form
        for key in ("school_name", "school_short", "classes"):
            if f.get(key, "").strip():
                L.set_setting(conn, key, f[key].strip()[:120])
        for key in ("late_after", "report_time"):
            if _valid_hm(f.get(key, "")):
                L.set_setting(conn, key, f[key])
        for key, lo, hi in (("unattended_minutes", 5, 90), ("confirm_early_minutes", 0, 30)):
            try:
                L.set_setting(conn, key, max(lo, min(hi, int(f.get(key)))))
            except (TypeError, ValueError):
                pass
        L.set_setting(conn, "enforce_wifi", "1" if f.get("enforce_wifi") else "0")
        L.set_setting(conn, "auto_checkin", "1" if f.get("auto_checkin") else "0")
        if f.get("use_my_network"):
            try:
                import ipaddress
                L.set_setting(conn, "allowed_subnets", str(ipaddress.ip_network(client_ip() + "/24", strict=False)))
            except ValueError:
                flash("Could not read your IP address.", "err")
        elif f.get("allowed_subnets") is not None:
            import ipaddress
            good = []
            for part in f["allowed_subnets"].split(","):
                part = part.strip()
                if part:
                    try:
                        good.append(str(ipaddress.ip_network(part, strict=False)))
                    except ValueError:
                        flash("Skipped invalid network: %s" % part, "warn")
            L.set_setting(conn, "allowed_subnets", ",".join(good))
        audit("settings_update")
        flash("Settings saved.", "ok")
        return redirect(url_for("admin_settings"))
    s = {k: L.setting(conn, k) for k in L.DEFAULT_SETTINGS}
    return render_template("admin_settings.html", s=s, my_ip=client_ip(), now=now(),
                           real=L.real_now().strftime("%Y-%m-%dT%H:%M"))


@app.route("/admin/demo/clock", methods=["POST"])
@roles_required("admin")
def demo_clock():
    conn = db()
    if request.form.get("reset"):
        L.set_setting(conn, "demo_offset", 0)
        flash("Clock is back on real time.", "ok")
    else:
        try:
            target = dt.datetime.strptime(request.form.get("when", ""), "%Y-%m-%dT%H:%M")
            L.set_setting(conn, "demo_offset", int((target - L.real_now()).total_seconds()))
            flash("Demo clock set to %s." % target.strftime("%a %d %b, %H:%M"), "ok")
        except ValueError:
            flash("Pick a date and time.", "err")
    audit("demo_clock")
    return redirect(url_for("admin_settings"))


@app.route("/admin/demo/populate", methods=["POST"])
@roles_required("admin")
def demo_populate():
    """Fill today with sample arrivals and confirmations so the monitors have something to show."""
    import random
    conn = db()
    n = now()
    rng = random.Random(n.toordinal())
    date = n.date()
    if date.weekday() > 4:
        flash("Today is not a school day. Move the demo clock to a weekday first.", "warn")
        return redirect(url_for("admin_settings"))
    for t in L.teachers(conn) + L.users_by_role(conn, "staff"):
        if conn.execute("SELECT 1 FROM day_attendance WHERE user_id=? AND date=?", (t["id"], L.dstr(date))).fetchone():
            continue
        arrive = L.at(date, "07:20") + dt.timedelta(minutes=rng.randint(0, 55 if rng.random() > 0.2 else 80))
        if arrive > n:
            continue
        status = "late" if (arrive.hour, arrive.minute) > tuple(int(x) for x in L.setting(conn, "late_after").split(":")) else "present"
        conn.execute("INSERT INTO day_attendance(user_id,date,check_in,status,method) VALUES(?,?,?,?,?)",
                     (t["id"], L.dstr(date), arrive.strftime("%H:%M:%S"), status, "demo"))
    skip_one = None
    for l in L.annotate(L.lessons_for_date(conn, date), n, L.threshold(conn)):
        if l["start"] > n or l["confirmed"]:
            continue
        if l["status"] in ("pending", "unattended") and skip_one is None and rng.random() < 0.25:
            skip_one = l["entry_id"]
            continue
        if l["entry_id"] == skip_one:
            continue
        if not conn.execute("SELECT 1 FROM day_attendance WHERE user_id=? AND date=?", (l["eff_id"], L.dstr(date))).fetchone():
            continue
        conf = l["start"] + dt.timedelta(minutes=rng.randint(0, 6))
        if conf > n:
            conf = n
        conn.execute("INSERT OR IGNORE INTO lesson_attendance(timetable_id,date,teacher_id,confirmed_at) VALUES(?,?,?,?)",
                     (l["entry_id"], L.dstr(date), l["eff_id"], conf.strftime("%H:%M:%S")))
    conn.commit()
    audit("demo_populate")
    flash("Sample attendance added for today.", "ok")
    return redirect(url_for("admin_settings"))


@app.route("/admin/demo/clear", methods=["POST"])
@roles_required("admin")
def demo_clear():
    conn = db()
    d = L.dstr(now().date())
    for table in ("day_attendance", "lesson_attendance", "lesson_alerts"):
        conn.execute("DELETE FROM %s WHERE date=?" % table, (d,))
    conn.execute("DELETE FROM reports WHERE report_date=?", (d,))
    conn.commit()
    audit("demo_clear", d)
    flash("Today's attendance records were cleared.", "ok")
    return redirect(url_for("admin_settings"))


@app.route("/admin/audit", endpoint="audit")
@roles_required("admin", "principal")
def audit_view():
    rows = db().execute("SELECT * FROM audit_log ORDER BY id DESC LIMIT 250").fetchall()
    return render_template("audit.html", rows=rows)


# ------------------------------------------------------------------ profile
@app.route("/profile", methods=["GET", "POST"])
@login_required
def profile():
    if request.method == "POST":
        cur, new, again = (request.form.get(k, "") for k in ("current", "new", "again"))
        if not check_password_hash(g.user["password_hash"], cur):
            flash("Your current password is not correct.", "err")
        elif len(new) < 8:
            flash("Use at least 8 characters.", "err")
        elif new != again:
            flash("The new passwords do not match.", "err")
        elif new == cur:
            flash("Choose a password you have not used here before.", "err")
        else:
            db().execute("UPDATE users SET password_hash=?, must_change=0 WHERE id=?",
                         (generate_password_hash(new), g.user["id"]))
            db().commit()
            audit("password_change")
            flash("Password updated.", "ok")
            return redirect(url_for("dashboard"))
    return render_template("profile.html")


# -------------------------------------------------------------------- start
def bootstrap():
    dbm.init_db(DB_PATH, L.real_now())


bootstrap()


def lan_ip():
    try:
        s = socket.socket(socket.AF_INET, socket.SOCK_DGRAM)
        s.connect(("10.255.255.255", 1))
        ip = s.getsockname()[0]
        s.close()
        return ip
    except Exception:
        return "127.0.0.1"


if __name__ == "__main__":
    scheduler.start(DB_PATH, REPORT_DIR)
    port = int(os.environ.get("PORT", "5000"))
    print("")
    print("  RCHE Staff App is running")
    print("  On this computer : http://localhost:%d" % port)
    print("  On school Wi-Fi  : http://%s:%d" % (lan_ip(), port))
    print("  Press Ctrl+C to stop.")
    print("")
    if os.environ.get("RCHE_OPEN_BROWSER") == "1":
        threading.Timer(1.5, lambda: webbrowser.open("http://localhost:%d" % port)).start()
    try:
        from waitress import serve
        serve(app, host="0.0.0.0", port=port, threads=8)
    except ImportError:
        app.run(host="0.0.0.0", port=port, threaded=True)
