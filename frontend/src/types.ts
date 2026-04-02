export type InvoiceStatus = 'draft' | 'sent' | 'paid' | 'overdue' | 'overdue_paid'

export interface Business {
  id: number
  name: string
  email: string
  phone?: string | null
  address_line1: string
  address_line2?: string | null
  city_state_zip: string
  tax_id?: string | null
  logo_url?: string | null
  bank_name: string
  account_number: string
  bsb?: string | null
  payment_terms: string
  paypal_url?: string | null
  stripe_enabled: boolean
  stripe_webhook_ready: boolean
  payment_currency: string
  created_at: string
  updated_at: string
}

export interface BusinessSummary {
  name: string
  email: string
  phone?: string | null
  address_line1: string
  address_line2?: string | null
  city_state_zip: string
  logo_url?: string | null
  bank_name: string
  account_number: string
  bsb?: string | null
  payment_terms: string
  paypal_url?: string | null
  stripe_enabled: boolean
  stripe_webhook_ready: boolean
  payment_currency: string
}

export interface Client {
  id: number
  name: string
  email: string
  phone?: string | null
  address_line1: string
  address_line2?: string | null
  city_state_zip: string
  tax_id?: string | null
  created_at: string
  updated_at: string
}

export interface ClientSummary {
  id: number
  name: string
  email: string
}

export interface LineItem {
  id: number
  invoice_id: number
  seq_order: number
  description: string
  details?: string | null
  qty: string
  rate: string
  adjustment_pct: string
  sub_total: string
}

export interface Invoice {
  id: number
  invoice_number: string
  order_number?: string | null
  client_id: number
  invoice_date: string
  due_date: string
  subtotal: string
  tax_rate_pct: string
  tax_amount: string
  total: string
  paid_amount: string
  status: InvoiceStatus
  notes?: string | null
  line_items: LineItem[]
  client?: ClientSummary | null
  business?: BusinessSummary | null
  public_url?: string | null
  amount_due?: string | null
  created_at: string
  updated_at: string
}

export interface Payment {
  id: number
  invoice_id: number
  date: string
  amount: string
  method: string
  transaction_id?: string | null
  notes?: string | null
  created_at: string
}

export interface DashboardSummary {
  total_invoices: number
  total_revenue: string
  paid_invoices: number
  paid_amount: string
  outstanding_amount: string
  overdue_invoices: number
  overdue_amount: string
}

export interface DashboardData {
  summary: DashboardSummary
  by_status: Record<string, number>
  monthly_revenue: Array<{ month: number; label: string; amount: string }>
  top_clients: Array<{ client_id: number; client_name: string; amount: string }>
  recent_payments: Array<{
    id: number
    invoice_id: number
    invoice_number: string
    client_name: string
    date: string
    amount: string
    method: string
  }>
}

export interface ClientPayload {
  name: string
  email: string
  phone?: string
  address_line1: string
  address_line2?: string
  city_state_zip: string
  tax_id?: string
}

export interface InvoiceLineItemPayload {
  description: string
  details?: string
  qty: string
  rate: string
  adjustment_pct: string
}

export interface InvoicePayload {
  client_id: number
  order_number?: string
  invoice_date: string
  due_date: string
  tax_rate_pct: string
  notes?: string
  line_items: InvoiceLineItemPayload[]
}

export interface InvoiceSendResponse {
  invoice_id: number
  invoice_number: string
  status: InvoiceStatus
  payment_url: string
  email: {
    status: string
    reason?: string
  }
}

export interface PaymentPayload {
  invoice_id: number
  date: string
  amount: string
  method: string
  transaction_id?: string
  notes?: string
}

export interface StripeCheckoutSessionResponse {
  url: string
}

export interface LoginPayload {
  username: string
  password: string
}

export interface LoginResponse {
  access_token: string
  token_type: 'bearer'
  username: string
  last_login?: string | null
}

export interface AdminProfile {
  username: string
  last_login?: string | null
  updated_at: string
}
