# How to Run This Project on cPanel (Trade Signals)

Step-by-step guide using **File Manager** and **Create Python App** to deploy the Trade Signals Flask app on cPanel (PostgreSQL, no Docker).

---

## Overview

- **Project folder name:** `tradesignals` (use this name in File Manager).
- **App type:** Flask (Python 3.x)
- **Database:** PostgreSQL (set via environment variables)
- **Deployment method:** Create Python App in cPanel; WSGI entry is `application` in `app.py`.

---

## Step 1: Upload the project and name the folder `tradesignals`

1. Zip the project (all files: `app.py`, `config.py`, `models/`, `routes/`, `utils/`, `requirements.txt`, `schema.sql`, templates, static, etc.).
2. In cPanel, open **File Manager** → go to your desired folder (e.g. `public_html` or a subdomain folder).
3. **Upload** the zip and **Extract**.
4. **Rename** the extracted folder to **`tradesignals`** (right‑click folder → Rename).  
   Your app root will be e.g. `public_html/tradesignals` (the folder that contains `app.py`).

---

## Step 2: Create the Python application (Create Python App)

1. In cPanel, open **Setup Python App** (or **Application Manager**).
2. Click **Create Application** (or **Create Python project**).
3. Set:
   - **Python version:** 3.10 or 3.11 (recommended).
   - **Application root:** The folder that contains `app.py` — use **`tradesignals`** (e.g. `tradesignals` or `public_html/tradesignals`, depending on how cPanel shows paths).
   - **Application URL:** Your domain or subdomain (e.g. `yourdomain.com` or `tradesignals.yourdomain.com`).
   - **Application startup file:** `app.py`.
   - **Application startup function / callable:** `application` (the app uses `application = app` in `app.py`).
4. Save/Create the application.

---

## Step 3: Create the PostgreSQL database

1. In cPanel, open **PostgreSQL Databases** (or **Databases** → **PostgreSQL**).
2. **Create a database** (e.g. `cpaneluser_tradesignals`). Note the full name (with prefix).
3. **Create a user** and set a strong password. Note the full username (e.g. `cpaneluser_tradeuser`).
4. **Add the user to the database** with **ALL PRIVILEGES**.
5. Note down: **DB_NAME**, **DB_USER**, **DB_PASSWORD**.  
   **DB_HOST** is usually `localhost`; **DB_PORT** is usually `5432` (check cPanel if different).

For detailed PostgreSQL setup in cPanel, see **POSTGRESQL_CPANEL_SETUP.md**.

---

## Step 4: Set environment variables

1. In **Setup Python App**, open your application → **Configuration** or **Environment Variables**.
2. Add these variables (use the exact names; values from Step 3 and your settings):

| Variable        | Example value        | Description                          |
|-----------------|----------------------|--------------------------------------|
| `DB_HOST`       | `localhost`          | PostgreSQL host                      |
| `DB_PORT`       | `5432`               | PostgreSQL port                      |
| `DB_NAME`       | `cpaneluser_tradesignals` | Full database name (from Step 3) |
| `DB_USER`       | `cpaneluser_tradeuser`  | Full database user (from Step 3)     |
| `DB_PASSWORD`   | `your_secure_password` | Database password                 |
| `SECRET_KEY`    | `your-long-random-secret-key` | Flask secret (change in production) |

**Optional:** For email (OTP), reCAPTCHA, payments, set:  
`MAIL_SERVER`, `MAIL_PORT`, `MAIL_USERNAME`, `MAIL_PASSWORD`, `RECAPTCHA_SITE_KEY`, `RECAPTCHA_SECRET_KEY`, `PAYMENT_GATEWAY_API_KEY`, `PAYMENT_GATEWAY_SECRET`.

**Optional:** If cPanel gives a single connection string, set `DATABASE_URL` instead (e.g. `postgresql+psycopg2://user:password@host:5432/dbname`). The app uses `DATABASE_URL` if set, otherwise builds the URL from `DB_*`.

3. Save. Then **Restart** the application so variables are loaded.

---

## Step 5: Install dependencies

1. In **Setup Python App**, open your application.
2. Find **Run pip install** or a terminal/SSH that uses the app’s virtual environment.
3. Run (path may differ; use the path cPanel shows for your app):

   ```bash
   pip install -r requirements.txt
   ```

   Or install in the app’s venv (path depends on your cPanel username and Python app name; use **tradesignals** as the app folder):

   ```bash
   source /home/cpaneluser/virtualenv/tradesignals/3.10/bin/activate
   pip install -r requirements.txt
   ```

   Ensure `psycopg2-binary` and all packages from `requirements.txt` are installed in **this** app’s environment.

---

## Step 6: Initialize the database

**Option A – Let the app create tables (easiest)**  
1. After Steps 1–5, click **Restart** on the Python app.  
2. Open your **Application URL** in a browser.  
3. The app runs `db.create_all()` on startup and creates all tables. It also seeds initial products and a default superadmin if the DB is empty.

**Option B – Run schema manually**  
1. In cPanel, use **Terminal** or **phpPgAdmin**.  
2. Connect to PostgreSQL as the database user.  
3. Run the project’s `schema.sql` (adjust paths to your home and folder **tradesignals**):

   ```bash
   psql -h localhost -U cpaneluser_tradeuser -d cpaneluser_tradesignals -f /home/cpaneluser/public_html/tradesignals/schema.sql
   ```

   Then open the Application URL; the app will use the existing tables.

---

## Step 7: Open the app and log in

1. Visit your **Application URL** (e.g. `https://yourdomain.com`).
2. **Admin:** Go to `/admin/login`.  
   Default superadmin (if seeded): **Email** `superadmin@tradesignal.tech`, **Password** `TradeSignal@2026` — change this in production.
3. **User:** Use the public pages to register/login and use the app.

---

## Troubleshooting

- **App won’t start:** Check cPanel **Error Logs** and the Python app log. Ensure the app root points to the folder containing `app.py` and the callable is `application`.
- **Database errors:** Confirm `DB_HOST`, `DB_PORT`, `DB_NAME`, `DB_USER`, `DB_PASSWORD` (or `DATABASE_URL`) are set correctly and the user has full access to the database. Test connection via phpPgAdmin or `psql`.
- **Missing module (e.g. psycopg2):** Run `pip install -r requirements.txt` inside the **same** virtual environment that cPanel uses for this app, then restart.
- **500 errors:** Enable debug only for testing; check logs for tracebacks. Ensure `SECRET_KEY` is set in production.

---

## Summary

| Step | Action |
|------|--------|
| 1 | Upload project in File Manager, extract, and **rename folder to `tradesignals`** |
| 2 | **Create Python App** in cPanel; application root = `tradesignals`, startup file `app.py`, callable `application` |
| 3 | Create PostgreSQL database and user (e.g. `cpaneluser_tradesignals`); grant ALL PRIVILEGES |
| 4 | In the Python app, set `DB_HOST`, `DB_PORT`, `DB_NAME`, `DB_USER`, `DB_PASSWORD`, `SECRET_KEY` (and optional mail/payment vars) |
| 5 | Run `pip install -r requirements.txt` in the **tradesignals** app’s virtual environment |
| 6 | Restart app and open URL (tables created on first load), or run `schema.sql` first |
| 7 | Log in at `/admin/login` with the seeded superadmin or your own admin |
