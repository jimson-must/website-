"""Business logic for the RCHE Staff App: clock, lessons, attendance, alerts."""
import os
import ipaddress
import datetime as dt

from database import DEFAULT_SETTINGS

try:
    from zoneinfo import ZoneInfo
    TZ = ZoneInfo(os.environ.get("RCHE_TZ", "Africa/Kampala"))
except Exception:  # Uganda has no daylight saving, so a fixed +3 is exact
    TZ = dt.timezone(dt.timedelta(hours=3))

DAYS = ["Monday", "Tuesday", "Wednesday", "Thursday", "Friday"]
MIN = dt.timedelta(minutes=1)


# ---------------------------------------------------------------- settings
def setting(conn, key, default=None):
    r = conn.execute("SELECT value FROM settings WHERE key=?", (key,)).fetchone()
    if r is not None:
        return r["value"]
    return DEFAULT_SETTINGS.get(key, default)


def set_setting(conn, key, value):
    conn.execute(
        "INSERT INTO settings(key,value) VALUES(?,?) ON CONFLICT(key) DO UPDATE SET value=excluded.value",
        (key, str(value)),
    )
    conn.commit()


# ------------------------------------------------------------------- clock
def real_now():
    return dt.datetime.now(TZ).replace(tzinfo=None, microsecond=0)


def app_now(conn):
    try:
        off = int(setting(conn, "demo_offset", "0") or 0)
    except ValueError:
        off = 0
    return real_now() + dt.timedelta(seconds=off)


def dstr(d):
    return d.strftime("%Y-%m-%d")


def ts(d):
    return d.strftime("%Y-%m-%d %H:%M:%S")


def at(date, hm):
    h, m = [int(x) for x in str(hm).split(":")[:2]]
    return dt.datetime.combine(date, dt.time(h, m))


def sod(d):
    return d.hour * 3600 + d.minute * 60 + d.second


def hm(v):
    if v is None or v == "":
        return ""
    if isinstance(v, (dt.datetime, dt.time)):
        return v.strftime("%H:%M")
    return str(v)[:5]


def date_label(d):
    return "%s %d %s" % (d.strftime("%a"), d.day, d.strftime("%b %Y"))


def long_date(d):
    return "%s, %d %s" % (d.strftime("%A"), d.day, d.strftime("%B %Y"))


def parse_date(s, default):
    try:
        return dt.datetime.strptime(s, "%Y-%m-%d").date()
    except (TypeError, ValueError):
        return default


def ago(then_str, now):
    try:
        then = dt.datetime.strptime(then_str, "%Y-%m-%d %H:%M:%S")
    except (TypeError, ValueError):
        return ""
    secs = int((now - then).total_seconds())
    if secs < 45:
        return "just now"
    if secs < 3600:
        return "%d min ago" % max(1, secs // 60)
    if secs < 86400:
        return "%d h ago" % (secs // 3600)
    if secs < 172800:
        return "yesterday"
    return "%d %s" % (then.day, then.strftime("%b"))


# ------------------------------------------------------------------- users
def users_by_role(conn, *roles):
    ph = ",".join("?" * len(roles))
    return conn.execute(
        "SELECT * FROM users WHERE active=1 AND role IN (%s) ORDER BY full_name" % ph, roles
    ).fetchall()


def teachers(conn):
    return users_by_role(conn, "teacher")


def leave_user_ids(conn, date):
    d = dstr(date)
    rows = conn.execute(
        "SELECT DISTINCT user_id FROM leave_requests WHERE status='approved' AND start_date<=? AND end_date>=?",
        (d, d),
    ).fetchall()
    return {r["user_id"] for r in rows}


# ----------------------------------------------------------- notifications
def notify(conn, user_id, kind, title, body="", link="", now=None):
    now = now or app_now(conn)
    conn.execute(
        "INSERT INTO notifications(user_id,kind,title,body,link,created_at) VALUES(?,?,?,?,?,?)",
        (user_id, kind, title, body, link, ts(now)),
    )


def notify_roles(conn, roles, kind, title, body="", link="", now=None, exclude=None):
    for u in users_by_role(conn, *roles):
        if exclude and u["id"] == exclude:
            continue
        notify(conn, u["id"], kind, title, body, link, now)


def notify_timetable(conn, user_id, now):
    """One rolling 'timetable updated' notice per teacher instead of one per edit."""
    recent = conn.execute(
        "SELECT id FROM notifications WHERE user_id=? AND kind='timetable' AND read_at IS NULL AND created_at>=?",
        (user_id, ts(now - 30 * MIN)),
    ).fetchone()
    if recent:
        conn.execute("UPDATE notifications SET created_at=? WHERE id=?", (ts(now), recent["id"]))
    else:
        notify(conn, user_id, "timetable", "Your timetable was updated",
               "The Director of Studies changed your timetable. Open it to review.", "/timetable", now)


# ----------------------------------------------------------------- network
def network_status(conn, ip):
    enforced = setting(conn, "enforce_wifi") == "1"
    if not enforced:
        return {"enforced": False, "ok": True, "ip": ip}
    ok = False
    try:
        addr = ipaddress.ip_address(ip)
        for part in setting(conn, "allowed_subnets", "").split(","):
            part = part.strip()
            if part and addr in ipaddress.ip_network(part, strict=False):
                ok = True
                break
    except Exception:
        ok = False
    return {"enforced": True, "ok": ok, "ip": ip}


# ----------------------------------------------------------------- periods
def periods(conn):
    return [dict(r) for r in conn.execute("SELECT * FROM periods ORDER BY start_time")]


# ------------------------------------------------------------------ lessons
_LESSON_SQL = """
SELECT t.id AS entry_id, t.class_name, t.subject, t.room, t.teacher_id,
       p.id AS period_id, p.label AS period_label, p.start_time, p.end_time,
       u.full_name AS teacher_name,
       s.sub_teacher_id, s.note AS sub_note, su.full_name AS sub_name,
       la.confirmed_at, la.teacher_id AS conf_by
FROM timetable t
JOIN periods p ON p.id = t.period_id
JOIN users u ON u.id = t.teacher_id
LEFT JOIN substitutions s ON s.timetable_id = t.id AND s.date = ?
LEFT JOIN users su ON su.id = s.sub_teacher_id
LEFT JOIN lesson_attendance la ON la.timetable_id = t.id AND la.date = ?
WHERE t.day = ? AND u.active = 1
ORDER BY p.start_time, t.class_name
"""


def lessons_for_date(conn, date):
    if date.weekday() > 4:
        return []
    rows = conn.execute(_LESSON_SQL, (dstr(date), dstr(date), date.weekday())).fetchall()
    out = []
    for r in rows:
        conf = None
        if r["confirmed_at"]:
            h, m, s = [int(x) for x in r["confirmed_at"].split(":")]
            conf = dt.datetime.combine(date, dt.time(h, m, s))
        out.append({
            "entry_id": r["entry_id"], "period_id": r["period_id"], "period": r["period_label"],
            "start": at(date, r["start_time"]), "end": at(date, r["end_time"]),
            "class_name": r["class_name"], "subject": r["subject"], "room": r["room"],
            "teacher_id": r["teacher_id"], "teacher": r["teacher_name"],
            "sub_id": r["sub_teacher_id"], "sub": r["sub_name"], "sub_note": r["sub_note"],
            "eff_id": r["sub_teacher_id"] or r["teacher_id"],
            "eff_name": r["sub_name"] or r["teacher_name"],
            "confirmed": conf, "confirmed_by": r["conf_by"],
        })
    return out


def annotate(lessons, now, threshold=30):
    for l in lessons:
        if now >= l["start"]:
            l["elapsed"] = int((now - l["start"]).total_seconds() // 60)
        else:
            l["elapsed"] = 0
        if l["confirmed"]:
            l["status"] = "attended"
            l["late_confirm"] = (l["confirmed"] - l["start"]).total_seconds() > 600
        else:
            l["late_confirm"] = False
            if now < l["start"]:
                l["status"] = "upcoming"
            elif now < l["end"]:
                l["status"] = "unattended" if l["elapsed"] >= threshold else "pending"
            else:
                l["status"] = "missed"
    return lessons


def threshold(conn):
    try:
        return int(setting(conn, "unattended_minutes", "30"))
    except ValueError:
        return 30


def my_lessons(conn, uid, date, now):
    ls = annotate(lessons_for_date(conn, date), now, threshold(conn))
    return [l for l in ls if l["eff_id"] == uid]


def status_clock(date, now):
    """Moment used to judge a day: end of day for past dates, 'now' for today."""
    if date < now.date():
        return dt.datetime.combine(date, dt.time(23, 59, 59))
    return now


# --------------------------------------------------------------- attendance
def do_checkin(conn, user_id, now, ip, method):
    d = dstr(now.date())
    existing = conn.execute("SELECT * FROM day_attendance WHERE user_id=? AND date=?", (user_id, d)).fetchone()
    if existing:
        return existing, False
    la = setting(conn, "late_after", "08:10")
    lh, lm = [int(x) for x in la.split(":")[:2]]
    status = "late" if (now.hour, now.minute) > (lh, lm) else "present"
    conn.execute(
        "INSERT INTO day_attendance(user_id,date,check_in,status,method,ip) VALUES(?,?,?,?,?,?)",
        (user_id, d, now.strftime("%H:%M:%S"), status, method, ip),
    )
    conn.commit()
    return conn.execute("SELECT * FROM day_attendance WHERE user_id=? AND date=?", (user_id, d)).fetchone(), True


def attendance_for_date(conn, date, now, group="teacher"):
    role = "teacher" if group == "teacher" else "staff"
    people = users_by_role(conn, role)
    att = {r["user_id"]: r for r in conn.execute("SELECT * FROM day_attendance WHERE date=?", (dstr(date),))}
    judge = status_clock(date, now)
    lessons = annotate(lessons_for_date(conn, date), judge, threshold(conn))
    day_over = date < now.date() or now >= at(date, setting(conn, "report_time", "17:00"))
    rows = []
    summary = {"total": len(people), "present": 0, "late": 0, "absent": 0, "not_in": 0}
    for p in people:
        a = att.get(p["id"])
        if a:
            status = a["status"]
        elif day_over and date.weekday() < 5:
            status = "absent"
        else:
            status = "not_in"
        mine = [l for l in lessons if l["eff_id"] == p["id"]]
        row = {
            "user": p, "status": status,
            "check_in": hm(a["check_in"]) if a else "", "check_out": hm(a["check_out"]) if a and a["check_out"] else "",
            "method": a["method"] if a else "",
            "scheduled": len(mine),
            "attended": sum(1 for l in mine if l["status"] == "attended"),
            "missed": sum(1 for l in mine if l["status"] in ("missed", "unattended")),
        }
        rows.append(row)
        if status in ("present", "late"):
            summary["present"] += 1
            if status == "late":
                summary["late"] += 1
        elif status in summary:
            summary[status] += 1
    summary["rate"] = round(100.0 * summary["present"] / summary["total"]) if summary["total"] else 0
    return rows, summary


def alerts_for_date(conn, date):
    rows = conn.execute(
        """SELECT a.created_at, t.class_name, t.subject, p.label AS period, p.start_time,
                  COALESCE(su.full_name, u.full_name) AS teacher, la.confirmed_at
           FROM lesson_alerts a
           JOIN timetable t ON t.id = a.timetable_id
           JOIN periods p ON p.id = t.period_id
           JOIN users u ON u.id = t.teacher_id
           LEFT JOIN substitutions s ON s.timetable_id = a.timetable_id AND s.date = a.date
           LEFT JOIN users su ON su.id = s.sub_teacher_id
           LEFT JOIN lesson_attendance la ON la.timetable_id = a.timetable_id AND la.date = a.date
           WHERE a.date = ? ORDER BY p.start_time, t.class_name""",
        (dstr(date),),
    ).fetchall()
    return [dict(r) for r in rows]


def covers_for_date(conn, date):
    rows = conn.execute(
        """SELECT p.label AS period, t.class_name, t.subject, u.full_name AS original, su.full_name AS cover, s.note
           FROM substitutions s
           JOIN timetable t ON t.id = s.timetable_id
           JOIN periods p ON p.id = t.period_id
           JOIN users u ON u.id = t.teacher_id
           JOIN users su ON su.id = s.sub_teacher_id
           WHERE s.date = ? ORDER BY p.start_time""",
        (dstr(date),),
    ).fetchall()
    return [dict(r) for r in rows]


def daily_series(conn, now, days=14):
    total = len(teachers(conn))
    out = []
    d = now.date() - dt.timedelta(days=1)
    while len(out) < days and (now.date() - d).days < 60:
        if d.weekday() < 5:
            rows = conn.execute(
                "SELECT da.status FROM day_attendance da JOIN users u ON u.id=da.user_id "
                "WHERE da.date=? AND u.role='teacher' AND u.active=1", (dstr(d),)).fetchall()
            present = len(rows)
            late = sum(1 for r in rows if r["status"] == "late")
            if present or total == 0:
                out.append({
                    "date": dstr(d), "label": "%s %d" % (d.strftime("%a")[0:3], d.day),
                    "rate": round(100.0 * present / total) if total else 0,
                    "punctual": round(100.0 * (present - late) / total) if total else 0,
                })
        d -= dt.timedelta(days=1)
    out.reverse()
    return out


def personal_history(conn, uid, now, days=30):
    """Weekday-by-weekday record for one person, newest first, plus summary stats."""
    start = now.date() - dt.timedelta(days=days)
    att = {r["date"]: r for r in conn.execute(
        "SELECT * FROM day_attendance WHERE user_id=? AND date>=?", (uid, dstr(start)))}
    rows = []
    stats = {"present": 0, "late": 0, "absent": 0, "lessons": 0, "confirmed": 0}
    d = now.date()
    while d >= start:
        if d.weekday() < 5:
            key = dstr(d)
            a = att.get(key)
            if a:
                status = a["status"]
            elif d < now.date():
                status = "absent"
            else:
                status = "not_in"
            ls = [l for l in annotate(lessons_for_date(conn, d), status_clock(d, now), threshold(conn))
                  if l["eff_id"] == uid]
            done = sum(1 for l in ls if l["status"] == "attended")
            past = sum(1 for l in ls if l["status"] in ("attended", "missed", "unattended"))
            rows.append({"date": key, "label": date_label(d), "status": status,
                         "check_in": hm(a["check_in"]) if a else "",
                         "check_out": hm(a["check_out"]) if a and a["check_out"] else "",
                         "lessons": len(ls), "attended": done})
            if status in stats:
                stats[status] += 1
            stats["lessons"] += past
            stats["confirmed"] += done
        d -= dt.timedelta(days=1)
    worked = stats["present"] + stats["late"]
    stats["punctuality"] = round(100.0 * stats["present"] / worked) if worked else 0
    stats["lesson_rate"] = round(100.0 * stats["confirmed"] / stats["lessons"]) if stats["lessons"] else 0
    return rows, stats


# ---------------------------------------------------------------- live data
def live_snapshot(conn, now):
    date = now.date()
    lessons = annotate(lessons_for_date(conn, date), now, threshold(conn))
    current = [l for l in lessons if l["start"] <= now < l["end"]]
    order = {"unattended": 0, "pending": 1, "attended": 2}
    current.sort(key=lambda l: (order.get(l["status"], 3), l["class_name"]))
    upcoming = [l for l in lessons if l["start"] > now]
    next_start = min((l["start"] for l in upcoming), default=None)
    nxt = [l for l in upcoming if l["start"] == next_start] if next_start else []
    brk = None
    for p in periods(conn):
        if p["is_break"] and at(date, p["start_time"]) <= now < at(date, p["end_time"]):
            brk = p
    return {
        "current": current, "next": nxt, "next_start": next_start, "break": brk,
        "counts": {
            "attended": sum(1 for l in current if l["status"] == "attended"),
            "pending": sum(1 for l in current if l["status"] == "pending"),
            "unattended": sum(1 for l in current if l["status"] == "unattended"),
        },
        "missed_today": sum(1 for l in lessons if l["status"] == "missed"),
        "total_today": len(lessons),
        "school_day": date.weekday() < 5,
        "alerts": alerts_for_date(conn, date),
    }


def needs_cover(conn, now):
    date = now.date()
    res = []
    for l in annotate(lessons_for_date(conn, date), now, threshold(conn)):
        if l["sub_id"] or l["status"] == "attended" or l["end"] <= now:
            continue
        if l["status"] == "unattended":
            l["reason"] = "Unattended for %d min" % l["elapsed"]
            res.append(l)
    return res


def free_teachers(conn, date, period_id):
    busy = {l["eff_id"] for l in lessons_for_date(conn, date) if l["period_id"] == period_id}
    return [t for t in teachers(conn) if t["id"] not in busy]


# ---------------------------------------------------- per-user "now" payload
def now_payload(conn, user, now, ip):
    uid = user["id"]
    d = now.date()
    att = conn.execute("SELECT * FROM day_attendance WHERE user_id=? AND date=?", (uid, dstr(d))).fetchone()
    payload = {
        "now_s": sod(now), "date": dstr(d), "weekday": now.strftime("%A"), "date_label": long_date(d),
        "role": user["role"], "school_day": d.weekday() < 5, "late_after": setting(conn, "late_after"),
        "auto_checkin": setting(conn, "auto_checkin") == "1",
        "network": network_status(conn, ip),
        "attendance": None, "lessons": [], "ribbon": [], "alert_min": threshold(conn),
    }
    if att:
        payload["attendance"] = {
            "check_in": hm(att["check_in"]), "status": att["status"],
            "check_out": hm(att["check_out"]) if att["check_out"] else None,
        }
    if user["role"] != "teacher":
        return payload

    early = int(setting(conn, "confirm_early_minutes", "5"))
    ls = my_lessons(conn, uid, d, now)

    def pack(l):
        return {
            "id": l["entry_id"], "class": l["class_name"], "subject": l["subject"], "room": l["room"],
            "period": l["period"], "start_s": sod(l["start"]), "end_s": sod(l["end"]),
            "start": hm(l["start"]), "end": hm(l["end"]), "status": l["status"],
            "confirmed": hm(l["confirmed"]) if l["confirmed"] else None, "cover": bool(l["sub_id"]),
            "can_confirm": (not l["confirmed"]) and (l["start"] - early * MIN <= now < l["end"]),
        }

    payload["lessons"] = [pack(l) for l in ls]
    by_period = {l["period_id"]: l for l in ls}
    for p in periods(conn):
        item = {"label": p["label"], "start_s": sod(at(d, p["start_time"])), "end_s": sod(at(d, p["end_time"])),
                "break": bool(p["is_break"]), "lesson": None}
        l = by_period.get(p["id"])
        if l:
            item["lesson"] = {"class": l["class_name"], "subject": l["subject"], "status": l["status"]}
        payload["ribbon"].append(item)
    return payload


# ------------------------------------------------------------------- alerts
def check_unattended(conn, now):
    """Notify Head of Academics when a lesson passes the threshold without confirmation."""
    if now.date().weekday() > 4:
        return 0
    sent = 0
    for l in annotate(lessons_for_date(conn, now.date()), now, threshold(conn)):
        if l["status"] != "unattended":
            continue
        cur = conn.execute(
            "INSERT OR IGNORE INTO lesson_alerts(timetable_id,date,created_at) VALUES(?,?,?)",
            (l["entry_id"], dstr(now.date()), ts(now)),
        )
        if cur.rowcount:
            sent += 1
            notify_roles(
                conn, ("hoa",), "alert",
                "Lesson unattended: %s, %s" % (l["class_name"], l["subject"]),
                "%s has not confirmed %s (%s-%s). %d min since it started."
                % (l["eff_name"], l["period"], hm(l["start"]), hm(l["end"]), l["elapsed"]),
                "/live", now,
            )
    conn.commit()
    return sent
