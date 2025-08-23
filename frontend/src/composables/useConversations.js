import { ref } from 'vue'
import axios from 'axios'

const API_URL = import.meta.env.VITE_API_URL || 'http://localhost:8000'

export const useConversations = () => {
  const conversations = ref([])
  const isLoading = ref(false)
  
  const loadConversations = async () => {
    isLoading.value = true
    
    try {
      const response = await axios.get(`${API_URL}/api/conversations/`, {
        params: {
          user_id: 'default_user',
          limit: 20
        }
      })
      
      conversations.value = response.data
    } catch (error) {
      console.error('Error loading conversations:', error)
      conversations.value = []
    } finally {
      isLoading.value = false
    }
  }
  
  const deleteConversation = async (conversationId) => {
    try {
      await axios.delete(`${API_URL}/api/conversations/${conversationId}`)
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
