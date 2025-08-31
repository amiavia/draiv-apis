# GitHub Actions Setup Guide for BMW API Pipeline

This guide will help you configure GitHub secrets and environments for the BMW API CI/CD pipeline.

## 🔐 Required GitHub Secrets

Navigate to your repository → Settings → Secrets and variables → Actions

### 1. Google Cloud Service Account Keys

#### Production Service Account
- **Secret Name**: `GCP_SA_KEY_PRODUCTION` ✅ (Already exists)
- **Value**: Your production GCP service account JSON key
- **Required Permissions**:
  - Cloud Functions Developer
  - Service Account User
  - Cloud Build Service Account

#### Staging Service Account
- **Secret Name**: `GCP_SA_KEY_STAGING` ❌ (Needs to be added)
- **Value**: Your staging GCP service account JSON key
- **How to create**:
  ```bash
  # Create service account
  gcloud iam service-accounts create github-actions-staging \
    --display-name="GitHub Actions Staging" \
    --project=miavia-staging

  # Grant permissions
  gcloud projects add-iam-policy-binding miavia-staging \
    --member="serviceAccount:github-actions-staging@miavia-staging.iam.gserviceaccount.com" \
    --role="roles/cloudfunctions.developer"

  gcloud projects add-iam-policy-binding miavia-staging \
    --member="serviceAccount:github-actions-staging@miavia-staging.iam.gserviceaccount.com" \
    --role="roles/iam.serviceAccountUser"

  # Create and download key
  gcloud iam service-accounts keys create ~/staging-key.json \
    --iam-account=github-actions-staging@miavia-staging.iam.gserviceaccount.com

  # Copy the contents of ~/staging-key.json to the GitHub secret
  cat ~/staging-key.json
  ```

### 2. Project Configuration

#### GCP Project ID
- **Secret Name**: `GCP_PROJECT_ID` ✅ (Already exists)
- **Value**: `miavia-422212`

#### GCP Region
- **Secret Name**: `GCP_REGION` ✅ (Already exists)
- **Value**: `europe-west6`

### 3. Notifications (Optional)

#### Slack Webhook
- **Secret Name**: `SLACK_WEBHOOK` ❌ (Optional - needs to be added)
- **Value**: Your Slack webhook URL
- **How to get**:
  1. Go to https://api.slack.com/apps
  2. Create a new app or select existing
  3. Add "Incoming Webhooks" feature
  4. Create webhook for your channel
  5. Copy the webhook URL

## 🌍 GitHub Environments Configuration

Navigate to your repository → Settings → Environments

### 1. Staging Environment

Click "New environment" and create:
- **Name**: `staging`
- **Configuration**:
  - ✅ No required reviewers (auto-deploy)
  - ✅ No deployment protection rules
  - **Environment URL**: `https://europe-west6-miavia-staging.cloudfunctions.net/bmw_api_stateless`

### 2. Production Environment

Click "New environment" and create:
- **Name**: `production`
- **Configuration**:
  - ✅ Required reviewers (add team members who can approve)
  - ✅ Prevent self-review
  - ⏱️ Wait timer: 5 minutes (optional)
  - **Environment URL**: `https://europe-west6-miavia-422212.cloudfunctions.net/bmw_api_stateless`
  - **Deployment branches**: Only allow `main` branch

#### Setting up Required Reviewers:
1. In the production environment settings
2. Check "Required reviewers"
3. Add GitHub usernames or teams who can approve
4. Check "Prevent self-review" to prevent PR authors from approving

## 🚀 Activating the New Pipeline

### 1. Disable Old Workflows (Optional)

To avoid confusion, you can disable the old workflows:

```bash
# Via GitHub CLI
gh workflow disable "Auto Deploy BMW API Stateless"
gh workflow disable "Deploy BMW API Stateless"
gh workflow disable "Deploy BMW API"

# Or manually in GitHub UI:
# Go to Actions → Select workflow → ⋯ menu → Disable workflow
```

### 2. Test the New Pipeline

#### Manual Test (Staging)
```bash
# Trigger staging deployment manually
gh workflow run bmw-api-pipeline.yml -f environment=staging
```

#### Manual Test (Production)
```bash
# Trigger production deployment manually (will require approval)
gh workflow run bmw-api-pipeline.yml -f environment=production
```

### 3. Automatic Triggers

The pipeline will automatically run when:
- **Pull Request**: Opens or updates against `main` or `develop`
- **Push to develop**: Auto-deploys to staging
- **Push to main**: Deploys to production (with approval)

## 📊 Monitoring Deployments

### View Deployment Status
```bash
# List recent workflow runs
gh run list --workflow=bmw-api-pipeline.yml

# Watch a specific run
gh run watch <run-id>

# View logs
gh run view <run-id> --log
```

### Google Cloud Console
- **Staging Logs**: https://console.cloud.google.com/functions/details/europe-west6/bmw_api_stateless?project=miavia-staging
- **Production Logs**: https://console.cloud.google.com/functions/details/europe-west6/bmw_api_stateless?project=miavia-422212

## 🔄 Rollback Procedure

If a production deployment fails:

### Automatic Rollback
The pipeline includes automatic rollback on failure (currently logs only, manual intervention needed)

### Manual Rollback
```bash
# List all function revisions
gcloud functions describe bmw_api_stateless \
  --region=europe-west6 \
  --project=miavia-422212 \
  --format="value(updateTime)"

# Redeploy previous version
gcloud functions deploy bmw_api_stateless \
  --source=gs://previous-source-bucket/source.zip \
  --region=europe-west6 \
  --project=miavia-422212
```

## ✅ Checklist

Before using the pipeline, ensure:

- [ ] `GCP_SA_KEY_STAGING` secret is added
- [ ] `SLACK_WEBHOOK` secret is added (optional)
- [ ] Staging environment is created
- [ ] Production environment is created with reviewers
- [ ] Old workflows are disabled (optional)
- [ ] Test deployment to staging works
- [ ] Test deployment to production works (with approval)

## 🆘 Troubleshooting

### Common Issues

1. **Container fails to start (PORT 8080)**
   - Fixed in main_stateless.py - removed Flask app initialization
   - Only uses functions_framework now

2. **Region mismatch errors**
   - All workflows now use `europe-west6` consistently

3. **Permission denied errors**
   - Check service account has required roles
   - Verify secret is correctly formatted JSON

4. **Workflow not triggering**
   - Check path filters in workflow file
   - Verify branch names match (main, develop)

## 📝 Notes

- The unified pipeline replaces all individual deployment workflows
- Staging deployments are automatic on push to `develop`
- Production deployments require manual approval
- All deployments include automated tests and security scans
- Artifacts are automatically cleaned up after 7 days

---

*Last Updated: January 2025*  
*Pipeline Version: 1.0.0*