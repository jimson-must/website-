"""Background worker: unattended-lesson alerts and the end-of-day PDF."""
import threading
import time
import traceback

import database as dbm
import logic as L
import reports as R

_started = False


def tick(db_path, report_dir):
    conn = dbm.connect(db_path)
    try:
        now = L.app_now(conn)
        L.check_unattended(conn, now)
        date = now.date()
        if date.weekday() <= 4 and now >= L.at(date, L.setting(conn, "report_time", "17:00")):
            exists = conn.execute("SELECT 1 FROM reports WHERE report_date=?", (L.dstr(date),)).fetchone()
            if not exists:
                R.generate_and_publish(conn, date, now, report_dir, by="System")
    finally:
        conn.close()


def start(db_path, report_dir, interval=20):
    global _started
    if _started:
        return
    _started = True

    def loop():
        while True:
            try:
                tick(db_path, report_dir)
            except Exception:
                traceback.print_exc()
            time.sleep(interval)

    threading.Thread(target=loop, name="rche-scheduler", daemon=True).start()
