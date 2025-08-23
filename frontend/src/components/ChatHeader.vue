<template>
  <header class="bg-gray-900/50 border-b border-gray-800 px-6 py-4">
    <div class="flex items-center justify-between">
      <div>
        <h1 class="text-xl font-semibold text-kk-text">
          {{ displayTitle }}
        </h1>
        <p class="text-sm text-gray-500 mt-1">
          {{ displaySubtitle }}
        </p>
      </div>
      
      <div class="flex items-center gap-2">
        <!-- Topic indicator -->
        <div 
          v-if="topic && topic !== 'pending'"
          class="px-3 py-1 bg-kk-slate-800 rounded-full"
        >
          <span class="text-sm text-kk-purple">{{ formatTopic(topic) }}</span>
        </div>
        
        <!-- Info icon -->
        <button
          class="p-2 hover:bg-gray-800 rounded-lg transition-colors"
          tabindex="0"
          aria-label="Information about this chat"
          @click="showInfo"
        >
          <svg class="w-5 h-5 text-gray-400" fill="none" stroke="currentColor" viewBox="0 0 24 24">
            <path stroke-linecap="round" stroke-linejoin="round" stroke-width="2" d="M13 16h-1v-4h-1m1-4h.01M21 12a9 9 0 11-18 0 9 9 0 0118 0z" />
          </svg>
        </button>
      </div>
    </div>
  </header>
</template>

<script setup>
import { computed } from 'vue'

const props = defineProps({
  topic: {
    type: String,
    default: ''
  },
  isNewConversation: {
    type: Boolean,
    default: true
  }
})

const displayTitle = computed(() => {
  if (props.isNewConversation) {
    return 'Start a New DevOps Learning Session'
  }
  return `Learning ${formatTopic(props.topic)}`
})

const displaySubtitle = computed(() => {
  if (props.isNewConversation) {
    return 'Ask me about Kubernetes, Docker, CI/CD, AWS, GCloud, or any DevOps topic!'
  }
  return 'Continue your learning journey'
})

const formatTopic = (topic) => {
  if (!topic || topic === 'pending') return 'DevOps'
  
  const topicMap = {
    'kubernetes': 'Kubernetes',
    'docker': 'Docker',
    'cicd': 'CI/CD',
    'aws': 'AWS',
    'gcloud': 'Google Cloud',
    'terraform': 'Terraform',
    'ansible': 'Ansible',
    'monitoring': 'Monitoring'
  }
  
  return topicMap[topic.toLowerCase()] || topic.charAt(0).toUpperCase() + topic.slice(1)
}

const showInfo = () => {
  alert('This is a DevOps learning chatbot. Ask questions about DevOps topics and I\'ll help you learn with examples and explanations!')
}
</script>
