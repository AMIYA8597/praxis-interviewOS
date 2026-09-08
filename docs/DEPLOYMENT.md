# Deployment & Hosting Guide

## Supabase Free Tier — Project Pause
**Current Inactivity Window**: Free tier projects are automatically paused after **1 week (7 days)** of compute inactivity.
**Application Impact**: When paused, the application will experience a "Connection Refused" error or timeout (`503 Service Unavailable` or `connection to server at "aws-0-...", port 5432 failed: Connection refused`) when the backend attempts to connect to the database or Redis instance.
**Mitigation**: Phase 1.13 implements an automated keepalive job to periodically ping the database and prevent it from entering the paused state. If it does pause, it must be manually restored via the Supabase Dashboard before the app will function.

## 1. Local Deployment (Windows 11)
The application natively supports Windows 11 without requiring WSL2. We use PowerShell to bootstrap the environment.
```powershell
.\scripts\setup.ps1
.\scripts\dev.ps1
```

## 2. Desktop Packaging (Electron NSIS)
We use `electron-builder` to package the Windows installer.
```powershell
pnpm --filter desktop build
pnpm --filter desktop release
```

> **WARNING (HACKATHON JUDGES)**: 
> The resulting `PRAXIS-Setup.exe` is **unsigned**. Windows SmartScreen will display a severe blue warning blocking execution. You must click "More info" -> "Run anyway". 
> *To fix this for a commercial release, we would need to purchase an EV Code Signing Certificate (~$300/yr) and a physical hardware USB token to satisfy Microsoft's driver signing policies.*

## 3. Web & API Hosting
For the hackathon, we recommend a split-tier free hosting layout:
- **Frontend (Web)**: Vercel Hobby Tier.
- **Backend (FastAPI)**: Render Free Tier.
- **Realtime (WebSocket)**: Fly.io (better WebSocket support than Render).

## 4. Supabase Keepalive & Manual Un-pause
The Supabase free tier pauses projects after **7 days of inactivity**. 

**Automated Prevention:** We prevent this using a GitHub Actions cron workflow (`.github/workflows/keepalive.yml`) that pings the REST API every 3 days. A secondary belt-and-suspenders keepalive runs daily via the arq background worker.

**Fallback Procedure (How to Un-pause):**
If the keepalive fails and the project is paused, the application will throw a `503 Service Unavailable` or a Postgres `Connection refused` error. 
To manually restore it before a demo:
1. Log into the [Supabase Dashboard](https://app.supabase.com/).
2. Select the PRAXIS project.
3. A large banner will state "This project is paused." Click the **Restore project** button.
4. Wait approximately 2–5 minutes for the database and API gateways to spin back up.
5. Verify connectivity by running `.\scripts\validate-config.ps1` locally.

## 5. Database Backups
Supabase's free tier historically does **NOT** include automated daily backups with point-in-time recovery (this is a paid-tier feature).
For a hackathon or portfolio deployment, we implement a lightweight manual/scheduled backup script: `scripts/backup-db.ps1`. This script runs `pg_dump` against the `SUPABASE_URL` to create a local `.sql` dump. 

*Production Path*: This script is a portfolio-appropriate workaround. If this were a real, revenue-generating product, the immediate first step would be upgrading to Supabase Pro ($25/mo), which buys daily automated backups, 7-day point-in-time recovery (PITR), and SLA guarantees.
