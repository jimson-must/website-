"""Daily teacher attendance PDF for the Head of Academics."""
import os
import smtplib
import ssl
from email.message import EmailMessage
from xml.sax.saxutils import escape

from reportlab.lib import colors
from reportlab.lib.pagesizes import A4
from reportlab.lib.styles import ParagraphStyle
from reportlab.lib.units import mm
from reportlab.lib.enums import TA_CENTER
from reportlab.platypus import SimpleDocTemplate, Paragraph, Spacer, Table, TableStyle, KeepTogether

import logic as L

NAVY = colors.HexColor("#0B1F44")
BLUE = colors.HexColor("#1747B8")
RED = colors.HexColor("#D6192F")
GREEN = colors.HexColor("#16A34A")
AMBER = colors.HexColor("#C77700")
INK = colors.HexColor("#0F1B33")
MUTED = colors.HexColor("#5B6783")
LINE = colors.HexColor("#DDE3F0")
ZEBRA = colors.HexColor("#F5F7FC")

STATUS = {
    "present": ("Present", "#16A34A"), "late": ("Late", "#C77700"), "absent": ("Absent", "#D6192F"),
    "not_in": ("Not in", "#5B6783"),
}


def _styles():
    base = ParagraphStyle("base", fontName="Helvetica", fontSize=8.5, leading=11, textColor=INK)
    return {
        "base": base,
        "h1": ParagraphStyle("h1", parent=base, fontName="Helvetica-Bold", fontSize=19, leading=23, textColor=NAVY),
        "h2": ParagraphStyle("h2", parent=base, fontName="Helvetica-Bold", fontSize=11.5, leading=14, textColor=NAVY,
                             spaceBefore=12, spaceAfter=5),
        "muted": ParagraphStyle("muted", parent=base, textColor=MUTED),
        "cell": ParagraphStyle("cell", parent=base, fontSize=8.3, leading=10.5),
        "head": ParagraphStyle("head", parent=base, fontName="Helvetica-Bold", fontSize=8, textColor=colors.white),
        "num": ParagraphStyle("num", parent=base, fontName="Helvetica-Bold", fontSize=20, leading=24, alignment=TA_CENTER),
        "lab": ParagraphStyle("lab", parent=base, fontSize=7.8, alignment=TA_CENTER, textColor=MUTED),
    }


def _p(text, style):
    return Paragraph(escape(str(text)), style)


def build_pdf(path, school, date, now, rows, summary, alerts, covers):
    st = _styles()
    doc = SimpleDocTemplate(path, pagesize=A4, leftMargin=15 * mm, rightMargin=15 * mm, topMargin=36 * mm,
                            bottomMargin=18 * mm, title="Daily Teacher Attendance - %s" % L.dstr(date),
                            author=school)
    W = A4[0] - 30 * mm

    def deco(canvas, d):
        canvas.saveState()
        w, h = A4
        canvas.setFillColor(NAVY)
        canvas.rect(0, h - 27 * mm, w, 27 * mm, fill=1, stroke=0)
        canvas.setFillColor(RED)
        canvas.rect(0, h - 29 * mm, w, 2 * mm, fill=1, stroke=0)
        x, y = 15 * mm, h - 22.5 * mm
        p = canvas.beginPath()
        p.moveTo(x + 6.5 * mm, y + 14 * mm)
        p.lineTo(x, y + 12 * mm)
        p.lineTo(x, y + 6 * mm)
        p.curveTo(x, y + 2 * mm, x + 3.5 * mm, y + 0.5 * mm, x + 6.5 * mm, y)
        p.curveTo(x + 9.5 * mm, y + 0.5 * mm, x + 13 * mm, y + 2 * mm, x + 13 * mm, y + 6 * mm)
        p.lineTo(x + 13 * mm, y + 12 * mm)
        p.close()
        canvas.setFillColor(BLUE)
        canvas.drawPath(p, fill=1, stroke=0)
        canvas.setFillColor(colors.white)
        canvas.setFont("Helvetica-Bold", 11)
        canvas.drawCentredString(x + 6.5 * mm, y + 4.2 * mm, "R")
        canvas.setFont("Helvetica-Bold", 15)
        canvas.drawString(34 * mm, h - 13 * mm, school)
        canvas.setFont("Helvetica", 9)
        canvas.setFillColor(colors.HexColor("#B9C8EE"))
        canvas.drawString(34 * mm, h - 19 * mm, "Staff attendance and lesson monitoring")
        canvas.setFillColor(colors.white)
        canvas.setFont("Helvetica-Bold", 10)
        canvas.drawRightString(w - 15 * mm, h - 13 * mm, L.date_label(date))
        canvas.setFont("Helvetica", 8.5)
        canvas.setFillColor(colors.HexColor("#B9C8EE"))
        canvas.drawRightString(w - 15 * mm, h - 19 * mm, "Generated %s" % now.strftime("%H:%M"))
        canvas.setStrokeColor(LINE)
        canvas.line(15 * mm, 13 * mm, w - 15 * mm, 13 * mm)
        canvas.setFillColor(MUTED)
        canvas.setFont("Helvetica", 7.5)
        canvas.drawString(15 * mm, 9 * mm, "Confidential. Prepared for the Head of Academics.")
        canvas.drawRightString(w - 15 * mm, 9 * mm, "Page %d" % d.page)
        canvas.restoreState()

    story = [_p("Daily teacher attendance report", st["h1"]),
             _p(L.long_date(date), st["muted"]), Spacer(1, 6 * mm)]

    # KPI strip
    kp = [("Teachers", summary["total"], NAVY), ("Present", summary["present"], GREEN),
          ("Late", summary["late"], AMBER), ("Absent", summary["absent"] + summary["not_in"], RED),
          ("Attendance", "%d%%" % summary["rate"], BLUE)]
    nums = [Paragraph('<font color="%s">%s</font>' % (c.hexval().replace("0x", "#"), v), st["num"]) for _, v, c in kp]
    labs = [_p(n, st["lab"]) for n, _, _ in kp]
    t = Table([nums, labs], colWidths=[W / float(len(kp))] * len(kp))
    style = [("BOX", (0, 0), (-1, -1), 0.6, LINE), ("INNERGRID", (0, 0), (-1, -1), 0.4, LINE),
             ("TOPPADDING", (0, 0), (-1, 0), 7), ("BOTTOMPADDING", (0, 1), (-1, 1), 6),
             ("VALIGN", (0, 0), (-1, -1), "MIDDLE")]
    for i, (_, _, c) in enumerate(kp):
        style.append(("LINEABOVE", (i, 0), (i, 0), 2.2, c))
    t.setStyle(TableStyle(style))
    story += [t]

    # Register
    story.append(_p("Attendance register", st["h2"]))
    head = [_p(h, st["head"]) for h in ("#", "Teacher", "Department", "Check-in", "Check-out", "Status", "Lessons")]
    data = [head]
    for i, r in enumerate(rows, 1):
        label, hexc = STATUS.get(r["status"], (r["status"], "#0F1B33"))
        lessons = "%d / %d" % (r["attended"], r["scheduled"]) if r["scheduled"] else "-"
        data.append([
            _p(i, st["cell"]), _p(r["user"]["full_name"], st["cell"]), _p(r["user"]["department"], st["cell"]),
            _p(r["check_in"] or "-", st["cell"]), _p(r["check_out"] or "-", st["cell"]),
            Paragraph('<font color="%s"><b>%s</b></font>' % (hexc, label), st["cell"]), _p(lessons, st["cell"]),
        ])
    cw = [9 * mm, 50 * mm, 34 * mm, 21 * mm, 21 * mm, 23 * mm, W - 158 * mm]
    reg = Table(data, colWidths=cw, repeatRows=1)
    rs = [("BACKGROUND", (0, 0), (-1, 0), NAVY), ("LINEBELOW", (0, 0), (-1, -1), 0.4, LINE),
          ("TOPPADDING", (0, 0), (-1, -1), 4.5), ("BOTTOMPADDING", (0, 0), (-1, -1), 4.5),
          ("VALIGN", (0, 0), (-1, -1), "MIDDLE")]
    for i in range(2, len(data), 2):
        rs.append(("BACKGROUND", (0, i), (-1, i), ZEBRA))
    reg.setStyle(TableStyle(rs))
    story.append(reg)

    # Alerts
    story.append(_p("Lesson alerts", st["h2"]))
    if alerts:
        d = [[_p(h, st["head"]) for h in ("Period", "Class", "Subject", "Teacher", "Outcome")]]
        for a in alerts:
            if a["confirmed_at"]:
                outcome = '<font color="#C77700"><b>Started late</b></font> (confirmed %s)' % a["confirmed_at"][:5]
            else:
                outcome = '<font color="#D6192F"><b>Never confirmed</b></font>'
            d.append([_p("%s, %s" % (a["period"], a["start_time"]), st["cell"]), _p(a["class_name"], st["cell"]),
                      _p(a["subject"], st["cell"]), _p(a["teacher"], st["cell"]), Paragraph(outcome, st["cell"])])
        at_ = Table(d, colWidths=[34 * mm, 18 * mm, 32 * mm, 46 * mm, W - 130 * mm], repeatRows=1)
        at_.setStyle(TableStyle([("BACKGROUND", (0, 0), (-1, 0), RED), ("LINEBELOW", (0, 0), (-1, -1), 0.4, LINE),
                                 ("TOPPADDING", (0, 0), (-1, -1), 4.5), ("BOTTOMPADDING", (0, 0), (-1, -1), 4.5),
                                 ("VALIGN", (0, 0), (-1, -1), "MIDDLE")]))
        story.append(at_)
    else:
        story.append(_p("No lessons went unattended past the alert threshold today.", st["muted"]))

    # Covers
    if covers:
        story.append(_p("Cover arrangements", st["h2"]))
        d = [[_p(h, st["head"]) for h in ("Period", "Class", "Subject", "Original teacher", "Cover teacher")]]
        for c in covers:
            d.append([_p(c["period"], st["cell"]), _p(c["class_name"], st["cell"]), _p(c["subject"], st["cell"]),
                      _p(c["original"], st["cell"]), _p(c["cover"], st["cell"])])
        ct = Table(d, colWidths=[28 * mm, 18 * mm, 34 * mm, 50 * mm, W - 130 * mm], repeatRows=1)
        ct.setStyle(TableStyle([("BACKGROUND", (0, 0), (-1, 0), BLUE), ("LINEBELOW", (0, 0), (-1, -1), 0.4, LINE),
                                ("TOPPADDING", (0, 0), (-1, -1), 4.5), ("BOTTOMPADDING", (0, 0), (-1, -1), 4.5)]))
        story.append(ct)

    sig = Table([[_p("Head of Academics", st["muted"]), _p("Signature", st["muted"]), _p("Date", st["muted"])]],
                colWidths=[W * 0.4, W * 0.35, W * 0.25])
    sig.setStyle(TableStyle([("LINEABOVE", (0, 0), (-1, 0), 0.6, MUTED), ("TOPPADDING", (0, 0), (-1, 0), 4)]))
    story.append(Spacer(1, 14 * mm))
    story.append(KeepTogether([sig]))

    doc.build(story, onFirstPage=deco, onLaterPages=deco)


def generate_and_publish(conn, date, now, out_dir, by="System"):
    """Build the PDF, record it, notify leadership, and email it when SMTP is configured."""
    os.makedirs(out_dir, exist_ok=True)
    school = L.setting(conn, "school_name")
    rows, summary = L.attendance_for_date(conn, date, now, "teacher")
    alerts = L.alerts_for_date(conn, date)
    covers = L.covers_for_date(conn, date)
    filename = "RCHE_Teacher_Attendance_%s.pdf" % L.dstr(date)
    path = os.path.join(out_dir, filename)
    build_pdf(path, school, date, now, rows, summary, alerts, covers)

    conn.execute("DELETE FROM reports WHERE report_date=?", (L.dstr(date),))
    cur = conn.execute(
        "INSERT INTO reports(report_date,filename,generated_at,generated_by) VALUES(?,?,?,?)",
        (L.dstr(date), filename, L.ts(now), by))
    rid = cur.lastrowid
    L.notify_roles(conn, ("hoa", "principal"), "report",
                   "Attendance report ready: %s" % L.date_label(date),
                   "%d of %d teachers present, %d late, %d absent."
                   % (summary["present"], summary["total"], summary["late"], summary["absent"]),
                   "/reports/%d/view" % rid, now)
    conn.commit()
    if _email(conn, path, date, summary):
        conn.execute("UPDATE reports SET emailed=1 WHERE id=?", (rid,))
        conn.commit()
    return rid


def _email(conn, path, date, summary):
    host = os.environ.get("RCHE_SMTP_HOST")
    if not host:
        return False
    to = [u["email"] for u in L.users_by_role(conn, "hoa") if u["email"]]
    if not to:
        return False
    try:
        msg = EmailMessage()
        msg["Subject"] = "Teacher attendance report - %s" % L.date_label(date)
        msg["From"] = os.environ.get("RCHE_SMTP_FROM", os.environ.get("RCHE_SMTP_USER", "rche@localhost"))
        msg["To"] = ", ".join(to)
        msg.set_content("Attached is the daily teacher attendance report. %d of %d teachers present."
                        % (summary["present"], summary["total"]))
        with open(path, "rb") as f:
            msg.add_attachment(f.read(), maintype="application", subtype="pdf", filename=os.path.basename(path))
        port = int(os.environ.get("RCHE_SMTP_PORT", "587"))
        with smtplib.SMTP(host, port, timeout=20) as s:
            s.starttls(context=ssl.create_default_context())
            if os.environ.get("RCHE_SMTP_USER"):
                s.login(os.environ["RCHE_SMTP_USER"], os.environ.get("RCHE_SMTP_PASS", ""))
            s.send_message(msg)
        return True
    except Exception:
        return False
