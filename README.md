# 🔴 Netflix Canada Top 10 Tracker

> Get a beautiful weekly email alert whenever a new title enters Netflix Canada's Top 10 — Movies and TV combined. Powered by **Netflix's own official data**. Fully automated, zero cost, runs on GitHub Actions.

![GitHub Actions](https://img.shields.io/badge/Automated-GitHub_Actions-2088FF?style=flat-square&logo=github-actions&logoColor=white)
![Python](https://img.shields.io/badge/Python-3.12-3776AB?style=flat-square&logo=python&logoColor=white)
![Data](https://img.shields.io/badge/Data-Official_Netflix_TSV-E50914?style=flat-square)
![License](https://img.shields.io/badge/License-MIT-green?style=flat-square)

---

## How it works

1. Runs every **Tuesday at 2 PM UTC** — Netflix publishes new weekly data on Tuesdays
2. Downloads the official Netflix Top 10 TSV from `top10.netflix.com`
3. Filters for Canada, extracts the latest week's Movies and TV Top 10
4. Compares to last week's saved list
5. Sends one email only if new titles appeared — no changes, no email
6. Saves state back to the repo for next week's diff

**Data source:** Netflix's own public TSV at `https://top10.netflix.com/data/all-weeks-countries.tsv` — no scraping, no third-party APIs, no paywalls.

---

## Email preview

Dark-mode cinematic design with:
- 🥇🥈🥉 medal badges for top 3 ranks
- Red `NEW` badge on newly entered titles
- IMDb + Rotten Tomatoes search links for every title
- Weeks-in-Top-10 counter for returning titles
- Dropped titles shown as struck-through pills
- Direct link to official Netflix Top 10 page

---

## Setup — fork and run in 15 minutes

### 1. Fork this repo

Click **Fork** at the top right. You can keep it private or public — your credentials are stored as GitHub Secrets, never in the code.

---

### 2. Get a Gmail App Password

The script sends email via Gmail SMTP using a special app password — not your real password.

1. Go to [myaccount.google.com/security](https://myaccount.google.com/security)
2. Ensure **2-Step Verification** is turned on
3. Go to [myaccount.google.com/apppasswords](https://myaccount.google.com/apppasswords)
4. Name it `netflix-tracker` → click **Create**
5. **Copy the 16-character password** — you won't see it again

---

### 3. Add your secrets to GitHub

In your forked repo → **Settings → Secrets and variables → Actions → New repository secret**

| Secret name     | Value                                        |
|-----------------|----------------------------------------------|
| `EMAIL_FROM`    | Your Gmail address (e.g. `you@gmail.com`)    |
| `EMAIL_TO`      | Where alerts go (can be same address)        |
| `GMAIL_APP_PWD` | The 16-char app password from Step 2         |

---

### 4. Allow Actions to write back to the repo

**Settings → Actions → General → Workflow permissions → Read and write permissions → Save**

---

### 5. Test it manually

**Actions tab → Netflix Canada Top 10 Tracker → Run workflow**

The first run emails the full current Top 10 (state is empty, everything is "new"). Check your inbox — if it arrives, you're live.

---

## Customise for another country

Change `COUNTRY_CODE` at the top of `tracker.py`:

```python
COUNTRY_CODE = "CA"   # Canada
# COUNTRY_CODE = "US"  # United States
# COUNTRY_CODE = "GB"  # United Kingdom
# COUNTRY_CODE = "AU"  # Australia
```

Netflix's TSV uses ISO 3166-1 alpha-2 country codes.

---

## Troubleshooting

| Problem | Fix |
|---|---|
| No email received | Check secrets are named exactly: `EMAIL_FROM`, `EMAIL_TO`, `GMAIL_APP_PWD` |
| Authentication error | Ensure 2-Step Verification is on before generating the app password |
| Workflow not showing in Actions | File must be at `.github/workflows/tracker.yml` (note the `s` in `workflows`) |
| Same email every week | Check `state.json` is being committed back — verify write permissions in Step 4 |

---

## Tech stack

- **Python 3.12** — data parsing, diffing, email
- **requests** — TSV download (only dependency)
- **GitHub Actions** — free weekly scheduling + state commits
- **Gmail SMTP** — email via app password

---

## License

MIT — fork it, use it, build on it.

---

Built by [Saayed Alam](https://saayedalam.me)
