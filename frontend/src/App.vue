<template>
  <div class="flex h-screen bg-kk-bg-dark">
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
      />
      
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
import { useChat } from './composables/useChat.js'
import { useConversations } from './composables/useConversations.js'

// Composables
const { sendMessage, getMessages, isLoading } = useChat()
const { conversations, loadConversations, deleteConversation } = useConversations()

// State
const messages = ref([])
const currentConversationId = ref(null)
const currentTopic = ref('')
const messageList = ref(null)

// Methods
const handleSendMessage = async (content) => {
  if (!content.trim() || isLoading.value) return
  
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
  }
}

const handleSelectConversation = async (conversationId) => {
  if (conversationId === currentConversationId.value) return
  
  currentConversationId.value = conversationId
  
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
  }
}

const handleNewConversation = () => {
  currentConversationId.value = null
  currentTopic.value = ''
  messages.value = []
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

// Lifecycle
onMounted(async () => {
  await loadConversations()
  
  // If there are conversations, load the most recent one
  if (conversations.value.length > 0) {
    await handleSelectConversation(conversations.value[0].id)
  }
})
</script>
