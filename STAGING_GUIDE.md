# 🧪 Staging Environment Guide

## Overview

We use a **dual-function staging approach** where staging and production are separate Cloud Functions in the same GCP project, providing different URLs for testing and production use.

## 🌐 Environment URLs

- **Staging**: `https://europe-west6-miavia-422212.cloudfunctions.net/bmw_api_staging`
  - Used by: preview--draiv.lovable.app
  - Auto-deploys from: `develop` branch
  - File: `apis/bmw/src/staging/main_staging.py`

- **Production**: `https://europe-west6-miavia-422212.cloudfunctions.net/bmw_api_stateless`
  - Used by: Production app
  - Deploys from: `main` branch
  - File: `apis/bmw/src/main_stateless.py`

## 📁 Project Structure

```
apis/bmw/
├── src/
│   ├── main_stateless.py         # Production (stable)
│   └── staging/
│       └── main_staging.py       # Staging (experimental)
├── .staging-version              # Tracks staging versions
└── promote.sh                    # Local promotion script
```

## 🚀 Development Workflow

### 1. Develop in Staging

Edit the staging file for experiments:
```bash
# Edit staging file
code apis/bmw/src/staging/main_staging.py

# Test locally
cd apis/bmw/src/staging
python3 -c "import main_staging"
```

### 2. Deploy to Staging

**Automatic** (on push to develop):
```bash
git add apis/bmw/src/staging/main_staging.py
git commit -m "feat: Add new feature to staging"
git push origin develop
```

**Manual** (from any branch):
```bash
gh workflow run deploy-staging.yml -f deploy_message="Testing new feature"
```

### 3. Test in Preview Environment

Configure preview--draiv.lovable.app to use:
```
https://europe-west6-miavia-422212.cloudfunctions.net/bmw_api_staging
```

### 4. Promote to Production

Once tested and ready:

**Via GitHub Actions** (Recommended):
```bash
gh workflow run promote-to-prod.yml \
  -f confirm_promotion=PROMOTE \
  -f promotion_message="Feature tested and ready"
```

**Via Local Script**:
```bash
cd apis/bmw
./promote.sh
# Follow prompts, then:
git add -A
git commit -m "Promote staging to production"
git push origin main
```

## 📊 Monitoring

### View Logs

**Staging logs**:
```bash
gcloud functions logs read bmw_api_staging \
  --region=europe-west6 \
  --project=miavia-422212
```

**Production logs**:
```bash
gcloud functions logs read bmw_api_stateless \
  --region=europe-west6 \
  --project=miavia-422212
```

### Check Function Status

```bash
# Staging status
gcloud functions describe bmw_api_staging \
  --region=europe-west6 \
  --project=miavia-422212

# Production status
gcloud functions describe bmw_api_stateless \
  --region=europe-west6 \
  --project=miavia-422212
```

## 🔄 Rollback Procedure

If production breaks after promotion:

### Quick Rollback

1. Find backup in GitHub Actions artifacts
2. Download `production-backup-{run-number}`
3. Restore the file:
```bash
# Restore from backup
cp backups/*/main_stateless.py.backup apis/bmw/src/main_stateless.py

# Redeploy
gh workflow run bmw-api-pipeline.yml -f environment=production
```

### Manual Rollback

```bash
# View git history
git log --oneline apis/bmw/src/main_stateless.py

# Revert to previous version
git checkout <commit-hash> -- apis/bmw/src/main_stateless.py

# Commit and deploy
git commit -m "Rollback to previous production version"
git push origin main
```

## 🎯 Best Practices

### DO's ✅
- Always test in staging first
- Use meaningful commit messages
- Monitor logs after deployment
- Keep staging close to production
- Document breaking changes

### DON'Ts ❌
- Don't edit production directly
- Don't skip staging tests
- Don't promote untested code
- Don't ignore deployment failures
- Don't forget to update docs

## 🛠️ Common Tasks

### Update Both Staging and Production

When you need the same change in both:
```bash
# Update staging
vim apis/bmw/src/staging/main_staging.py

# Copy to production
cp apis/bmw/src/staging/main_staging.py apis/bmw/src/main_stateless.py

# Commit both
git add apis/bmw/src/
git commit -m "Update both staging and production"
git push origin main
```

### Emergency Production Fix

For critical fixes that can't wait:
```bash
# Fix production directly
vim apis/bmw/src/main_stateless.py

# Deploy immediately
git add apis/bmw/src/main_stateless.py
git commit -m "HOTFIX: Critical production fix"
git push origin main

# Backport to staging
cp apis/bmw/src/main_stateless.py apis/bmw/src/staging/main_staging.py
git add apis/bmw/src/staging/main_staging.py
git commit -m "Backport hotfix to staging"
git push origin develop
```

## 📝 Version Tracking

The `.staging-version` file tracks deployments:
```bash
# View staging history
cat apis/bmw/.staging-version

# Add custom version note
echo "1.2.0|$(git rev-parse HEAD)|$(date)|Added new feature X" >> apis/bmw/.staging-version
```

## 🔍 Testing

### Test Staging Endpoint
```bash
curl -X POST 'https://europe-west6-miavia-422212.cloudfunctions.net/bmw_api_staging' \
  -H 'Content-Type: application/json' \
  -d '{
    "email": "test@example.com",
    "password": "test",
    "wkn": "TEST123",
    "hcaptcha": "test-token",
    "action": "status"
  }'
```

### Test Production Endpoint
```bash
curl -X POST 'https://europe-west6-miavia-422212.cloudfunctions.net/bmw_api_stateless' \
  -H 'Content-Type: application/json' \
  -d '{
    "email": "test@example.com",
    "password": "test",
    "wkn": "TEST123",
    "hcaptcha": "test-token",
    "action": "status"
  }'
```

## 🚨 Troubleshooting

### Staging deployment fails
1. Check syntax: `python3 -m py_compile apis/bmw/src/staging/main_staging.py`
2. Check logs: `gh run list --workflow=deploy-staging.yml`
3. Verify secrets: `gh secret list`

### Production promotion fails
1. Check staging is healthy first
2. Verify you typed "PROMOTE" correctly
3. Check GitHub Actions logs
4. Use manual rollback if needed

### Functions not responding
1. Check function status in GCP Console
2. View function logs for errors
3. Verify CORS headers are set
4. Check if function is rate-limited

## 📚 Related Documentation

- [BMW API README](apis/bmw/README.md)
- [GitHub Actions Setup](.github/SETUP_GUIDE.md)
- [Main Project README](README.md)

---

*Last Updated: January 2025*  
*Staging System Version: 1.0.0*