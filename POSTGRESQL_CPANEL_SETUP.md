# How to Set Up PostgreSQL in cPanel and Connect This Project

This guide explains how to create and manage PostgreSQL in cPanel, and how the Trade Signals Flask app connects to it.

---

## Part 1: Setting Up PostgreSQL in cPanel

### 1.1 Open PostgreSQL in cPanel

1. Log in to **cPanel**.
2. In the **Databases** section, click **PostgreSQL Databases** (or **PostgreSQL® Databases**).  
   - If you don’t see it, your host may use a different label (e.g. **Remote PostgreSQL®** or **Database** tools). Check your host’s docs.

### 1.2 Create a New Database

1. In **Create New Database**:
   - **New Database:** Enter a name (e.g. `tradesignals`).  
   - cPanel will add your username as a prefix. The full name will look like: `cpaneluser_tradesignals`.
2. Click **Create Database**.
3. **Write down the full database name** (with prefix). You will use it as `DB_NAME` in the app.

### 1.3 Create a Database User

1. Scroll to **PostgreSQL Users** → **Add New User**.
2. **Username:** Choose a name (e.g. `tradeuser`).  
   Full username will be something like: `cpaneluser_tradeuser`.
3. **Password:** Use the **Password Generator** or type a strong password.
4. **Password Strength:** Ensure it is “Very Strong”.
5. Click **Create User**.
6. **Save the username and password** (e.g. in a password manager). You will use them as `DB_USER` and `DB_PASSWORD`.

### 1.4 Add the User to the Database

1. Scroll to **Add User To Database**.
2. **User:** Select the user you created (e.g. `cpaneluser_tradeuser`).
3. **Database:** Select the database you created (e.g. `cpaneluser_tradesignals`).
4. Click **Add**.
5. On the **Manage User Privileges** page, select **ALL PRIVILEGES** (or at least: SELECT, INSERT, UPDATE, DELETE, CREATE, and schema/table rights needed for the app).
6. Click **Make Changes**.

Your PostgreSQL database and user are ready. The app will connect using these credentials.

### 1.5 Connection Details (for reference)

| Item        | Typical value   | Where to use it        |
|------------|-----------------|-------------------------|
| **Host**   | `localhost`     | `DB_HOST`               |
| **Port**   | `5432`          | `DB_PORT`               |
| **Database** | `cpaneluser_tradesignals` | `DB_NAME`   |
| **Username** | `cpaneluser_tradeuser`   | `DB_USER`   |
| **Password** | (the one you set)        | `DB_PASSWORD` |

Some hosts show a **Socket** path instead of host/port. In that case you may need to set `DB_HOST` to the socket path or ask support how to use PostgreSQL with Python on their cPanel.

---

## Part 2: How This Project Connects to PostgreSQL

### 2.1 Connection method

The app uses **SQLAlchemy** with the **psycopg2** driver. It does **not** use SQLite; the only database is PostgreSQL.

- **Driver:** `psycopg2-binary` (in `requirements.txt`).
- **URI format:**  
  `postgresql+psycopg2://USER:PASSWORD@HOST:PORT/DATABASE`

### 2.2 Where the app gets credentials

Credentials come from **environment variables** (set in cPanel’s **Setup Python App** for this project):

| Variable       | Required | Description        |
|----------------|----------|--------------------|
| `DB_HOST`      | Yes      | Usually `localhost` |
| `DB_PORT`      | Yes      | Usually `5432`      |
| `DB_NAME`      | Yes      | Full DB name (e.g. `cpaneluser_tradesignals`) |
| `DB_USER`      | Yes      | Full user (e.g. `cpaneluser_tradeuser`)      |
| `DB_PASSWORD`  | Yes      | User’s password     |

Optional:

- **`DATABASE_URL`** – If set, the app uses this full URI instead of building it from `DB_*`. Example:  
  `postgresql+psycopg2://cpaneluser_tradeuser:YOUR_PASSWORD@localhost:5432/cpaneluser_tradesignals`

- **`SECRET_KEY`** – Required for production (Flask sessions).

### 2.3 Where this is configured in code

- **config.py**  
  - If `DATABASE_URL` is set, it is used as `SQLALCHEMY_DATABASE_URI`.  
  - Otherwise, the URI is built from `DB_HOST`, `DB_PORT`, `DB_NAME`, `DB_USER`, and `DB_PASSWORD`.  
  - Passwords with special characters are URL-encoded before being put in the URI.

So: **setting the five `DB_*` variables in cPanel is enough** for this project to connect to the PostgreSQL database you created above.

### 2.4 Where to set variables in cPanel (Connect app to PostgreSQL)

1. In cPanel, open **Setup Python App** (or **Application Manager**).
2. Open your **Trade Signals** application (e.g. `tradesignals`).
3. Find **Environment Variables** or **Configuration** → **Environment Variables**.
4. Add each variable:
   - **Name:** `DB_HOST` → **Value:** `localhost`
   - **Name:** `DB_PORT` → **Value:** `5432`
   - **Name:** `DB_NAME` → **Value:** your full database name (e.g. `cpaneluser_tradesignals`)
   - **Name:** `DB_USER` → **Value:** your full PostgreSQL user (e.g. `cpaneluser_tradeuser`)
   - **Name:** `DB_PASSWORD` → **Value:** the user’s password
   - **Name:** `SECRET_KEY` → **Value:** a long random string (for production)
5. Save and **Restart** the application.

After restart, the app will connect to your PostgreSQL database using these values.

---

## Part 3: Initialize the Database (Tables)

The app can create tables in two ways.

### 3.1 Option A: Let the app create tables (recommended)

1. Ensure the Python app is created, env vars are set, and `pip install -r requirements.txt` has been run (see **cpanel.md**).
2. **Restart** the Python app.
3. Open your **Application URL** in a browser (e.g. `https://yourdomain.com`).
4. On first request, the app runs `db.create_all()` and creates all tables. It may also seed default products and a superadmin account.

No manual SQL is required.

### 3.2 Option B: Run schema.sql manually

If you prefer to create tables yourself:

1. In cPanel, open **Terminal** or use **phpPgAdmin**.
2. Connect to PostgreSQL with the same user and database you use in the app.
3. Run the project’s **schema.sql** (path example; adjust `cpaneluser` and path to your app):

   ```bash
   psql -h localhost -U cpaneluser_tradeuser -d cpaneluser_tradesignals -f /home/cpaneluser/public_html/tradesignals/schema.sql
   ```

4. Then open the Application URL. The app will use the existing tables.

---

## Part 4: Verify the Connection

1. **Restart** the Python app after setting env vars.
2. Open the **Application URL**. If the app loads (home or login page), the connection is working.
3. If you see database errors:
   - Check **Error Logs** in cPanel.
   - Confirm all five `DB_*` variables are set and match the database and user you created.
   - In **PostgreSQL Databases**, confirm the user is added to the database with **ALL PRIVILEGES**.
   - Optionally, test the same credentials in **phpPgAdmin** (if available) to confirm they work.

---

## Part 5: Summary

| Task                         | Where / How |
|-----------------------------|-------------|
| Create PostgreSQL database  | cPanel → PostgreSQL Databases → Create New Database |
| Create PostgreSQL user      | cPanel → PostgreSQL Databases → Add New User |
| Grant access                 | Add User To Database → ALL PRIVILEGES |
| Give app the credentials     | Setup Python App → your app → Environment Variables: `DB_HOST`, `DB_PORT`, `DB_NAME`, `DB_USER`, `DB_PASSWORD` |
| Create tables                | Either visit the app URL (app runs `db.create_all()`) or run `schema.sql` manually |

After this, the Trade Signals project is using PostgreSQL in cPanel with no SQLite involved.
