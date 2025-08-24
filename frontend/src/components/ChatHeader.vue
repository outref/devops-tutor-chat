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
        <!-- User info -->
        <div class="flex items-center gap-3">
          <span class="text-sm text-gray-400">{{ user?.username }}</span>
          
          <!-- Topic indicator -->
          <div 
            v-if="topic && topic !== 'pending'"
            class="px-3 py-1 bg-kk-slate-800 rounded-full"
          >
            <span class="text-sm text-kk-purple">{{ formatTopic(topic) }}</span>
          </div>
        </div>
        
        <!-- Action buttons -->
        <div class="flex items-center gap-2">
          <!-- Logout button -->
          <button
            class="p-2 hover:bg-red-800/20 rounded-lg transition-colors"
            tabindex="0"
            aria-label="Sign out"
            @click="handleLogout"
          >
            <svg class="w-5 h-5 text-gray-400 hover:text-red-400" fill="none" stroke="currentColor" viewBox="0 0 24 24">
              <path stroke-linecap="round" stroke-linejoin="round" stroke-width="2" d="M17 16l4-4m0 0l-4-4m4 4H7m6 4v1a3 3 0 01-3 3H6a3 3 0 01-3-3V7a3 3 0 013-3h4a3 3 0 013 3v1" />
            </svg>
          </button>
        </div>
      </div>
    </div>
    
    <!-- Logout confirmation modal -->
    <Modal
      :isVisible="showLogoutModal"
      title="Sign Out"
      message="Are you sure you want to sign out? You will need to login again to access your conversations."
      confirmText="Sign Out"
      cancelText="Cancel"
      variant="danger"
      @confirm="confirmLogout"
      @cancel="cancelLogout"
      @close="cancelLogout"
    />
  </header>
</template>

<script setup>
import { computed, ref } from 'vue'
import { useAuth } from '../composables/useAuth.js'
import Modal from './Modal.vue'

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

const emit = defineEmits(['logout'])

const { user, logout } = useAuth()

const showLogoutModal = ref(false)

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

const handleLogout = () => {
  showLogoutModal.value = true
}

const confirmLogout = () => {
  showLogoutModal.value = false
  logout()
  emit('logout')
}

const cancelLogout = () => {
  showLogoutModal.value = false
}
</script>
