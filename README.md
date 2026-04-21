# 🔴 Netflix Canada Top 10 Tracker

> Get a beautiful daily email alert whenever a new title enters Netflix Canada's Top 10 — Movies and TV combined. Fully automated, zero cost, runs on GitHub Actions.

![GitHub Actions](https://img.shields.io/badge/Automated-GitHub_Actions-2088FF?style=flat-square&logo=github-actions&logoColor=white)
![Python](https://img.shields.io/badge/Python-3.12-3776AB?style=flat-square&logo=python&logoColor=white)
![License](https://img.shields.io/badge/License-MIT-green?style=flat-square)

---

## What it does

- Runs every day at 8 AM ET via GitHub Actions
- Scrapes the live Netflix Canada Top 10 from FlixPatrol
- Compares it to yesterday's list
- Sends you one email only if something new appeared — no changes, no email
- Includes **IMDb** and **Rotten Tomatoes** search links for every title
- Shows titles that dropped out of the Top 10 too

---

## Email preview

Dark-mode cinematic design with:
- 🥇🥈🥉 medal badges for top 3
- Red `NEW` badge on new entries
- IMDb + RT links per title
- Dropped titles shown as struck-through
- Full Movies + TV tables in one digest

---

## Setup — fork and run in 15 minutes

### 1. Fork this repo

Click **Fork** at the top right of this page. Make it **private** (your secrets stay safe either way, but private is cleaner).

---

### 2. Get a Gmail App Password

The script sends email via your Gmail using a special app-specific password — not your real password.

1. Go to [myaccount.google.com/security](https://myaccount.google.com/security)
2. Make sure **2-Step Verification** is turned on
3. Go to [myaccount.google.com/apppasswords](https://myaccount.google.com/apppasswords)
4. Type `netflix-tracker` → click **Create**
5. **Copy the 16-character password** — save it, you won't see it again

---

### 3. Add your secrets to GitHub

In your forked repo → **Settings → Secrets and variables → Actions → New repository secret**

Add these three:

| Secret name     | Value                                        |
|-----------------|----------------------------------------------|
| `EMAIL_FROM`    | Your Gmail address (e.g. `you@gmail.com`)    |
| `EMAIL_TO`      | Where alerts go (can be same address)        |
| `GMAIL_APP_PWD` | The 16-char app password from Step 2         |

---

### 4. Allow Actions to write back to the repo

The workflow saves `state.json` after each run so it knows what changed tomorrow.

**Settings → Actions → General → Workflow permissions → Read and write permissions → Save**

---

### 5. Run it manually to test

**Actions tab → Netflix Canada Top 10 Tracker → Run workflow**

Wait ~30 seconds → check your inbox. The first run emails the full Top 10 since there's no prior state. From then on, only changes trigger an email.

---

## Customise for another country

In `tracker.py`, change the URLs at the top:

```python
MOVIES_URL = "https://flixpatrol.com/top10/netflix/canada/today/full/"
TV_URL     = "https://flixpatrol.com/top10/netflix/canada/today/full/?page=tv"
```

Replace `canada` with any country slug from FlixPatrol (e.g. `united-states`, `united-kingdom`, `australia`).

---

## Troubleshooting

| Problem | Fix |
|---|---|
| No email received | Check secrets are named exactly right (`EMAIL_FROM`, `EMAIL_TO`, `GMAIL_APP_PWD`) |
| Authentication error | Make sure 2-Step Verification is on before generating the app password |
| Actions tab shows no workflow | Check the file is at `.github/workflows/tracker.yml` (note the `s` in `workflows`) |
| Emails stop arriving | Check Actions logs for errors — FlixPatrol HTML may have changed |

---

## Tech stack

- **Python 3.12** — scraping, diffing, email
- **BeautifulSoup4** — HTML parsing
- **GitHub Actions** — free daily scheduling
- **Gmail SMTP** — email delivery via app password

---

## License

MIT — fork it, use it, build on it.

---

Built by [Saayed Alam](https://saayedalam.me)
