-- Add invitation token fields to workspace_members table
-- This enables secure invitation acceptance flow

ALTER TABLE workspace_members
ADD COLUMN invitation_token VARCHAR(255),
ADD COLUMN token_expires_at TIMESTAMP WITH TIME ZONE;

-- Create index on invitation_token for fast lookups
CREATE INDEX idx_workspace_members_invitation_token ON workspace_members(invitation_token);

-- Add comment for documentation
COMMENT ON COLUMN workspace_members.invitation_token IS 'Secure token for invitation acceptance';
COMMENT ON COLUMN workspace_members.token_expires_at IS 'Expiration timestamp for invitation token';
