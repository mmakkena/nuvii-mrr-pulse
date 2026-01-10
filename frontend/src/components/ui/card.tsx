import * as React from 'react'
import MuiCard, { CardProps as MuiCardProps } from '@mui/material/Card'
import CardContent from '@mui/material/CardContent'
import Typography from '@mui/material/Typography'
import Box from '@mui/material/Box'

export interface CardProps extends MuiCardProps {}

const Card = React.forwardRef<HTMLDivElement, CardProps>(
  ({ sx, ...props }, ref) => (
    <MuiCard
      ref={ref}
      sx={{
        borderRadius: 2,
        ...sx,
      }}
      {...props}
    />
  )
)
Card.displayName = 'Card'

const CardHeader = React.forwardRef<
  HTMLDivElement,
  React.HTMLAttributes<HTMLDivElement>
>(({ style, ...props }, ref) => (
  <Box
    ref={ref}
    sx={{
      display: 'flex',
      flexDirection: 'column',
      gap: 1.5,
      p: 3,
    }}
    {...props}
  />
))
CardHeader.displayName = 'CardHeader'

const CardTitle = React.forwardRef<
  HTMLHeadingElement,
  React.HTMLAttributes<HTMLHeadingElement>
>(({ style, ...props }, ref) => (
  <Typography
    ref={ref}
    variant="h5"
    component="h3"
    sx={{
      fontWeight: 600,
      lineHeight: 1,
    }}
    {...props}
  />
))
CardTitle.displayName = 'CardTitle'

const CardDescription = React.forwardRef<
  HTMLParagraphElement,
  React.HTMLAttributes<HTMLParagraphElement>
>(({ style, ...props }, ref) => (
  <Typography
    ref={ref}
    variant="body2"
    color="text.secondary"
    {...props}
  />
))
CardDescription.displayName = 'CardDescription'

const CardContentCustom = React.forwardRef<
  HTMLDivElement,
  React.HTMLAttributes<HTMLDivElement>
>(({ style, ...props }, ref) => (
  <CardContent
    ref={ref}
    sx={{
      pt: 0,
    }}
    {...props}
  />
))
CardContentCustom.displayName = 'CardContent'

const CardFooter = React.forwardRef<
  HTMLDivElement,
  React.HTMLAttributes<HTMLDivElement>
>(({ style, ...props }, ref) => (
  <Box
    ref={ref}
    sx={{
      display: 'flex',
      alignItems: 'center',
      p: 3,
      pt: 0,
    }}
    {...props}
  />
))
CardFooter.displayName = 'CardFooter'

export { Card, CardHeader, CardFooter, CardTitle, CardDescription, CardContentCustom as CardContent }
