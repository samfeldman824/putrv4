# Render Deployment Guide

This guide will help you deploy the PUTR v4 application to Render.

## Prerequisites

- GitHub account with this repository pushed
- Render account (sign up at https://render.com - free)

## Deployment Steps

### Option 1: Blueprint Deploy (Recommended - Automated)

1. **Push your code to GitHub** (if not already done)
   ```bash
   git add .
   git commit -m "Add Render deployment configuration"
   git push origin main
   ```

2. **Deploy to Render**
   - Go to [Render Dashboard](https://dashboard.render.com)
   - Click **"New +"** → **"Blueprint"**
   - Connect your GitHub repository: `samfeldman824/putrv4`
   - Render will automatically detect `render.yaml` and create:
     - PostgreSQL database (`putrv4-db`)
     - Web service (`putrv4-api`)
   - Click **"Apply"**

3. **Wait for deployment** (~3-5 minutes)
   - Database provisioning: ~1 minute
   - Application build: ~2-4 minutes
   - Your app will be live at: `https://putrv4-api.onrender.com`

### Option 2: Manual Setup

#### Step 1: Create PostgreSQL Database

1. Go to Render Dashboard → **New +** → **PostgreSQL**
2. Settings:
   - **Name**: `putrv4-db`
   - **Database**: `putr`
   - **User**: `putr_user`
   - **Region**: Choose closest to you
   - **Plan**: Free
3. Click **"Create Database"**
4. Copy the **Internal Database URL** (starts with `postgresql://...`)

#### Step 2: Create Web Service

1. Go to Render Dashboard → **New +** → **Web Service**
2. Connect your GitHub repository
3. Settings:
   - **Name**: `putrv4-api`
   - **Region**: Same as database
   - **Branch**: `main`
   - **Runtime**: `Python 3`
   - **Build Command**: `pip install uv && uv sync --frozen`
   - **Start Command**: `uvicorn src.main:app --host 0.0.0.0 --port $PORT`
   - **Plan**: Free

4. **Environment Variables**:
   - Click **"Advanced"** → **"Add Environment Variable"**
   - Add:
     ```
     DATABASE_URL = <paste Internal Database URL from Step 1>
     PYTHON_VERSION = 3.12.0
     ENVIRONMENT = production
     LOG_LEVEL = INFO
     ```

5. Click **"Create Web Service"**

## Post-Deployment

### Access Your Application

- **API URL**: `https://putrv4-api.onrender.com`
- **Health Check**: `https://putrv4-api.onrender.com/`
- **API Docs**: `https://putrv4-api.onrender.com/docs`

### Import CSV Data (Optional)

If you need to import your ledger CSV files:

1. Go to Render Dashboard → Your Web Service
2. Click **"Shell"** tab
3. Run:
   ```bash
   python -m src.import_csv
   ```

### Monitor Your Application

- **Logs**: Render Dashboard → Your service → "Logs" tab
- **Metrics**: Dashboard shows CPU, memory, request metrics
- **Events**: Dashboard shows deployment history

## Important Notes

### Free Tier Limitations

- **Database**: 90 days free, then expires (can create new one)
- **Web Service**: 
  - 750 hours/month free compute
  - Spins down after 15 minutes of inactivity
  - Cold start: ~20-30 seconds on first request
  - Limited to 512 MB RAM

### Cold Starts

Your app will "sleep" after 15 minutes of no requests. First request after sleep takes ~30s. Solutions:

1. **Use a ping service** (free):
   - [UptimeRobot](https://uptimerobot.com) - ping every 5 minutes
   - [Cron-Job.org](https://cron-job.org) - scheduled pings

2. **Upgrade to paid plan** ($7/month):
   - Always-on (no cold starts)
   - Better performance
   - More RAM

### Database Backups

Free tier doesn't include automatic backups. To backup:

```bash
# Download from Render
pg_dump $DATABASE_URL > backup.sql

# Or use Render's manual backup feature in dashboard
```

## Troubleshooting

### Build Fails

- Check build logs in Render dashboard
- Ensure `uv.lock` is committed to git
- Try: `Build Command: pip install -r requirements.txt`

### Database Connection Issues

- Verify `DATABASE_URL` is set correctly
- Check database is in same region as web service
- Ensure database is "Available" (not "Creating")

### Application Errors

- Check logs: Dashboard → Service → Logs
- Verify environment variables are set
- Check health check endpoint is responding

### Cold Start Too Slow

- Optimize imports in `main.py`
- Use lazy loading for heavy dependencies
- Consider upgrading to paid tier

## Environment Variables Reference

| Variable | Required | Default | Description |
|----------|----------|---------|-------------|
| `DATABASE_URL` | Yes | - | PostgreSQL connection string (auto-set by Render) |
| `PYTHON_VERSION` | No | 3.12.0 | Python runtime version |
| `ENVIRONMENT` | No | development | Application environment |
| `LOG_LEVEL` | No | INFO | Logging level (DEBUG, INFO, WARNING, ERROR) |

## Updating Your Application

Render auto-deploys on every push to `main`:

```bash
git add .
git commit -m "Your changes"
git push origin main
```

Deployment starts automatically and takes ~2-3 minutes.

## Cost Optimization

To maximize free tier:

1. **Use one repository** for multiple projects (share 750 hours)
2. **Deploy only when needed** (pause service when not using)
3. **Optimize cold starts** (faster = less compute time)
4. **Use external logging** if needed (free tier has 7-day log retention)

## Support

- **Render Docs**: https://render.com/docs
- **Community**: https://community.render.com
- **Status**: https://status.render.com

## Next Steps

1. Set up custom domain (optional, free with Render)
2. Configure CI/CD for testing before deploy
3. Add monitoring/alerting
4. Set up staging environment
5. Configure CORS properly for your frontend

---

**Deployment completed!** 🚀

Your FastAPI app is now live on Render with PostgreSQL.
