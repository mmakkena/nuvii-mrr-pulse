# MRRPulse API - Postman Collection Guide

This guide explains how to use the Postman collection for testing the MRRPulse API.

## Files Created

1. **MRRPulse_API.postman_collection.json** - Complete API collection with all endpoints
2. **MRRPulse_Local.postman_environment.json** - Local environment variables

## Quick Start

### 1. Import into Postman

1. Open Postman
2. Click **Import** button (top left)
3. Drag and drop both JSON files:
   - `MRRPulse_API.postman_collection.json`
   - `MRRPulse_Local.postman_environment.json`
4. Click **Import**

### 2. Set Environment

1. Select **MRRPulse - Local** from the environment dropdown (top right)
2. The environment is pre-configured with:
   - `baseUrl`: http://localhost:8000
   - `test_email`: test@example.com
   - `test_password`: password123

### 3. Authenticate

#### Option A: Use Existing Test Account

1. Open the **Authentication** folder
2. Run the **Login** request
3. The access token will be automatically saved to your environment
4. All subsequent requests will use this token automatically

#### Option B: Create New Account

1. Open the **Authentication** folder
2. Run the **Sign Up** request (modify the email/password in the body)
3. Tokens will be automatically saved

### 4. Get Workspace ID

After logging in:

1. Open the **Workspaces** folder
2. Run **List Workspaces**
3. The workspace_id will be automatically saved to your environment

## Collection Structure

### 1. Health
- **Health Check** - Verify API is running (no auth required)

### 2. Authentication
- **Sign Up** - Create new user account
- **Login** - Authenticate and get tokens ⚡ Auto-saves tokens
- **Get Current User** - Get authenticated user details
- **Refresh Token** - Get new access token
- **Logout** - End session
- **Google OAuth** - Sign in with Google
- **Forgot Password** - Request password reset
- **Reset Password** - Complete password reset

### 3. Workspaces
- **List Workspaces** - Get all workspaces ⚡ Auto-saves workspace_id
- **Create Workspace** - Create new workspace
- **Get Workspace** - Get workspace details with members
- **Update Workspace** - Update workspace settings
- **Invite Member** - Add team member
- **Update Member Role** - Change member permissions
- **Remove Member** - Remove team member

### 4. Stripe Connect
- **Start Stripe Connect** - Begin OAuth flow
- **Create Test Stripe Account** - Create test account (dev only)
- **List Stripe Accounts** - Get connected accounts
- **Get Stripe Account** - Get account details
- **Disconnect Stripe Account** - Revoke connection
- **Sync Stripe Account** - Refresh account data

### 5. Webhooks
- **Stripe Webhook (Connect)** - Receive Stripe events
- **Billing Webhook** - Receive billing events
- **List Webhook Events** - View event history
- **Retry Webhook Event** - Reprocess failed event

### 6. Alerts
- **List Alerts** - Get alerts with filters
- **Get Alert** - Get single alert details
- **Get Alert Stats** - Get alert counts by severity
- **Acknowledge Alert** - Mark alert as seen
- **Acknowledge All Alerts** - Clear all alerts
- **Send Test Alert** - Test notification channels

### 7. Alert Rules
- **List Rules** - Get all alert rules
- **Create Rule** - Define new alert rule
- **Get Rule** - Get rule details
- **Update Rule** - Modify existing rule
- **Delete Rule** - Remove rule
- **Apply Preset (Founder)** - Enable founder pack
- **Apply Preset (Risk)** - Enable risk monitoring pack
- **Apply Preset (Team)** - Enable team notification pack

### 8. Integrations
- **List Integrations** - Get all integrations
- **Configure Slack** - Setup Slack webhooks
- **Configure Discord** - Setup Discord webhooks
- **Configure Email** - Setup email notifications
- **Configure SMS** - Setup SMS alerts
- **Get Integration** - Get integration details
- **Update Integration** - Modify integration
- **Delete Integration** - Remove integration
- **Test Integration** - Send test notification
- **Escalation - Get Roster** - Get SMS escalation contacts
- **Escalation - Add Contact** - Add escalation contact
- **Escalation - Update Contact** - Modify contact
- **Escalation - Delete Contact** - Remove contact

### 9. Risk
- **Get Risk Status** - Get workspace risk metrics
- **Get Account Risk Status** - Get account-specific risk
- **Get Risk History** - Get risk event timeline
- **Get Risk Thresholds** - Get configured thresholds
- **Update Risk Thresholds** - Modify alert thresholds

### 10. Billing
- **Get Subscription** - Get current plan
- **Create Checkout Session** - Start subscription flow
- **Get Billing Portal** - Get Stripe portal URL
- **List Invoices** - Get billing history
- **Get Usage** - Get current usage metrics

## Authentication

Most endpoints require authentication via Bearer token.

### Auto-Authentication
The collection is configured to automatically use the `{{access_token}}` variable from your environment. When you run the **Login** or **Sign Up** requests, the token is automatically saved.

### Manual Token Setup
If needed, you can manually set the token:
1. Click on the environment (top right)
2. Set the `access_token` variable
3. Save

## Headers

Some endpoints use additional headers:

### X-Workspace-ID
Used to specify which workspace the request applies to. This is automatically populated using `{{workspace_id}}` from your environment.

To change workspace:
1. Run **List Workspaces** to see available workspaces
2. Copy the desired workspace ID
3. Update the `workspace_id` variable in your environment

## Example Workflow

### Complete Setup Flow

1. **Start Backend**
   ```bash
   docker compose up
   ```

2. **Login**
   - Run: `Authentication > Login`
   - Verify you see tokens in the response

3. **Get Workspace**
   - Run: `Workspaces > List Workspaces`
   - Verify workspace_id is saved

4. **Connect Stripe (Test)**
   - Run: `Stripe Connect > Create Test Stripe Account`
   - Note: Only works in test mode

5. **Configure Notifications**
   - Run: `Integrations > Configure Slack` (or Email/Discord)
   - Update webhook URL in request body

6. **Create Alert Rule**
   - Run: `Alert Rules > Create Rule`
   - Customize conditions in request body

7. **Test Alerts**
   - Run: `Alerts > Send Test Alert`
   - Check your configured channels

## Tips

### Variables
The collection uses these environment variables:
- `{{baseUrl}}` - API base URL
- `{{access_token}}` - JWT access token
- `{{refresh_token}}` - JWT refresh token
- `{{workspace_id}}` - Active workspace ID
- `{{test_email}}` - Test account email
- `{{test_password}}` - Test account password

### Filters
Many list endpoints support filters via query parameters. These are disabled by default in the collection. Enable them by checking the box next to the parameter.

Example (Alerts):
- `severity` - Filter by critical/warning/info
- `status` - Filter by active/acknowledged
- `type` - Filter by alert type
- `page` - Pagination page number
- `page_size` - Results per page

### Scripts
Some requests have built-in test scripts that:
- Automatically save tokens after login/signup
- Save workspace_id after listing workspaces
- Log useful information to the console

View the **Tests** tab in any request to see the scripts.

## Troubleshooting

### "Unauthorized" Errors
- Verify you're logged in (run Login request)
- Check that `access_token` is set in environment
- Token may have expired - run Refresh Token request

### "No workspace found" Errors
- Run List Workspaces to get workspace_id
- Verify workspace_id is set in environment
- Check X-Workspace-ID header is present

### "Invalid workspace ID format" Errors
- Ensure workspace_id is a valid UUID
- Don't include quotes around the ID in the environment

### 404 Errors
- Check the baseUrl in your environment
- Verify the backend is running: `docker compose ps`
- Test health endpoint first

## API Documentation

For detailed API documentation, visit:
- **Swagger UI**: http://localhost:8000/docs
- **ReDoc**: http://localhost:8000/redoc

## Test Data

The collection includes example request bodies for all POST/PUT requests. Customize these as needed for your testing.

### Pre-configured Test Account
- **Email**: test@example.com
- **Password**: password123
- **Workspace**: Test Workspace

This account is automatically created when you run the setup script.

## Support

For issues or questions:
- Check API logs: `docker compose logs backend`
- View API documentation: http://localhost:8000/docs
- Review the README.md in the project root

---

**Happy Testing! 🚀**
