'use client'

import { useState } from 'react'
import {
  Box,
  Card,
  CardContent,
  FormControl,
  InputLabel,
  Select,
  MenuItem,
  TextField,
  Button,
  IconButton,
  Typography,
  Chip,
  Stack,
  Alert,
  Divider,
} from '@mui/material'
import {
  Add as AddIcon,
  Delete as DeleteIcon,
  ContentCopy as CopyIcon,
} from '@mui/icons-material'

// Available fields for conditions
const FIELD_OPTIONS = [
  { value: 'amount', label: 'Amount (cents)', type: 'number', example: '1000 = $10' },
  { value: 'amount_usd', label: 'Amount (USD)', type: 'number', example: '10.00' },
  { value: 'currency', label: 'Currency', type: 'string', example: 'usd, eur' },
  { value: 'failure_code', label: 'Failure Code', type: 'string', example: 'card_declined' },
  { value: 'failure_message', label: 'Failure Message', type: 'string' },
  { value: 'card.brand', label: 'Card Brand', type: 'string', example: 'visa, mastercard' },
  { value: 'card.country', label: 'Card Country', type: 'string', example: 'US, GB' },
  { value: 'card.funding', label: 'Card Funding', type: 'string', example: 'credit, debit' },
  { value: 'customer_email', label: 'Customer Email', type: 'string' },
  { value: 'reason', label: 'Dispute Reason', type: 'string', example: 'fraudulent' },
  { value: 'status', label: 'Status', type: 'string' },
  { value: 'metadata.customer_tier', label: 'Customer Tier (Metadata)', type: 'string', example: 'premium' },
]

// Operators
const OPERATORS = {
  number: [
    { value: '>', label: 'Greater than (>)' },
    { value: '>=', label: 'Greater than or equal (>=)' },
    { value: '<', label: 'Less than (<)' },
    { value: '<=', label: 'Less than or equal (<=)' },
    { value: '==', label: 'Equal to (==)' },
    { value: '!=', label: 'Not equal to (!=)' },
  ],
  string: [
    { value: '==', label: 'Equal to (==)' },
    { value: '!=', label: 'Not equal to (!=)' },
    { value: 'in', label: 'In list (in)' },
  ],
}

interface Condition {
  id: string
  field: string
  operator: string
  value: string | number
}

interface ConditionBuilderProps {
  value: Record<string, any>
  onChange: (conditions: Record<string, any>) => void
  alertType?: string
}

export function ConditionBuilder({ value, onChange, alertType }: ConditionBuilderProps) {
  const [conditions, setConditions] = useState<Condition[]>(() => {
    // Parse existing JsonLogic to conditions if possible
    if (value && typeof value === 'object') {
      return parseJsonLogicToConditions(value)
    }
    return []
  })
  const [logic, setLogic] = useState<'and' | 'or'>('and')
  const [showJson, setShowJson] = useState(false)

  // Convert conditions to JsonLogic
  const buildJsonLogic = (conds: Condition[], logicOp: 'and' | 'or') => {
    if (conds.length === 0) return {}

    const jsonLogicConditions = conds.map((cond) => {
      const fieldInfo = FIELD_OPTIONS.find((f) => f.value === cond.field)
      const isNumber = fieldInfo?.type === 'number'

      // Parse value
      let parsedValue: any = cond.value
      if (isNumber && typeof cond.value === 'string') {
        parsedValue = parseFloat(cond.value) || 0
      }

      // Handle 'in' operator for lists
      if (cond.operator === 'in') {
        const listValues = typeof parsedValue === 'string'
          ? parsedValue.split(',').map(v => v.trim())
          : [parsedValue]
        return {
          [cond.operator]: [{ var: cond.field }, listValues]
        }
      }

      return {
        [cond.operator]: [{ var: cond.field }, parsedValue]
      }
    })

    if (jsonLogicConditions.length === 1) {
      return jsonLogicConditions[0]
    }

    return {
      [logicOp]: jsonLogicConditions
    }
  }

  const handleAddCondition = () => {
    const newCondition: Condition = {
      id: Date.now().toString(),
      field: 'amount',
      operator: '>',
      value: 1000,
    }
    const newConditions = [...conditions, newCondition]
    setConditions(newConditions)
    onChange(buildJsonLogic(newConditions, logic))
  }

  const handleRemoveCondition = (id: string) => {
    const newConditions = conditions.filter((c) => c.id !== id)
    setConditions(newConditions)
    onChange(buildJsonLogic(newConditions, logic))
  }

  const handleUpdateCondition = (id: string, field: keyof Condition, value: any) => {
    const newConditions = conditions.map((c) => {
      if (c.id === id) {
        const updated = { ...c, [field]: value }

        // Reset operator if field type changes
        if (field === 'field') {
          const fieldInfo = FIELD_OPTIONS.find((f) => f.value === value)
          const fieldType = fieldInfo?.type || 'string'
          const availableOps = OPERATORS[fieldType as keyof typeof OPERATORS]
          updated.operator = availableOps[0].value
        }

        return updated
      }
      return c
    })
    setConditions(newConditions)
    onChange(buildJsonLogic(newConditions, logic))
  }

  const handleLogicChange = (newLogic: 'and' | 'or') => {
    setLogic(newLogic)
    onChange(buildJsonLogic(conditions, newLogic))
  }

  const jsonOutput = buildJsonLogic(conditions, logic)

  return (
    <Box>
      <Stack spacing={2}>
        {/* Header */}
        <Box display="flex" justifyContent="space-between" alignItems="center">
          <Typography variant="h6">Conditions</Typography>
          <Stack direction="row" spacing={1}>
            <Button
              size="small"
              variant={showJson ? 'contained' : 'outlined'}
              onClick={() => setShowJson(!showJson)}
            >
              {showJson ? 'Hide' : 'Show'} JSON
            </Button>
            <Button
              size="small"
              variant="contained"
              startIcon={<AddIcon />}
              onClick={handleAddCondition}
            >
              Add Condition
            </Button>
          </Stack>
        </Box>

        {/* Help text */}
        {conditions.length === 0 && (
          <Alert severity="info">
            Add conditions to filter when alerts should be created. For example: "amount {'>'} 1000 AND currency == usd"
          </Alert>
        )}

        {/* Logic selector (only show if multiple conditions) */}
        {conditions.length > 1 && (
          <Box>
            <Typography variant="body2" color="text.secondary" gutterBottom>
              Condition Logic
            </Typography>
            <Stack direction="row" spacing={1}>
              <Chip
                label="AND (all must match)"
                onClick={() => handleLogicChange('and')}
                color={logic === 'and' ? 'primary' : 'default'}
                variant={logic === 'and' ? 'filled' : 'outlined'}
              />
              <Chip
                label="OR (any can match)"
                onClick={() => handleLogicChange('or')}
                color={logic === 'or' ? 'primary' : 'default'}
                variant={logic === 'or' ? 'filled' : 'outlined'}
              />
            </Stack>
          </Box>
        )}

        {/* Conditions list */}
        {conditions.map((condition, index) => {
          const fieldInfo = FIELD_OPTIONS.find((f) => f.value === condition.field)
          const fieldType = fieldInfo?.type || 'string'
          const availableOperators = OPERATORS[fieldType as keyof typeof OPERATORS]

          return (
            <Card key={condition.id} variant="outlined">
              <CardContent>
                <Stack spacing={2}>
                  {/* Condition number */}
                  {conditions.length > 1 && (
                    <Box display="flex" justifyContent="space-between" alignItems="center">
                      <Chip
                        label={`Condition ${index + 1}`}
                        size="small"
                        color="primary"
                        variant="outlined"
                      />
                      <IconButton
                        size="small"
                        onClick={() => handleRemoveCondition(condition.id)}
                        color="error"
                      >
                        <DeleteIcon fontSize="small" />
                      </IconButton>
                    </Box>
                  )}

                  <Stack direction="row" spacing={2} alignItems="flex-start">
                    {/* Field selector */}
                    <FormControl sx={{ flex: 2 }}>
                      <InputLabel>Field</InputLabel>
                      <Select
                        value={condition.field}
                        label="Field"
                        onChange={(e) => handleUpdateCondition(condition.id, 'field', e.target.value)}
                      >
                        {FIELD_OPTIONS.map((field) => (
                          <MenuItem key={field.value} value={field.value}>
                            <Box>
                              <Typography variant="body2">{field.label}</Typography>
                              {field.example && (
                                <Typography variant="caption" color="text.secondary">
                                  Example: {field.example}
                                </Typography>
                              )}
                            </Box>
                          </MenuItem>
                        ))}
                      </Select>
                    </FormControl>

                    {/* Operator selector */}
                    <FormControl sx={{ minWidth: 120, flex: 0.8 }}>
                      <InputLabel>Operator</InputLabel>
                      <Select
                        value={condition.operator}
                        label="Operator"
                        onChange={(e) => handleUpdateCondition(condition.id, 'operator', e.target.value)}
                      >
                        {availableOperators.map((op) => (
                          <MenuItem key={op.value} value={op.value}>
                            {op.label}
                          </MenuItem>
                        ))}
                      </Select>
                    </FormControl>

                    {/* Value input */}
                    <TextField
                      sx={{ flex: 1.5 }}
                      label="Value"
                      type={fieldType === 'number' ? 'number' : 'text'}
                      value={condition.value}
                      onChange={(e) => handleUpdateCondition(condition.id, 'value', e.target.value)}
                      helperText={
                        condition.operator === 'in'
                          ? 'Enter comma-separated values: visa, mastercard'
                          : fieldInfo?.example
                      }
                    />

                    {/* Remove button (single row) */}
                    {conditions.length === 1 && (
                      <IconButton
                        onClick={() => handleRemoveCondition(condition.id)}
                        color="error"
                      >
                        <DeleteIcon />
                      </IconButton>
                    )}
                  </Stack>
                </Stack>
              </CardContent>
            </Card>
          )
        })}

        {/* JSON output (when shown) */}
        {showJson && (
          <Card variant="outlined">
            <CardContent>
              <Box display="flex" justifyContent="space-between" alignItems="center" mb={1}>
                <Typography variant="subtitle2" color="text.secondary">
                  Generated JsonLogic
                </Typography>
                <IconButton
                  size="small"
                  onClick={() => {
                    navigator.clipboard.writeText(JSON.stringify(jsonOutput, null, 2))
                  }}
                  title="Copy to clipboard"
                >
                  <CopyIcon fontSize="small" />
                </IconButton>
              </Box>
              <Box
                component="pre"
                sx={{
                  bgcolor: 'grey.100',
                  p: 2,
                  borderRadius: 1,
                  overflow: 'auto',
                  fontSize: '0.875rem',
                }}
              >
                {JSON.stringify(jsonOutput, null, 2)}
              </Box>
            </CardContent>
          </Card>
        )}
      </Stack>
    </Box>
  )
}

// Helper function to parse JsonLogic back to conditions (basic implementation)
function parseJsonLogicToConditions(jsonLogic: Record<string, any>): Condition[] {
  const conditions: Condition[] = []

  // Handle simple case: {">": [{"var": "amount"}, 1000]}
  const operators = ['>', '>=', '<', '<=', '==', '!=', 'in']
  for (const op of operators) {
    if (jsonLogic[op]) {
      const [varObj, value] = jsonLogic[op]
      if (varObj?.var) {
        conditions.push({
          id: Date.now().toString(),
          field: varObj.var,
          operator: op,
          value: Array.isArray(value) ? value.join(', ') : value,
        })
      }
      return conditions
    }
  }

  // Handle AND/OR: {"and": [...]}
  if (jsonLogic.and || jsonLogic.or) {
    const condArray = jsonLogic.and || jsonLogic.or
    if (Array.isArray(condArray)) {
      condArray.forEach((cond, idx) => {
        for (const op of operators) {
          if (cond[op]) {
            const [varObj, value] = cond[op]
            if (varObj?.var) {
              conditions.push({
                id: `${Date.now()}-${idx}`,
                field: varObj.var,
                operator: op,
                value: Array.isArray(value) ? value.join(', ') : value,
              })
            }
          }
        }
      })
    }
  }

  return conditions
}
