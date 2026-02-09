import * as React from 'react'
import MuiFormLabel, { FormLabelProps } from '@mui/material/FormLabel'

export interface LabelProps extends FormLabelProps {}

const Label = React.forwardRef<HTMLLabelElement, LabelProps>(
  ({ sx, ...props }, ref) => {
    return (
      <MuiFormLabel
        ref={ref}
        sx={{
          fontSize: '0.875rem',
          fontWeight: 500,
          color: 'text.primary',
          mb: 0.5,
          display: 'block',
          ...sx,
        }}
        {...props}
      />
    )
  }
)
Label.displayName = 'Label'

export { Label }
