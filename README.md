# Netflix Canada Top 10 Tracker

Sends you a combined email digest whenever a new title enters Netflix Canada's
Top 10 for Movies or TV — powered by Netflix's public weekly data and GitHub Actions.

---

## How it works

1. Runs every Tuesday at 9 AM UTC (Netflix updates weekly on Tuesdays)
2. Fetches the latest Top 10 from `top10.netflix.com`
3. Diffs against `state.json` (the previous week's list)
4. If any new titles appear → sends one combined HTML email
5. Saves the new state back to the repo for next week's diff

---

## Setup

### 1. Create a new private GitHub repo

Push this folder to it:
```
git init
git add .
git commit -m "init"
git remote add origin https://github.com/YOUR_USERNAME/netflix-tracker.git
git push -u origin main
```

### 2. Get a Gmail App Password

> You need 2-Step Verification enabled on your Google account first.

1. Go to [myaccount.google.com/apppasswords](https://myaccount.google.com/apppasswords)
2. App name: `netflix-tracker` → click **Create**
3. Copy the 16-character password

### 3. Add GitHub Secrets

In your repo → **Settings → Secrets and variables → Actions → New repository secret**:

| Secret name     | Value                          |
|----------------|-------------------------------|
| `EMAIL_FROM`   | your Gmail address             |
| `EMAIL_TO`     | destination email (can be same)|
| `GMAIL_APP_PWD`| the 16-char app password       |

### 4. Enable Actions write permissions

Repo → **Settings → Actions → General → Workflow permissions**
→ Select **Read and write permissions** → Save

### 5. Test it manually

Go to **Actions → Netflix Canada Top 10 Tracker → Run workflow**

---

## Email format

- Subject: `🎬 Netflix Canada: 3 new titles in the Top 10 — 2026-04-14`
- Body: Full Top 10 for Movies + TV, with new entries highlighted in yellow + a red NEW badge
- No email is sent if nothing changed (same list as last week)

---

## Local testing

```bash
pip install requests
export EMAIL_FROM="you@gmail.com"
export EMAIL_TO="you@gmail.com"
export GMAIL_APP_PWD="xxxx xxxx xxxx xxxx"
python tracker.py
```
# netflix-tracker
