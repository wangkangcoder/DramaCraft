import { reactive } from 'vue'

const AUTH_STORAGE_KEY = 'screenplay_auth_v1'

function loadUser() {
  try {
    const raw = localStorage.getItem(AUTH_STORAGE_KEY)
    if (!raw) return null
    const parsed = JSON.parse(raw)
    if (!parsed?.token || !parsed?.user) return null
    return parsed
  } catch {
    return null
  }
}

const cached = loadUser()

export const authState = reactive({
  token: cached?.token || '',
  user: cached?.user || null,
})

export const isAuthenticated = () => !!authState.token

export function loginSuccess(token, user, rememberMe) {
  authState.token = token
  authState.user = user

  if (rememberMe) {
    localStorage.setItem(AUTH_STORAGE_KEY, JSON.stringify({ token, user }))
  } else {
    localStorage.removeItem(AUTH_STORAGE_KEY)
  }
}

export function logout() {
  authState.token = ''
  authState.user = null
  localStorage.removeItem(AUTH_STORAGE_KEY)
}
