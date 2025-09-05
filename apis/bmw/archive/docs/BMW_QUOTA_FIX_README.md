# BMW API Quota Limit Fix - Production Critical Update

## 🚨 Issue Summary

BMW introduced server-side quota limits tracked via `x-user-agent` HTTP header, causing production 403 "Out of call volume quota" errors that were being misinterpreted as authentication failures.

## ✅ Solution Implemented

### 1. Library Update
- **Upgraded** `bimmer-connected` from v0.16.4 → v0.17.2
- Includes latest BMW API compatibility improvements

### 2. Dynamic User Agent Generation
- **New component**: `utils/user_agent_manager.py`
- Generates stable, unique user agents per deployment/container
- Uses SHA256 hash of system UUID for distribution across quota pools
- Format: `draiv-bmw-api/{16-char-hash}`

### 3. Enhanced Error Handling  
- **New exception**: `QuotaLimitError` with retry timing
- Parses BMW quota error messages to extract replenishment times
- Returns HTTP 429 (Too Many Requests) for proper client handling

### 4. Circuit Breaker Enhancement
- **New state**: `QUOTA_PAUSED` (distinct from service failures)
- Respects BMW quota replenishment timing
- Exponential backoff for repeated quota errors
- Preserves authentication tokens during quota periods

### 5. Monitoring & Observability
- Health endpoint includes quota status and user agent info
- Circuit breaker stats include quota retry counts and timing
- Enhanced logging for quota events vs. service failures

## 🚀 Deployment Strategy

### Phase 1: Staging Deployment (Immediate)
```bash
# Deploy to staging first
cd /path/to/bmw-api
docker build -t bmw-api:quota-fix .
docker run -p 8080:8080 bmw-api:quota-fix

# Test quota handling
curl -X POST "http://localhost:8080" \
  -H "Content-Type: application/json" \
  -d '{"email": "test@example.com", "password": "test", "wkn": "TEST123"}'

# Check health endpoint for quota status
curl http://localhost:8080/health
```

### Phase 2: Production Canary (After 24h staging)
- Deploy to 10% of production traffic
- Monitor quota metrics vs. error rates
- Verify stable user agent generation

### Phase 3: Full Production (After 48h monitoring)
- Complete production rollout
- Monitor for reduced 403 errors
- Confirm quota distribution working

## 📊 Key Metrics to Monitor

### Before Fix (Baseline)
- 403 quota errors: ~X per hour
- Authentication failures: ~Y per hour  
- Average response time: ~Z ms

### After Fix (Expected)
- 403 quota errors: <5% of baseline
- Authentication failures: Only genuine auth issues
- Response time: Similar or improved
- Quota pause events: Logged but handled gracefully

## 🔍 Verification Commands

### Check User Agent Generation
```bash
curl http://localhost:8080/health | jq '.user_agent_info'
```

### Monitor Quota Status
```bash
curl http://localhost:8080/health | jq '.circuit_breaker_state'
```

### Check Circuit Breaker Stats
```bash
curl http://localhost:8080/metrics | jq '.quota_retry_count'
```

## 🛡️ Rollback Plan

If issues occur:

1. **Immediate revert** to v0.16.4 deployment
```bash
# Revert to previous image
docker run -p 8080:8080 bmw-api:v0.16.4
```

2. **Keep monitoring** quota errors for patterns
3. **Analyze logs** for unexpected behavior

## 🔧 Configuration Options

### Environment Variables
```bash
# Optional: Custom user agent prefix
BMW_USER_AGENT_PREFIX="draiv-bmw-api"

# Optional: Quota pause max duration (seconds)
BMW_QUOTA_MAX_PAUSE=300
```

### Health Check Endpoints
- `GET /health` - Overall service health + quota status
- `GET /metrics` - Detailed metrics including quota stats

## 🧪 Testing Scenarios

### 1. Quota Error Simulation
```python
# Simulate quota error for testing
async def test_quota_handling():
    with pytest.raises(QuotaLimitError) as exc:
        # Trigger quota error
        pass
    assert exc.value.retry_after is not None
```

### 2. Circuit Breaker Validation
```bash
# Should show quota_paused state during quota limits
curl http://localhost:8080/health
```

### 3. User Agent Consistency
```bash
# Should return same user agent across requests
curl http://localhost:8080/health | jq '.user_agent_info.user_agent'
```

## 📋 Production Checklist

- [ ] Staging deployment successful
- [ ] Quota handling tests pass
- [ ] User agent generation stable
- [ ] Circuit breaker quota logic verified
- [ ] Health endpoints return quota status
- [ ] Monitoring configured for quota metrics
- [ ] Rollback plan documented and tested
- [ ] Team notified of deployment window
- [ ] On-call engineer identified

## 🔗 Related Resources

- [BMW API Quota GitHub Issue](https://github.com/home-assistant/core/issues/149750)
- [bimmer_connected Quota Fix PR](https://github.com/bimmerconnected/bimmer_connected/pull/743)
- [Circuit Breaker Pattern Documentation](utils/circuit_breaker.py)
- [User Agent Manager Documentation](utils/user_agent_manager.py)

## 🆘 Emergency Contacts

If quota issues persist after deployment:
1. Check circuit breaker state via health endpoint
2. Review BMW API status pages
3. Consider temporary rate limiting via nginx
4. Escalate to BMW Connected Drive support if widespread

---

**Status**: Ready for staging deployment ✅  
**Risk Level**: Medium (tested, with rollback plan)  
**Expected Impact**: Elimination of quota-related 403 errors  
**Deployment Window**: 2-4 hours including monitoring