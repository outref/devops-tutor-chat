import { ref } from 'vue'
import axios from 'axios'

const API_URL = import.meta.env.VITE_API_URL || 'http://localhost:8000'

export const useChat = () => {
  const isLoading = ref(false)
  
  const sendMessage = async (message, conversationId = null) => {
    isLoading.value = true
    
    try {
      const response = await axios.post(`${API_URL}/api/chat/send`, {
        message,
        conversation_id: conversationId,
        user_id: 'default_user'
      })
      
      return response.data
    } catch (error) {
      console.error('Error sending message:', error)
      throw error
    } finally {
      isLoading.value = false
    }
  }
  
  const getMessages = async (conversationId) => {
    try {
      const response = await axios.get(`${API_URL}/api/chat/messages/${conversationId}`)
      return response.data
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
