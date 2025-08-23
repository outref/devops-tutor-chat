<template>
  <div class="border-t border-gray-800 bg-gray-900/50 px-6 py-4">
    <form @submit.prevent="handleSubmit" class="max-w-3xl mx-auto">
      <div class="flex gap-3">
        <textarea
          ref="textareaRef"
          v-model="message"
          @keydown="handleKeyDown"
          :disabled="disabled"
          placeholder="Ask about Kubernetes, Docker, CI/CD, AWS, or any DevOps topic..."
          class="flex-1 input-primary resize-none min-h-[44px] max-h-32"
          rows="1"
          tabindex="0"
          aria-label="Type your message"
        ></textarea>
        
        <button
          type="submit"
          :disabled="disabled || !message.trim()"
          class="btn-primary px-4 flex items-center gap-2"
          tabindex="0"
          aria-label="Send message"
        >
          <span v-if="!disabled">Send</span>
          <span v-else>Sending...</span>
          <svg class="w-4 h-4" fill="none" stroke="currentColor" viewBox="0 0 24 24">
            <path stroke-linecap="round" stroke-linejoin="round" stroke-width="2" d="M12 19l9 2-9-18-9 18 9-2zm0 0v-8" />
          </svg>
        </button>
      </div>
      
      <div class="mt-2 text-xs text-gray-500">
        Press Enter to send, Shift+Enter for new line
      </div>
    </form>
  </div>
</template>

<script setup>
import { ref, watch, nextTick } from 'vue'

const props = defineProps({
  disabled: {
    type: Boolean,
    default: false
  }
})

const emit = defineEmits(['send-message'])

const message = ref('')
const textareaRef = ref(null)

const handleSubmit = () => {
  if (message.value.trim() && !props.disabled) {
    emit('send-message', message.value)
    message.value = ''
    resetTextareaHeight()
  }
}

const handleKeyDown = (event) => {
  if (event.key === 'Enter' && !event.shiftKey) {
    event.preventDefault()
    handleSubmit()
  }
}

const adjustTextareaHeight = () => {
  if (textareaRef.value) {
    textareaRef.value.style.height = 'auto'
    textareaRef.value.style.height = textareaRef.value.scrollHeight + 'px'
  }
}

const resetTextareaHeight = () => {
  if (textareaRef.value) {
    textareaRef.value.style.height = '44px'
  }
}

// Auto-resize textarea as user types
watch(message, () => {
  nextTick(() => {
    adjustTextareaHeight()
  })
})

// Focus on mount
import { onMounted } from 'vue'
onMounted(() => {
  textareaRef.value?.focus()
})
</script>
