# Deployment History

## August 31, 2025

### Production Deployment - bmw_api
- **Time**: 05:13 UTC
- **Function**: bmw_api
- **Region**: europe-west6
- **Runtime**: python310
- **Status**: ✅ Success
- **URL**: https://europe-west6-miavia-422212.cloudfunctions.net/bmw_api
- **Method**: Manual deployment via gcloud CLI
- **Deployed by**: Anton (Cloud Shell)
- **Command Used**:
  ```bash
  gcloud functions deploy bmw_api \
    --gen2 \
    --runtime python310 \
    --region europe-west6 \
    --trigger-http \
    --allow-unauthenticated \
    --entry-point bmw_api \
    --source .
  ```

### Staging Deployment - bmw_api_staging
- **Time**: 08:11 UTC
- **Function**: bmw_api_staging
- **Region**: europe-west6
- **Runtime**: python310
- **Status**: ✅ Success (with manual IAM fix)
- **URL**: https://europe-west6-miavia-422212.cloudfunctions.net/bmw_api_staging
- **Method**: GitHub Actions workflow
- **Fixes Applied**:
  1. Added httpx==0.24.1 to requirements-stateless.txt
  2. Changed runtime from python311 to python310
  3. Simplified deployment to use `--source .` directly
  4. Manual IAM policy update for public access:
     ```bash
     gcloud run services add-iam-policy-binding bmw-api-staging \
       --member="allUsers" \
       --role="roles/run.invoker" \
       --region=europe-west6 \
       --project=miavia-422212
     ```

## Lessons Learned

### Critical Issues Resolved
1. **httpx Compatibility Error**
   - **Issue**: `AttributeError: module 'httpx._types' has no attribute 'VerifyTypes'`
   - **Solution**: Added explicit httpx==0.24.1 to requirements
   - **Root Cause**: bimmer-connected dependency conflict

2. **PORT 8080 Container Error**
   - **Issue**: Container failed to start and listen on PORT=8080
   - **Solution**: Fixed missing imports (jsonify, json) in main_stateless.py
   - **Root Cause**: Incomplete Flask imports

3. **IAM Permission Error**
   - **Issue**: `Permission 'run.services.setIamPolicy' denied`
   - **Solution**: Manual IAM policy update via gcloud CLI
   - **Root Cause**: Service account insufficient permissions

### Best Practices Identified
1. **Keep deployments simple**: Use `--source .` directly instead of complex packaging
2. **Match production setup**: Use same runtime (python310) as working deployment
3. **Pin dependencies**: Explicitly specify versions for critical dependencies
4. **Test imports**: Ensure all required imports are present before deployment
5. **Document manual steps**: Some IAM operations may require manual intervention

## Configuration Summary

### Working Configuration
- **Runtime**: python310 (NOT python311)
- **Dependencies**:
  - bimmer-connected==0.16.4
  - flask==3.0.3
  - functions-framework==3.8.2
  - aiohttp==3.10.10
  - httpx==0.24.1 (critical for compatibility)

### GitHub Actions Workflows
- **deploy-staging.yml**: Deploys to bmw_api_staging
- **bmw-api-pipeline.yml**: Production deployment pipeline
- **promote-to-prod.yml**: Promotes staging to production

### Environment Variables
- `BIMMER_CONNECTED_OAUTH_STORE`: /tmp/bimmer_connected/bimmer_connected.json
- `LOG_EXECUTION_ID`: true

---

**Last Updated**: August 31, 2025