# PRP-002-UI: Skoda Connect Frontend & Edge Function Integration

**Author**: DRAIV Engineering Team  
**Date**: January 2025  
**Status**: APPROVED  
**Priority**: P0 - Critical Business Feature  
**Impact**: UI/UX and Edge Function implementation for Skoda vehicle support
**Document Type**: Frontend & Edge Function Implementation

## Executive Summary

This document specifies the frontend user interface, user experience flows, and edge function requirements for integrating Skoda Connect into the DRAIV platform. The implementation builds upon established BMW patterns while introducing new S-PIN authentication flows and enhanced vehicle management capabilities.

### Key Differentiators
1. **S-PIN Authentication**: Unique security flow with progressive enhancement
2. **Session Management**: Different from OAuth token handling
3. **Enhanced Feature Set**: EV charging, service intervals, advanced diagnostics
4. **Unified Architecture**: Shared components for future manufacturer integrations

### Success Metrics
- **Onboarding Completion Rate**: >90% of users complete account setup
- **S-PIN Adoption Rate**: >70% of users set up S-PIN within 7 days
- **Feature Usage**: >80% of users use remote controls weekly
- **Error Resolution**: <5% of operations result in user-visible errors
- **Component Load Time**: <200ms for initial render
- **Bundle Size Impact**: <50KB addition to main bundle
- **Accessibility Score**: >95% Lighthouse accessibility score

## Current BMW UI Architecture Analysis

Based on analysis of `/Users/antonsteininger/draiv-workspace/draiv-ui/src/components/cars/BMW/`, the existing BMW implementation follows these patterns:

**Component Structure**:
```
src/components/cars/BMW/
├── BMWVehicleDashboard.tsx          # Main dashboard container
├── BMWVehicleStatusModal.tsx        # Detailed status modal
├── LinkBMWVehicleDialog.tsx         # WKN linking dialog
├── components/
│   ├── dashboard/                   # Dashboard sub-components
│   │   ├── DashboardHeader.tsx      # Lock status, unlink button
│   │   ├── DashboardContent.tsx     # Status display & controls
│   │   ├── RemoteCommands.tsx       # Action buttons
│   │   ├── VehicleStatus.tsx        # Door, fuel, battery status
│   │   ├── LocationDisplay.tsx      # GPS coordinates & timestamp
│   │   └── DiagnosticAlerts.tsx     # Check control messages
│   ├── BMWControlButtons.tsx        # Lock/unlock, flash, climate
│   └── BMWHCaptchaModal.tsx        # Captcha verification
├── hooks/
│   ├── vehicle-control/
│   │   ├── index.ts                 # Main hook composition
│   │   ├── useVehicleData.ts        # Data fetching
│   │   ├── useRemoteActions.ts      # Command execution
│   │   └── useDataExtraction.ts     # Status parsing
│   └── useBMWConnectivity.ts
├── types/
│   └── bmw-types.ts                 # TypeScript definitions
└── utils/
    └── dateFormatter.ts
```

**Authentication Flow** (BMW):
1. User clicks "Add BMW Account" in integrations
2. `BMWCredentialsDialog.tsx` collects email/password
3. Credentials encrypted via `supabase.functions.invoke("encrypt-bmw-credentials")`
4. Vehicle linking via `LinkBMWVehicleDialog.tsx` (WKN entry)
5. hCaptcha verification when needed
6. Dashboard displays connected vehicle

## Skoda UI Component Architecture

### Component Hierarchy

```
src/components/cars/Skoda/
├── SkodaVehicleDashboard.tsx        # Main dashboard (mirrors BMW structure)
├── SkodaVehicleStatusModal.tsx      # Detailed status modal
├── LinkSkodaVehicleDialog.tsx       # Vehicle discovery & linking
├── components/
│   ├── dashboard/                   # Reusable dashboard components
│   │   ├── SkodaDashboardHeader.tsx # Lock status, S-PIN indicator
│   │   ├── SkodaDashboardContent.tsx# Status display & controls
│   │   ├── SkodaRemoteCommands.tsx  # Action buttons with S-PIN gates
│   │   ├── SkodaVehicleStatus.tsx   # Doors, fuel/battery, mileage
│   │   ├── SkodaLocationDisplay.tsx # GPS with address resolution
│   │   ├── EVChargingStatus.tsx     # EV-specific charging display
│   │   └── ServiceIntervals.tsx     # Maintenance schedule display
│   ├── SkodaControlButtons.tsx      # Lock/unlock, climate, charging
│   ├── SPinSetupModal.tsx           # S-PIN setup and management
│   ├── SPinPromptModal.tsx          # S-PIN entry for operations
│   ├── SkodaAccountSetupModal.tsx   # Initial account setup
│   └── SkodaLoadingState.tsx        # Loading states
├── hooks/
│   ├── vehicle-control/
│   │   ├── index.ts                 # Main Skoda vehicle control hook
│   │   ├── useSkodaVehicleData.ts   # Data fetching with sessions
│   │   ├── useSkodaRemoteActions.ts # Commands with S-PIN handling
│   │   ├── useSkodaDataExtraction.ts# Status parsing
│   │   └── useSkodaSPinManager.ts   # S-PIN state management
│   ├── useSkodaConnectivity.ts      # Connection management
│   └── useSkodaAccountSetup.ts      # Account setup flow
├── types/
│   └── skoda-types.ts               # Skoda-specific TypeScript definitions
└── utils/
    ├── skodaStatusParser.ts         # Parse MySkoda responses
    ├── vehicleCapabilities.ts       # Detect EV vs ICE features
    └── spInManager.ts               # S-PIN encryption utilities
```

### Shared Components (Manufacturer-Agnostic)

Create reusable components that work across manufacturers:

```
src/components/cars/shared/
├── VehicleDashboardLayout.tsx       # Common layout structure
├── VehicleStatusCard.tsx            # Generic status display
├── RemoteActionButton.tsx           # Standardized action buttons
├── LocationCard.tsx                 # GPS display component
├── FuelBatteryDisplay.tsx           # Fuel/battery level indicator
├── SecurityStatusBadge.tsx          # Lock/unlock status indicator
├── LastUpdatedTimestamp.tsx         # Data freshness indicator
├── ErrorStateDisplay.tsx            # Error handling UI
├── LoadingStateSpinner.tsx          # Loading states
└── UnlinkConfirmDialog.tsx          # Account unlinking
```

## User Flows & Onboarding

### 1. Account Setup Flow (First-time User)

**Step 1: Integration Selection**
- Location: `/settings/integrations` or main vehicle page
- UI: Cards showing available integrations (BMW, Skoda, "More coming soon")
- User clicks "Connect Skoda Account"

**Step 2: Account Credentials (`SkodaAccountSetupModal.tsx`)**
```tsx
// Modal content structure
<Dialog>
  <DialogHeader>
    <DialogTitle>Connect Your Skoda Account</DialogTitle>
    <DialogDescription>
      Enter your MySkoda credentials to connect your vehicles
    </DialogDescription>
  </DialogHeader>
  <Form>
    <FormField name="username">
      <Label>MySkoda Username/Email</Label>
      <Input type="email" placeholder="your-email@example.com" />
      <FormDescription>
        Use the same credentials you use for the MySkoda app
      </FormDescription>
    </FormField>
    
    <FormField name="password">
      <Label>MySkoda Password</Label>
      <Input type="password" />
      <FormDescription>
        Your password is encrypted and stored securely
      </FormDescription>
    </FormField>
    
    <FormField name="s_pin" optional>
      <Label>S-PIN (Optional but Recommended)</Label>
      <Input type="password" maxLength="4" pattern="[0-9]{4}" />
      <FormDescription>
        <div className="space-y-2">
          <p>Your 4-digit S-PIN enables advanced features:</p>
          <ul className="list-disc pl-4 space-y-1">
            <li>Remote lock/unlock</li>
            <li>Climate control</li>
            <li>Charging control (EVs)</li>
          </ul>
          <p className="text-orange-600">⚠️ Without S-PIN, you can only view vehicle status</p>
        </div>
      </FormDescription>
    </FormField>
    
    <SecurityNotice />
  </Form>
  <DialogFooter>
    <Button variant="outline" onClick={onCancel}>Cancel</Button>
    <Button onClick={onSubmit} disabled={isSubmitting}>
      {isSubmitting ? <Loader2 className="mr-2" /> : null}
      Connect Account
    </Button>
  </DialogFooter>
</Dialog>
```

**Step 3: Vehicle Discovery (`LinkSkodaVehicleDialog.tsx`)**
- Automatic vehicle discovery using MySkoda API
- Display found vehicles with model, year, VIN (partial)
- User selects which vehicles to add to DRAIV
- Confirmation and vehicle naming options

**Step 4: Setup Completion**
- Success message with next steps
- Redirect to vehicle dashboard
- Onboarding tooltips for first-time usage

### 2. S-PIN Management Flow

**S-PIN Setup (`SPinSetupModal.tsx`)**
```tsx
<Dialog>
  <DialogHeader>
    <DialogTitle>Set Up S-PIN</DialogTitle>
    <DialogDescription>
      Create a 4-digit S-PIN to enable remote vehicle control
    </DialogDescription>
  </DialogHeader>
  <Form>
    <FormField name="s_pin">
      <Label>Create S-PIN</Label>
      <PinInput length={4} onComplete={setPin} />
      <FormDescription>
        Choose a 4-digit PIN you'll remember
      </FormDescription>
    </FormField>
    
    <FormField name="s_pin_confirm">
      <Label>Confirm S-PIN</Label>
      <PinInput length={4} onComplete={setConfirmPin} />
    </FormField>
    
    <SecurityWarning>
      <AlertTriangle className="h-5 w-5" />
      <div>
        <p>Your S-PIN enables powerful vehicle control features.</p>
        <p>Keep it secure and don't share it with others.</p>
      </div>
    </SecurityWarning>
  </Form>
  <DialogFooter>
    <Button variant="outline" onClick={onCancel}>Skip for Now</Button>
    <Button onClick={onSave} disabled={!pinsMatch}>
      Save S-PIN
    </Button>
  </DialogFooter>
</Dialog>
```

**S-PIN Entry for Operations (`SPinPromptModal.tsx`)**
```tsx
<Dialog size="sm">
  <DialogHeader>
    <DialogTitle>Confirm Operation</DialogTitle>
    <DialogDescription>
      Enter your S-PIN to {operation === 'lock' ? 'lock' : 'unlock'} the vehicle
    </DialogDescription>
  </DialogHeader>
  <Form>
    <FormField>
      <Label>S-PIN</Label>
      <PinInput 
        length={4} 
        onComplete={handleSubmit}
        error={hasError}
      />
      {hasError && (
        <FormMessage>Incorrect S-PIN. Please try again.</FormMessage>
      )}
    </FormField>
  </Form>
  <DialogFooter>
    <Button variant="outline" onClick={onCancel}>Cancel</Button>
  </DialogFooter>
</Dialog>
```

## Vehicle Control Interfaces

### Main Dashboard (`SkodaVehicleDashboard.tsx`)

**Header Section:**
- Vehicle name/model
- Lock status indicator (large, prominent)
- Connection status (online/offline)
- Last updated timestamp
- Settings/unlink button

**Status Cards Grid:**
```tsx
<div className="grid grid-cols-1 md:grid-cols-2 lg:grid-cols-3 gap-4">
  <SecurityStatusCard 
    isLocked={vehicleData.doors.locked}
    hasOpenDoors={hasOpenDoors}
    hasOpenWindows={hasOpenWindows}
  />
  
  <FuelBatteryCard 
    type={vehicleType} // 'fuel' | 'electric' | 'hybrid'
    fuelLevel={vehicleData.fuel?.level}
    batteryLevel={vehicleData.battery?.level}
    range={vehicleData.range}
  />
  
  <LocationCard 
    coordinates={vehicleData.location}
    address={resolvedAddress}
    lastUpdated={vehicleData.location.updatedAt}
  />
  
  <MileageCard 
    odometer={vehicleData.mileage}
    nextService={vehicleData.serviceInterval}
  />
  
  {/* EV-specific */}
  {vehicleType === 'electric' && (
    <ChargingStatusCard 
      isCharging={vehicleData.charging.isCharging}
      chargingPower={vehicleData.charging.power}
      timeToFull={vehicleData.charging.timeToFull}
    />
  )}
</div>
```

**Remote Actions Section:**
```tsx
<Card>
  <CardHeader>
    <CardTitle>Remote Controls</CardTitle>
    {!hasSpin && (
      <Alert>
        <Info className="h-4 w-4" />
        <AlertDescription>
          Set up an S-PIN to enable remote vehicle control
          <Button variant="link" onClick={onSetupSpin}>
            Set up now
          </Button>
        </AlertDescription>
      </Alert>
    )}
  </CardHeader>
  
  <CardContent>
    <div className="grid grid-cols-2 md:grid-cols-4 gap-3">
      <RemoteActionButton
        icon={<Lock />}
        label={isLocked ? "Unlock" : "Lock"}
        onClick={() => handleLockUnlock(isLocked ? 'unlock' : 'lock')}
        requiresPin={true}
        disabled={!hasSpin || isLoading}
        variant={isLocked ? "destructive" : "default"}
      />
      
      <RemoteActionButton
        icon={<Thermometer />}
        label="Climate"
        onClick={handleClimateControl}
        requiresPin={true}
        disabled={!hasSpin || isLoading}
      />
      
      <RemoteActionButton
        icon={<Flashlight />}
        label="Flash Lights"
        onClick={handleFlashLights}
        requiresPin={false}
        disabled={isLoading}
      />
      
      {vehicleType === 'electric' && (
        <RemoteActionButton
          icon={<Battery />}
          label={isCharging ? "Stop Charging" : "Start Charging"}
          onClick={handleChargingControl}
          requiresPin={true}
          disabled={!hasSpin || isLoading}
        />
      )}
      
      <RemoteActionButton
        icon={<RefreshCw />}
        label="Refresh Status"
        onClick={handleRefresh}
        requiresPin={false}
        disabled={isLoading}
        variant="outline"
      />
    </div>
  </CardContent>
</Card>
```

## State Management Approach

### Main Vehicle Control Hook (`useSkodaVehicleControl`)

```tsx
export const useSkodaVehicleControl = (carId: string) => {
  const { 
    connectivityData, 
    isLoading, 
    error, 
    refetch 
  } = useSkodaVehicleData(carId);
  
  const {
    hasSpin,
    setupSpin,
    updateSpin,
    verifySpin
  } = useSkodaSPinManager(carId);
  
  const {
    isRefreshing,
    isLocking,
    isUnlocking,
    isActivatingClimate,
    isChargingControlling,
    showSpinPrompt,
    pendingOperation,
    handleRemoteAction,
    handleSpinSubmit,
    handleSpinCancel
  } = useSkodaRemoteActions({
    carId,
    connectivityData,
    hasSpin,
    refetch
  });
  
  const {
    vehicleStatusData,
    isLocked,
    fuelLevel,
    batteryLevel,
    mileage,
    location,
    chargingStatus,
    serviceInterval,
    vehicleType
  } = useSkodaDataExtraction(connectivityData);
  
  // ... compose and return all state and actions
};
```

### S-PIN Manager Hook (`useSkodaSPinManager`)

```tsx
export const useSkodaSPinManager = (carId: string) => {
  const [hasSpin, setHasSpin] = useState<boolean>(false);
  const [isVerifying, setIsVerifying] = useState<boolean>(false);
  
  const checkSpinStatus = useCallback(async () => {
    const { data } = await supabase
      .from('car_connectivity')
      .select('metadata')
      .eq('car_id', carId)
      .single();
    
    setHasSpin(!!data?.metadata?.has_spin);
  }, [carId]);
  
  const setupSpin = useCallback(async (spin: string) => {
    const { error } = await supabase.functions.invoke('skoda-setup-spin', {
      body: { carId, spin }
    });
    
    if (!error) {
      setHasSpin(true);
      toast.success('S-PIN set up successfully');
    }
    
    return { error };
  }, [carId]);
  
  const verifySpin = useCallback(async (spin: string) => {
    setIsVerifying(true);
    
    const { data, error } = await supabase.functions.invoke('skoda-verify-spin', {
      body: { carId, spin }
    });
    
    setIsVerifying(false);
    return { verified: data?.verified, error };
  }, [carId]);
  
  return {
    hasSpin,
    isVerifying,
    setupSpin,
    verifySpin,
    checkSpinStatus
  };
};
```

## Design Patterns & Consistency

### Progressive Enhancement for S-PIN

1. **No S-PIN State**: Users see read-only dashboard with clear call-to-action
2. **S-PIN Setup**: Guided setup flow with security explanations
3. **S-PIN Enabled**: Full control capabilities with secure authentication

### Unified Visual Language

**Color Coding:**
- Green: Secured/locked state, positive actions
- Red: Unsecured/unlocked state, destructive actions  
- Blue: Information, status updates
- Orange: Warnings, attention needed
- Gray: Disabled/inactive states

**Typography:**
- Consistent with existing DRAIV design system
- Clear hierarchy (H1 for vehicle name, H2 for sections, H3 for cards)
- Monospace for technical data (VIN, coordinates)

**Iconography:**
- Lucide React icons for consistency
- Manufacturer-neutral icons
- Clear visual metaphors (lock for security, battery for power, etc.)

### Error States & Recovery

**Connection Errors:**
```tsx
<ErrorStateDisplay
  icon={<WifiOff />}
  title="Connection Lost"
  description="Unable to connect to your Skoda vehicle"
  actions={[
    { label: "Retry", onClick: handleRetry },
    { label: "Check Settings", onClick: openSettings }
  ]}
/>
```

**Authentication Errors:**
```tsx
<ErrorStateDisplay
  icon={<AlertTriangle />}
  title="Authentication Failed"
  description="Your MySkoda credentials may have expired"
  actions={[
    { label: "Update Credentials", onClick: openCredentialsDialog },
    { label: "Contact Support", onClick: openSupport }
  ]}
/>
```

**S-PIN Errors:**
```tsx
<Alert variant="destructive">
  <AlertTriangle className="h-4 w-4" />
  <AlertTitle>Incorrect S-PIN</AlertTitle>
  <AlertDescription>
    Please check your S-PIN and try again. 
    <Button variant="link" onClick={openSpinReset}>
      Forgot your S-PIN?
    </Button>
  </AlertDescription>
</Alert>
```

## API Integration Patterns

### Consistent Error Handling

```tsx
// Standard error response handling
const handleApiError = (error: any) => {
  switch (error.code) {
    case 'SPIN_REQUIRED':
      setShowSpinPrompt(true);
      break;
    case 'INVALID_SPIN':
      toast.error('Incorrect S-PIN');
      break;
    case 'RATE_LIMITED':
      toast.error('Too many requests. Please wait a moment.');
      break;
    case 'SERVICE_UNAVAILABLE':
      toast.error('Skoda services temporarily unavailable');
      break;
    default:
      toast.error('An unexpected error occurred');
  }
};
```

### Real-time Status Updates

```tsx
// WebSocket integration for real-time updates
useEffect(() => {
  const channel = supabase
    .channel(`vehicle_${carId}`)
    .on('postgres_changes', {
      event: 'UPDATE',
      schema: 'public',
      table: 'car_connectivity',
      filter: `car_id=eq.${carId}`
    }, (payload) => {
      setVehicleData(payload.new);
    })
    .subscribe();
  
  return () => supabase.removeChannel(channel);
}, [carId]);
```

## Mobile Responsiveness & Touch Optimization

### Responsive Grid System

```tsx
// Dashboard layout adapts to screen size
<div className="grid grid-cols-1 sm:grid-cols-2 lg:grid-cols-3 xl:grid-cols-4 gap-4">
  {statusCards}
</div>

// Control buttons scale for touch
<div className="grid grid-cols-2 sm:grid-cols-3 md:grid-cols-4 gap-3">
  <Button 
    size="lg" 
    className="h-20 text-base"
    touch-action="manipulation"
  >
    <Lock className="h-6 w-6 mb-2" />
    {isLocked ? 'Unlock' : 'Lock'}
  </Button>
</div>
```

### Touch-Friendly S-PIN Input

```tsx
<PinInput 
  length={4}
  size="large"
  className="touch-none" // Prevent zoom on touch
  inputMode="numeric"
  pattern="[0-9]*"
  autoComplete="one-time-code"
/>
```

## Accessibility Considerations

### Screen Reader Support

```tsx
<Button 
  aria-label={`${isLocked ? 'Unlock' : 'Lock'} vehicle ${vehicleName}`}
  aria-describedby="lock-status-description"
>
  <Lock className="h-5 w-5" aria-hidden="true" />
  {isLocked ? 'Unlock' : 'Lock'}
</Button>

<div id="lock-status-description" className="sr-only">
  Vehicle is currently {isLocked ? 'locked and secure' : 'unlocked'}
</div>
```

### Keyboard Navigation

```tsx
// Support keyboard navigation for all interactive elements
<div 
  role="button" 
  tabIndex={0}
  onKeyDown={(e) => {
    if (e.key === 'Enter' || e.key === ' ') {
      handleAction();
    }
  }}
>
  Action Button
</div>
```

### Color Contrast & Visual Indicators

- All color-coded states include visual indicators (icons, text)
- Minimum 4.5:1 contrast ratio for all text
- Focus indicators for keyboard navigation
- Clear visual feedback for all user actions

## Performance Optimizations

### Code Splitting & Lazy Loading

```tsx
// Lazy load Skoda components
const SkodaVehicleDashboard = lazy(() => import('./components/cars/Skoda/SkodaVehicleDashboard'));
const SPinSetupModal = lazy(() => import('./components/cars/Skoda/SPinSetupModal'));

// Conditional loading based on vehicle manufacturer
const DashboardComponent = vehicleManufacturer === 'skoda' 
  ? SkodaVehicleDashboard 
  : BMWVehicleDashboard;
```

### Caching Strategy

```tsx
// React Query configuration for Skoda data
const useSkodaVehicleData = (carId: string) => {
  return useQuery({
    queryKey: ['skoda-vehicle', carId],
    queryFn: () => fetchSkodaVehicleData(carId),
    staleTime: 60 * 1000, // 60 seconds
    cacheTime: 5 * 60 * 1000, // 5 minutes
    refetchOnWindowFocus: true,
    retry: 3
  });
};
```

### Bundle Size Optimization

- Shared components between manufacturers
- Tree-shaking unused code
- Dynamic imports for large components
- Optimized image assets (WebP, lazy loading)

## Edge Function Requirements

### New Edge Functions

**skoda-api** (Primary edge function)
```typescript
// supabase/functions/skoda-api/index.ts
import { serve } from 'https://deno.land/std@0.131.0/http/server.ts'

serve(async (req: Request) => {
  const { method, url } = req
  const path = new URL(url).pathname
  
  // Handle different endpoints
  switch (path) {
    case '/auth/setup':
      return handleAuthSetup(req)
    case '/vehicles':
      return handleVehicleList(req)
    case '/vehicles/lock':
      return handleVehicleLock(req)
    // ... other endpoints
  }
})
```

**skoda-setup-spin** (S-PIN management)
```typescript
// supabase/functions/skoda-setup-spin/index.ts
export async function handler(req: Request) {
  const { carId, spin } = await req.json()
  
  // Validate S-PIN format
  if (!spin || !/^\d{4}$/.test(spin)) {
    return new Response(
      JSON.stringify({ error: 'Invalid S-PIN format' }),
      { status: 400 }
    )
  }
  
  // Encrypt and store S-PIN
  const encryptedPin = await encryptData(spin)
  await updateVehicleMetadata(carId, {
    has_spin: true,
    spin_hash: encryptedPin
  })
  
  return new Response(
    JSON.stringify({ success: true }),
    { status: 200 }
  )
}
```

**skoda-verify-spin** (S-PIN verification)
```typescript
// supabase/functions/skoda-verify-spin/index.ts
export async function handler(req: Request) {
  const { carId, spin } = await req.json()
  
  const metadata = await getVehicleMetadata(carId)
  const isValid = await verifyPin(spin, metadata.spin_hash)
  
  return new Response(
    JSON.stringify({ verified: isValid }),
    { status: 200 }
  )
}
```

### Database Schema Updates

```sql
-- Update car_connectivity table
ALTER TABLE car_connectivity 
ADD COLUMN metadata JSONB DEFAULT '{}';

-- Metadata structure for Skoda vehicles
-- {
--   "has_spin": boolean,
--   "spin_hash": string (encrypted),
--   "session_token": string,
--   "session_expires": timestamp,
--   "capabilities": {
--     "electric": boolean,
--     "climate_control": boolean,
--     "remote_lock": boolean
--   }
-- }
```

## Implementation Dependencies

### Frontend Dependencies

```json
{
  "dependencies": {
    "@tanstack/react-query": "^4.x", // Existing
    "react-hook-form": "^7.x",       // Existing
    "zustand": "^4.x",               // State management
    "react-pin-input": "^1.x",      // S-PIN input component
    "react-hot-keys": "^2.x",       // Keyboard shortcuts
    "@radix-ui/react-*": "^1.x"     // Existing UI primitives
  },
  "devDependencies": {
    "@testing-library/react": "^13.x", // Existing
    "msw": "^1.x",                     // API mocking
    "axe-core": "^4.x"                 // Accessibility testing
  }
}
```

## Testing Strategy

### Component Testing

```tsx
describe('SkodaVehicleDashboard', () => {
  test('displays vehicle status correctly', async () => {
    render(<SkodaVehicleDashboard carId="test-car-id" />);
    
    expect(screen.getByText('Octavia')).toBeInTheDocument();
    expect(screen.getByText('Locked')).toBeInTheDocument();
    expect(screen.getByText('65% fuel')).toBeInTheDocument();
  });
  
  test('prompts for S-PIN on lock action', async () => {
    render(<SkodaVehicleDashboard carId="test-car-id" />);
    
    fireEvent.click(screen.getByText('Lock'));
    
    expect(screen.getByText('Enter your S-PIN')).toBeInTheDocument();
  });
});
```

### Integration Testing

```tsx
describe('Skoda API Integration', () => {
  test('handles S-PIN authentication flow', async () => {
    // Mock successful API responses
    server.use(
      rest.post('/api/skoda/vehicles/:vin/lock', (req, res, ctx) => {
        return res(ctx.json({ success: true }));
      })
    );
    
    // Test complete flow from UI to API
    render(<SkodaVehicleDashboard carId="test-car-id" />);
    
    fireEvent.click(screen.getByText('Lock'));
    fireEvent.change(screen.getByLabelText('S-PIN'), { target: { value: '1234' } });
    fireEvent.click(screen.getByText('Confirm'));
    
    await waitFor(() => {
      expect(screen.getByText('Vehicle locked')).toBeInTheDocument();
    });
  });
});
```

### Accessibility Testing

```tsx
describe('Accessibility', () => {
  test('meets WCAG guidelines', async () => {
    const { container } = render(<SkodaVehicleDashboard carId="test-car-id" />);
    
    const results = await axe(container);
    expect(results).toHaveNoViolations();
  });
  
  test('supports keyboard navigation', () => {
    render(<SkodaVehicleDashboard carId="test-car-id" />);
    
    const lockButton = screen.getByRole('button', { name: /lock/i });
    lockButton.focus();
    fireEvent.keyDown(lockButton, { key: 'Enter' });
    
    expect(screen.getByText('Enter your S-PIN')).toBeInTheDocument();
  });
});
```

## Rollout Strategy

### Phased Release Plan

**Phase 1: Core UI (Week 1-2)**
- Basic dashboard components
- Account setup flow
- Read-only vehicle status
- No S-PIN requirements

**Phase 2: S-PIN Integration (Week 3)**
- S-PIN setup modal
- S-PIN prompt for operations
- Secure storage integration
- Full remote controls

**Phase 3: Advanced Features (Week 4-5)**
- EV charging controls
- Service interval displays
- Real-time updates
- Performance optimizations

**Phase 4: Polish & Launch (Week 6)**
- Error state improvements
- Accessibility audit
- Mobile optimization
- User acceptance testing

## Advanced UI Implementation Details

### Unified Vehicle Management Interface

To provide a seamless experience across manufacturers, implement a unified vehicle management interface:

```tsx
// src/components/cars/UnifiedVehicleManager.tsx
interface UnifiedVehicleManagerProps {
  vehicles: Array<{
    id: string;
    manufacturer: 'BMW' | 'Skoda' | 'Mercedes' | 'Audi';
    model: string;
    vin: string;
    capabilities: VehicleCapabilities;
  }>;
}

export function UnifiedVehicleManager({ vehicles }: UnifiedVehicleManagerProps) {
  return (
    <div className="space-y-6">
      <div className="flex justify-between items-center">
        <h2 className="text-2xl font-semibold">My Vehicles</h2>
        <AddVehicleDropdown manufacturers={['BMW', 'Skoda']} />
      </div>
      
      <div className="grid grid-cols-1 md:grid-cols-2 lg:grid-cols-3 gap-6">
        {vehicles.map((vehicle) => (
          <VehicleCard
            key={vehicle.id}
            vehicle={vehicle}
            onClick={() => openManufacturerDashboard(vehicle)}
          />
        ))}
      </div>
    </div>
  );
}
```

### State Management Architecture

Implement a global state management solution for vehicle data across manufacturers:

```tsx
// src/stores/vehicleStore.ts
import { create } from 'zustand';
import { devtools, persist } from 'zustand/middleware';

interface VehicleStore {
  // BMW vehicles
  bmwVehicles: BMWVehicle[];
  bmwCredentials: boolean;
  
  // Skoda vehicles  
  skodaVehicles: SkodaVehicle[];
  skodaCredentials: boolean;
  skodaHasSPin: boolean;
  
  // Actions
  addBMWVehicle: (vehicle: BMWVehicle) => void;
  addSkodaVehicle: (vehicle: SkodaVehicle) => void;
  updateVehicleStatus: (vin: string, status: VehicleStatus) => void;
  setSkodaSPin: (hasSPin: boolean) => void;
  
  // Unified getters
  getAllVehicles: () => UnifiedVehicle[];
  getVehicleByVin: (vin: string) => UnifiedVehicle | undefined;
}

export const useVehicleStore = create<VehicleStore>()(
  devtools(
    persist(
      (set, get) => ({
        // Initial state
        bmwVehicles: [],
        bmwCredentials: false,
        skodaVehicles: [],
        skodaCredentials: false,
        skodaHasSPin: false,
        
        // Implementation...
      }),
      {
        name: 'vehicle-storage',
        partialize: (state) => ({
          // Only persist non-sensitive data
          bmwCredentials: state.bmwCredentials,
          skodaCredentials: state.skodaCredentials,
          skodaHasSPin: state.skodaHasSPin,
        }),
      }
    )
  )
);
```

### S-PIN Management Component Library

Create a reusable S-PIN management component library:

```tsx
// src/components/cars/Skoda/components/spin/SPinManager.tsx
interface SPinManagerProps {
  carId: string;
  onSuccess?: () => void;
  variant?: 'setup' | 'verify' | 'change';
}

export function SPinManager({ carId, onSuccess, variant = 'verify' }: SPinManagerProps) {
  const [step, setStep] = useState<'info' | 'input' | 'confirm'>('info');
  const [attempts, setAttempts] = useState(0);
  const MAX_ATTEMPTS = 3;
  
  return (
    <Dialog open onOpenChange={() => {}}>
      <DialogContent className="sm:max-w-md">
        {step === 'info' && (
          <SPinInfoStep 
            variant={variant}
            onContinue={() => setStep('input')}
          />
        )}
        
        {step === 'input' && (
          <SPinInputStep
            variant={variant}
            attempts={attempts}
            maxAttempts={MAX_ATTEMPTS}
            onSubmit={async (pin) => {
              const result = await verifySPin(carId, pin);
              if (result.success) {
                setStep('confirm');
                onSuccess?.();
              } else {
                setAttempts(prev => prev + 1);
                if (attempts >= MAX_ATTEMPTS - 1) {
                  // Lock out after max attempts
                  showLockoutDialog();
                }
              }
            }}
          />
        )}
        
        {step === 'confirm' && (
          <SPinConfirmStep variant={variant} />
        )}
      </DialogContent>
    </Dialog>
  );
}
```

### Real-time Synchronization

Implement real-time data synchronization across tabs and devices:

```tsx
// src/hooks/useVehicleSync.ts
export function useVehicleSync(vehicleId: string) {
  const queryClient = useQueryClient();
  
  useEffect(() => {
    // Subscribe to vehicle updates
    const channel = supabase
      .channel(`vehicle-sync-${vehicleId}`)
      .on('broadcast', { event: 'vehicle-update' }, (payload) => {
        // Update React Query cache
        queryClient.setQueryData(
          ['vehicle', vehicleId],
          payload.data
        );
        
        // Update Zustand store
        useVehicleStore.getState().updateVehicleStatus(
          vehicleId,
          payload.data.status
        );
      })
      .subscribe();
    
    // Sync across tabs
    const handleStorageChange = (e: StorageEvent) => {
      if (e.key === `vehicle-${vehicleId}` && e.newValue) {
        const data = JSON.parse(e.newValue);
        queryClient.setQueryData(['vehicle', vehicleId], data);
      }
    };
    
    window.addEventListener('storage', handleStorageChange);
    
    return () => {
      supabase.removeChannel(channel);
      window.removeEventListener('storage', handleStorageChange);
    };
  }, [vehicleId, queryClient]);
}
```

### Error Boundary Implementation

Implement manufacturer-specific error boundaries:

```tsx
// src/components/cars/shared/ManufacturerErrorBoundary.tsx
interface ManufacturerErrorBoundaryProps {
  manufacturer: 'BMW' | 'Skoda';
  children: React.ReactNode;
}

export class ManufacturerErrorBoundary extends Component<
  ManufacturerErrorBoundaryProps,
  { hasError: boolean; error: Error | null }
> {
  constructor(props: ManufacturerErrorBoundaryProps) {
    super(props);
    this.state = { hasError: false, error: null };
  }
  
  static getDerivedStateFromError(error: Error) {
    return { hasError: true, error };
  }
  
  componentDidCatch(error: Error, info: ErrorInfo) {
    // Log to monitoring service
    logErrorToService({
      error,
      info,
      manufacturer: this.props.manufacturer,
      timestamp: new Date().toISOString(),
    });
  }
  
  render() {
    if (this.state.hasError) {
      return (
        <ManufacturerErrorFallback
          manufacturer={this.props.manufacturer}
          error={this.state.error}
          onReset={() => this.setState({ hasError: false, error: null })}
        />
      );
    }
    
    return this.props.children;
  }
}
```

### Optimistic Updates Pattern

Implement optimistic updates for better perceived performance:

```tsx
// src/hooks/useOptimisticVehicleControl.ts
export function useOptimisticVehicleControl(vehicleId: string) {
  const queryClient = useQueryClient();
  
  const lockVehicle = useMutation({
    mutationFn: async (sPin?: string) => {
      return await api.skoda.lockVehicle(vehicleId, sPin);
    },
    onMutate: async () => {
      // Cancel outgoing refetches
      await queryClient.cancelQueries(['vehicle', vehicleId]);
      
      // Snapshot previous value
      const previousVehicle = queryClient.getQueryData(['vehicle', vehicleId]);
      
      // Optimistically update
      queryClient.setQueryData(['vehicle', vehicleId], (old: any) => ({
        ...old,
        status: { ...old.status, locked: true },
      }));
      
      return { previousVehicle };
    },
    onError: (err, variables, context) => {
      // Rollback on error
      queryClient.setQueryData(
        ['vehicle', vehicleId],
        context?.previousVehicle
      );
      
      toast.error('Failed to lock vehicle. Please try again.');
    },
    onSettled: () => {
      // Always refetch after error or success
      queryClient.invalidateQueries(['vehicle', vehicleId]);
    },
  });
  
  return { lockVehicle };
}
```

### Analytics Integration

Implement comprehensive analytics tracking:

```tsx
// src/utils/analytics/vehicleAnalytics.ts
export const vehicleAnalytics = {
  trackVehicleAdded: (manufacturer: string, model: string) => {
    analytics.track('Vehicle Added', {
      manufacturer,
      model,
      timestamp: new Date().toISOString(),
    });
  },
  
  trackSPinSetup: (success: boolean, attempts: number) => {
    analytics.track('S-PIN Setup', {
      success,
      attempts,
      timestamp: new Date().toISOString(),
    });
  },
  
  trackRemoteAction: (action: string, manufacturer: string, success: boolean) => {
    analytics.track('Remote Vehicle Action', {
      action,
      manufacturer,
      success,
      timestamp: new Date().toISOString(),
    });
  },
  
  trackErrorOccurred: (error: string, context: any) => {
    analytics.track('Error Occurred', {
      error,
      context,
      timestamp: new Date().toISOString(),
    });
  },
};
```

## Future Enhancements

### Phase 2 Roadmap (Month 2-3)

**Advanced S-PIN Features:**
- Biometric authentication fallback
- Temporary S-PINs for sharing
- S-PIN rotation policies

**Enhanced Vehicle Insights:**
- Predictive maintenance alerts
- Trip analysis and reporting
- Fuel/energy efficiency tracking
- Driver behavior insights

**Integration Improvements:**
- Voice assistant support
- Apple CarPlay/Android Auto
- Smart home integrations
- Calendar-based climate scheduling

### Long-term Vision

**Unified Vehicle Platform:**
- Manufacturer-agnostic component library
- Cross-platform mobile apps
- Fleet management dashboard
- API for third-party integrations

## Conclusion

The Skoda Connect frontend integration builds upon the solid foundation established by the BMW implementation while introducing new UI patterns for S-PIN management and enhanced security. The modular component architecture ensures maintainability and enables future expansion to additional manufacturers.

Key differentiators from the BMW implementation:
1. **S-PIN Authentication**: Unique security flow with progressive enhancement
2. **Session Management**: Different from OAuth token handling
3. **Enhanced Feature Set**: EV charging, service intervals, advanced diagnostics
4. **Unified Architecture**: Shared components for future manufacturer integrations

The comprehensive testing strategy, accessibility focus, and performance optimizations ensure a production-ready implementation that provides excellent user experience while maintaining security and reliability standards.

---

**Document Version**: 1.0.0  
**Last Updated**: January 2025  
**Next Review**: February 2025  
**Approval Status**: READY FOR IMPLEMENTATION

**Related Documents**:
- PRP-002-API.md - Backend API Implementation
- PRP-002-Skoda-Connect-API-Integration.md - Original comprehensive PRP

*This document focuses exclusively on the frontend UI/UX and edge function implementation for the Skoda Connect integration. For backend API specifications, refer to PRP-002-API.md.*