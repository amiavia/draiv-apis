# Simplified Setup Guide - Production Only

Since staging project setup failed, here's how to proceed with **production only**:

## ✅ What You Already Have

- `GCP_SA_KEY_PRODUCTION` secret ✅
- `GCP_PROJECT_ID` secret ✅  
- `GCP_REGION` secret ✅
- Production GCP project working ✅

## 🚀 Quick Setup Steps

### 1. No Additional Secrets Needed!

The pipeline now uses your existing production secrets for both staging and production deployments.

### 2. Create GitHub Environments

Go to your repo → Settings → Environments:

#### Staging Environment
- Click "New environment"
- Name: `staging`
- No approval needed
- URL: `https://europe-west6-miavia-422212.cloudfunctions.net/bmw_api_stateless_staging`

#### Production Environment  
- Click "New environment"
- Name: `production`
- Add required reviewers (optional but recommended)
- URL: `https://europe-west6-miavia-422212.cloudfunctions.net/bmw_api_stateless`

### 3. How It Works

The pipeline now deploys:
- **Staging**: Function named `bmw_api_stateless_staging` (in production project)
- **Production**: Function named `bmw_api_stateless` (in production project)

Both use the same GCP project but different function names to keep them separate.

## 🎯 Test the Pipeline

Push your changes to trigger deployment:

```bash
# Commit and push
git add -A
git commit -m "Use production project for both staging and prod"
git push origin master

# Or manually trigger staging
gh workflow run bmw-api-pipeline.yml -f environment=staging

# Or manually trigger production (requires approval if configured)
gh workflow run bmw-api-pipeline.yml -f environment=production
```

## 📝 Deployment URLs

After deployment, your functions will be available at:

- **Staging**: https://europe-west6-miavia-422212.cloudfunctions.net/bmw_api_stateless_staging
- **Production**: https://europe-west6-miavia-422212.cloudfunctions.net/bmw_api_stateless

## 💰 Cost Considerations

Using the same project for both environments:
- ✅ Simpler billing (one project)
- ✅ No additional setup required
- ⚠️ Staging and production share quotas
- ⚠️ Less isolation between environments

## 🔄 Optional: Disable Old Workflows

To avoid confusion:

```bash
gh workflow disable "Auto Deploy BMW API Stateless"
gh workflow disable "Deploy BMW API Stateless" 
```

## ✨ That's It!

You're ready to deploy. The pipeline will:
1. Run tests on pull requests
2. Deploy to staging (`bmw_api_stateless_staging`) on push to develop
3. Deploy to production (`bmw_api_stateless`) on push to main

No additional secrets or project setup needed!