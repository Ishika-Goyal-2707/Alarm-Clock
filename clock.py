#!/usr/bin/env python3
import http.server
import socketserver
import threading
import json
import os
import time
from urllib.parse import urlparse, parse_qs
from datetime import datetime
import webbrowser

# ───── Audio (pygame) ─────
import pygame

# You can tweak these if your device needs different values
# (common defaults work for most Windows laptops)
try:
    pygame.mixer.init()   # frequency=44100, size=-16, channels=2, buffer=512
    AUDIO_OK = True
except Exception as e:
    print("⚠️  pygame.mixer.init() failed:", e)
    AUDIO_OK = False

# ───── Config ─────
PORT = 8000
SCRIPT_DIR = os.path.dirname(os.path.abspath(__file__))

# Prefer your known music folder; fallback to ./music next to this script
USER_MUSIC_DIR = r"E:\Ishika\alarm clock\music"
MUSIC_DIR = USER_MUSIC_DIR if os.path.isdir(USER_MUSIC_DIR) else os.path.join(SCRIPT_DIR, "music")

ALARM_FILE = os.path.join(SCRIPT_DIR, "alarm_settings.json")

# ───── State ─────
RINGING = False
STOPPED_THIS_MINUTE = None      # stores "HH:MM AM/PM" of stop time to avoid immediate re-start
LOCK = threading.Lock()         # protects RINGING & STOPPED_THIS_MINUTE

# ───── Helpers ─────
def list_ringtones():
    """Return absolute paths to mp3/wav files in MUSIC_DIR."""
    if not os.path.isdir(MUSIC_DIR):
        return []
    files = []
    for name in os.listdir(MUSIC_DIR):
        if name.lower().endswith((".mp3", ".wav")):
            files.append(os.path.join(MUSIC_DIR, name))
    files.sort()
    return files

def load_alarm():
    if not os.path.exists(ALARM_FILE):
        return {}
    try:
        with open(ALARM_FILE, "r", encoding="utf-8") as f:
            return json.load(f)
    except Exception:
        return {}

def save_alarm_obj(obj):
    with open(ALARM_FILE, "w", encoding="utf-8") as f:
        json.dump(obj, f, indent=2)

def normalize_time(hour_str, min_str, ampm_str):
    """Return ('HH','MM','AM/PM') normalized and a combined 'HH:MM AM/PM' string."""
    try:
        h = int(hour_str)
    except Exception:
        h = 7
    try:
        m = int(min_str)
    except Exception:
        m = 0

    h = max(1, min(12, h))
    m = max(0, min(59, m))
    ampm = "AM" if str(ampm_str).strip().upper() != "PM" else "PM"
    return f"{h:02d}", f"{m:02d}", ampm, f"{h:02d}:{m:02d} {ampm}"

def current_h_m_ampm():
    now = datetime.now()
    hour12 = now.strftime("%I")  # 01..12
    minute = now.strftime("%M")
    ampm = now.strftime("%p")    # AM/PM
    return hour12, minute, ampm

def play_loop(path):
    """Start looping playback via pygame.mixer.music."""
    global RINGING
    if not AUDIO_OK:
        print("❌ Audio device not initialized; cannot play.")
        return
    try:
        pygame.mixer.music.load(path)
        pygame.mixer.music.play(-1)  # loop indefinitely
        with LOCK:
            RINGING = True
        print(f"🔊 Ringing (looping): {path}")
    except Exception as e:
        print("⚠️  Failed to play:", e)
        with LOCK:
            RINGING = False

def stop_playback():
    """Stop playback and mark this minute as stopped."""
    global RINGING, STOPPED_THIS_MINUTE
    with LOCK:
        if RINGING and AUDIO_OK:
            try:
                pygame.mixer.music.stop()
            except Exception:
                pass
        RINGING = False
        STOPPED_THIS_MINUTE = datetime.now().strftime("%I:%M %p")
    print(f"⏹️  Alarm stopped for {STOPPED_THIS_MINUTE}")

def resolve_tone_path(tone_path):
    """Return an existing absolute path for the ringtone or None."""
    if not tone_path:
        return None
    candidates = []
    # If absolute and exists, use it.
    if os.path.isabs(tone_path):
        candidates.append(tone_path)
    # Try as-is relative to music dir and script dir
    candidates.append(os.path.join(MUSIC_DIR, tone_path))
    candidates.append(os.path.join(SCRIPT_DIR, tone_path))
    # Also: if tone_path already contains MUSIC_DIR, just check it
    if tone_path.startswith(MUSIC_DIR):
        candidates.insert(0, tone_path)

    for p in candidates:
        if os.path.exists(p):
            return os.path.abspath(p)
    return None

# ───── Alarm checker thread ─────
def alarm_checker():
    """Check every second and start playback when time matches."""
    global RINGING, STOPPED_THIS_MINUTE

    last_minute_seen = None
    last_log = 0

    while True:
        try:
            alarm = load_alarm()
            # Expect: {'hour','minute','ampm','time12','ringtone'}
            if alarm.get("hour") and alarm.get("minute") and alarm.get("ampm") and alarm.get("ringtone"):
                now_h, now_m, now_ap = current_h_m_ampm()
                now_comp = f"{now_h}:{now_m} {now_ap}"
                current_minute_key = f"{now_h}:{now_m}"  # used to reset stop flag each minute

                # Reset the "stopped this minute" flag when minute ticks
                if last_minute_seen != current_minute_key:
                    with LOCK:
                        STOPPED_THIS_MINUTE = None
                    last_minute_seen = current_minute_key

                # periodic log to console for visibility
                if time.time() - last_log > 12:
                    print(f"⏳ now={now_comp}   target={alarm.get('time12')}   ringing={RINGING}")
                    last_log = time.time()

                # Match by fields (no formatting surprises)
                should_ring = (
                    (alarm["hour"] == now_h) and
                    (alarm["minute"] == now_m) and
                    (alarm["ampm"].upper() == now_ap.upper())
                )

                with LOCK:
                    blocked_this_minute = (STOPPED_THIS_MINUTE == now_comp)
                    already_ringing = RINGING

                if should_ring and not already_ringing and not blocked_this_minute:
                    tone_hit = resolve_tone_path(alarm.get("ringtone"))
                    if tone_hit:
                        play_loop(tone_hit)
                    else:
                        print(f"❌ Ringtone path not found: {alarm.get('ringtone')}")
            time.sleep(1)
        except Exception as e:
            print("Checker error:", e)
            time.sleep(2)

# ───── HTML UI ─────
def options_html(options, selected=None):
    html = []
    for value, label in options:
        sel = " selected" if selected and value == selected else ""
        html.append(f"<option value=\"{value}\"{sel}>{label}</option>")
    return "\n".join(html)

def make_page():
    ringtones = list_ringtones()
    ring_opts = []
    if ringtones:
        for p in ringtones:
            ring_opts.append((p, os.path.basename(p)))
    else:
        ring_opts.append(("", "No audio files found"))

    saved = load_alarm()
    saved_hour = saved.get("hour", "07")
    saved_min = saved.get("minute", "00")
    saved_ampm = saved.get("ampm", "AM")
    saved_ring = saved.get("ringtone", ring_opts[0][0] if ring_opts else "")

    hours = [(f"{h:02d}", f"{h:02d}") for h in range(1, 13)]
    mins = [(f"{m:02d}", f"{m:02d}") for m in range(0, 60)]
    ampm_opts = [("AM", "AM"), ("PM", "PM")]

    return f"""<!doctype html>
<html>
<head>
  <meta charset="utf-8" />
  <title>Alarm Clock</title>
  <style>
    body {{ font-family: Arial, sans-serif; max-width: 560px; margin: 2rem auto; }}
    h1 {{ margin-bottom: .2rem }}
    .card {{ padding: 1rem; border: 1px solid #ddd; border-radius: 12px; box-shadow: 0 2px 8px rgba(0,0,0,.06); }}
    label {{ display:block; margin:.6rem 0 .2rem; font-weight:600 }}
    select, button {{ padding:.4rem; font-size: 1rem; }}
    .row {{ display:flex; gap:.5rem; align-items:center }}
    .row > * {{ flex:1 }}
    .muted {{ color:#666; font-size:.95rem }}
    .warning {{ color:#b00 }}
    .ok {{ color:#0a0 }}
  </style>
  <script>
    function tick() {{
      const now = new Date();
      const hh = String((now.getHours()%12)||12).padStart(2,'0');
      const mm = String(now.getMinutes()).padStart(2,'0');
      const ampm = now.getHours()>=12 ? 'PM' : 'AM';
      document.getElementById('now').textContent = hh+':'+mm+' '+ampm;
    }}
    setInterval(tick, 1000); window.onload = tick;
  </script>
</head>
<body>
  <h1>Alarm Clock</h1>
  <p class="muted">Current time: <strong id="now">--:-- --</strong></p>

  <div class="card">
    <form action="/save" method="get">
      <div class="row">
        <div>
          <label>Hour</label>
          <select name="hour">{options_html(hours, saved_hour)}</select>
        </div>
        <div>
          <label>Minute</label>
          <select name="minute">{options_html(mins, saved_min)}</select>
        </div>
        <div>
          <label>AM/PM</label>
          <select name="ampm">{options_html(ampm_opts, saved_ampm)}</select>
        </div>
      </div>

      <label>Ringtone</label>
      <select name="ringtone">{options_html(ring_opts, saved_ring)}</select>

      <div style="margin-top:1rem;">
        <button type="submit">Save Alarm</button>
        <a href="/test" style="margin-left:.6rem;">Test Play</a>
      </div>

      <p class="muted" style="margin-top:.6rem;">
        Music folder used: <code>{MUSIC_DIR}</code>
      </p>
      {"<p class='warning'>No audio files found. Put .mp3 or .wav files in the music folder.</p>" if not ringtones else ""}
      {"<p class='warning'>Audio device not initialized; playback may fail.</p>" if not AUDIO_OK else "<p class='ok'>Audio device ready.</p>"}
    </form>
  </div>

  <div class="card" style="margin-top:1rem;">
    <form action="/stop" method="get">
      <button type="submit">Stop Alarm</button>
      <span class="muted"> (Stops looping sound)</span>
    </form>
  </div>
</body>
</html>"""

# ───── HTTP handler ─────
class Handler(http.server.SimpleHTTPRequestHandler):
    def do_GET(self):
        parsed = urlparse(self.path)
        path = parsed.path
        if path == "/":
            self.respond_html(make_page())

        elif path == "/save":
            params = parse_qs(parsed.query)
            hour = params.get("hour", ["07"])[0]
            minute = params.get("minute", ["00"])[0]
            ampm = params.get("ampm", ["AM"])[0]
            ringtone = params.get("ringtone", [""])[0]

            H, M, AP, time12 = normalize_time(hour, minute, ampm)

            # Validate ringtone path now to avoid surprises later
            tone_hit = resolve_tone_path(ringtone)
            if not tone_hit:
                self.respond_html(
                    f"<h2>⚠️ Ringtone not found</h2>"
                    f"<p>We couldn't find: <code>{ringtone or '(empty)'}</code></p>"
                    f"<p>Put .mp3 or .wav files in <code>{MUSIC_DIR}</code> and select again.</p>"
                    f"<p><a href='/'>Back</a></p>"
                )
                return

            data = {
                "hour": H, "minute": M, "ampm": AP,
                "time12": time12,
                "ringtone": tone_hit  # store the resolved absolute path
            }
            save_alarm_obj(data)
            self.respond_html(
                f"<h2>✅ Saved!</h2>"
                f"<p>Alarm: <b>{time12}</b></p>"
                f"<p>Ringtone: <code>{os.path.basename(tone_hit)}</code></p>"
                f"<p><a href='/'>Back</a></p>"
            )

        elif path == "/stop":
            stop_playback()
            self.respond_html("<h2>⛔ Stopped</h2><p>Alarm sound stopped for this minute.</p><p><a href='/'>Back</a></p>")

        elif path == "/test":
            alarm = load_alarm()
            tone = alarm.get("ringtone", "")
            if not tone:
                self.respond_html("<p>No ringtone selected. Save an alarm first.</p><p><a href='/'>Back</a></p>")
                return
            try:
                if AUDIO_OK:
                    pygame.mixer.music.load(tone)
                    pygame.mixer.music.play()
                    time.sleep(1.8)
                    pygame.mixer.music.stop()
                    self.respond_html("<p>✅ Test OK (played ~2s).</p><p><a href='/'>Back</a></p>")
                else:
                    self.respond_html("<p>❌ Audio device not initialized. Check speakers/output.</p><p><a href='/'>Back</a></p>")
            except Exception as e:
                self.respond_html(f"<p>❌ Test failed: {e}</p><p><a href='/'>Back</a></p>")

        else:
            # Serve other static files if needed
            return super().do_GET()

    def respond_html(self, html):
        self.send_response(200)
        self.send_header("Content-Type", "text/html; charset=utf-8")
        self.end_headers()
        self.wfile.write(html.encode("utf-8"))

# ───── Main ─────
def main():
    # Start checker thread
    t = threading.Thread(target=alarm_checker, daemon=True)
    t.start()

    # Start server
    with socketserver.TCPServer(("", PORT), Handler) as httpd:
        url = f"http://localhost:{PORT}"
        print(f"🌐 Serving {url}   (Music dir: {MUSIC_DIR})")
        try:
            webbrowser.open(url)
        except Exception:
            pass
        httpd.serve_forever()

if __name__ == "__main__":
    main()
