import React from 'react'
import {
  Dialog,
  DialogTitle,
  DialogContent,
  DialogContentText,
  DialogActions,
  Button,
} from '@mui/material'

interface ConfirmationDialogProps {
  open: boolean
  onClose: () => void
  onConfirm: () => void
  title: string
  message: string
  confirmText?: string
  cancelText?: string
  severity?: 'error' | 'warning' | 'info'
}

export function ConfirmationDialog({
  open,
  onClose,
  onConfirm,
  title,
  message,
  confirmText = 'Confirm',
  cancelText = 'Cancel',
  severity = 'warning',
}: ConfirmationDialogProps) {
  const handleConfirm = () => {
    onConfirm()
    onClose()
  }

  const getConfirmColor = () => {
    switch (severity) {
      case 'error':
        return 'error'
      case 'warning':
        return 'warning'
      case 'info':
        return 'primary'
      default:
        return 'primary'
    }
  }

  return (
    <Dialog
      open={open}
      onClose={onClose}
      aria-labelledby="confirmation-dialog-title"
      aria-describedby="confirmation-dialog-description"
    >
      <DialogTitle id="confirmation-dialog-title">{title}</DialogTitle>
      <DialogContent>
        <DialogContentText id="confirmation-dialog-description">
          {message}
        </DialogContentText>
      </DialogContent>
      <DialogActions>
        <Button onClick={onClose} color="inherit">
          {cancelText}
        </Button>
        <Button onClick={handleConfirm} color={getConfirmColor()} variant="contained" autoFocus>
          {confirmText}
        </Button>
      </DialogActions>
    </Dialog>
  )
}

// Hook for easier usage
export function useConfirmationDialog() {
  const [dialogState, setDialogState] = React.useState<{
    open: boolean
    title: string
    message: string
    onConfirm: () => void
    severity?: 'error' | 'warning' | 'info'
    confirmText?: string
  }>({
    open: false,
    title: '',
    message: '',
    onConfirm: () => {},
  })

  const confirm = (
    title: string,
    message: string,
    onConfirm: () => void,
    options?: {
      severity?: 'error' | 'warning' | 'info'
      confirmText?: string
    }
  ) => {
    setDialogState({
      open: true,
      title,
      message,
      onConfirm,
      ...options,
    })
  }

  const closeDialog = () => {
    setDialogState((prev) => ({ ...prev, open: false }))
  }

  const DialogComponent = () => (
    <ConfirmationDialog
      open={dialogState.open}
      onClose={closeDialog}
      onConfirm={dialogState.onConfirm}
      title={dialogState.title}
      message={dialogState.message}
      severity={dialogState.severity}
      confirmText={dialogState.confirmText}
    />
  )

  return { confirm, ConfirmationDialog: DialogComponent }
}
