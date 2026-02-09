import * as React from 'react'
import MuiDialog, { DialogProps as MuiDialogProps } from '@mui/material/Dialog'
import MuiDialogTitle from '@mui/material/DialogTitle'
import MuiDialogContent from '@mui/material/DialogContent'
import MuiDialogActions from '@mui/material/DialogActions'
import IconButton from '@mui/material/IconButton'
import { X } from 'lucide-react'

interface DialogProps extends MuiDialogProps {
  onOpenChange?: (open: boolean) => void
}

const Dialog = React.forwardRef<HTMLDivElement, DialogProps>(
  ({ onOpenChange, onClose, children, ...props }, ref) => {
    const handleClose = (event: {}, reason: 'backdropClick' | 'escapeKeyDown') => {
      if (onClose) {
        onClose(event, reason)
      }
      if (onOpenChange) {
        onOpenChange(false)
      }
    }

    return (
      <MuiDialog
        ref={ref}
        onClose={handleClose}
        maxWidth="sm"
        fullWidth
        PaperProps={{
          sx: {
            borderRadius: 3,
          },
        }}
        {...props}
      >
        {children}
      </MuiDialog>
    )
  }
)
Dialog.displayName = 'Dialog'

const DialogContent = React.forwardRef<
  HTMLDivElement,
  React.ComponentProps<typeof MuiDialogContent>
>(({ children, sx, ...props }, ref) => {
  return (
    <MuiDialogContent
      ref={ref}
      sx={{
        px: 3,
        py: 2,
        ...sx,
      }}
      {...props}
    >
      {children}
    </MuiDialogContent>
  )
})
DialogContent.displayName = 'DialogContent'

interface DialogHeaderProps {
  children: React.ReactNode
  onClose?: () => void
}

const DialogHeader = ({ children, onClose }: DialogHeaderProps) => {
  return (
    <MuiDialogTitle
      sx={{
        px: 3,
        pt: 3,
        pb: 1,
        display: 'flex',
        alignItems: 'flex-start',
        justifyContent: 'space-between',
      }}
    >
      <div style={{ flex: 1 }}>{children}</div>
      {onClose && (
        <IconButton
          aria-label="close"
          onClick={onClose}
          size="small"
          sx={{
            color: 'text.secondary',
          }}
        >
          <X size={20} />
        </IconButton>
      )}
    </MuiDialogTitle>
  )
}
DialogHeader.displayName = 'DialogHeader'

interface DialogTitleProps {
  children: React.ReactNode
  className?: string
}

const DialogTitle = ({ children, className }: DialogTitleProps) => {
  return (
    <div className={className} style={{ fontSize: '1.25rem', fontWeight: 600, marginBottom: '0.5rem' }}>
      {children}
    </div>
  )
}
DialogTitle.displayName = 'DialogTitle'

interface DialogDescriptionProps {
  children: React.ReactNode
  className?: string
}

const DialogDescription = ({ children, className }: DialogDescriptionProps) => {
  return (
    <div className={className} style={{ fontSize: '0.875rem', color: '#64748b' }}>
      {children}
    </div>
  )
}
DialogDescription.displayName = 'DialogDescription'

const DialogActions = MuiDialogActions

export { Dialog, DialogContent, DialogHeader, DialogTitle, DialogDescription, DialogActions }
