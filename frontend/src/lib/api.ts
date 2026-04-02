import { AUTH_EXPIRED_EVENT, getSessionToken } from './session'

const API_BASE =
  import.meta.env.VITE_API_BASE_URL?.replace(/\/$/, '') ??
  '/api/v1'

type RequestOptions = RequestInit & {
  auth?: boolean
}

async function request<T>(path: string, init?: RequestOptions): Promise<T> {
  const headers = new Headers(init?.headers)
  const shouldAttachAuth = init?.auth !== false
  const token = shouldAttachAuth ? getSessionToken() : null

  if (token) {
    headers.set('Authorization', `Bearer ${token}`)
  }

  if (init?.body !== undefined && !(init.body instanceof FormData) && !headers.has('Content-Type')) {
    headers.set('Content-Type', 'application/json')
  }

  const response = await fetch(`${API_BASE}${path}`, {
    ...init,
    headers,
  })

  if (response.status === 401) {
    window.dispatchEvent(new Event(AUTH_EXPIRED_EVENT))
  }

  if (!response.ok) {
    let message = `Request failed with status ${response.status}`
    try {
      const data = (await response.json()) as { detail?: string; message?: string }
      message = data.detail ?? data.message ?? message
    } catch {
      // Ignore parse failure and fall back to status message.
    }
    throw new Error(message)
  }

  if (response.status === 204) {
    return undefined as T
  }

  return (await response.json()) as T
}

export const api = {
  get: <T>(path: string, init?: RequestOptions) => request<T>(path, init),
  post: <T>(path: string, body?: unknown, init?: RequestOptions) =>
    request<T>(path, {
      ...init,
      method: 'POST',
      body: body !== undefined ? JSON.stringify(body) : undefined,
    }),
  put: <T>(path: string, body: unknown, init?: RequestOptions) =>
    request<T>(path, {
      ...init,
      method: 'PUT',
      body: JSON.stringify(body),
    }),
  delete: (path: string, init?: RequestOptions) =>
    request<void>(path, {
      ...init,
      method: 'DELETE',
    }),
  baseUrl: API_BASE,
}
