'''
Netflix Canada Top 10 Tracker
Fetches weekly Top 10 data from Netflix's public TSV feed,
compares against last known state, and sends an email digest
whenever new titles appear in either the Movies or TV list.
'''

import os
import json
import csv
import smtplib
import logging
from io import StringIO
from datetime import date
from email.mime.multipart import MIMEMultipart
from email.mime.text import MIMEText
from pathlib import Path

import requests

# ── Config ────────────────────────────────────────────────────────────────────

NETFLIX_TSV_URL = "https://top10.netflix.com/data/all-weeks-countries.tsv"
STATE_FILE      = Path("state.json")
COUNTRY_CODE    = "CA"   # Canada
TOP_N           = 10

SMTP_HOST = "smtp.gmail.com"
SMTP_PORT = 587

EMAIL_FROM    = os.environ["EMAIL_FROM"]     # your Gmail address
EMAIL_TO      = os.environ["EMAIL_TO"]       # destination (can be same)
GMAIL_APP_PWD = os.environ["GMAIL_APP_PWD"]  # Gmail app password

logging.basicConfig(level=logging.INFO, format="%(levelname)s: %(message)s")
log = logging.getLogger(__name__)


# ── Data fetching ─────────────────────────────────────────────────────────────

def fetch_top10_canada() -> dict[str, list[dict]]:
    '''
    Fetches the Netflix Top 10 TSV, filters for Canada,
    and returns the most recent week's top 10 for Movies and TV.

    Returns a dict with keys "movies" and "tv", each a list of
    up to 10 dicts with keys: rank, show_title, category, weeks_in_top10.
    '''
    log.info("Fetching Netflix Top 10 data...")
    response = requests.get(NETFLIX_TSV_URL, timeout=30)
    response.raise_for_status()

    reader = csv.DictReader(StringIO(response.text), delimiter="\t")
    rows = [r for r in reader if r.get("country_iso2") == COUNTRY_CODE]

    if not rows:
        raise ValueError(f"No data found for country code: {COUNTRY_CODE}")

    latest_week = max(rows, key=lambda r: r["week"])["week"]
    log.info(f"Latest data week: {latest_week}")

    week_rows = [r for r in rows if r["week"] == latest_week]

    movies, tv = [], []
    for row in week_rows:
        category = row.get("category", "")
        entry = {
            "rank":           int(row.get("weekly_rank", 0)),
            "show_title":     row.get("show_title", "").strip(),
            "category":       category,
            "weeks_in_top10": row.get("cumulative_weeks_in_top_10", "N/A"),
            "week":           latest_week,
        }
        if "Film" in category and len(movies) < TOP_N:
            movies.append(entry)
        elif "TV" in category and len(tv) < TOP_N:
            tv.append(entry)

    movies.sort(key=lambda x: x["rank"])
    tv.sort(key=lambda x: x["rank"])

    return {"movies": movies, "tv": tv, "week": latest_week}


# ── State management ──────────────────────────────────────────────────────────

def load_state() -> dict:
    '''
    Loads the previously saved Top 10 state from disk.
    Returns an empty dict if no state file exists yet.
    '''
    if STATE_FILE.exists():
        return json.loads(STATE_FILE.read_text())
    return {}


def save_state(data: dict) -> None:
    '''
    Persists the current Top 10 data to state.json so the
    next run can diff against it.
    '''
    STATE_FILE.write_text(json.dumps(data, indent=2))
    log.info("State saved.")


# ── Diff logic ────────────────────────────────────────────────────────────────

def find_new_entries(current: list[dict], previous: list[dict]) -> list[dict]:
    '''
    Returns entries in current that were not present in previous,
    matched by show_title (case-insensitive).
    '''
    prev_titles = {e["show_title"].lower() for e in previous}
    return [e for e in current if e["show_title"].lower() not in prev_titles]


# ── Email ─────────────────────────────────────────────────────────────────────

def build_email_html(
    week: str,
    new_movies: list[dict],
    new_tv: list[dict],
    all_movies: list[dict],
    all_tv: list[dict],
) -> str:
    '''
    Builds a clean HTML email body showing new entries prominently
    and the full current Top 10 for both Movies and TV.
    '''

    def rows(entries: list[dict], new_titles: set[str]) -> str:
        out = []
        for e in entries:
            is_new  = e["show_title"].lower() in new_titles
            bg      = "#fff3cd" if is_new else "white"
            badge   = " <span style='background:#e50914;color:white;font-size:11px;padding:2px 6px;border-radius:4px;margin-left:6px;'>NEW</span>" if is_new else ""
            out.append(
                f"<tr style='background:{bg}'>"
                f"<td style='padding:8px 12px;font-weight:bold;color:#555;'>#{e['rank']}</td>"
                f"<td style='padding:8px 12px;'>{e['show_title']}{badge}</td>"
                f"<td style='padding:8px 12px;color:#888;font-size:13px;'>{e['weeks_in_top10']} wk{'s' if str(e['weeks_in_top10']) != '1' else ''}</td>"
                f"</tr>"
            )
        return "\n".join(out)

    new_movie_titles = {e["show_title"].lower() for e in new_movies}
    new_tv_titles    = {e["show_title"].lower() for e in new_tv}

    new_count = len(new_movies) + len(new_tv)
    headline  = f"{new_count} new title{'s' if new_count != 1 else ''} entered the Netflix Canada Top 10 this week."

    table_style = (
        "width:100%;border-collapse:collapse;margin-top:12px;font-family:sans-serif;"
        "font-size:14px;border:1px solid #eee;"
    )
    th_style = (
        "text-align:left;padding:10px 12px;background:#141414;color:white;"
        "font-size:13px;letter-spacing:0.5px;"
    )

    return f"""
    <div style="max-width:620px;margin:0 auto;font-family:sans-serif;color:#222;">
      <div style="background:#e50914;padding:20px 24px;border-radius:6px 6px 0 0;">
        <h1 style="margin:0;color:white;font-size:22px;">🎬 Netflix Canada Top 10 Alert</h1>
        <p style="margin:6px 0 0;color:#ffd;font-size:13px;">Week of {week}</p>
      </div>

      <div style="background:#f9f9f9;padding:16px 24px;border-left:1px solid #eee;border-right:1px solid #eee;">
        <p style="margin:0;font-size:15px;">{headline}</p>
      </div>

      <div style="padding:20px 24px;background:white;border:1px solid #eee;">
        <h2 style="margin:0 0 4px;font-size:16px;">🎥 Movies</h2>
        <table style="{table_style}">
          <tr>
            <th style="{th_style}">Rank</th>
            <th style="{th_style}">Title</th>
            <th style="{th_style}">Weeks</th>
          </tr>
          {rows(all_movies, new_movie_titles)}
        </table>

        <h2 style="margin:24px 0 4px;font-size:16px;">📺 TV Shows</h2>
        <table style="{table_style}">
          <tr>
            <th style="{th_style}">Rank</th>
            <th style="{th_style}">Title</th>
            <th style="{th_style}">Weeks</th>
          </tr>
          {rows(all_tv, new_tv_titles)}
        </table>
      </div>

      <div style="padding:12px 24px;background:#f0f0f0;border-radius:0 0 6px 6px;font-size:12px;color:#999;text-align:center;">
        Powered by Netflix Top 10 public data · saayedalam.me
      </div>
    </div>
    """


def send_email(subject: str, html_body: str) -> None:
    '''
    Sends an HTML email via Gmail SMTP using an app password.
    Credentials are read from environment variables.
    '''
    msg = MIMEMultipart("alternative")
    msg["Subject"] = subject
    msg["From"]    = EMAIL_FROM
    msg["To"]      = EMAIL_TO
    msg.attach(MIMEText(html_body, "html"))

    with smtplib.SMTP(SMTP_HOST, SMTP_PORT) as server:
        server.ehlo()
        server.starttls()
        server.login(EMAIL_FROM, GMAIL_APP_PWD)
        server.sendmail(EMAIL_FROM, EMAIL_TO, msg.as_string())

    log.info(f"Email sent: {subject}")


# ── Main ──────────────────────────────────────────────────────────────────────

def main() -> None:
    '''
    Entry point. Fetches current Top 10, diffs against saved state,
    sends an email if there are any new entries, then saves the new state.
    '''
    current = fetch_top10_canada()
    state   = load_state()

    prev_movies = state.get("movies", [])
    prev_tv     = state.get("tv", [])

    new_movies = find_new_entries(current["movies"], prev_movies)
    new_tv     = find_new_entries(current["tv"], prev_tv)

    log.info(f"New movies: {len(new_movies)} | New TV: {len(new_tv)}")

    if new_movies or new_tv:
        new_count = len(new_movies) + len(new_tv)
        subject   = f"🎬 Netflix Canada: {new_count} new title{'s' if new_count != 1 else ''} in the Top 10 — {current['week']}"
        html      = build_email_html(
            week       = current["week"],
            new_movies = new_movies,
            new_tv     = new_tv,
            all_movies = current["movies"],
            all_tv     = current["tv"],
        )
        send_email(subject, html)
    else:
        log.info("No new entries — no email sent.")

    save_state({"movies": current["movies"], "tv": current["tv"], "week": current["week"]})


if __name__ == "__main__":
    main()
