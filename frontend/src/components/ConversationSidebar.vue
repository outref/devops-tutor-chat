<template>
  <div class="w-64 bg-gray-900 border-r border-gray-800 flex flex-col">
    <!-- Header -->
    <div class="p-4 border-b border-gray-800">
      <button
        @click="$emit('new-conversation')"
        class="w-full btn-primary flex items-center justify-center gap-2"
        tabindex="0"
        aria-label="Start new conversation"
      >
        <svg class="w-5 h-5" fill="none" stroke="currentColor" viewBox="0 0 24 24">
          <path stroke-linecap="round" stroke-linejoin="round" stroke-width="2" d="M12 4v16m8-8H4" />
        </svg>
        New Chat
      </button>
    </div>
    
    <!-- Conversations list -->
    <div class="flex-1 overflow-y-auto custom-scrollbar">
      <div class="p-2">
        <div
          v-for="conversation in conversations"
          :key="conversation.id"
          class="group relative mb-1"
        >
          <button
            @click="$emit('select-conversation', conversation.id)"
            :class="[
              'w-full text-left p-3 rounded-lg transition-colors',
              currentConversationId === conversation.id
                ? 'bg-kk-slate-800 text-kk-text'
                : 'hover:bg-gray-800 text-gray-400 hover:text-kk-text'
            ]"
            tabindex="0"
            :aria-label="`Select conversation: ${conversation.topic}`"
          >
            <div class="flex items-start gap-2">
              <svg class="w-4 h-4 mt-0.5 flex-shrink-0" fill="none" stroke="currentColor" viewBox="0 0 24 24">
                <path stroke-linecap="round" stroke-linejoin="round" stroke-width="2" d="M8 10h.01M12 10h.01M16 10h.01M9 16H5a2 2 0 01-2-2V6a2 2 0 012-2h14a2 2 0 012 2v8a2 2 0 01-2 2h-5l-5 5v-5z" />
              </svg>
              <div class="flex-1 min-w-0">
                <p class="text-sm font-medium truncate">{{ formatTopic(conversation.topic) }}</p>
                <p class="text-xs text-gray-500">{{ formatDate(conversation.updated_at) }}</p>
              </div>
            </div>
          </button>
          
          <!-- Delete button -->
          <button
            @click.stop="handleDelete(conversation.id)"
            class="absolute right-2 top-1/2 -translate-y-1/2 opacity-0 group-hover:opacity-100 transition-opacity p-1 hover:bg-gray-700 rounded"
            tabindex="0"
            :aria-label="`Delete conversation: ${conversation.topic}`"
          >
            <svg class="w-4 h-4 text-gray-400 hover:text-red-400" fill="none" stroke="currentColor" viewBox="0 0 24 24">
              <path stroke-linecap="round" stroke-linejoin="round" stroke-width="2" d="M19 7l-.867 12.142A2 2 0 0116.138 21H7.862a2 2 0 01-1.995-1.858L5 7m5 4v6m4-6v6m1-10V4a1 1 0 00-1-1h-4a1 1 0 00-1 1v3M4 7h16" />
            </svg>
          </button>
        </div>
        
        <p v-if="conversations.length === 0" class="text-center text-gray-500 mt-8">
          No conversations yet
        </p>
      </div>
    </div>
    
    <!-- Footer -->
    <div class="p-4 border-t border-gray-800 text-xs text-gray-500">
      <p>DevOps Learning Assistant</p>
    </div>
    
    <!-- Delete confirmation modal -->
    <Modal
      :isVisible="showDeleteModal"
      title="Delete Conversation"
      :message="`Are you sure you want to delete this conversation? This action cannot be undone.`"
      confirmText="Delete"
      cancelText="Cancel"
      variant="danger"
      @confirm="confirmDelete"
      @cancel="cancelDelete"
      @close="cancelDelete"
    />
  </div>
</template>

<script setup>
import { defineProps, defineEmits, ref } from 'vue'
import Modal from './Modal.vue'

const props = defineProps({
  conversations: {
    type: Array,
    required: true
  },
  currentConversationId: {
    type: String,
    default: null
  }
})

const emit = defineEmits(['select-conversation', 'new-conversation', 'delete-conversation'])

const showDeleteModal = ref(false)
const conversationToDelete = ref(null)

const formatTopic = (topic) => {
  if (!topic || topic === 'pending') return 'New Chat'
  return topic.charAt(0).toUpperCase() + topic.slice(1).replace(/-/g, ' ')
}

const formatDate = (dateString) => {
  const date = new Date(dateString)
  const now = new Date()
  const diffMs = now - date
  const diffMins = Math.floor(diffMs / 60000)
  
  if (diffMins < 1) return 'Just now'
  if (diffMins < 60) return `${diffMins}m ago`
  if (diffMins < 1440) return `${Math.floor(diffMins / 60)}h ago`
  return date.toLocaleDateString()
}

const handleDelete = (conversationId) => {
  conversationToDelete.value = conversationId
  showDeleteModal.value = true
}

const confirmDelete = () => {
  if (conversationToDelete.value) {
    emit('delete-conversation', conversationToDelete.value)
    conversationToDelete.value = null
  }
  showDeleteModal.value = false
}

const cancelDelete = () => {
  conversationToDelete.value = null
  showDeleteModal.value = false
}
</script>
