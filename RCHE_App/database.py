"""Database layer for the RCHE Staff App: schema, defaults and demo seed data."""
import random
import sqlite3
import datetime as dt
from werkzeug.security import generate_password_hash

DEFAULT_SETTINGS = {
    "school_name": "Ryakasinga CHE",
    "school_short": "RCHE",
    "late_after": "08:10",
    "report_time": "17:00",
    "unattended_minutes": "30",
    "confirm_early_minutes": "5",
    "enforce_wifi": "0",
    "allowed_subnets": "192.168.1.0/24",
    "auto_checkin": "1",
    "classes": "S.1,S.2,S.3,S.4,S.5,S.6",
    "demo_offset": "0",
}

SCHEMA = """
CREATE TABLE IF NOT EXISTS settings (key TEXT PRIMARY KEY, value TEXT NOT NULL);

CREATE TABLE IF NOT EXISTS users (
    id INTEGER PRIMARY KEY AUTOINCREMENT,
    username TEXT NOT NULL UNIQUE COLLATE NOCASE,
    full_name TEXT NOT NULL,
    role TEXT NOT NULL CHECK(role IN ('admin','principal','hoa','dos','teacher','staff')),
    department TEXT NOT NULL DEFAULT '',
    phone TEXT NOT NULL DEFAULT '',
    email TEXT NOT NULL DEFAULT '',
    password_hash TEXT NOT NULL,
    active INTEGER NOT NULL DEFAULT 1,
    must_change INTEGER NOT NULL DEFAULT 0,
    failed_count INTEGER NOT NULL DEFAULT 0,
    locked_until TEXT,
    last_login TEXT,
    created_at TEXT NOT NULL
);

CREATE TABLE IF NOT EXISTS periods (
    id INTEGER PRIMARY KEY AUTOINCREMENT,
    label TEXT NOT NULL,
    start_time TEXT NOT NULL,
    end_time TEXT NOT NULL,
    is_break INTEGER NOT NULL DEFAULT 0
);

CREATE TABLE IF NOT EXISTS timetable (
    id INTEGER PRIMARY KEY AUTOINCREMENT,
    day INTEGER NOT NULL CHECK(day BETWEEN 0 AND 4),
    period_id INTEGER NOT NULL REFERENCES periods(id) ON DELETE CASCADE,
    teacher_id INTEGER NOT NULL REFERENCES users(id),
    class_name TEXT NOT NULL,
    subject TEXT NOT NULL,
    room TEXT NOT NULL DEFAULT '',
    UNIQUE(day, period_id, class_name),
    UNIQUE(day, period_id, teacher_id)
);

CREATE TABLE IF NOT EXISTS substitutions (
    id INTEGER PRIMARY KEY AUTOINCREMENT,
    timetable_id INTEGER NOT NULL REFERENCES timetable(id) ON DELETE CASCADE,
    date TEXT NOT NULL,
    sub_teacher_id INTEGER NOT NULL REFERENCES users(id),
    note TEXT NOT NULL DEFAULT '',
    created_by INTEGER REFERENCES users(id),
    created_at TEXT NOT NULL,
    UNIQUE(timetable_id, date)
);

CREATE TABLE IF NOT EXISTS day_attendance (
    id INTEGER PRIMARY KEY AUTOINCREMENT,
    user_id INTEGER NOT NULL REFERENCES users(id),
    date TEXT NOT NULL,
    check_in TEXT NOT NULL,
    check_out TEXT,
    status TEXT NOT NULL CHECK(status IN ('present','late')),
    method TEXT NOT NULL DEFAULT '',
    ip TEXT NOT NULL DEFAULT '',
    UNIQUE(user_id, date)
);

CREATE TABLE IF NOT EXISTS lesson_attendance (
    id INTEGER PRIMARY KEY AUTOINCREMENT,
    timetable_id INTEGER NOT NULL REFERENCES timetable(id) ON DELETE CASCADE,
    date TEXT NOT NULL,
    teacher_id INTEGER NOT NULL REFERENCES users(id),
    confirmed_at TEXT NOT NULL,
    ip TEXT NOT NULL DEFAULT '',
    UNIQUE(timetable_id, date)
);

CREATE TABLE IF NOT EXISTS lesson_alerts (
    id INTEGER PRIMARY KEY AUTOINCREMENT,
    timetable_id INTEGER NOT NULL REFERENCES timetable(id) ON DELETE CASCADE,
    date TEXT NOT NULL,
    created_at TEXT NOT NULL,
    UNIQUE(timetable_id, date)
);

CREATE TABLE IF NOT EXISTS announcements (
    id INTEGER PRIMARY KEY AUTOINCREMENT,
    title TEXT NOT NULL,
    body TEXT NOT NULL,
    audience TEXT NOT NULL DEFAULT 'all' CHECK(audience IN ('all','teachers','staff')),
    priority TEXT NOT NULL DEFAULT 'normal' CHECK(priority IN ('normal','urgent')),
    pinned INTEGER NOT NULL DEFAULT 0,
    author_id INTEGER REFERENCES users(id),
    created_at TEXT NOT NULL
);

CREATE TABLE IF NOT EXISTS announcement_reads (
    announcement_id INTEGER NOT NULL REFERENCES announcements(id) ON DELETE CASCADE,
    user_id INTEGER NOT NULL REFERENCES users(id),
    read_at TEXT NOT NULL,
    PRIMARY KEY (announcement_id, user_id)
);

CREATE TABLE IF NOT EXISTS notifications (
    id INTEGER PRIMARY KEY AUTOINCREMENT,
    user_id INTEGER NOT NULL REFERENCES users(id),
    kind TEXT NOT NULL,
    title TEXT NOT NULL,
    body TEXT NOT NULL DEFAULT '',
    link TEXT NOT NULL DEFAULT '',
    created_at TEXT NOT NULL,
    read_at TEXT
);
CREATE INDEX IF NOT EXISTS idx_notif_user ON notifications(user_id, read_at);

CREATE TABLE IF NOT EXISTS leave_requests (
    id INTEGER PRIMARY KEY AUTOINCREMENT,
    user_id INTEGER NOT NULL REFERENCES users(id),
    start_date TEXT NOT NULL,
    end_date TEXT NOT NULL,
    kind TEXT NOT NULL,
    reason TEXT NOT NULL DEFAULT '',
    status TEXT NOT NULL DEFAULT 'pending' CHECK(status IN ('pending','approved','declined','cancelled')),
    decided_by INTEGER REFERENCES users(id),
    decided_at TEXT,
    decision_note TEXT NOT NULL DEFAULT '',
    created_at TEXT NOT NULL
);

CREATE TABLE IF NOT EXISTS reports (
    id INTEGER PRIMARY KEY AUTOINCREMENT,
    report_date TEXT NOT NULL UNIQUE,
    filename TEXT NOT NULL,
    generated_at TEXT NOT NULL,
    generated_by TEXT NOT NULL DEFAULT 'System',
    emailed INTEGER NOT NULL DEFAULT 0
);

CREATE TABLE IF NOT EXISTS audit_log (
    id INTEGER PRIMARY KEY AUTOINCREMENT,
    user_id INTEGER,
    username TEXT NOT NULL DEFAULT '',
    action TEXT NOT NULL,
    detail TEXT NOT NULL DEFAULT '',
    ip TEXT NOT NULL DEFAULT '',
    created_at TEXT NOT NULL
);
"""

DEMO_PASSWORD = "Rche@2026"

PERIODS = [
    ("Period 1", "08:00", "08:40", 0),
    ("Period 2", "08:40", "09:20", 0),
    ("Period 3", "09:20", "10:00", 0),
    ("Break", "10:00", "10:30", 1),
    ("Period 4", "10:30", "11:10", 0),
    ("Period 5", "11:10", "11:50", 0),
    ("Period 6", "11:50", "12:30", 0),
    ("Lunch", "12:30", "14:00", 1),
    ("Period 7", "14:00", "14:40", 0),
    ("Period 8", "14:40", "15:20", 0),
    ("Period 9", "15:20", "16:00", 0),
]

LEADERS = [
    ("admin", "Daniel Opio", "admin", "ICT"),
    ("principal", "Mr. Samuel Mwebaze", "principal", "Administration"),
    ("hoa", "Mrs. Agnes Kobusingye", "hoa", "Academics"),
    ("dos", "Mr. Charles Okello", "dos", "Academics"),
]

TEACHERS = [
    ("t.mugisha", "Joseph Mugisha", "Mathematics"),
    ("t.atuhaire", "Grace Atuhaire", "English"),
    ("t.ssemakula", "David Ssemakula", "Physics"),
    ("t.namukasa", "Ruth Namukasa", "Chemistry"),
    ("t.byaruhanga", "Peter Byaruhanga", "Biology"),
    ("t.nakato", "Esther Nakato", "History"),
    ("t.kiiza", "Moses Kiiza", "Geography"),
    ("t.auma", "Sarah Auma", "Computer Studies"),
]

NON_TEACHING = [
    ("s.nabirye", "Florence Nabirye", "Bursary"),
    ("s.mwesigwa", "Isaac Mwesigwa", "Library"),
    ("s.akello", "Betty Akello", "Front office"),
]


def connect(path):
    conn = sqlite3.connect(path, timeout=15, check_same_thread=False)
    conn.row_factory = sqlite3.Row
    conn.execute("PRAGMA foreign_keys=ON")
    try:
        conn.execute("PRAGMA journal_mode=WAL")
    except sqlite3.DatabaseError:
        pass
    return conn


def init_db(path, now):
    conn = connect(path)
    conn.executescript(SCHEMA)
    conn.commit()
    if conn.execute("SELECT COUNT(*) FROM users").fetchone()[0] == 0:
        seed_demo(conn, now)
    conn.close()


def _ts(d):
    return d.strftime("%Y-%m-%d %H:%M:%S")


def seed_demo(conn, now):
    rng = random.Random(2026)
    created = _ts(now)
    pw = generate_password_hash(DEMO_PASSWORD)
    for k, v in DEFAULT_SETTINGS.items():
        conn.execute("INSERT OR IGNORE INTO settings(key,value) VALUES(?,?)", (k, v))

    def add_user(username, name, role, dept):
        cur = conn.execute(
            "INSERT INTO users(username,full_name,role,department,phone,password_hash,created_at) "
            "VALUES(?,?,?,?,?,?,?)",
            (username, name, role, dept, "07" + str(rng.randint(10000000, 99999999)), pw, created),
        )
        return cur.lastrowid

    for u, n, r, d in LEADERS:
        add_user(u, n, r, d)
    teacher_ids = [add_user(u, n, "teacher", d) for u, n, d in TEACHERS]
    staff_ids = [add_user(u, n, "staff", d) for u, n, d in NON_TEACHING]

    period_ids = []
    for label, s, e, brk in PERIODS:
        cur = conn.execute(
            "INSERT INTO periods(label,start_time,end_time,is_break) VALUES(?,?,?,?)", (label, s, e, brk)
        )
        period_ids.append((cur.lastrowid, brk))

    classes = DEFAULT_SETTINGS["classes"].split(",")
    lesson_periods = [pid for pid, brk in period_ids if not brk]
    for day in range(5):
        for p_index, pid in enumerate(lesson_periods):
            for c_index, cls in enumerate(classes):
                if (p_index * 7 + c_index * 3 + day * 5) % 10 < 3:
                    continue  # leave some free periods
                t_index = (p_index + c_index + day) % len(teacher_ids)
                subject = TEACHERS[t_index][2]
                room = "ICT Lab" if subject == "Computer Studies" else "Room %d" % (c_index + 1)
                conn.execute(
                    "INSERT INTO timetable(day,period_id,teacher_id,class_name,subject,room) VALUES(?,?,?,?,?,?)",
                    (day, pid, teacher_ids[t_index], cls, subject, room),
                )

    # --- history so charts, reports and profiles are not empty ---
    entries = {}
    for r in conn.execute(
        "SELECT t.id, t.day, t.teacher_id, p.start_time FROM timetable t JOIN periods p ON p.id=t.period_id"
    ):
        entries.setdefault((r["day"], r["teacher_id"]), []).append((r["id"], r["start_time"]))

    day = now.date() - dt.timedelta(days=1)
    seeded = 0
    while seeded < 24:
        if day.weekday() < 5:
            seeded += 1
            for tid in teacher_ids + staff_ids:
                roll = rng.random()
                if roll < 0.05:
                    continue  # absent
                if roll < 0.16:
                    mins = rng.randint(11, 45)  # late
                    status = "late"
                    ci = dt.datetime.combine(day, dt.time(8, 0)) + dt.timedelta(minutes=mins)
                else:
                    ci = dt.datetime.combine(day, dt.time(7, 15)) + dt.timedelta(minutes=rng.randint(0, 53))
                    status = "present"
                co = dt.datetime.combine(day, dt.time(16, 5)) + dt.timedelta(minutes=rng.randint(0, 40))
                conn.execute(
                    "INSERT INTO day_attendance(user_id,date,check_in,check_out,status,method) VALUES(?,?,?,?,?,?)",
                    (tid, day.isoformat(), ci.strftime("%H:%M:%S"), co.strftime("%H:%M:%S"), status, "wifi-auto"),
                )
                for eid, st in entries.get((day.weekday(), tid), []):
                    if rng.random() < 0.96:
                        h, m = map(int, st.split(":"))
                        conf = dt.datetime.combine(day, dt.time(h, m)) + dt.timedelta(minutes=rng.randint(-3, 7))
                        conn.execute(
                            "INSERT OR IGNORE INTO lesson_attendance(timetable_id,date,teacher_id,confirmed_at) "
                            "VALUES(?,?,?,?)",
                            (eid, day.isoformat(), tid, conf.strftime("%H:%M:%S")),
                        )
        day -= dt.timedelta(days=1)

    admin_id = conn.execute("SELECT id FROM users WHERE username='principal'").fetchone()["id"]
    hoa_id = conn.execute("SELECT id FROM users WHERE username='hoa'").fetchone()["id"]
    dos_id = conn.execute("SELECT id FROM users WHERE username='dos'").fetchone()["id"]
    anns = [
        ("Welcome to the RCHE Staff App",
         "Check in each morning on the school Wi-Fi, confirm every lesson when you reach the class, "
         "and watch this space for announcements. Your timetable is always up to date here.",
         "all", "normal", 1, admin_id, now - dt.timedelta(days=2)),
        ("Staff meeting this Friday",
         "All teaching and non-teaching staff are asked to attend the staff meeting at 4:00 PM in the staffroom.",
         "all", "urgent", 0, admin_id, now - dt.timedelta(hours=5)),
        ("Mid-term assessment submission",
         "Teachers should submit mid-term assessment scripts and marks to the Head of Academics by Wednesday.",
         "teachers", "normal", 0, hoa_id, now - dt.timedelta(days=1)),
        ("Fee collection reconciliation",
         "Bursary and front office: please finalise the weekly reconciliation before close of business Thursday.",
         "staff", "normal", 0, admin_id, now - dt.timedelta(days=1, hours=3)),
        ("Timetable adjustments",
         "The DOS will publish adjustments to the timetable when needed. Affected teachers are notified automatically.",
         "teachers", "normal", 0, dos_id, now - dt.timedelta(hours=20)),
    ]
    for t, b, a, p, pin, au, c in anns:
        conn.execute(
            "INSERT INTO announcements(title,body,audience,priority,pinned,author_id,created_at) VALUES(?,?,?,?,?,?,?)",
            (t, b, a, p, pin, au, _ts(c)),
        )

    kiiza = conn.execute("SELECT id FROM users WHERE username='t.kiiza'").fetchone()["id"]
    tomorrow = now.date() + dt.timedelta(days=1)
    conn.execute(
        "INSERT INTO leave_requests(user_id,start_date,end_date,kind,reason,created_at) VALUES(?,?,?,?,?,?)",
        (kiiza, tomorrow.isoformat(), tomorrow.isoformat(), "Personal", "Family matter, one day.", created),
    )
    conn.commit()
