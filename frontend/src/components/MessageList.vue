<template>
  <div 
    ref="scrollContainer"
    class="flex-1 overflow-y-auto custom-scrollbar px-6 py-4"
  >
    <!-- Welcome message for empty state -->
    <div v-if="messages.length === 0 && !isLoading" class="max-w-3xl mx-auto mt-8">
      <div class="text-center mb-8">
        <div class="inline-flex items-center justify-center w-16 h-16 bg-gradient-to-r from-kk-blue via-kk-sky to-kk-indigo rounded-full mb-4">
          <svg class="w-8 h-8 text-white" fill="none" stroke="currentColor" viewBox="0 0 24 24">
            <path stroke-linecap="round" stroke-linejoin="round" stroke-width="2" d="M9.663 17h4.673M12 3v1m6.364 1.636l-.707.707M21 12h-1M4 12H3m3.343-5.657l-.707-.707m2.828 9.9a5 5 0 117.072 0l-.548.547A3.374 3.374 0 0014 18.469V19a2 2 0 11-4 0v-.531c0-.895-.356-1.754-.988-2.386l-.548-.547z" />
          </svg>
        </div>
        <h2 class="text-2xl font-semibold text-kk-text mb-2">Welcome to DevOps Learning Assistant</h2>
        <p class="text-gray-400">Pick any topic on DevOps that interests you!</p>
      </div>
      
      <!-- Suggested topics -->
      <div class="grid grid-cols-2 gap-3 max-w-2xl mx-auto">
        <button
          v-for="topic in suggestedTopics"
          :key="topic.name"
          @click="$emit('suggest-topic', topic.prompt)"
          class="p-4 bg-gray-800/60 hover:bg-gray-800 rounded-lg text-left transition-colors group"
          tabindex="0"
          :aria-label="`Learn about ${topic.name}`"
        >
          <div class="flex items-start gap-3">
            <div :class="['p-2 rounded-lg', topic.color]">
              <component :is="topic.icon" class="w-5 h-5 text-white" />
            </div>
            <div>
              <h3 class="font-medium text-kk-text group-hover:text-kk-purple transition-colors">{{ topic.name }}</h3>
              <p class="text-sm text-gray-500 mt-1">{{ topic.description }}</p>
            </div>
          </div>
        </button>
      </div>
    </div>
    
    <!-- Messages -->
    <div v-else class="max-w-3xl mx-auto">
      <MessageItem
        v-for="message in messages"
        :key="message.id"
        :message="message"
      />
      
      <!-- Loading indicator -->
      <div v-if="isLoading" class="chat-message assistant">
        <div class="flex items-center gap-2">
          <div class="animate-pulse flex gap-1">
            <div class="w-2 h-2 bg-kk-purple rounded-full"></div>
            <div class="w-2 h-2 bg-kk-purple rounded-full animation-delay-200"></div>
            <div class="w-2 h-2 bg-kk-purple rounded-full animation-delay-400"></div>
          </div>
          <span class="text-sm text-gray-500">Thinking...</span>
        </div>
      </div>
    </div>
  </div>
</template>

<script setup>
import { ref, defineProps, defineEmits, defineExpose } from 'vue'
import MessageItem from './MessageItem.vue'

const props = defineProps({
  messages: {
    type: Array,
    required: true
  },
  isLoading: {
    type: Boolean,
    default: false
  }
})

const emit = defineEmits(['suggest-topic'])

const scrollContainer = ref(null)

const suggestedTopics = [
  {
    name: 'Kubernetes',
    prompt: 'Give me a lesson on Kubernetes',
    description: 'Container orchestration platform',
    color: 'bg-blue-600',
    icon: defineComponent({
      render: () => h('svg', { fill: 'none', stroke: 'currentColor', viewBox: '0 0 24 24' },
        h('path', { 'stroke-linecap': 'round', 'stroke-linejoin': 'round', 'stroke-width': '2', d: 'M5 12h14M5 12a2 2 0 01-2-2V6a2 2 0 012-2h14a2 2 0 012 2v4a2 2 0 01-2 2M5 12a2 2 0 00-2 2v4a2 2 0 002 2h14a2 2 0 002-2v-4a2 2 0 00-2-2m-2-4h.01M17 16h.01' })
      )
    })
  },
  {
    name: 'Docker',
    prompt: 'Give me a lesson on Docker',
    description: 'Application containerization',
    color: 'bg-cyan-600',
    icon: defineComponent({
      render: () => h('svg', { fill: 'none', stroke: 'currentColor', viewBox: '0 0 24 24' },
        h('path', { 'stroke-linecap': 'round', 'stroke-linejoin': 'round', 'stroke-width': '2', d: 'M20 7l-8-4-8 4m16 0l-8 4m8-4v10l-8 4m0-10L4 7m8 4v10M4 7v10l8 4' })
      )
    })
  },
  {
    name: 'CI/CD',
    prompt: 'Give me a lesson on CI/CD',
    description: 'Continuous Integration & Deployment',
    color: 'bg-green-600',
    icon: defineComponent({
      render: () => h('svg', { fill: 'none', stroke: 'currentColor', viewBox: '0 0 24 24' },
        h('path', { 'stroke-linecap': 'round', 'stroke-linejoin': 'round', 'stroke-width': '2', d: 'M4 4v5h.582m15.356 2A8.001 8.001 0 004.582 9m0 0H9m11 11v-5h-.581m0 0a8.003 8.003 0 01-15.357-2m15.357 2H15' })
      )
    })
  },
  {
    name: 'AWS CLI',
    prompt: 'Give me a lesson on AWS CLI',
    description: 'Amazon Web Services CLI',
    color: 'bg-orange-600',
    icon: defineComponent({
      render: () => h('svg', { fill: 'none', stroke: 'currentColor', viewBox: '0 0 24 24' },
        h('path', { 'stroke-linecap': 'round', 'stroke-linejoin': 'round', 'stroke-width': '2', d: 'M3 15a4 4 0 004 4h9a5 5 0 10-.1-9.999 5.002 5.002 0 10-9.78 2.096A4.001 4.001 0 003 15z' })
      )
    })
  }
]

const scrollToBottom = () => {
  if (scrollContainer.value) {
    scrollContainer.value.scrollTop = scrollContainer.value.scrollHeight
  }
}

// Import necessary Vue functions
import { h, defineComponent } from 'vue'

defineExpose({
  scrollToBottom
})
</script>

<style scoped>
.animation-delay-200 {
  animation-delay: 200ms;
}

.animation-delay-400 {
  animation-delay: 400ms;
}
</style>
