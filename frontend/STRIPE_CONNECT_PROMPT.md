# Stripe Connect Prompt Dialog

## Overview

A reusable Material-UI dialog component that prompts users to connect their Stripe account when it's not configured. This helps onboard new users and ensures they connect Stripe to access payment monitoring features.

## Components

### `StripeConnectPrompt`

Location: `src/components/ui/stripe-connect-prompt.tsx`

A themed dialog that:
- Shows when Stripe is not connected
- Explains what will be monitored
- Emphasizes read-only access
- Redirects to Stripe Connect OAuth flow

**Props:**
```typescript
interface StripeConnectPromptProps {
  open: boolean          // Controls dialog visibility
  onClose: () => void    // Callback when dialog is closed
  workspaceId: string    // Current workspace ID
  title?: string         // Optional custom title
  message?: string       // Optional custom message
}
```

### `useStripeConnectPrompt` Hook

A convenience hook for managing dialog state:

```typescript
const { open, show, hide, StripeConnectPrompt } = useStripeConnectPrompt()
```

## Usage

### 1. Import the Component

```typescript
import { StripeConnectPrompt } from '@/components/ui/stripe-connect-prompt'
import { stripeConnectApi } from '@/lib/api'
```

### 2. Add State Management

```typescript
const [showStripePrompt, setShowStripePrompt] = useState(false)
const [hasStripeAccount, setHasStripeAccount] = useState<boolean | null>(null)
```

### 3. Check Stripe Connection Status

```typescript
useEffect(() => {
  async function checkStripeConnection() {
    try {
      const accounts = await stripeConnectApi.listAccounts(workspaceId)
      const hasAccount = accounts.length > 0
      setHasStripeAccount(hasAccount)

      // Show prompt after delay if no account
      if (!hasAccount) {
        setTimeout(() => setShowStripePrompt(true), 2000)
      }
    } catch (err) {
      console.error('Failed to check Stripe connection:', err)
    }
  }

  if (workspaceId) {
    checkStripeConnection()
  }
}, [workspaceId])
```

### 4. Render the Dialog

```typescript
{workspaceId && hasStripeAccount === false && (
  <StripeConnectPrompt
    open={showStripePrompt}
    onClose={() => setShowStripePrompt(false)}
    workspaceId={workspaceId}
    title="Connect Your Stripe Account"
    message="Custom message for your page context"
  />
)}
```

## Currently Implemented

### Dashboard Page (`src/app/dashboard/page.tsx`)

- Automatically checks for Stripe connection on page load
- Shows prompt 2 seconds after loading if no account is connected
- Custom message focused on viewing payment data and MRR trends

## Where to Add Next

Consider adding the Stripe Connect prompt to:

1. **Alerts Page** - When users try to create alerts without Stripe
2. **Rules Page** - When users try to create rules without payment data
3. **Risk Page** - When users try to view risk analysis
4. **Onboarding** - As part of the initial setup flow

## Example: Adding to Alerts Page

```typescript
// src/app/alerts/page.tsx
import { StripeConnectPrompt } from '@/components/ui/stripe-connect-prompt'
import { stripeConnectApi } from '@/lib/api'

export default function AlertsPage() {
  const { workspaceId } = useAuth()
  const [showStripePrompt, setShowStripePrompt] = useState(false)
  const [hasStripeAccount, setHasStripeAccount] = useState<boolean | null>(null)

  // Check Stripe connection
  useEffect(() => {
    if (!workspaceId) return

    stripeConnectApi.listAccounts(workspaceId).then(accounts => {
      setHasStripeAccount(accounts.length > 0)
    })
  }, [workspaceId])

  // Show prompt when user clicks "Create Alert" without Stripe
  const handleCreateAlert = () => {
    if (hasStripeAccount === false) {
      setShowStripePrompt(true)
      return
    }
    // Continue with alert creation
  }

  return (
    <>
      {/* Your page content */}

      {workspaceId && hasStripeAccount === false && (
        <StripeConnectPrompt
          open={showStripePrompt}
          onClose={() => setShowStripePrompt(false)}
          workspaceId={workspaceId}
          title="Connect Stripe to Create Alerts"
          message="Alerts monitor your Stripe payment data. Connect your account to set up alerts."
        />
      )}
    </>
  )
}
```

## Customization

### Custom Title and Message

```typescript
<StripeConnectPrompt
  open={open}
  onClose={onClose}
  workspaceId={workspaceId}
  title="Stripe Required"
  message="This feature requires a connected Stripe account."
/>
```

### Conditional Display

Show only on specific conditions:

```typescript
{shouldShowPrompt && hasStripeAccount === false && (
  <StripeConnectPrompt {...props} />
)}
```

## User Flow

1. User lands on dashboard (or another page)
2. App checks if Stripe account is connected
3. If not connected, dialog appears after 2 seconds
4. User can:
   - Click "Connect Stripe" → Redirected to Stripe OAuth
   - Click "Maybe Later" → Dialog closes
5. After connecting, user returns to the app and dialog doesn't show again

## Benefits

- ✅ Consistent UI across all pages
- ✅ Clear call-to-action for new users
- ✅ Explains what will be monitored
- ✅ Emphasizes security (read-only access)
- ✅ Easy to add to any page
- ✅ Customizable messaging per page
- ✅ Material-UI themed

## Testing

To test the dialog:

1. Navigate to dashboard without a connected Stripe account
2. Wait 2 seconds - dialog should appear
3. Click "Maybe Later" - dialog should close
4. Click "Connect Stripe" - should redirect to Stripe OAuth
5. After connecting, dialog should not appear again
