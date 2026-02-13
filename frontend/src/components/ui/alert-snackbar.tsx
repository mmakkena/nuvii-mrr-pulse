import React from 'react'
import { Snackbar, Alert, AlertColor } from '@mui/material'

interface AlertSnackbarProps {
  open: boolean
  onClose: () => void
  message: string
  severity?: AlertColor
  autoHideDuration?: number
}

export function AlertSnackbar({
  open,
  onClose,
  message,
  severity = 'info',
  autoHideDuration = 6000,
}: AlertSnackbarProps) {
  return (
    <Snackbar
      open={open}
      autoHideDuration={autoHideDuration}
      onClose={onClose}
      anchorOrigin={{ vertical: 'top', horizontal: 'right' }}
    >
      <Alert onClose={onClose} severity={severity} sx={{ width: '100%' }} variant="filled">
        {message}
      </Alert>
    </Snackbar>
  )
}

// Hook for easier usage
export function useAlertSnackbar() {
  const [snackbarState, setSnackbarState] = React.useState<{
    open: boolean
    message: string
    severity: AlertColor
  }>({
    open: false,
    message: '',
    severity: 'info',
  })

  const showAlert = (message: string, severity: AlertColor = 'info') => {
    setSnackbarState({
      open: true,
      message,
      severity,
    })
  }

  const closeSnackbar = () => {
    setSnackbarState((prev) => ({ ...prev, open: false }))
  }

  const SnackbarComponent = () => (
    <AlertSnackbar
      open={snackbarState.open}
      onClose={closeSnackbar}
      message={snackbarState.message}
      severity={snackbarState.severity}
    />
  )

  return {
    showAlert,
    showSuccess: (message: string) => showAlert(message, 'success'),
    showError: (message: string) => showAlert(message, 'error'),
    showWarning: (message: string) => showAlert(message, 'warning'),
    showInfo: (message: string) => showAlert(message, 'info'),
    AlertSnackbar: SnackbarComponent,
  }
}
