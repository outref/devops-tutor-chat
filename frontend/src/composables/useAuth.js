import { ref, computed } from 'vue'

const API_BASE = import.meta.env.VITE_API_BASE_URL || 'http://localhost:8000'

// Global auth state
const user = ref(null)
const credentials = ref(null) // { username, password }
const isLoading = ref(false)
const error = ref(null)

const isAuthenticated = computed(() => !!user.value && !!credentials.value)

const useAuth = () => {
  const setError = (message) => {
    error.value = message
    setTimeout(() => {
      error.value = null
    }, 5000)
  }

  const setCredentials = (username, password) => {
    credentials.value = { username, password }
    // Store in sessionStorage for persistence
    sessionStorage.setItem('auth_credentials', JSON.stringify({ username, password }))
  }

  const clearCredentials = () => {
    user.value = null
    credentials.value = null
    sessionStorage.removeItem('auth_credentials')
  }

  const getAuthHeaders = () => {
    if (!credentials.value) return {}
    
    const encoded = btoa(`${credentials.value.username}:${credentials.value.password}`)
    return {
      'Authorization': `Basic ${encoded}`
    }
  }

  const register = async (username, password) => {
    if (username.length < 3) {
      setError('Username must be at least 3 characters long')
      return false
    }
    
    if (password.length < 4) {
      setError('Password must be at least 4 characters long')
      return false
    }

    isLoading.value = true
    error.value = null

    try {
      const response = await fetch(`${API_BASE}/api/auth/register`, {
        method: 'POST',
        headers: {
          'Content-Type': 'application/json',
          ...getAuthHeaders()
        },
        body: JSON.stringify({ username, password })
      })

      const data = await response.json()

      if (!response.ok) {
        throw new Error(data.detail || 'Registration failed')
      }

      // After successful registration, set credentials and user
      setCredentials(username, password)
      user.value = data
      return true

    } catch (err) {
      setError(err.message)
      return false
    } finally {
      isLoading.value = false
    }
  }

  const login = async (username, password) => {
    if (!username || !password) {
      setError('Username and password are required')
      return false
    }

    isLoading.value = true
    error.value = null

    try {
      const tempCredentials = { username, password }
      const encoded = btoa(`${tempCredentials.username}:${tempCredentials.password}`)
      
      const response = await fetch(`${API_BASE}/api/auth/login`, {
        method: 'POST',
        headers: {
          'Authorization': `Basic ${encoded}`,
          'Content-Type': 'application/json'
        }
      })

      const data = await response.json()

      if (!response.ok) {
        throw new Error(data.detail || 'Login failed')
      }

      // Set credentials and user data
      setCredentials(username, password)
      user.value = data
      return true

    } catch (err) {
      setError(err.message)
      return false
    } finally {
      isLoading.value = false
    }
  }

  const logout = () => {
    clearCredentials()
  }

  const checkAuth = async () => {
    // Check if we have stored credentials
    const stored = sessionStorage.getItem('auth_credentials')
    if (!stored) return false

    try {
      const storedCredentials = JSON.parse(stored)
      credentials.value = storedCredentials
      
      // Verify credentials are still valid
      const encoded = btoa(`${storedCredentials.username}:${storedCredentials.password}`)
      const response = await fetch(`${API_BASE}/api/auth/me`, {
        headers: {
          'Authorization': `Basic ${encoded}`
        }
      })

      if (response.ok) {
        const userData = await response.json()
        user.value = userData
        return true
      } else {
        // Credentials are invalid, clear them
        clearCredentials()
        return false
      }
    } catch (err) {
      clearCredentials()
      return false
    }
  }

  return {
    // State
    user: computed(() => user.value),
    isAuthenticated,
    isLoading: computed(() => isLoading.value),
    error: computed(() => error.value),
    
    // Methods
    register,
    login,
    logout,
    checkAuth,
    getAuthHeaders,
    setError
  }
}

export { useAuth }
