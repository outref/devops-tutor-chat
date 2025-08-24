import { ref } from 'vue'
import { useAuth } from './useAuth.js'

const API_URL = import.meta.env.VITE_API_URL || 'http://localhost:8000'

export const useChat = () => {
  const { getAuthHeaders } = useAuth()
  const isLoading = ref(false)
  
  const sendMessage = async (message, conversationId = null) => {
    isLoading.value = true
    
    try {
      const response = await fetch(`${API_URL}/api/chat/send`, {
        method: 'POST',
        headers: {
          'Content-Type': 'application/json',
          ...getAuthHeaders()
        },
        body: JSON.stringify({
          message,
          conversation_id: conversationId
        })
      })
      
      if (!response.ok) {
        const error = await response.json()
        throw new Error(error.detail || 'Failed to send message')
      }
      
      return await response.json()
    } catch (error) {
      console.error('Error sending message:', error)
      throw error
    } finally {
      isLoading.value = false
    }
  }
  
  const getMessages = async (conversationId) => {
    try {
      const response = await fetch(`${API_URL}/api/chat/messages/${conversationId}`, {
        headers: {
          ...getAuthHeaders()
        }
      })
      
      if (!response.ok) {
        const error = await response.json()
        throw new Error(error.detail || 'Failed to fetch messages')
      }
      
      return await response.json()
    } catch (error) {
      console.error('Error fetching messages:', error)
      throw error
    }
  }
  
  return {
    sendMessage,
    getMessages,
    isLoading
  }
}
