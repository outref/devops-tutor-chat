<template>
  <div class="border-t border-gray-800 bg-gray-900/50 px-6 py-4">
    <form @submit.prevent="handleSubmit" class="max-w-3xl mx-auto">
      <div class="flex gap-3">
        <textarea
          ref="textareaRef"
          v-model="message"
          @keydown="handleKeyDown"
          :disabled="disabled || (isQuizMode && !quizState?.is_active)"
          :placeholder="dynamicPlaceholder"
          class="flex-1 input-primary resize-none min-h-[44px] max-h-32"
          rows="1"
          tabindex="0"
          aria-label="Type your message"
        ></textarea>
        
        <button
          v-if="showQuizButton && !isQuizMode"
          type="button"
          @click="handleStartQuiz"
          :disabled="disabled"
          class="btn-secondary px-4 flex items-center gap-2"
          tabindex="0"
          aria-label="Start quiz"
        >
          <svg class="w-4 h-4" fill="none" stroke="currentColor" viewBox="0 0 24 24">
            <path stroke-linecap="round" stroke-linejoin="round" stroke-width="2" d="M8.228 9c.549-1.165 2.03-2 3.772-2 2.21 0 4 1.343 4 3 0 1.4-1.278 2.575-3.006 2.907-.542.104-.994.54-.994 1.093m0 3h.01M21 12a9 9 0 11-18 0 9 9 0 0118 0z" />
          </svg>
          Quiz
        </button>
        
        <button
          type="submit"
          :disabled="disabled || (!message.trim() && !(isQuizMode && quizState?.is_active))"
          class="btn-primary px-4 flex items-center gap-2"
          tabindex="0"
          aria-label="Send message"
        >
          <span v-if="!disabled">{{ isQuizMode && quizState?.is_active ? 'Answer' : 'Send' }}</span>
          <span v-else>Sending...</span>
          <svg class="w-4 h-4" fill="none" stroke="currentColor" viewBox="0 0 24 24">
            <path stroke-linecap="round" stroke-linejoin="round" stroke-width="2" d="M12 19l9 2-9-18-9 18 9-2zm0 0v-8" />
          </svg>
        </button>
      </div>
      
      <div class="mt-2 text-xs text-gray-500">
        <span v-if="isQuizMode && quizState?.is_active">
          Answer the quiz question above
        </span>
        <span v-else>
          Press Enter to send, Shift+Enter for new line
        </span>
      </div>
    </form>
  </div>
</template>

<script setup>
import { ref, watch, nextTick, computed } from 'vue'

const props = defineProps({
  disabled: {
    type: Boolean,
    default: false
  },
  showQuizButton: {
    type: Boolean,
    default: false
  },
  isQuizMode: {
    type: Boolean,
    default: false
  },
  quizState: {
    type: Object,
    default: null
  },
  currentTopic: {
    type: String,
    default: ''
  }
})

const emit = defineEmits(['send-message', 'start-quiz'])

const message = ref('')
const textareaRef = ref(null)

const dynamicPlaceholder = computed(() => {
  if (props.currentTopic && props.currentTopic !== '' && props.currentTopic !== 'pending') {
    return `Ask about ${props.currentTopic}...`
  }
  return 'Ask about Kubernetes, Docker, CI/CD, AWS, or any DevOps topic...'
})

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

const handleStartQuiz = () => {
  emit('start-quiz')
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
