<template>
  <!-- Authentication required -->
  <AuthForm
    v-if="!isAuthenticated"
    @authenticated="handleAuthenticated"
  />
  
  <!-- Main app (authenticated) -->
  <div v-else class="flex h-screen bg-kk-bg-dark">
    <!-- Sidebar -->
    <ConversationSidebar 
      :conversations="conversations"
      :currentConversationId="currentConversationId"
      @select-conversation="handleSelectConversation"
      @new-conversation="handleNewConversation"
      @delete-conversation="handleDeleteConversation"
    />
    
    <!-- Main chat area -->
    <div class="flex-1 flex flex-col">
      <!-- Header -->
      <ChatHeader 
        :topic="currentTopic"
        :isNewConversation="!currentConversationId"
        @logout="handleLogout"
      />
      
      <!-- Error message -->
      <div v-if="errorMessage" class="mx-6 mb-4">
        <div class="max-w-3xl mx-auto p-4 bg-red-900/20 border border-red-500/30 rounded-lg">
          <div class="flex items-start gap-3">
            <svg class="w-5 h-5 text-red-400 flex-shrink-0 mt-0.5" fill="none" stroke="currentColor" viewBox="0 0 24 24">
              <path stroke-linecap="round" stroke-linejoin="round" stroke-width="2" d="M12 8v4m0 4h.01M21 12a9 9 0 11-18 0 9 9 0 0118 0z" />
            </svg>
            <div class="flex-1">
              <p class="text-red-300 text-sm">{{ errorMessage }}</p>
              <button 
                @click="clearError" 
                class="text-red-400 hover:text-red-300 text-xs mt-2 underline"
                tabindex="0"
                aria-label="Dismiss error"
              >
                Dismiss
              </button>
            </div>
          </div>
        </div>
      </div>

      <!-- Messages area -->
      <MessageList 
        :messages="messages"
        :isLoading="isLoading"
        ref="messageList"
        @suggest-topic="handleSendMessage"
      />
      
      <!-- Input area -->
      <ChatInput 
        :disabled="isLoading"
        @send-message="handleSendMessage"
      />
    </div>
  </div>
</template>

<script setup>
import { ref, onMounted, nextTick } from 'vue'
import ConversationSidebar from './components/ConversationSidebar.vue'
import ChatHeader from './components/ChatHeader.vue'
import MessageList from './components/MessageList.vue'
import ChatInput from './components/ChatInput.vue'
import AuthForm from './components/AuthForm.vue'
import { useChat } from './composables/useChat.js'
import { useConversations } from './composables/useConversations.js'
import { useAuth } from './composables/useAuth.js'

// Composables
const { sendMessage, getMessages, isLoading } = useChat()
const { conversations, loadConversations, deleteConversation } = useConversations()
const { isAuthenticated, checkAuth } = useAuth()

// State
const messages = ref([])
const currentConversationId = ref(null)
const currentTopic = ref('')
const messageList = ref(null)
const errorMessage = ref('')

// Methods
const handleSendMessage = async (content) => {
  if (!content.trim() || isLoading.value) return
  
  // Clear any previous error
  clearError()
  
  // Add user message to UI immediately
  messages.value.push({
    id: Date.now().toString(),
    role: 'user',
    content: content,
    created_at: new Date().toISOString()
  })
  
  // Scroll to bottom
  await nextTick()
  messageList.value?.scrollToBottom()
  
  try {
    // Send message to backend
    const response = await sendMessage(content, currentConversationId.value)
    
    // Update conversation ID if this was a new conversation
    if (!currentConversationId.value) {
      currentConversationId.value = response.conversation_id
      currentTopic.value = response.topic
      
      // Reload conversations list
      await loadConversations()
    }
    
    // Add assistant response
    messages.value.push({
      id: Date.now().toString() + '-assistant',
      role: 'assistant',
      content: response.response,
      created_at: new Date().toISOString()
    })
    
    // Scroll to bottom
    await nextTick()
    messageList.value?.scrollToBottom()
  } catch (error) {
    console.error('Error sending message:', error)
    
    // Remove the user message if there was an error
    messages.value.pop()
    
    // Show error message to user
    errorMessage.value = error.message || 'An error occurred while sending your message. Please try again.'
    
    // Scroll to top to show error if needed
    await nextTick()
    messageList.value?.scrollToBottom()
  }
}

const clearError = () => {
  errorMessage.value = ''
}

const handleSelectConversation = async (conversationId) => {
  if (conversationId === currentConversationId.value) return
  
  currentConversationId.value = conversationId
  clearError()
  
  // Find conversation to get topic
  const conversation = conversations.value.find(c => c.id === conversationId)
  if (conversation) {
    currentTopic.value = conversation.topic
  }
  
  // Load messages
  try {
    const loadedMessages = await getMessages(conversationId)
    messages.value = loadedMessages
    
    // Scroll to bottom after loading
    await nextTick()
    messageList.value?.scrollToBottom()
  } catch (error) {
    console.error('Error loading messages:', error)
    messages.value = []
    errorMessage.value = 'Error loading conversation. Please try again.'
  }
}

const handleNewConversation = () => {
  currentConversationId.value = null
  currentTopic.value = ''
  messages.value = []
  clearError()
}

const handleDeleteConversation = async (conversationId) => {
  try {
    await deleteConversation(conversationId)
    
    // If we deleted the current conversation, start a new one
    if (conversationId === currentConversationId.value) {
      handleNewConversation()
    }
    
    // Reload conversations
    await loadConversations()
  } catch (error) {
    console.error('Error deleting conversation:', error)
  }
}

const handleAuthenticated = async () => {
  // Load conversations after authentication
  await loadConversations()
  
  // If there are conversations, load the most recent one
  if (conversations.value.length > 0) {
    await handleSelectConversation(conversations.value[0].id)
  }
}

const handleLogout = () => {
  // Clear current state
  currentConversationId.value = null
  currentTopic.value = ''
  messages.value = []
  conversations.value = []
}

// Lifecycle
onMounted(async () => {
  // Check if user is already authenticated
  const isAuth = await checkAuth()
  if (isAuth) {
    await handleAuthenticated()
  }
})
</script>
