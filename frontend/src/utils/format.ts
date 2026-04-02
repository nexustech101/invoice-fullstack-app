export function formatCurrency(value: number | string): string {
  const amount = typeof value === 'number' ? value : Number.parseFloat(value || '0')
  return new Intl.NumberFormat('en-US', {
    style: 'currency',
    currency: 'USD',
    maximumFractionDigits: 2,
  }).format(Number.isFinite(amount) ? amount : 0)
}

export function formatDate(value: string): string {
  if (!value) return '--'
  return new Intl.DateTimeFormat('en-US', {
    month: 'short',
    day: 'numeric',
    year: 'numeric',
  }).format(new Date(value))
}

export function statusLabel(status: string): string {
  return status.replace('_', ' ')
}
