# Skoda Connect API - Frontend Integration Guide

## 📋 Overview

This guide provides complete instructions for integrating the Skoda Connect API into the draiv.ch UI. The API enables real-time vehicle control including lock/unlock, status monitoring, and climate control for Skoda vehicles.

## 🔗 API Endpoint

**Production URL:** `https://europe-west6-miavia-422212.cloudfunctions.net/skoda_api_stateless`
- **Method:** POST
- **Content-Type:** application/json
- **Response Time:** 5-10 seconds (real vehicle communication)
- **Timeout:** Set to 30 seconds

## 🔐 Authentication Requirements

Every API request requires Skoda Connect (MySkoda app) credentials:

| Field | Type | Required | Description |
|-------|------|----------|-------------|
| `email` | string | Yes | User's MySkoda account email |
| `password` | string | Yes | MySkoda account password |
| `vin` | string | Yes | 17-character Vehicle Identification Number |
| `s_pin` | string | Conditional | 4-digit Security PIN (required for lock/unlock/climate) |
| `action` | string | Yes | Operation to perform (see Actions section) |

## 🎯 Available Actions

### 1. Get Vehicle Status
**No S-PIN required**
```javascript
const getVehicleStatus = async (credentials) => {
  const response = await fetch(API_URL, {
    method: 'POST',
    headers: { 'Content-Type': 'application/json' },
    body: JSON.stringify({
      email: credentials.email,
      password: credentials.password,
      vin: credentials.vin,
      action: 'status'
    })
  });
  return response.json();
};
```

**Response includes:**
- Vehicle model and year
- Lock status
- Door/window states
- Fuel level and range
- Mileage
- GPS location
- Last update timestamp

### 2. Lock Vehicle
**S-PIN required**
```javascript
const lockVehicle = async (credentials, sPin) => {
  const response = await fetch(API_URL, {
    method: 'POST',
    headers: { 'Content-Type': 'application/json' },
    body: JSON.stringify({
      email: credentials.email,
      password: credentials.password,
      vin: credentials.vin,
      s_pin: sPin,
      action: 'lock'
    })
  });
  return response.json();
};
```

### 3. Unlock Vehicle
**S-PIN required**
```javascript
const unlockVehicle = async (credentials, sPin) => {
  const response = await fetch(API_URL, {
    method: 'POST',
    headers: { 'Content-Type': 'application/json' },
    body: JSON.stringify({
      email: credentials.email,
      password: credentials.password,
      vin: credentials.vin,
      s_pin: sPin,
      action: 'unlock'
    })
  });
  return response.json();
};
```

### 4. Flash Lights
**No S-PIN required**
```javascript
const flashLights = async (credentials) => {
  const response = await fetch(API_URL, {
    method: 'POST',
    headers: { 'Content-Type': 'application/json' },
    body: JSON.stringify({
      email: credentials.email,
      password: credentials.password,
      vin: credentials.vin,
      action: 'flash'
    })
  });
  return response.json();
};
```

### 5. Start Climate Control
**S-PIN required**
```javascript
const startClimate = async (credentials, sPin) => {
  const response = await fetch(API_URL, {
    method: 'POST',
    headers: { 'Content-Type': 'application/json' },
    body: JSON.stringify({
      email: credentials.email,
      password: credentials.password,
      vin: credentials.vin,
      s_pin: sPin,
      action: 'climate_start'
    })
  });
  return response.json();
};
```

### 6. Stop Climate Control
**No S-PIN required**
```javascript
const stopClimate = async (credentials) => {
  const response = await fetch(API_URL, {
    method: 'POST',
    headers: { 'Content-Type': 'application/json' },
    body: JSON.stringify({
      email: credentials.email,
      password: credentials.password,
      vin: credentials.vin,
      action: 'climate_stop'
    })
  });
  return response.json();
};
```

### 7. Health Check
**For debugging/monitoring**
```javascript
const healthCheck = async (credentials) => {
  const response = await fetch(API_URL, {
    method: 'POST',
    headers: { 'Content-Type': 'application/json' },
    body: JSON.stringify({
      email: credentials.email,
      password: credentials.password,
      vin: credentials.vin,
      action: 'health'
    })
  });
  return response.json();
};
```

## 📦 Response Formats

### Success Response - Status
```json
{
  "success": true,
  "action": "status",
  "data": {
    "vin": "TMBJJ7NX5MY061741",
    "model": "Skoda Octavia",
    "year": 2024,
    "status": {
      "locked": true,
      "doors": {
        "driver": "closed",
        "passenger": "closed",
        "rear_left": "closed",
        "rear_right": "closed"
      },
      "windows": {
        "driver": "closed",
        "passenger": "closed",
        "rear_left": "closed",
        "rear_right": "closed"
      },
      "fuel": {
        "level": 65,
        "range_km": 520
      },
      "mileage_km": 197655,
      "location": {
        "latitude": 47.3769,
        "longitude": 8.5417,
        "address": "Zürich, Switzerland",
        "updated_at": "2025-09-04T10:00:00Z"
      }
    },
    "capabilities": {
      "remote_lock": true,
      "climate_control": true,
      "location_tracking": true
    },
    "last_updated": "2025-09-04T10:00:00Z"
  },
  "timestamp": "2025-09-04T10:00:00Z",
  "vin": "TMBJJ7NX5MY061741"
}
```

### Success Response - Action
```json
{
  "success": true,
  "action": "lock",
  "data": {
    "action": "lock",
    "result": "Command sent",
    "success": true,
    "timestamp": "2025-09-04T10:00:00Z",
    "vin": "TMBJJ7NX5MY061741"
  },
  "timestamp": "2025-09-04T10:00:00Z",
  "vin": "TMBJJ7NX5MY061741"
}
```

### Error Response
```json
{
  "success": false,
  "error": "AUTHENTICATION_ERROR",
  "message": "Authentication failed: Invalid credentials",
  "action": "status",
  "vin": "TMBJJ7NX5MY061741",
  "timestamp": "2025-09-04T10:00:00Z"
}
```

## ❌ Error Codes

| Error Code | Description | User Message |
|------------|-------------|--------------|
| `AUTHENTICATION_ERROR` | Invalid email/password | "Invalid Skoda Connect credentials. Please check your email and password." |
| `VEHICLE_NOT_FOUND` | VIN not found in account | "This vehicle is not registered to your Skoda Connect account." |
| `SPIN_REQUIRED` | S-PIN missing or invalid | "Invalid S-PIN. Please enter your 4-digit security code." |
| `INTERNAL_ERROR` | Server or API error | "Service temporarily unavailable. Please try again later." |

## 🎨 UI Component Requirements

### 1. Credential Management Component
```jsx
// SkodaCredentials.jsx
const SkodaCredentials = () => {
  const [credentials, setCredentials] = useState({
    email: '',
    password: '',
    vin: ''
  });
  
  const [savedCredentials, setSavedCredentials] = useSecureStorage('skoda_credentials');
  
  return (
    <CredentialForm>
      <Input
        type="email"
        placeholder="MySkoda Email"
        value={credentials.email}
        onChange={(e) => setCredentials({...credentials, email: e.target.value})}
        autoComplete="email"
      />
      <Input
        type="password"
        placeholder="MySkoda Password"
        value={credentials.password}
        onChange={(e) => setCredentials({...credentials, password: e.target.value})}
        autoComplete="current-password"
      />
      <Input
        type="text"
        placeholder="Vehicle VIN (17 characters)"
        pattern="[A-Z0-9]{17}"
        maxLength={17}
        value={credentials.vin}
        onChange={(e) => setCredentials({...credentials, vin: e.target.value.toUpperCase()})}
      />
      <Checkbox>
        <input type="checkbox" id="save-credentials" />
        <label htmlFor="save-credentials">Save credentials (encrypted)</label>
      </Checkbox>
      <Button onClick={handleSave}>Save Credentials</Button>
    </CredentialForm>
  );
};
```

### 2. S-PIN Modal Component
```jsx
// SPinModal.jsx
const SPinModal = ({ isOpen, onConfirm, onCancel, action }) => {
  const [pin, setPin] = useState('');
  const [error, setError] = useState('');
  
  const validatePin = (value) => {
    if (value.length !== 4) return false;
    if (!/^\d{4}$/.test(value)) return false;
    // Reject simple patterns
    const simplePatterns = ['0000', '1111', '2222', '3333', '4444', 
                           '5555', '6666', '7777', '8888', '9999', 
                           '1234', '4321'];
    if (simplePatterns.includes(value)) {
      setError('Please use a more secure PIN');
      return false;
    }
    return true;
  };
  
  const handleSubmit = () => {
    if (validatePin(pin)) {
      onConfirm(pin);
    }
  };
  
  return (
    <Modal isOpen={isOpen} onClose={onCancel}>
      <ModalHeader>
        <Icon>{action === 'lock' ? '🔒' : action === 'unlock' ? '🔓' : '❄️'}</Icon>
        <Title>Enter S-PIN to {action}</Title>
      </ModalHeader>
      <ModalBody>
        <PinInput
          type="password"
          inputMode="numeric"
          pattern="[0-9]{4}"
          maxLength={4}
          placeholder="••••"
          value={pin}
          onChange={(e) => setPin(e.target.value.replace(/\D/g, ''))}
          autoFocus
        />
        {error && <ErrorMessage>{error}</ErrorMessage>}
        <InfoText>Enter your 4-digit Skoda security PIN</InfoText>
      </ModalBody>
      <ModalFooter>
        <Button variant="secondary" onClick={onCancel}>Cancel</Button>
        <Button variant="primary" onClick={handleSubmit} disabled={pin.length !== 4}>
          Confirm
        </Button>
      </ModalFooter>
    </Modal>
  );
};
```

### 3. Vehicle Status Card Component
```jsx
// SkodaVehicleCard.jsx
const SkodaVehicleCard = ({ vehicleData }) => {
  const { model, year, status, vin } = vehicleData;
  
  return (
    <Card>
      <CardHeader>
        <VehicleBrand>
          <SkodaLogo />
          ŠKODA
        </VehicleBrand>
        <VehicleModel>{model}</VehicleModel>
        <VehicleYear>{year}</VehicleYear>
      </CardHeader>
      
      <CardBody>
        <StatusGrid>
          <StatusItem>
            <Icon>{status.locked ? '🔒' : '🔓'}</Icon>
            <Label>Lock Status</Label>
            <Value>{status.locked ? 'Locked' : 'Unlocked'}</Value>
          </StatusItem>
          
          <StatusItem>
            <Icon>⛽</Icon>
            <Label>Fuel Level</Label>
            <Value>{status.fuel.level}%</Value>
            <SubValue>{status.fuel.range_km} km range</SubValue>
          </StatusItem>
          
          <StatusItem>
            <Icon>🚗</Icon>
            <Label>Mileage</Label>
            <Value>{status.mileage_km.toLocaleString()} km</Value>
          </StatusItem>
          
          <StatusItem>
            <Icon>📍</Icon>
            <Label>Location</Label>
            <Value>{status.location.address}</Value>
            <MapLink 
              href={`https://maps.google.com/?q=${status.location.latitude},${status.location.longitude}`}
              target="_blank"
            >
              View on map
            </MapLink>
          </StatusItem>
        </StatusGrid>
        
        <VinDisplay>VIN: {vin}</VinDisplay>
        <LastUpdated>Last updated: {formatTime(status.last_updated)}</LastUpdated>
      </CardBody>
    </Card>
  );
};
```

### 4. Action Control Panel Component
```jsx
// SkodaControls.jsx
const SkodaControls = ({ credentials }) => {
  const [loading, setLoading] = useState(false);
  const [actionInProgress, setActionInProgress] = useState(null);
  const [showPinModal, setShowPinModal] = useState(false);
  const [pendingAction, setPendingAction] = useState(null);
  
  const executeAction = async (action, requiresPin = false) => {
    if (requiresPin) {
      setPendingAction(action);
      setShowPinModal(true);
      return;
    }
    
    setLoading(true);
    setActionInProgress(action);
    
    try {
      const response = await fetch(API_URL, {
        method: 'POST',
        headers: { 'Content-Type': 'application/json' },
        body: JSON.stringify({
          ...credentials,
          action
        })
      });
      
      const data = await response.json();
      
      if (data.success) {
        showNotification(`✅ ${action} successful`, 'success');
        // Update vehicle status
        await refreshStatus();
      } else {
        handleError(data.error, data.message);
      }
    } catch (error) {
      showNotification('Network error. Please try again.', 'error');
    } finally {
      setLoading(false);
      setActionInProgress(null);
    }
  };
  
  const handlePinConfirm = async (pin) => {
    setShowPinModal(false);
    setLoading(true);
    setActionInProgress(pendingAction);
    
    try {
      const response = await fetch(API_URL, {
        method: 'POST',
        headers: { 'Content-Type': 'application/json' },
        body: JSON.stringify({
          ...credentials,
          s_pin: pin,
          action: pendingAction
        })
      });
      
      const data = await response.json();
      
      if (data.success) {
        showNotification(`✅ ${pendingAction} successful`, 'success');
        await refreshStatus();
      } else {
        handleError(data.error, data.message);
      }
    } catch (error) {
      showNotification('Network error. Please try again.', 'error');
    } finally {
      setLoading(false);
      setActionInProgress(null);
      setPendingAction(null);
    }
  };
  
  return (
    <>
      <ControlPanel>
        <ActionButton
          onClick={() => executeAction('lock', true)}
          disabled={loading}
          loading={actionInProgress === 'lock'}
        >
          <Icon>🔒</Icon>
          <Label>Lock</Label>
        </ActionButton>
        
        <ActionButton
          onClick={() => executeAction('unlock', true)}
          disabled={loading}
          loading={actionInProgress === 'unlock'}
        >
          <Icon>🔓</Icon>
          <Label>Unlock</Label>
        </ActionButton>
        
        <ActionButton
          onClick={() => executeAction('flash', false)}
          disabled={loading}
          loading={actionInProgress === 'flash'}
        >
          <Icon>💡</Icon>
          <Label>Flash</Label>
        </ActionButton>
        
        <ActionButton
          onClick={() => executeAction('climate_start', true)}
          disabled={loading}
          loading={actionInProgress === 'climate_start'}
        >
          <Icon>❄️</Icon>
          <Label>Start Climate</Label>
        </ActionButton>
        
        <ActionButton
          onClick={() => executeAction('climate_stop', false)}
          disabled={loading}
          loading={actionInProgress === 'climate_stop'}
        >
          <Icon>🛑</Icon>
          <Label>Stop Climate</Label>
        </ActionButton>
        
        <ActionButton
          onClick={() => executeAction('status', false)}
          disabled={loading}
          loading={actionInProgress === 'status'}
        >
          <Icon>🔄</Icon>
          <Label>Refresh</Label>
        </ActionButton>
      </ControlPanel>
      
      <SPinModal
        isOpen={showPinModal}
        onConfirm={handlePinConfirm}
        onCancel={() => {
          setShowPinModal(false);
          setPendingAction(null);
        }}
        action={pendingAction}
      />
    </>
  );
};
```

## 🔄 Complete Implementation Example

```jsx
// SkodaVehicleManager.jsx
import { useState, useEffect, useCallback } from 'react';
import { useSecureStorage } from '@/hooks/useSecureStorage';
import { useNotification } from '@/hooks/useNotification';

const SKODA_API_URL = 'https://europe-west6-miavia-422212.cloudfunctions.net/skoda_api_stateless';
const REQUEST_TIMEOUT = 30000; // 30 seconds
const STATUS_CACHE_TTL = 60000; // 60 seconds

export const SkodaVehicleManager = () => {
  const [credentials, setCredentials] = useSecureStorage('skoda_credentials', null);
  const [vehicleStatus, setVehicleStatus] = useState(null);
  const [loading, setLoading] = useState(false);
  const [error, setError] = useState(null);
  const [lastFetch, setLastFetch] = useState(null);
  const { showNotification } = useNotification();
  
  // Fetch with timeout
  const fetchWithTimeout = async (url, options) => {
    const controller = new AbortController();
    const timeout = setTimeout(() => controller.abort(), REQUEST_TIMEOUT);
    
    try {
      const response = await fetch(url, {
        ...options,
        signal: controller.signal
      });
      clearTimeout(timeout);
      return response;
    } catch (error) {
      clearTimeout(timeout);
      if (error.name === 'AbortError') {
        throw new Error('Request timeout - vehicle may be offline');
      }
      throw error;
    }
  };
  
  // Make API request
  const apiRequest = useCallback(async (action, sPin = null) => {
    const requestBody = {
      email: credentials.email,
      password: credentials.password,
      vin: credentials.vin,
      action
    };
    
    if (sPin) {
      requestBody.s_pin = sPin;
    }
    
    const response = await fetchWithTimeout(SKODA_API_URL, {
      method: 'POST',
      headers: { 'Content-Type': 'application/json' },
      body: JSON.stringify(requestBody)
    });
    
    const data = await response.json();
    
    if (!data.success) {
      throw new Error(data.message || 'Operation failed');
    }
    
    return data;
  }, [credentials]);
  
  // Fetch vehicle status
  const fetchStatus = useCallback(async (force = false) => {
    // Check cache
    if (!force && lastFetch && Date.now() - lastFetch < STATUS_CACHE_TTL) {
      return vehicleStatus;
    }
    
    setLoading(true);
    setError(null);
    
    try {
      const data = await apiRequest('status');
      setVehicleStatus(data.data);
      setLastFetch(Date.now());
      return data.data;
    } catch (err) {
      setError(err.message);
      showNotification(err.message, 'error');
      throw err;
    } finally {
      setLoading(false);
    }
  }, [apiRequest, lastFetch, vehicleStatus, showNotification]);
  
  // Execute vehicle action
  const executeAction = useCallback(async (action, sPin = null) => {
    setLoading(true);
    setError(null);
    
    try {
      showNotification(`Sending ${action} command...`, 'info');
      const data = await apiRequest(action, sPin);
      
      showNotification(`✅ ${action} successful`, 'success');
      
      // Refresh status after action
      setTimeout(() => fetchStatus(true), 3000);
      
      return data;
    } catch (err) {
      setError(err.message);
      showNotification(`❌ ${action} failed: ${err.message}`, 'error');
      throw err;
    } finally {
      setLoading(false);
    }
  }, [apiRequest, fetchStatus, showNotification]);
  
  // Auto-refresh status on mount
  useEffect(() => {
    if (credentials) {
      fetchStatus();
    }
  }, [credentials]);
  
  // Periodic status refresh
  useEffect(() => {
    if (!credentials) return;
    
    const interval = setInterval(() => {
      fetchStatus();
    }, STATUS_CACHE_TTL);
    
    return () => clearInterval(interval);
  }, [credentials, fetchStatus]);
  
  return {
    credentials,
    setCredentials,
    vehicleStatus,
    loading,
    error,
    fetchStatus,
    executeAction,
    actions: {
      lock: (pin) => executeAction('lock', pin),
      unlock: (pin) => executeAction('unlock', pin),
      flash: () => executeAction('flash'),
      startClimate: (pin) => executeAction('climate_start', pin),
      stopClimate: () => executeAction('climate_stop')
    }
  };
};
```

## 🧪 Testing

### Test Credentials
```javascript
const TEST_ACCOUNT = {
  email: "Info@miavia.ai",
  password: "wozWi9-matvah-xonmyq",
  vin: "TMBJJ7NX5MY061741",
  s_pin: "2405"
};

// Test vehicle: Škoda Octavia Combi AMBITION (197,655 km)
// Location: Zürich, Switzerland
```

### Test Cases
1. **Authentication Test**
   - Valid credentials → Success
   - Invalid email/password → AUTHENTICATION_ERROR
   - Invalid VIN format → Validation error

2. **Action Tests**
   - Lock with valid S-PIN → Success
   - Lock with invalid S-PIN → SPIN_REQUIRED error
   - Flash lights → Success (no PIN needed)
   - Status refresh → Updated data

3. **Error Handling**
   - Network timeout (>30s) → Timeout error
   - Invalid action → Error response
   - Vehicle offline → Appropriate message

## 🔒 Security Best Practices

1. **Credential Storage**
   ```javascript
   // Use encrypted storage
   import CryptoJS from 'crypto-js';
   
   const encryptCredentials = (creds, key) => {
     return CryptoJS.AES.encrypt(JSON.stringify(creds), key).toString();
   };
   
   const decryptCredentials = (encrypted, key) => {
     const bytes = CryptoJS.AES.decrypt(encrypted, key);
     return JSON.parse(bytes.toString(CryptoJS.enc.Utf8));
   };
   ```

2. **S-PIN Handling**
   - Never log S-PIN
   - Clear from memory after use
   - Optional: Session-based storage with timeout

3. **Rate Limiting**
   ```javascript
   const rateLimiter = {
     lastRequest: 0,
     minInterval: 5000, // 5 seconds
     
     canRequest: () => {
       return Date.now() - rateLimiter.lastRequest > rateLimiter.minInterval;
     },
     
     recordRequest: () => {
       rateLimiter.lastRequest = Date.now();
     }
   };
   ```

## 📊 Analytics & Monitoring

Track these events:
- Vehicle action success/failure rates
- Average response times
- Most used features
- Error frequencies by type

```javascript
// Example analytics integration
const trackAction = (action, success, duration) => {
  analytics.track('skoda_action', {
    action,
    success,
    duration,
    vehicle_model: vehicleStatus?.model,
    error_type: success ? null : error
  });
};
```

## ✅ Implementation Checklist

- [ ] Create Skoda brand selection in vehicle picker
- [ ] Implement credential input and validation
- [ ] Add secure credential storage (encrypted)
- [ ] Create S-PIN input modal with validation
- [ ] Build vehicle status display card
- [ ] Implement action buttons with loading states
- [ ] Add comprehensive error handling
- [ ] Implement request timeout (30s)
- [ ] Add response caching (60s for status)
- [ ] Create notification system for actions
- [ ] Add rate limiting (5s between requests)
- [ ] Implement auto-refresh for status
- [ ] Add analytics tracking
- [ ] Test with real vehicle
- [ ] Add user documentation

## 🚀 Deployment Notes

1. The API is already deployed and production-ready
2. No CORS issues (API allows all origins)
3. HTTPS required for production
4. Consider adding request retry logic for network failures
5. Monitor API response times and adjust timeouts if needed

## 📞 Support

For API issues or questions:
- Check the health endpoint first
- Review error messages (they're specific)
- Test with provided test credentials
- Verify VIN format (17 uppercase alphanumeric)

---

**This completes the Skoda Connect API integration guide. The frontend engineer now has everything needed to implement full Skoda vehicle control in the draiv.ch UI!**