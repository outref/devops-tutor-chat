<template>
  <div class="min-h-screen bg-kk-bg-dark flex items-center justify-center px-4">
    <div class="max-w-md w-full">
      <!-- Header -->
      <div class="text-center mb-8">
        <h1 class="text-3xl font-bold text-kk-text mb-2">
          DevOps Learning Assistant
        </h1>
        <p class="text-gray-400">
          {{ isLoginMode ? 'Sign in to continue your learning' : 'Create an account to get started' }}
        </p>
      </div>

      <!-- Auth Form -->
      <div class="bg-gray-900/50 border border-gray-800 rounded-lg p-6">
        <form @submit.prevent="handleSubmit">
          <!-- Toggle Mode -->
          <div class="flex bg-gray-800/50 rounded-lg p-1 mb-6">
            <button
              type="button"
              @click="isLoginMode = true"
              :class="[
                'flex-1 py-2 px-4 rounded-md transition-colors text-sm font-medium',
                isLoginMode
                  ? 'bg-kk-purple text-white'
                  : 'text-gray-400 hover:text-kk-text'
              ]"
              tabindex="0"
              aria-label="Switch to login mode"
            >
              Sign In
            </button>
            <button
              type="button"
              @click="isLoginMode = false"
              :class="[
                'flex-1 py-2 px-4 rounded-md transition-colors text-sm font-medium',
                !isLoginMode
                  ? 'bg-kk-purple text-white'
                  : 'text-gray-400 hover:text-kk-text'
              ]"
              tabindex="0"
              aria-label="Switch to register mode"
            >
              Sign Up
            </button>
          </div>

          <!-- Error Message -->
          <div
            v-if="error"
            class="bg-red-900/20 border border-red-800 rounded-lg p-3 mb-4"
          >
            <p class="text-red-400 text-sm">{{ error }}</p>
          </div>

          <!-- Username Field -->
          <div class="mb-4">
            <label for="username" class="block text-sm font-medium text-kk-text mb-2">
              Username
            </label>
            <input
              id="username"
              v-model="username"
              type="text"
              class="input-primary w-full"
              placeholder="Enter your username"
              :minlength="3"
              required
              :disabled="isLoading"
              tabindex="0"
              @keydown.enter="handleSubmit"
            />
            <p class="text-xs text-gray-500 mt-1">Minimum 3 characters</p>
          </div>

          <!-- Password Field -->
          <div class="mb-6">
            <label for="password" class="block text-sm font-medium text-kk-text mb-2">
              Password
            </label>
            <input
              id="password"
              v-model="password"
              type="password"
              class="input-primary w-full"
              placeholder="Enter your password"
              :minlength="4"
              required
              :disabled="isLoading"
              tabindex="0"
              @keydown.enter="handleSubmit"
            />
            <p class="text-xs text-gray-500 mt-1">Minimum 4 characters</p>
          </div>

          <!-- Submit Button -->
          <button
            type="submit"
            class="w-full btn-primary"
            :disabled="isLoading || !username || !password"
            tabindex="0"
            :aria-label="isLoginMode ? 'Sign in' : 'Create account'"
          >
            <div class="flex items-center justify-center">
              <svg
                v-if="isLoading"
                class="animate-spin -ml-1 mr-2 h-4 w-4 text-white"
                fill="none"
                viewBox="0 0 24 24"
              >
                <circle
                  class="opacity-25"
                  cx="12"
                  cy="12"
                  r="10"
                  stroke="currentColor"
                  stroke-width="4"
                ></circle>
                <path
                  class="opacity-75"
                  fill="currentColor"
                  d="M4 12a8 8 0 018-8V0C5.373 0 0 5.373 0 12h4zm2 5.291A7.962 7.962 0 014 12H0c0 3.042 1.135 5.824 3 7.938l3-2.647z"
                ></path>
              </svg>
              {{ isLoading ? 'Please wait...' : (isLoginMode ? 'Sign In' : 'Create Account') }}
            </div>
          </button>
        </form>

        <!-- Info Text -->
        <div class="mt-6 text-center">
          <p class="text-xs text-gray-500">
            {{ isLoginMode ? 'New to DevOps Learning?' : 'Already have an account?' }}
            <button
              type="button"
              @click="isLoginMode = !isLoginMode"
              class="text-kk-purple hover:text-kk-teal transition-colors ml-1"
              tabindex="0"
              :aria-label="isLoginMode ? 'Switch to register' : 'Switch to login'"
            >
              {{ isLoginMode ? 'Create an account' : 'Sign in instead' }}
            </button>
          </p>
        </div>
      </div>

      <!-- Footer -->
      <div class="mt-8 text-center">
        <p class="text-xs text-gray-500">
          Learn Kubernetes, Docker, CI/CD, AWS, GCloud, and more!
        </p>
      </div>
    </div>
  </div>
</template>

<script setup>
import { ref, computed } from 'vue'
import { useAuth } from '../composables/useAuth.js'

const { register, login, isLoading, error } = useAuth()

// Component state
const isLoginMode = ref(true)
const username = ref('')
const password = ref('')

// Emit events
const emit = defineEmits(['authenticated'])

const handleSubmit = async () => {
  if (!username.value || !password.value) return
  
  let success = false
  
  if (isLoginMode.value) {
    success = await login(username.value, password.value)
  } else {
    success = await register(username.value, password.value)
  }
  
  if (success) {
    emit('authenticated')
  }
}
</script>
