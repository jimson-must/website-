# RCHE Staff App (Ryakasinga CHE)

Teacher attendance on the school Wi-Fi, live lessons, timetables, announcements, cover and an end-of-day PDF for the Head of Academics.

## Run it (Windows)

1. Unzip the folder anywhere.
2. Double-click **START_RCHE.bat**.
3. The first run creates the virtual environment and installs everything (about a minute, needs internet once). Your browser opens at **http://localhost:5000**.

Next time, double-click the same file. It starts straight away.

Mac or Linux: run `./start_rche.sh`.

To open it on phones: connect them to the same Wi-Fi and use the "On school Wi-Fi" address printed in the black window (for example `http://192.168.1.20:5000`). Windows may ask to allow Python through the firewall. Click Allow for private networks.

## Demo accounts

Every account uses the password `Rche@2026` until it is changed.

| Role | Username |
|---|---|
| System administrator | `admin` |
| Principal | `principal` |
| Head of Academics | `hoa` |
| Director of Studies | `dos` |
| Teachers | `t.mugisha`, `t.atuhaire`, `t.ssemakula`, `t.namukasa`, `t.byaruhanga`, `t.nakato`, `t.kiiza`, `t.auma` |
| Non-teaching staff | `s.nabirye`, `s.mwesigwa`, `s.akello` |

Before real use: sign in as `admin`, open **Users**, reset every password, deactivate the demo accounts you do not need, and add the real staff.

## Showing it to the Principal

Sign in as `admin`, open **Settings**:

1. **Demo clock**: pick a school day at, for example, 10:45. The whole app jumps to that time, so a lesson is in progress, the green bar moves and the countdown runs.
2. **Add sample attendance**: fills today with arrivals and confirmed lessons.

Then sign in as a teacher to show the lesson timer, as `dos` for the timetable editor and cover, and as `hoa` for live lessons and the PDF. Use **Back to real time** and **Clear today** afterwards.

To see the 30-minute alert: set the demo clock to a time 35 minutes into a lesson (for example 09:55 for Period 3) without confirming it. The Head of Academics gets a notification within about 20 seconds.

## What is inside

**Teachers:** lesson in progress with a green progress bar and minutes left, countdown to the next lesson, a day ribbon, one-tap lesson confirmation, automatic Wi-Fi check-in, weekly timetable with cover shown, personal attendance and punctuality.

**Non-teaching staff:** check-in, announcements, own attendance. They never see teacher timetables, lessons or attendance.

**Director of Studies:** timetable editor with clash detection (teacher and room), editable periods and breaks, cover and substitutions for any day, automatic notice to affected teachers.

**Head of Academics:** live lessons board, alert when a lesson is unconfirmed for 30 minutes, attendance register with CSV export, daily PDF report.

**Principal:** everything above, read-only for the timetable, plus the non-teaching staff register and the audit log.

**Administrator:** users, settings, Wi-Fi rules, demo tools, audit log.

**Everyone:** announcements for all staff, teachers only, or non-teaching only (urgent and pinned options, read counts for senders), notification bell, light and dark mode, installs on a phone home screen.

## Settings you will want

In **Settings**:

- **Wi-Fi verification**: when switched on, check-in and lesson confirmation only work from the school network. Click "Use this device's network" while connected to the school Wi-Fi to fill in the range. It is off by default so the demo works on one computer.
- **Daily report time**, **late after**, **alert after (minutes)**.
- **Classes**: the class names used in the timetable.
- Optional email of the PDF: set `RCHE_SMTP_HOST`, `RCHE_SMTP_PORT`, `RCHE_SMTP_USER`, `RCHE_SMTP_PASS` and `RCHE_SMTP_FROM` as environment variables, and give the Head of Academics an email address on their user page.

## Things to know

- **How Wi-Fi attendance works.** A web app cannot read the Wi-Fi name. Instead the server checks that the request comes from the school network address range. A teacher on mobile data cannot check in. A teacher who shares their login or hotspot could, so keep accounts individual.
- **Notifications** appear while the app is open in a tab or installed app. Pushing alerts to a closed phone needs an internet-facing HTTPS server, which this local version does not include.
- **Keep the computer running** during school hours. The 30-minute alerts and the daily PDF are produced by this program, so it must be on and the window left open.
- **Time zone** is Africa/Kampala. Change with the `RCHE_TZ` environment variable.
- **Font.** The design asks for SF Pro Display. Apple does not allow it to be bundled, so Apple devices use it automatically and Windows and Android fall back to the closest system font (Segoe UI Variable or Roboto).
- **Data** lives in `instance/rche.db`. Back up that file. PDFs are in `instance/reports`.
- **No Gradle.** Gradle builds native Android apps. This is a web app that installs on phones from the browser instead, so it needs no build step.
