'use client'

import * as React from 'react'
import TextField, { TextFieldProps } from '@mui/material/TextField'
import InputAdornment from '@mui/material/InputAdornment'
import IconButton from '@mui/material/IconButton'
import Visibility from '@mui/icons-material/Visibility'
import VisibilityOff from '@mui/icons-material/VisibilityOff'

export interface PasswordInputProps extends Omit<TextFieldProps, 'variant' | 'type'> {
  showStrengthIndicator?: boolean
}

// Password strength calculation
function calculatePasswordStrength(password: string): {
  score: number
  label: string
  color: string
} {
  let score = 0

  if (password.length >= 8) score += 1
  if (password.length >= 12) score += 1
  if (/[a-z]/.test(password)) score += 1
  if (/[A-Z]/.test(password)) score += 1
  if (/[0-9]/.test(password)) score += 1
  if (/[^a-zA-Z0-9]/.test(password)) score += 1

  if (score <= 2) return { score, label: 'Weak', color: '#ef4444' }
  if (score <= 4) return { score, label: 'Medium', color: '#f59e0b' }
  return { score, label: 'Strong', color: '#22c55e' }
}

const PasswordInput = React.forwardRef<HTMLInputElement, PasswordInputProps>(
  ({ sx, showStrengthIndicator = false, value, ...props }, ref) => {
    const [showPassword, setShowPassword] = React.useState(false)

    const handleClickShowPassword = () => setShowPassword(!showPassword)
    const handleMouseDownPassword = (event: React.MouseEvent<HTMLButtonElement>) => {
      event.preventDefault()
    }

    const passwordValue = typeof value === 'string' ? value : ''
    const strength = showStrengthIndicator && passwordValue
      ? calculatePasswordStrength(passwordValue)
      : null

    return (
      <div>
        <TextField
          inputRef={ref}
          variant="outlined"
          size="small"
          fullWidth
          type={showPassword ? 'text' : 'password'}
          value={value}
          sx={{
            '& .MuiOutlinedInput-root': {
              borderRadius: 1.5,
            },
            ...sx,
          }}
          InputProps={{
            endAdornment: (
              <InputAdornment position="end">
                <IconButton
                  aria-label={showPassword ? 'Hide password' : 'Show password'}
                  onClick={handleClickShowPassword}
                  onMouseDown={handleMouseDownPassword}
                  edge="end"
                  size="small"
                >
                  {showPassword ? <VisibilityOff fontSize="small" /> : <Visibility fontSize="small" />}
                </IconButton>
              </InputAdornment>
            ),
          }}
          {...props}
        />
        {showStrengthIndicator && passwordValue && strength && (
          <div className="mt-2">
            <div className="flex gap-1 mb-1">
              {[1, 2, 3, 4, 5, 6].map((level) => (
                <div
                  key={level}
                  className="h-1 flex-1 rounded-full transition-colors"
                  style={{
                    backgroundColor: level <= strength.score ? strength.color : '#e2e8f0',
                  }}
                />
              ))}
            </div>
            <p className="text-xs" style={{ color: strength.color }}>
              Password strength: {strength.label}
            </p>
          </div>
        )}
      </div>
    )
  }
)
PasswordInput.displayName = 'PasswordInput'

export { PasswordInput, calculatePasswordStrength }
