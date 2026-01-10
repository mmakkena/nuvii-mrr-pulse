import * as React from 'react'
import TextField, { TextFieldProps } from '@mui/material/TextField'

export interface InputProps extends Omit<TextFieldProps, 'variant'> {}

const Input = React.forwardRef<HTMLInputElement, InputProps>(
  ({ sx, ...props }, ref) => {
    return (
      <TextField
        inputRef={ref}
        variant="outlined"
        size="small"
        fullWidth
        sx={{
          '& .MuiOutlinedInput-root': {
            borderRadius: 1.5,
          },
          ...sx,
        }}
        {...props}
      />
    )
  }
)
Input.displayName = 'Input'

export { Input }
