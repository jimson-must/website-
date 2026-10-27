/* RCHE Staff App front-end. No external libraries, works offline on the school network. */
(() => {
  const $ = (s, r = document) => r.querySelector(s);
  const $$ = (s, r = document) => Array.from(r.querySelectorAll(s));
  const esc = (s) => String(s ?? "").replace(/[&<>"']/g, (c) => ({ "&": "&amp;", "<": "&lt;", ">": "&gt;", '"': "&quot;", "'": "&#39;" }[c]));
  const csrf = () => ($("meta[name=csrf]") || {}).content || "";
  const pad = (n) => String(n).padStart(2, "0");
  const hm = (s) => pad(Math.floor(s / 3600) % 24) + ":" + pad(Math.floor((s % 3600) / 60));

  async function api(url, opts = {}) {
    const o = { method: opts.method || "GET", credentials: "same-origin", headers: { "X-CSRF-Token": csrf(), Accept: "application/json" } };
    if (opts.body !== undefined) { o.headers["Content-Type"] = "application/json"; o.body = JSON.stringify(opts.body); }
    const r = await fetch(url, o);
    let data = {};
    try { data = await r.json(); } catch (e) { /* not json */ }
    if (r.status === 401) { location.href = "/login"; throw new Error("signed out"); }
    if (!r.ok) { const err = new Error(data.error || "Something went wrong."); err.status = r.status; throw err; }
    return data;
  }

  /* ---------- toasts ---------- */
  function toast(msg, kind = "") {
    let box = $("#toasts");
    if (!box) { box = document.createElement("div"); box.id = "toasts"; document.body.appendChild(box); }
    const t = document.createElement("div");
    t.className = "toast " + kind; t.setAttribute("role", "status"); t.textContent = msg;
    box.appendChild(t);
    setTimeout(() => t.remove(), 6500);
  }
  window.rcheToast = toast;

  /* ---------- theme, drawer, confirms ---------- */
  const themeBtn = $("#theme-btn");
  const applyThemeIcon = () => {
    if (!themeBtn) return;
    const dark = document.documentElement.getAttribute("data-theme") === "dark";
    $(".i-sun", themeBtn).hidden = !dark; $(".i-moon", themeBtn).hidden = dark;
  };
  if (themeBtn) {
    applyThemeIcon();
    themeBtn.addEventListener("click", () => {
      const next = document.documentElement.getAttribute("data-theme") === "dark" ? "light" : "dark";
      document.documentElement.setAttribute("data-theme", next);
      try { localStorage.setItem("rche-theme", next); } catch (e) { /* ignore */ }
      applyThemeIcon();
    });
  }
  const menuBtn = $("#menu-btn");
  if (menuBtn) {
    menuBtn.addEventListener("click", () => document.body.classList.toggle("nav-open"));
    document.addEventListener("click", (e) => { if (document.body.classList.contains("nav-open") && !e.target.closest(".side") && !e.target.closest("#menu-btn")) document.body.classList.remove("nav-open"); });
  }
  document.addEventListener("submit", (e) => {
    const m = e.target.getAttribute && e.target.getAttribute("data-confirm");
    if (m && !confirm(m)) e.preventDefault();
  });
  $$(".flash[data-dismiss]").forEach((f) => setTimeout(() => f.remove(), 9000));

  /* ---------- server-synced clock ---------- */
  let baseS = parseInt(document.body.dataset.nowS || "0", 10);
  let t0 = performance.now();
  const nowS = () => baseS + (performance.now() - t0) / 1000;
  const sync = (s) => { baseS = s; t0 = performance.now(); };
  const clockEl = $("#clock");
  if (clockEl) {
    const tick = () => { const s = Math.floor(nowS()) % 86400; clockEl.textContent = pad(Math.floor(s / 3600)) + ":" + pad(Math.floor((s % 3600) / 60)) + ":" + pad(s % 60); };
    tick(); setInterval(tick, 1000);
  }

  /* ---------- notifications ---------- */
  const bellBtn = $("#bell-btn"), bellPanel = $("#bell-panel"), badge = $("#bell-badge");
  let seenMax = null;
  async function pollNotifs() {
    if (!bellBtn) return;
    try {
      const d = await api("/api/notifications");
      if (badge) { badge.textContent = d.unread > 99 ? "99+" : d.unread; badge.hidden = d.unread === 0; }
      const list = $("#bell-list");
      if (list) {
        list.innerHTML = d.items.length ? d.items.map((i) =>
          `<a class="nitem ${i.read ? "" : "unread"} ${esc(i.kind)}" href="${esc(i.link || "#")}" data-id="${i.id}"><b>${esc(i.title)}</b>${i.body ? `<span>${esc(i.body)}</span>` : ""}<small>${esc(i.ago)}</small></a>`).join("")
          : `<div class="empty"><b>You are all caught up</b>New alerts will show up here.</div>`;
      }
      const max = d.items.reduce((m, i) => Math.max(m, i.id), 0);
      if (seenMax !== null) {
        d.items.filter((i) => i.id > seenMax && !i.read).reverse().forEach((i) => {
          toast(i.title + (i.body ? ": " + i.body : ""), i.kind === "alert" ? "err" : "");
          if ("Notification" in window && Notification.permission === "granted") {
            try { new Notification(i.title, { body: i.body, icon: "/static/icons/icon-192.png" }); } catch (e) { /* ignore */ }
          }
        });
      }
      seenMax = Math.max(seenMax || 0, max);
    } catch (e) { /* offline, try again next tick */ }
  }
  if (bellBtn) {
    bellBtn.addEventListener("click", (e) => { e.stopPropagation(); bellPanel.hidden = !bellPanel.hidden; });
    document.addEventListener("click", (e) => { if (!bellPanel.hidden && !e.target.closest("#bell-panel")) bellPanel.hidden = true; });
    $("#bell-read").addEventListener("click", async () => { await api("/api/notifications/read", { method: "POST", body: {} }); pollNotifs(); });
    $("#bell-list").addEventListener("click", (e) => { const a = e.target.closest(".nitem"); if (a) api("/api/notifications/read", { method: "POST", body: { id: a.dataset.id } }).catch(() => {}); });
    pollNotifs(); setInterval(pollNotifs, 15000);
  }
  const notifBtn = $("#enable-notifs");
  if (notifBtn) {
    const paint = () => { notifBtn.textContent = !("Notification" in window) ? "Not supported on this browser" : Notification.permission === "granted" ? "Desktop alerts are on" : "Turn on desktop alerts"; };
    paint();
    notifBtn.addEventListener("click", async () => { if ("Notification" in window) { await Notification.requestPermission(); paint(); } });
  }

  /* ---------- personal "now" panel (teachers) and check-in card (everyone) ---------- */
  const nowPanel = $("#now-panel"), ciCard = $("#ci-card");
  let S = null, autoTried = false, lastKey = "";

  function buildRibbon() {
    const rb = $("#ribbon");
    if (!rb || !S || !S.ribbon.length) return;
    const a = S.ribbon[0].start_s, b = S.ribbon[S.ribbon.length - 1].end_s, span = b - a;
    rb.innerHTML = S.ribbon.map((p, i) => {
      const w = (((p.end_s - p.start_s) / span) * 100).toFixed(3);
      const cls = p.break ? "brk" : p.lesson ? "les" : "free";
      const label = p.break ? "" : p.lesson ? `<b>${esc(p.lesson.class)}</b><i>${esc(p.lesson.subject)}</i>` : "<i>Free</i>";
      return `<div class="seg ${cls}" data-i="${i}" style="flex:0 0 calc(${w}% - 3px)" title="${esc(p.label)} ${hm(p.start_s)}-${hm(p.end_s)}"><span class="fill"></span><div class="lbl">${label}</div><small>${hm(p.start_s)}</small></div>`;
    }).join("");
  }

  function paintRibbon(s) {
    $$("#ribbon .seg").forEach((el) => {
      const p = S.ribbon[+el.dataset.i];
      const pct = s <= p.start_s ? 0 : s >= p.end_s ? 100 : ((s - p.start_s) / (p.end_s - p.start_s)) * 100;
      $(".fill", el).style.width = pct + "%";
      el.classList.toggle("now", s >= p.start_s && s < p.end_s && !p.break);
      el.classList.toggle("done", s >= p.end_s);
      el.classList.toggle("ok", !!(p.lesson && p.lesson.status === "attended"));
    });
  }

  function paintNow() {
    if (!S || !nowPanel) return;
    const s = nowS();
    const cur = S.lessons.find((l) => s >= l.start_s && s < l.end_s);
    const nxt = S.lessons.find((l) => l.start_s > s);
    const brk = S.ribbon.find((p) => p.break && s >= p.start_s && s < p.end_s);
    const set = (id, v) => { const el = $("#" + id); if (el) el.innerHTML = v; };
    const show = (id, on) => { const el = $("#" + id); if (el) el.hidden = !on; };

    if (cur) {
      const total = cur.end_s - cur.start_s, el = s - cur.start_s, pct = Math.min(100, (el / total) * 100), left = Math.max(0, cur.end_s - s);
      set("np-label", `<span class="live-dot"></span>Lesson in progress`);
      set("np-title", `${esc(cur.class)} &middot; ${esc(cur.subject)}`);
      set("np-meta", `${esc(cur.period)} &middot; ${cur.start} to ${cur.end}${cur.room ? " &middot; " + esc(cur.room) : ""}${cur.cover ? " &middot; Cover" : ""}`);
      show("np-bar", true);
      $("#np-fill").style.width = pct.toFixed(2) + "%";
      set("np-left", `<b>${Math.floor(left / 60)} min ${pad(Math.floor(left % 60))} s</b> left`);
      set("np-pct", `${Math.floor(pct)}% done`);
      const unconfirmed = !cur.confirmed;
      nowPanel.classList.toggle("now-state-warn", unconfirmed && el / 60 >= S.alert_min * 0.66);
      const btn = $("#np-confirm");
      btn.hidden = !cur.can_confirm; btn.dataset.id = cur.id;
      set("np-confirmed", cur.confirmed ? `Confirmed at ${esc(cur.confirmed)}` : "");
    } else {
      show("np-bar", false); show("np-confirm", false); set("np-confirmed", ""); nowPanel.classList.remove("now-state-warn");
      if (!S.school_day) { set("np-label", "No school today"); set("np-title", "Enjoy your day off"); set("np-meta", S.date_label); }
      else if (brk) { set("np-label", "Break"); set("np-title", esc(brk.label)); set("np-meta", `Lessons resume at ${hm(brk.end_s)}`); }
      else if (nxt) { set("np-label", "Free for now"); set("np-title", "No lesson right now"); set("np-meta", `Your next lesson starts at ${nxt.start}`); }
      else if (S.lessons.length) { set("np-label", "Done for today"); set("np-title", "All lessons complete"); set("np-meta", `${S.lessons.length} lessons today`); }
      else { set("np-label", "Today"); set("np-title", "No lessons scheduled"); set("np-meta", S.date_label); }
    }
    if (nxt) {
      const d = Math.max(0, nxt.start_s - s);
      set("np-count", `${Math.floor(d / 60)}<small>min ${pad(Math.floor(d % 60))} s</small>`);
      set("np-next", `Next: <b>${esc(nxt.class)} &middot; ${esc(nxt.subject)}</b> at ${nxt.start}`);
      const early = nxt.can_confirm && !cur;
      const btn2 = $("#np-confirm"); if (early) { btn2.hidden = false; btn2.dataset.id = nxt.id; }
    } else {
      set("np-count", `&ndash;`);
      set("np-next", S.lessons.length ? "No more lessons today" : "Nothing scheduled");
    }
    paintRibbon(s);
    const key = cur ? "c" + cur.id : nxt ? "n" + nxt.id : "x";
    if (key !== lastKey) { lastKey = key; setTimeout(load, 1200); }
  }

  function paintCheckin() {
    if (!S || !ciCard) return;
    const a = S.attendance, net = S.network;
    const state = a ? "ok" : (!net.ok ? "bad" : "");
    ciCard.className = "ci " + state;
    const icon = a ? "check" : net.ok ? "wifi" : "alert";
    $("#ci-ic").innerHTML = ICON[icon];
    const title = $("#ci-title"), sub = $("#ci-sub"), inBtn = $("#ci-btn"), outBtn = $("#co-btn");
    inBtn.hidden = true; outBtn.hidden = true;
    if (!S.school_day) { title.textContent = "No school today"; sub.textContent = S.date_label; return; }
    if (a) {
      title.textContent = (a.status === "late" ? "Checked in late at " : "Checked in at ") + a.check_in;
      sub.textContent = a.check_out ? `Checked out at ${a.check_out}` : (net.enforced ? "Verified on the school Wi-Fi" : "Demo mode: Wi-Fi check is off");
      outBtn.hidden = !!a.check_out;
    } else if (net.ok) {
      title.textContent = net.enforced ? "You are on the school Wi-Fi" : "Ready to check in";
      sub.textContent = net.enforced ? "Tap to record your arrival." : `Demo mode: Wi-Fi check is off. On time until ${S.late_after}.`;
      inBtn.hidden = false;
    } else {
      title.textContent = "Not on the school Wi-Fi";
      sub.textContent = "Connect to the school network to check in.";
    }
  }

  async function autoCheckin() {
    if (autoTried || !S || S.attendance || !S.school_day) return;
    autoTried = true;
    if (S.auto_checkin && S.network.enforced && S.network.ok) {
      try { const r = await api("/api/checkin", { method: "POST", body: { auto: true } }); if (r.created) toast("Checked in automatically at " + r.time + " on the school Wi-Fi.", "ok"); await load(); } catch (e) { /* user can tap */ }
    }
  }

  async function load() {
    if (!nowPanel && !ciCard) return;
    try { S = await api("/api/me/now"); sync(S.now_s); buildRibbon(); paintCheckin(); paintNow(); autoCheckin(); } catch (e) { /* retry */ }
  }

  const ICON = {};
  $$("template[data-icon]").forEach((t) => { ICON[t.dataset.icon] = t.innerHTML; });
  if (nowPanel || ciCard) {
    load(); setInterval(load, 20000); setInterval(() => { paintNow(); paintCheckin(); }, 1000);
    const act = async (btn, url, body, ok) => {
      btn.disabled = true;
      try { const r = await api(url, { method: "POST", body }); toast(ok(r), "ok"); await load(); } catch (e) { toast(e.message, "err"); } finally { btn.disabled = false; }
    };
    const inBtn = $("#ci-btn"), outBtn = $("#co-btn"), conf = $("#np-confirm");
    if (inBtn) inBtn.addEventListener("click", () => act(inBtn, "/api/checkin", {}, (r) => "Checked in at " + r.time));
    if (outBtn) outBtn.addEventListener("click", () => act(outBtn, "/api/checkout", {}, (r) => "Checked out at " + r.time));
    if (conf) conf.addEventListener("click", () => act(conf, "/api/lesson/confirm", { entry_id: +conf.dataset.id }, (r) => "Lesson confirmed at " + r.time));
  }

  /* ---------- live board auto-refresh ---------- */
  const liveBox = $("[data-live-url]");
  if (liveBox) {
    setInterval(async () => {
      try { const r = await fetch(liveBox.dataset.liveUrl, { credentials: "same-origin" }); if (r.ok) liveBox.innerHTML = await r.text(); } catch (e) { /* ignore */ }
    }, 15000);
  }

  /* ---------- attendance chart (inline SVG) ---------- */
  $$(".chart[data-series]").forEach((el) => {
    let data = []; try { data = JSON.parse(el.dataset.series); } catch (e) { /* ignore */ }
    if (!data.length) { el.innerHTML = `<div class="empty"><b>No history yet</b>The chart fills in after the first full school day.</div>`; return; }
    const W = 760, H = 210, L = 46, R = 12, T = 20, B = 28, iw = W - L - R, ih = H - T - B, step = iw / data.length, bw = Math.min(30, step * 0.58);
    const y = (v) => T + ih - (v / 100) * ih;
    let svg = `<svg viewBox="0 0 ${W} ${H}" role="img" aria-label="Teacher attendance, last ${data.length} school days">`;
    [0, 50, 75, 100].forEach((g) => { svg += `<line class="grid-line" x1="${L}" x2="${W - R}" y1="${y(g)}" y2="${y(g)}"/><text x="${L - 8}" y="${y(g) + 4}" text-anchor="end">${g}%</text>`; });
    const pts = [];
    data.forEach((d, i) => {
      const cx = L + step * i + step / 2, h = (d.rate / 100) * ih;
      svg += `<rect class="${d.rate < 85 ? "bar-low" : "bar-ok"}" x="${cx - bw / 2}" y="${y(d.rate)}" width="${bw}" height="${h}" rx="5"><title>${esc(d.label)}: ${d.rate}% present, ${d.punctual}% on time</title></rect>`;
      if (data.length <= 16) svg += `<text class="val" x="${cx}" y="${y(d.rate) - 6}" text-anchor="middle">${d.rate}</text>`;
      svg += `<text x="${cx}" y="${H - 10}" text-anchor="middle">${esc(d.label.split(" ")[1] || d.label)}</text>`;
      pts.push([cx, y(d.punctual)]);
    });
    svg += `<polyline fill="none" stroke="#16A34A" stroke-width="2" points="${pts.map((p) => p.join(",")).join(" ")}"/>`;
    pts.forEach((p) => { svg += `<circle class="dot-p" cx="${p[0]}" cy="${p[1]}" r="3.6"/>`; });
    el.innerHTML = svg + "</svg>";
  });

  /* ---------- timetable editor modal ---------- */
  const modal = $("#cell-modal");
  if (modal) {
    const f = $("form", modal);
    $$("td[data-edit]").forEach((td) => td.addEventListener("click", () => {
      f.day.value = td.dataset.day; f.period_id.value = td.dataset.period;
      f.teacher_id.value = td.dataset.teacher || ""; f.subject.value = td.dataset.subject || ""; f.room.value = td.dataset.room || "";
      $("#cell-title").textContent = td.dataset.label;
      $("#cell-clear").hidden = !td.dataset.teacher;
      modal.hidden = false; setTimeout(() => f.teacher_id.focus(), 30);
    }));
    $$("[data-close]", modal).forEach((b) => b.addEventListener("click", () => (modal.hidden = true)));
    modal.addEventListener("click", (e) => { if (e.target === modal) modal.hidden = true; });
    document.addEventListener("keydown", (e) => { if (e.key === "Escape") modal.hidden = true; });
    f.teacher_id.addEventListener("change", () => { const o = f.teacher_id.selectedOptions[0]; if (o && !f.subject.value) f.subject.value = o.dataset.dept || ""; });
  }

  /* ---------- service worker ---------- */
  if ("serviceWorker" in navigator) navigator.serviceWorker.register("/sw.js").catch(() => {});
})();
