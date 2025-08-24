import { ref } from 'vue'
import { useAuth } from './useAuth.js'

const API_URL = import.meta.env.VITE_API_URL || 'http://localhost:8000'

// Global state - shared across all component instances
const conversations = ref([])
const isLoading = ref(false)

export const useConversations = () => {
  const { getAuthHeaders } = useAuth()
  
  const loadConversations = async (retryCount = 0) => {
    isLoading.value = true
    
    try {
      const authHeaders = getAuthHeaders()
      
      // If no auth headers and this is the first attempt, wait a bit and retry
      if (Object.keys(authHeaders).length === 0 && retryCount === 0) {
        await new Promise(resolve => setTimeout(resolve, 100))
        return await loadConversations(1)
      }
      
      if (Object.keys(authHeaders).length === 0) {
        throw new Error('No authentication credentials available')
      }
      
      const response = await fetch(`${API_URL}/api/conversations/?limit=20`, {
        headers: {
          ...authHeaders
        }
      })
      
      if (!response.ok) {
        const error = await response.json()
        throw new Error(error.detail || 'Failed to load conversations')
      }
      
      const data = await response.json()
      conversations.value = data
    } catch (error) {
      console.error('Error loading conversations:', error)
      conversations.value = []
      throw error // Re-throw so caller can handle it
    } finally {
      isLoading.value = false
    }
  }
  
  const deleteConversation = async (conversationId) => {
    try {
      const response = await fetch(`${API_URL}/api/conversations/${conversationId}`, {
        method: 'DELETE',
        headers: {
          ...getAuthHeaders()
        }
      })
      
      if (!response.ok) {
        const error = await response.json()
        throw new Error(error.detail || 'Failed to delete conversation')
      }
      
      // Remove from local state
      conversations.value = conversations.value.filter(c => c.id !== conversationId)
    } catch (error) {
      console.error('Error deleting conversation:', error)
      throw error
    }
  }
  
  const clearConversations = () => {
    conversations.value = []
  }
  
  return {
    conversations,
    isLoading,
    loadConversations,
    deleteConversation,
    clearConversations
  }
}
