# Trading Simulator Production Runbook

This runbook outlines operational procedures for managing the production deployment of the Trading Simulator.

## 1. Environment Variable Checklist

Before deploying, ensure the following environment variables are correctly set in their respective environments:

### Backend (Render)
- `DATABASE_URL`: Connection string to the Neon Postgres database.
- `SECRET_KEY`: A strong, randomly generated string for signing JWTs.
- `FRONTEND_ORIGINS`: Comma-separated list of allowed origins (e.g., `https://trading-app.vercel.app`).
- `ENVIRONMENT`: Must be set to `production` (enables secure cookies).
- `ADMIN_INITIAL_EMAIL`: Email for the first admin user (used by `seed_production.py`).
- `ADMIN_INITIAL_PASSWORD`: Password for the first admin user (used by `seed_production.py`).
- `LOG_LEVEL`: Usually `INFO`.

### Frontend (Vercel)
- `VITE_API_URL`: The production URL of the backend (e.g., `https://trading-api.onrender.com/api/v1`).

---

## 2. Admin Account Recovery Process

If the initial Admin account password is lost and needs to be recovered, or if no admin account exists:

1. **Option A: CLI Override (Recommended)**
   If you have access to the Render Dashboard shell:
   - Navigate to the `backend` directory.
   - Set the `ADMIN_INITIAL_EMAIL` and `ADMIN_INITIAL_PASSWORD` variables in the shell.
   - Run the seed script: `python scripts/seed_production.py`
   - This will check if the user exists. If they don't, it will create them.

2. **Option B: Database Direct Modification**
   - Connect to the Neon database using a SQL client.
   - Locate the admin user in the `users` table.
   - Update the `hashed_password` column with a newly generated bcrypt hash.
   - Ensure the `role` column is set to `'ADMIN'`.

---

## 3. Render Service Restart Procedure

If the backend becomes unresponsive or needs to be restarted manually:

1. Log in to the [Render Dashboard](https://dashboard.render.com).
2. Select the `trading-api` Web Service.
3. Click the **Manual Deploy** button in the top right corner.
4. Select **Deploy latest commit** (if you want to pull new code) or **Restart service** (to simply reboot the container).
5. Watch the Logs tab to ensure `uvicorn` starts successfully on the assigned `$PORT`.

*Note on Free Tier*: Render spins down free web services after 15 minutes of inactivity. The next request will experience a cold boot delay (up to 50 seconds).

---

## 4. Vercel Deployment Rollback

If a bad frontend build is deployed and needs to be reverted immediately:

1. Log in to the [Vercel Dashboard](https://vercel.com/dashboard).
2. Navigate to the Trading Simulator project.
3. Click on the **Deployments** tab.
4. Locate the last known good deployment in the list.
5. Click the three dots (`...`) next to that deployment and select **Promote to Production** (or **Assign Custom Domains**).
6. Confirm the action. Traffic will instantly route to the older, stable build without waiting for a re-compile.

---

## 5. Neon Outage Recovery

If the Neon PostgreSQL database experiences an outage or data corruption:

1. **Verify Outage**: Check the [Neon Status Page](https://neon.statuspage.io/) to confirm if it's a provider issue.
2. **Connection Issues**: If the database is simply sleeping (Neon free tier scales to zero), the backend will automatically wake it up, though the first query may take a few seconds. Ensure the connection string in Render is still valid.
3. **Point-in-Time Recovery**:
   - Log in to the Neon Console.
   - Navigate to the **Branches** section.
   - Select the `main` branch (or your production branch) and click **Restore**.
   - Choose a timestamp prior to the corruption/outage.
   - Neon will spin up a new branch with the state at that exact second.
   - Update the `DATABASE_URL` in the Render dashboard to point to the recovered branch and restart the Render service.

---

## 6. Production Smoke-Test Checklist

After a fresh deployment to production, perform the following manual smoke tests to verify platform stability:

- [ ] **Signup**: Create a new account.
- [ ] **Email Verification**: Verify the account via the emailed link/token.
- [ ] **Login**: Log in with the verified account.
- [ ] **Refresh Session**: Reload the browser to ensure the refresh token restores the session without requiring a new login.
- [ ] **Create Watchlist**: Add a symbol to a new watchlist.
- [ ] **Simulate Trade**: Open the trade panel and verify pre-trade simulation charges.
- [ ] **Execute Buy**: Execute a BUY order and verify portfolio holdings update.
- [ ] **Execute Sell**: Execute a SELL order and verify cash balance updates.
- [ ] **Admin Login**: Log in using the seeded Admin account.
- [ ] **Suspend User**: Suspend the newly created user account.
- [ ] **Reactivate User**: Reactivate the user account.
- [ ] **Balance Adjustment**: Adjust a user's cash balance and verify the ledger entry.
- [ ] **CSV Export**: Export user data as CSV from the Admin Panel.

