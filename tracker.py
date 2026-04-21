'''
Netflix Canada Top 10 — Daily Tracker
Scrapes FlixPatrol for the live Netflix Canada Top 10 (Movies + TV),
diffs against last known state, and sends a premium dark-mode HTML
email whenever any new title appears in either list.
'''

import os
import json
import time
import random
import smtplib
import logging
from datetime import datetime, timezone
from email.mime.multipart import MIMEMultipart
from email.mime.text import MIMEText
from pathlib import Path
from urllib.parse import quote_plus

import requests
from bs4 import BeautifulSoup

# ── Logging ───────────────────────────────────────────────────────────────────

logging.basicConfig(
    level=logging.INFO,
    format="%(asctime)s  %(levelname)-8s  %(message)s",
    datefmt="%Y-%m-%d %H:%M:%S",
)
log = logging.getLogger(__name__)

# ── Constants ─────────────────────────────────────────────────────────────────

BASE_URL   = "https://flixpatrol.com"
MOVIES_URL = f"{BASE_URL}/top10/netflix/canada/today/full/"
TV_URL     = f"{BASE_URL}/top10/netflix/canada/today/full/?page=tv"
STATE_FILE = Path("state.json")
TOP_N      = 10

SMTP_HOST = "smtp.gmail.com"
SMTP_PORT = 587

EMAIL_FROM    = os.environ["EMAIL_FROM"]
EMAIL_TO      = os.environ["EMAIL_TO"]
GMAIL_APP_PWD = os.environ["GMAIL_APP_PWD"]

HEADERS = {
    "User-Agent": (
        "Mozilla/5.0 (Macintosh; Intel Mac OS X 10_15_7) "
        "AppleWebKit/537.36 (KHTML, like Gecko) "
        "Chrome/123.0.0.0 Safari/537.36"
    ),
    "Accept-Language": "en-CA,en;q=0.9",
    "Accept": "text/html,application/xhtml+xml,application/xml;q=0.9,*/*;q=0.8",
}

# ── Scraping ──────────────────────────────────────────────────────────────────

def _fetch_html(url: str, retries: int = 3) -> str:
    '''
    Fetches HTML from a URL with retry logic and polite rate limiting.
    Raises on persistent failure after all retries are exhausted.
    '''
    for attempt in range(1, retries + 1):
        try:
            time.sleep(random.uniform(1.5, 3.0))
            response = requests.get(url, headers=HEADERS, timeout=20)
            response.raise_for_status()
            return response.text
        except requests.RequestException as exc:
            log.warning(f"Attempt {attempt}/{retries} failed for {url}: {exc}")
            if attempt == retries:
                raise
            time.sleep(attempt * 4)


def _parse_top10(html: str, category: str) -> list[dict]:
    '''
    Parses the FlixPatrol Top 10 table from raw HTML.
    Returns a list of entry dicts with rank, title, and category.
    Falls back to empty list with a warning if structure changes.
    '''
    soup    = BeautifulSoup(html, "html.parser")
    entries = []

    table = soup.find("table", class_=lambda c: c and "top10" in c.lower())
    if not table:
        table = soup.find("table")

    if not table:
        log.warning(f"No table found for {category} — FlixPatrol HTML may have changed.")
        return entries

    for row in table.find_all("tr")[1:TOP_N + 1]:
        cols = row.find_all("td")
        if len(cols) < 2:
            continue
        rank_text  = cols[0].get_text(strip=True)
        title_text = cols[1].get_text(strip=True)
        if not rank_text.isdigit() or not title_text:
            continue
        entries.append({
            "rank":     int(rank_text),
            "title":    title_text,
            "category": category,
        })

    return entries[:TOP_N]


def fetch_canada_top10() -> dict:
    '''
    Fetches and parses the current Netflix Canada Top 10 for
    Movies and TV from FlixPatrol.

    Returns:
        dict with keys "movies", "tv", and "fetched_at" (ISO timestamp).
    '''
    log.info("Fetching Movies top 10...")
    movies_html = _fetch_html(MOVIES_URL)
    movies      = _parse_top10(movies_html, "Movie")

    log.info("Fetching TV top 10...")
    tv_html = _fetch_html(TV_URL)
    tv      = _parse_top10(tv_html, "TV")

    log.info(f"Parsed: {len(movies)} movies, {len(tv)} TV shows.")

    return {
        "movies":     movies,
        "tv":         tv,
        "fetched_at": datetime.now(timezone.utc).isoformat(),
    }


# ── State management ──────────────────────────────────────────────────────────

def load_state() -> dict:
    '''
    Loads previously saved Top 10 state from disk.
    Auto-creates an empty state.json on the very first run.
    '''
    if not STATE_FILE.exists():
        log.info("No state.json found — first run, will email full Top 10.")
        save_state({})
        return {}
    content = STATE_FILE.read_text(encoding="utf-8").strip()
    if not content or content == "{}":
        return {}
    return json.loads(content)


def save_state(data: dict) -> None:
    '''
    Persists the current Top 10 lists and fetch timestamp to state.json.
    '''
    STATE_FILE.write_text(json.dumps(data, indent=2, ensure_ascii=False), encoding="utf-8")
    log.info("State saved.")


def _title_set(entries: list[dict]) -> set[str]:
    ''' Returns a normalised lowercase title set for O(1) lookup. '''
    return {e["title"].lower().strip() for e in entries}


def find_new_entries(current: list[dict], previous: list[dict]) -> list[dict]:
    '''
    Returns entries in current absent from previous, matched by normalised title.
    '''
    prev = _title_set(previous)
    return [e for e in current if e["title"].lower().strip() not in prev]


def find_dropped_entries(current: list[dict], previous: list[dict]) -> list[dict]:
    '''
    Returns entries from previous no longer present in current.
    '''
    curr = _title_set(current)
    return [e for e in previous if e["title"].lower().strip() not in curr]


# ── Link helpers ──────────────────────────────────────────────────────────────

def imdb_url(title: str) -> str:
    ''' Generates an IMDB search URL for a given title. '''
    return f"https://www.imdb.com/find/?q={quote_plus(title)}&s=tt"


def rt_url(title: str) -> str:
    ''' Generates a Rotten Tomatoes search URL for a given title. '''
    return f"https://www.rottentomatoes.com/search?search={quote_plus(title)}"


# ── Email HTML ─────────────────────────────────────────────────────────────────

def build_email_html(
    new_movies:     list[dict],
    new_tv:         list[dict],
    all_movies:     list[dict],
    all_tv:         list[dict],
    dropped_movies: list[dict],
    dropped_tv:     list[dict],
) -> str:
    '''
    Renders a premium cinematic dark-mode HTML email.
    Wide layout, per-title IMDB + RT links, new entry highlights,
    dropped titles, and full inline CSS for email client compatibility.
    '''
    today         = datetime.now().strftime("%B %d, %Y")
    new_count     = len(new_movies) + len(new_tv)
    new_movie_set = {e["title"].lower() for e in new_movies}
    new_tv_set    = {e["title"].lower() for e in new_tv}

    # ── Rank medal ────────────────────────────────────────────────────────────
    def rank_cell(rank: int) -> str:
        medals = {1: ("🥇", "#FFD700"), 2: ("🥈", "#C0C0C0"), 3: ("🥉", "#CD7F32")}
        if rank in medals:
            icon, color = medals[rank]
            return (
                f"<td style='padding:14px 16px 14px 20px;width:52px;vertical-align:middle;'>"
                f"<span style='font-size:18px;'>{icon}</span>"
                f"</td>"
            )
        return (
            f"<td style='padding:14px 16px 14px 20px;width:52px;vertical-align:middle;'>"
            f"<span style='display:inline-block;width:28px;height:28px;line-height:28px;"
            f"text-align:center;border-radius:50%;background:#1e1e1e;color:#555;"
            f"font-size:11px;font-weight:700;border:1px solid #2a2a2a;'>{rank}</span>"
            f"</td>"
        )

    # ── Link pill ─────────────────────────────────────────────────────────────
    def link_pill(label: str, url: str, color: str) -> str:
        return (
            f"<a href='{url}' style='display:inline-block;color:{color};"
            f"font-size:10px;font-weight:700;letter-spacing:1px;text-transform:uppercase;"
            f"padding:3px 8px;border-radius:3px;border:1px solid {color};"
            f"text-decoration:none;margin-left:6px;opacity:0.85;'>{label}</a>"
        )

    # ── Table rows ────────────────────────────────────────────────────────────
    def table_rows(entries: list[dict], new_set: set) -> str:
        rows = []
        for e in entries:
            is_new      = e["title"].lower() in new_set
            row_bg      = "background:rgba(229,9,20,0.06);" if is_new else ""
            left_border = "border-left:3px solid #E50914;" if is_new else "border-left:3px solid transparent;"
            new_badge   = (
                "<span style='display:inline-block;background:#E50914;color:#fff;"
                "font-size:9px;font-weight:800;letter-spacing:1.5px;padding:2px 7px;"
                "border-radius:2px;margin-left:10px;text-transform:uppercase;"
                "vertical-align:middle;'>NEW</span>"
            ) if is_new else ""

            imdb = link_pill("IMDb", imdb_url(e["title"]), "#F5C518")
            rt   = link_pill("RT", rt_url(e["title"]), "#FA320A")

            rows.append(f"""
            <tr style="{row_bg}{left_border}border-bottom:1px solid #1a1a1a;">
              {rank_cell(e['rank'])}
              <td style="padding:14px 12px;vertical-align:middle;">
                <span style="color:#EFEFEF;font-size:15px;font-family:Georgia,serif;
                font-weight:400;letter-spacing:0.2px;">{e['title']}</span>
                {new_badge}
                <div style="margin-top:5px;">
                  {imdb}{rt}
                </div>
              </td>
            </tr>""")
        return "".join(rows)

    # ── Dropped pills ─────────────────────────────────────────────────────────
    def dropped_bar(entries: list[dict]) -> str:
        if not entries:
            return ""
        pills = "".join(
            f"<span style='display:inline-block;background:#111;color:#444;"
            f"font-size:11px;padding:3px 10px;border-radius:20px;margin:3px;"
            f"border:1px solid #1e1e1e;text-decoration:line-through;'>{e['title']}</span>"
            for e in entries
        )
        return (
            f"<div style='padding:12px 20px;border-top:1px solid #161616;"
            f"background:#0c0c0c;'>"
            f"<span style='color:#3a3a3a;font-size:9px;font-weight:800;"
            f"letter-spacing:2px;text-transform:uppercase;margin-right:8px;'>Left Top 10</span>"
            f"{pills}</div>"
        )

    # ── Section header ────────────────────────────────────────────────────────
    def section_header(emoji: str, label: str, new_count_local: int) -> str:
        badge = (
            f"<span style='background:#E50914;color:#fff;font-size:9px;"
            f"font-weight:800;padding:3px 9px;border-radius:2px;"
            f"letter-spacing:1px;margin-left:10px;text-transform:uppercase;'>"
            f"+{new_count_local} NEW</span>"
        ) if new_count_local else ""
        return (
            f"<div style='padding:20px 20px 12px;display:flex;align-items:center;'>"
            f"<span style='font-size:18px;margin-right:10px;'>{emoji}</span>"
            f"<span style='color:#fff;font-size:11px;font-weight:800;"
            f"letter-spacing:3px;text-transform:uppercase;'>{label}</span>"
            f"{badge}</div>"
        )

    preview = ", ".join(e["title"] for e in (new_movies + new_tv)[:3])
    if new_count > 3:
        preview += f" +{new_count - 3} more"

    return f"""<!DOCTYPE html>
<html lang="en">
<head>
<meta charset="UTF-8">
<meta name="viewport" content="width=device-width,initial-scale=1.0">
<title>Netflix Canada Top 10</title>
</head>
<body style="margin:0;padding:24px 0;background:#060606;
font-family:'Helvetica Neue',Helvetica,Arial,sans-serif;">

<div style="max-width:680px;margin:0 auto;background:#0f0f0f;
border-radius:10px;overflow:hidden;border:1px solid #1c1c1c;
box-shadow:0 24px 60px rgba(0,0,0,0.6);">

  <!-- TOP BAR -->
  <div style="height:3px;background:linear-gradient(90deg,#E50914 0%,#ff6b6b 50%,#E50914 100%);"></div>

  <!-- HEADER -->
  <div style="padding:32px 32px 24px;background:linear-gradient(160deg,#1c0000 0%,#0f0f0f 55%);">
    <table width="100%" cellpadding="0" cellspacing="0">
      <tr>
        <td>
          <div style="color:#E50914;font-size:9px;font-weight:800;
          letter-spacing:4px;text-transform:uppercase;margin-bottom:6px;">Netflix Canada</div>
          <div style="color:#FFFFFF;font-size:26px;font-weight:700;
          letter-spacing:-0.5px;line-height:1.1;">Top 10 Daily Alert</div>
          <div style="color:#444;font-size:12px;margin-top:8px;
          letter-spacing:0.5px;">{today}</div>
        </td>
        <td style="text-align:right;vertical-align:top;">
          <div style="display:inline-block;background:#E50914;color:#fff;
          font-size:28px;font-weight:900;width:52px;height:52px;line-height:52px;
          text-align:center;border-radius:8px;letter-spacing:-1px;">N</div>
        </td>
      </tr>
    </table>
  </div>

  <!-- ALERT BANNER -->
  <div style="background:#E50914;padding:16px 32px;">
    <div style="color:#fff;font-size:15px;font-weight:700;line-height:1.4;">
      🔴 {new_count} new title{'s' if new_count != 1 else ''} entered the Top 10 today
    </div>
    <div style="color:rgba(255,255,255,0.65);font-size:12px;margin-top:4px;">{preview}</div>
  </div>

  <!-- MOVIES SECTION -->
  <div style="padding:0 0 4px;">
    {section_header("🎬", "Movies", len(new_movies))}
    <table width="100%" cellpadding="0" cellspacing="0"
    style="border-collapse:collapse;background:#111;">
      <tr style="background:#161616;border-bottom:1px solid #1e1e1e;">
        <th style="padding:10px 16px 10px 20px;text-align:left;color:#333;
        font-size:9px;font-weight:800;letter-spacing:2px;
        text-transform:uppercase;width:52px;"></th>
        <th style="padding:10px 16px;text-align:left;color:#333;
        font-size:9px;font-weight:800;letter-spacing:2px;text-transform:uppercase;">Title</th>
      </tr>
      {table_rows(all_movies, new_movie_set)}
    </table>
    {dropped_bar(dropped_movies)}
  </div>

  <!-- DIVIDER -->
  <div style="height:1px;background:#1a1a1a;margin:8px 20px;"></div>

  <!-- TV SECTION -->
  <div style="padding:0 0 4px;">
    {section_header("📺", "TV Shows", len(new_tv))}
    <table width="100%" cellpadding="0" cellspacing="0"
    style="border-collapse:collapse;background:#111;">
      <tr style="background:#161616;border-bottom:1px solid #1e1e1e;">
        <th style="padding:10px 16px 10px 20px;text-align:left;color:#333;
        font-size:9px;font-weight:800;letter-spacing:2px;
        text-transform:uppercase;width:52px;"></th>
        <th style="padding:10px 16px;text-align:left;color:#333;
        font-size:9px;font-weight:800;letter-spacing:2px;text-transform:uppercase;">Title</th>
      </tr>
      {table_rows(all_tv, new_tv_set)}
    </table>
    {dropped_bar(dropped_tv)}
  </div>

  <!-- FOOTER -->
  <div style="padding:20px 32px;border-top:1px solid #161616;
  background:#0a0a0a;text-align:center;">
    <div style="margin-bottom:10px;">
      <a href="https://flixpatrol.com/top10/netflix/canada/"
      style="color:#E50914;text-decoration:none;font-size:11px;
      font-weight:700;letter-spacing:1px;text-transform:uppercase;
      margin:0 12px;">View on FlixPatrol ↗</a>
      <a href="https://saayedalam.me"
      style="color:#333;text-decoration:none;font-size:11px;
      font-weight:700;letter-spacing:1px;text-transform:uppercase;
      margin:0 12px;">saayedalam.me ↗</a>
    </div>
    <div style="color:#222;font-size:10px;letter-spacing:0.3px;">
      You're receiving this because a new title entered Netflix Canada's Top 10.
    </div>
  </div>

  <!-- BOTTOM BAR -->
  <div style="height:3px;background:linear-gradient(90deg,#E50914 0%,#ff6b6b 50%,#E50914 100%);"></div>

</div>
</body>
</html>"""


# ── Email sending ─────────────────────────────────────────────────────────────

def send_email(subject: str, html_body: str) -> None:
    '''
    Sends a multipart HTML email via Gmail SMTP using an app password.
    Raises on failure so GitHub Actions marks the run as failed.
    '''
    msg            = MIMEMultipart("alternative")
    msg["Subject"] = subject
    msg["From"]    = EMAIL_FROM
    msg["To"]      = EMAIL_TO

    plain = f"{subject}\n\nOpen in an HTML email client to view the full Top 10."
    msg.attach(MIMEText(plain, "plain"))
    msg.attach(MIMEText(html_body, "html"))

    with smtplib.SMTP(SMTP_HOST, SMTP_PORT) as server:
        server.ehlo()
        server.starttls()
        server.login(EMAIL_FROM, GMAIL_APP_PWD)
        server.sendmail(EMAIL_FROM, [EMAIL_TO], msg.as_string())

    log.info(f"✓ Email sent → {subject}")


# ── Entry point ───────────────────────────────────────────────────────────────

def main() -> None:
    '''
    Full daily check cycle:
    1. Fetch current Top 10 from FlixPatrol
    2. Diff against saved state
    3. Send email if any new entries found
    4. Persist updated state
    '''
    log.info("─── Netflix Canada Top 10 Tracker starting ───")

    current = fetch_canada_top10()
    state   = load_state()

    prev_movies = state.get("movies", [])
    prev_tv     = state.get("tv", [])

    new_movies     = find_new_entries(current["movies"], prev_movies)
    new_tv         = find_new_entries(current["tv"], prev_tv)
    dropped_movies = find_dropped_entries(current["movies"], prev_movies)
    dropped_tv     = find_dropped_entries(current["tv"], prev_tv)

    log.info(
        f"Δ New → Movies: {len(new_movies)}  TV: {len(new_tv)} | "
        f"Dropped → Movies: {len(dropped_movies)}  TV: {len(dropped_tv)}"
    )

    if new_movies or new_tv:
        new_count = len(new_movies) + len(new_tv)
        preview   = ", ".join(e["title"] for e in (new_movies + new_tv)[:2])
        ellipsis  = "..." if new_count > 2 else ""
        subject   = f"🔴 Netflix Canada Top 10: {new_count} new — {preview}{ellipsis}"

        html = build_email_html(
            new_movies     = new_movies,
            new_tv         = new_tv,
            all_movies     = current["movies"],
            all_tv         = current["tv"],
            dropped_movies = dropped_movies,
            dropped_tv     = dropped_tv,
        )
        send_email(subject, html)
    else:
        log.info("No new entries — no email sent.")

    save_state({
        "movies":     current["movies"],
        "tv":         current["tv"],
        "fetched_at": current["fetched_at"],
    })

    log.info("─── Done ───")


if __name__ == "__main__":
    main()
