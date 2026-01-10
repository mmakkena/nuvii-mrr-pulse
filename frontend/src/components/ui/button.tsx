import * as React from 'react'
import MuiButton, { ButtonProps as MuiButtonProps } from '@mui/material/Button'
import IconButton, { IconButtonProps } from '@mui/material/IconButton'

export interface ButtonProps extends Omit<MuiButtonProps, 'variant' | 'size'> {
  variant?: 'default' | 'destructive' | 'outline' | 'secondary' | 'ghost' | 'link'
  size?: 'default' | 'sm' | 'lg' | 'icon'
  className?: string
}

const Button = React.forwardRef<HTMLButtonElement, ButtonProps>(
  ({ variant = 'default', size = 'default', sx, className, ...props }, ref) => {
    // Map custom variants to MUI variants
    const getMuiVariant = (): MuiButtonProps['variant'] => {
      switch (variant) {
        case 'default':
          return 'contained'
        case 'outline':
          return 'outlined'
        case 'ghost':
        case 'link':
          return 'text'
        case 'destructive':
          return 'contained'
        case 'secondary':
          return 'contained'
        default:
          return 'contained'
      }
    }

    // Map custom sizes to MUI sizes
    const getMuiSize = (): MuiButtonProps['size'] => {
      switch (size) {
        case 'sm':
          return 'small'
        case 'lg':
          return 'large'
        case 'default':
        case 'icon':
          return 'medium'
        default:
          return 'medium'
      }
    }

    // Handle icon size separately
    if (size === 'icon') {
      return (
        <IconButton
          ref={ref as React.Ref<HTMLButtonElement>}
          size="medium"
          className={className}
          sx={{
            ...sx,
          }}
          {...(props as IconButtonProps)}
        />
      )
    }

    return (
      <MuiButton
        ref={ref}
        variant={getMuiVariant()}
        size={getMuiSize()}
        color={variant === 'destructive' ? 'error' : variant === 'secondary' ? 'secondary' : 'primary'}
        className={className}
        sx={{
          textTransform: 'none',
          fontWeight: 500,
          ...(variant === 'ghost' && {
            '&:hover': {
              backgroundColor: 'action.hover',
            },
          }),
          ...(variant === 'link' && {
            textDecoration: 'underline',
            '&:hover': {
              textDecoration: 'underline',
            },
          }),
          ...sx,
        }}
        {...props}
      />
    )
  }
)
Button.displayName = 'Button'

export { Button }
