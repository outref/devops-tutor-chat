import { ref } from 'vue'
import { useAuth } from './useAuth.js'

const API_URL = import.meta.env.VITE_API_URL || 'http://localhost:8000'

export const useConversations = () => {
  const { getAuthHeaders } = useAuth()
  const conversations = ref([])
  const isLoading = ref(false)
  
  const loadConversations = async () => {
    isLoading.value = true
    
    try {
      const response = await fetch(`${API_URL}/api/conversations/?limit=20`, {
        headers: {
          ...getAuthHeaders()
        }
      })
      
      if (!response.ok) {
        const error = await response.json()
        throw new Error(error.detail || 'Failed to load conversations')
      }
      
      conversations.value = await response.json()
    } catch (error) {
      console.error('Error loading conversations:', error)
      conversations.value = []
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
  
  return {
    conversations,
    isLoading,
    loadConversations,
    deleteConversation
  }
}
