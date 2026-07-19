# Deploying Athena — Step-by-Step Guide

This guide takes you from a GitHub repository to a **live, public Athena web
app**, with no prior DevOps experience assumed. You will use five free-tier
services:

| Service | Role | What it hosts |
|---|---|---|
| **GitHub** | source code | your repository |
| **Neon** | database | PostgreSQL (your decisions & evidence) |
| **Upstash** | cache | Redis (fast temporary data) |
| **Render** | backend | the Athena API (FastAPI) |
| **Vercel** | frontend | the Athena website (Next.js) |

The order matters: **database and cache first**, then the **backend**, then the
**frontend**. Each step tells you exactly what to click and what to copy.

> **Time estimate:** about **30–45 minutes**, most of it waiting for builds.

> **A note on cost:** every service below has a free tier that is enough to try
> Athena. Neon and Render free tiers "sleep" when idle, so the very first visit
> after a quiet period takes a few extra seconds to wake up. That is normal.

---

## Before you start

You need accounts on: [github.com](https://github.com),
[neon.tech](https://neon.tech), [upstash.com](https://upstash.com),
[render.com](https://render.com), [vercel.com](https://vercel.com). You can
sign into all four of the last ones **with your GitHub account** — use that,
it makes connecting the repository one click.

You will also copy a few "secrets" between services. Keep a temporary notepad
open to paste them into. **Never commit these into the code.**

Generate one strong secret now — you will need it for the backend. On Mac/Linux
open a terminal and run:

```bash
openssl rand -hex 32
```

Copy the long line it prints; that is your `JWT_SECRET`.

---

## Step 1 — Put the code on GitHub

If your code is already on GitHub, skip to Step 2. Otherwise, from the project
folder in a terminal:

```bash
git init
git add .
git commit -m "Athena"
git branch -M main
git remote add origin https://github.com/<your-username>/athena.git
git push -u origin main
```

Replace `<your-username>` with your GitHub username. Refresh the repo page on
GitHub — you should see all the files.

---

## Step 2 — Create the database (Neon)

1. Go to [neon.tech](https://neon.tech) and sign in.
2. Click **New Project**. Name it `athena`. Pick the region closest to you.
   Click **Create**.
3. On the project dashboard find **Connection string**. Choose the
   **"Direct connection"** (not "Pooled") option and copy it. It looks like:

   ```
   postgresql://alex:AbCd1234@ep-cool-name-123.eu-central-1.aws.neon.tech/athena?sslmode=require
   ```

4. **Edit it slightly** so Athena's driver understands it: change the very
   beginning from `postgresql://` to `postgresql+psycopg://`. The result:

   ```
   postgresql+psycopg://alex:AbCd1234@ep-cool-name-123.eu-central-1.aws.neon.tech/athena?sslmode=require
   ```

5. Paste this into your notepad labelled **DATABASE_URL**. Keep the
   `?sslmode=require` at the end — Neon requires it.

> You do **not** need to create any tables. Athena builds them automatically on
> first launch.

---

## Step 3 — Create the cache (Upstash Redis)

1. Go to [upstash.com](https://upstash.com), sign in, open the **Redis** tab.
2. Click **Create Database**. Name it `athena`. Pick a nearby region. Leave
   **TLS** enabled (it is by default). Click **Create**.
3. On the database page, scroll to **Connect** and find the connection string
   that starts with `rediss://` (note the **double "s"** — that means secure).
   It looks like:

   ```
   rediss://default:AxYz...@sunny-cat-12345.upstash.io:6379
   ```

4. Copy it to your notepad labelled **REDIS_URL**.

---

## Step 4 — Deploy the backend (Render)

Athena includes a `render.yaml` "blueprint" that tells Render exactly how to
build and run the backend, so this is mostly clicking **Approve**.

1. Go to [render.com](https://render.com) and sign in with GitHub.
2. Click **New → Blueprint**.
3. Select your **athena** repository. Render finds `render.yaml` and shows a
   service called **athena-api**. Click **Apply / Create**.
4. Render will ask you to fill in the secret values it needs (they were marked
   "set in dashboard"). Enter, from your notepad:

   | Field | Value |
   |---|---|
   | `DATABASE_URL` | the Neon string from Step 2 |
   | `REDIS_URL` | the Upstash string from Step 3 |
   | `JWT_SECRET` | the `openssl rand -hex 32` value from "Before you start" |
   | `ATHENA_SEED_ADMIN_EMAIL` | the email you want for the first admin login |
   | `ATHENA_SEED_ADMIN_PASSWORD` | a password (8+ characters) for that admin |

   (The optional `ALPHAVANTAGE_API_KEY` can be left blank — Athena shows
   clearly-labelled sample market data without it.)

5. Click **Create / Deploy**. Render now builds the backend. This takes a few
   minutes. Watch the **Logs** tab — you should see, in order:

   ```
   [start] Applying database migrations (alembic upgrade head)…
   [start] Running idempotent seed…
   [start] Created initial ADMIN user: <your email>
   [start] Launching uvicorn on 0.0.0.0:10000 …
   ```

   That means the database tables were created and your admin account was set
   up **automatically**.

6. When it says **Live**, copy your backend's public URL from the top of the
   page. It looks like `https://athena-api.onrender.com`. Save it to your
   notepad as **ATHENA_API_URL**.

7. Check it works: open `https://athena-api.onrender.com/health` in your
   browser. You should see `{"status":"ok"}`.

---

## Step 5 — Deploy the frontend (Vercel)

1. Go to [vercel.com](https://vercel.com) and sign in with GitHub.
2. Click **Add New → Project** and import your **athena** repository.
3. **Important — set the project root:** in the import screen, find **Root
   Directory** and set it to **`web`** (the website lives in that sub-folder).
   Vercel then auto-detects Next.js and fills in the build settings from the
   included `vercel.json`.
4. Open **Environment Variables** and add one:

   | Name | Value |
   |---|---|
   | `ATHENA_API_URL` | your Render URL from Step 4 (e.g. `https://athena-api.onrender.com`) |

5. Click **Deploy**. Vercel builds the site (a couple of minutes) and then
   shows you a public address like `https://athena.vercel.app`.

6. Open that address. You should see the Athena login screen.

---

## Step 6 — Log in and confirm

1. On the login page, sign in with the **admin email and password** you set in
   Step 4.
2. You should land on the **Dashboard**. Click into **Market**, open a company,
   view **Portfolio** and **Reports** — the whole app is live.

🎉 **Athena is deployed.** Your public address is the Vercel URL from Step 5.

---

## Everyday operation (good to know)

- **Updating the app:** just `git push` to the `main` branch. Render and Vercel
  both redeploy automatically. Database migrations run themselves on each
  backend deploy — you never run them by hand.
- **First visit after idle is slow:** free-tier Neon and Render sleep when
  unused; the first request wakes them in a few seconds, then it's fast.
- **Health check:** `https://<your-render-url>/health` should always return
  `{"status":"ok"}`. A fuller view is at `/health/full`.
- **Your data is safe on the server:** decisions and evidence live in Neon
  (your database). Some preferences (notes, watchlist, theme) are saved in your
  browser in this pilot.

## If something goes wrong

| Symptom | Likely cause | Fix |
|---|---|---|
| Backend log: *"JWT_SECRET is the development default"* | `JWT_SECRET` not set (or too short) | set a 32+ char secret in Render → Environment, redeploy |
| Backend log: database connection error | `DATABASE_URL` wrong or missing `?sslmode=require` | re-copy the Neon **direct** string, keep `postgresql+psycopg://` and `?sslmode=require` |
| `/health/full` shows `redis: unavailable` | `REDIS_URL` wrong | re-copy the Upstash `rediss://` string |
| Website loads but data calls fail | `ATHENA_API_URL` on Vercel is wrong | set it to the exact Render URL, redeploy on Vercel |
| Can't log in | admin seed vars weren't set at first deploy | set `ATHENA_SEED_ADMIN_EMAIL`/`PASSWORD` in Render and redeploy, or register a new account on the login page |

## Safety posture (unchanged, by design)

Athena never executes trades, connects to no broker, and requires **you** to
approve every decision. There is no trading or money-movement path anywhere in
the app.
