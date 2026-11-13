// The only file that calls fetch(). Every service uses it.
export const API_BASE_URL = (import.meta.env.VITE_API_BASE_URL || 'http://127.0.0.1:8000').replace(/\/+$/, '')

const TOKEN_KEY = 'crisislens_token'
const TIMEOUT_MS = 15000

export class ApiError extends Error {
  constructor({ code, message, status = 0, details = null }) {
    super(message)
    this.name = 'ApiError'
    this.code = code
    this.status = status
    this.details = details
  }
}

// Authentication token support (used once Member 2 adds login)
export function getToken() {
  try { return localStorage.getItem(TOKEN_KEY) } catch { return null }
}
export function setToken(token) {
  try {
    if (token) localStorage.setItem(TOKEN_KEY, token)
    else localStorage.removeItem(TOKEN_KEY)
  } catch { /* ignore */ }
}

function buildQuery(params) {
  const search = new URLSearchParams()
  Object.entries(params || {}).forEach(([key, value]) => {
    if (value !== undefined && value !== null && value !== '' && value !== 'all') {
      search.append(key, String(value))
    }
  })
  const text = search.toString()
  return text ? `?${text}` : ''
}

// Turns any error body into the contract's error shape
function toApiError(status, json) {
  if (json?.error?.message) {
    return new ApiError({ code: json.error.code || 'server_error', message: json.error.message, status, details: json.error.details })
  }
  if (json?.detail) {
    // FastAPI's default error format (Member 2 should convert it, see contract)
    const message = typeof json.detail === 'string' ? json.detail : 'Request failed validation'
    return new ApiError({ code: status === 422 ? 'validation_error' : 'server_error', message, status, details: json.detail })
  }
  return new ApiError({ code: 'server_error', message: `Request failed with status ${status}`, status })
}

async function request(method, path, { params, body } = {}) {
  const controller = new AbortController()
  const timer = setTimeout(() => controller.abort(), TIMEOUT_MS)
  const headers = { Accept: 'application/json' }
  if (body !== undefined) headers['Content-Type'] = 'application/json'
  const token = getToken()
  if (token) headers.Authorization = `Bearer ${token}`

  let response
  try {
    response = await fetch(`${API_BASE_URL}${path}${buildQuery(params)}`, {
      method,
      headers,
      body: body !== undefined ? JSON.stringify(body) : undefined,
      signal: controller.signal,
    })
  } catch (err) {
    if (err.name === 'AbortError') {
      throw new ApiError({ code: 'timeout', message: `The backend did not answer within ${TIMEOUT_MS / 1000} seconds.` })
    }
    throw new ApiError({
      code: 'network_error',
      message: `Cannot reach the backend at ${API_BASE_URL}. Check that the server is running and that CORS allows ${window.location.origin}.`,
    })
  } finally {
    clearTimeout(timer)
  }

  if (response.status === 204) return null

  const text = await response.text()
  let json = null
  if (text) {
    try {
      json = JSON.parse(text)
    } catch {
      throw new ApiError({ code: 'invalid_json', message: 'The backend returned a response that is not valid JSON.', status: response.status })
    }
  }

  if (!response.ok) throw toApiError(response.status, json)
  return json
}

export const api = {
  get: (path, options) => request('GET', path, options),
  post: (path, body, options) => request('POST', path, { ...options, body }),
  patch: (path, body, options) => request('PATCH', path, { ...options, body }),
}

// Used by the header's Live switch. Always calls the real server.
export async function checkConnection() {
  await api.get('/incidents')
  return true
}