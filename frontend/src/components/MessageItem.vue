<template>
  <div :class="['chat-message', message.role]">
    <div class="flex items-start gap-3">
      <!-- Avatar -->
      <div class="flex-shrink-0">
        <div v-if="message.role === 'user'" class="w-8 h-8 bg-kk-purple rounded-full flex items-center justify-center">
          <svg class="w-5 h-5 text-white" fill="none" stroke="currentColor" viewBox="0 0 24 24">
            <path stroke-linecap="round" stroke-linejoin="round" stroke-width="2" d="M16 7a4 4 0 11-8 0 4 4 0 018 0zM12 14a7 7 0 00-7 7h14a7 7 0 00-7-7z" />
          </svg>
        </div>
        <div v-else class="w-8 h-8 bg-gradient-to-r from-kk-blue to-kk-indigo rounded-full flex items-center justify-center">
          <svg class="w-5 h-5 text-white" fill="none" stroke="currentColor" viewBox="0 0 24 24">
            <path stroke-linecap="round" stroke-linejoin="round" stroke-width="2" d="M9.75 17L9 20l-1 1h8l-1-1-.75-3M3 13h18M5 17h14a2 2 0 002-2V5a2 2 0 00-2-2H5a2 2 0 00-2 2v10a2 2 0 002 2z" />
          </svg>
        </div>
      </div>
      
      <!-- Content -->
      <div class="flex-1 min-w-0">
        <div class="text-sm text-gray-500 mb-1">
          {{ message.role === 'user' ? 'You' : 'DevOps Assistant' }}
        </div>
        <div 
          class="prose prose-invert max-w-none"
          v-html="renderedContent"
        ></div>
      </div>
    </div>
  </div>
</template>

<script setup>
import { computed, onMounted, getCurrentInstance } from 'vue'
import { marked } from 'marked'

const props = defineProps({
  message: {
    type: Object,
    required: true
  }
})

const instance = getCurrentInstance()
const hljs = instance.appContext.config.globalProperties.$hljs

// Configure marked
marked.setOptions({
  highlight: function(code, lang) {
    if (lang && hljs.getLanguage(lang)) {
      try {
        return hljs.highlight(code, { language: lang }).value
      } catch (err) {
        console.error('Highlight error:', err)
      }
    }
    return code
  },
  breaks: true,
  gfm: true
})

const renderedContent = computed(() => {
  try {
    const html = marked(props.message.content)
    
    // Add custom styling to code blocks
    return html.replace(
      /<pre><code/g, 
      '<pre class="code-block"><code'
    ).replace(
      /<code>([^<]+)<\/code>/g,
      '<code class="bg-gray-800 px-1 py-0.5 rounded text-kk-purple">$1</code>'
    )
  } catch (error) {
    console.error('Markdown parsing error:', error)
    return props.message.content
  }
})
</script>

<style scoped>
/* Prose customizations */
:deep(.prose) {
  color: theme('colors.kk-text');
}

:deep(.prose h1),
:deep(.prose h2),
:deep(.prose h3),
:deep(.prose h4) {
  color: theme('colors.kk-text');
  font-weight: 600;
}

:deep(.prose strong) {
  color: theme('colors.kk-text');
}

:deep(.prose a) {
  color: theme('colors.kk-purple');
  text-decoration: underline;
}

:deep(.prose a:hover) {
  color: theme('colors.kk-teal');
}

:deep(.prose ul) {
  list-style-type: disc;
  padding-left: 1.5rem;
}

:deep(.prose ol) {
  list-style-type: decimal;
  padding-left: 1.5rem;
}

:deep(.prose li) {
  margin-top: 0.25rem;
  margin-bottom: 0.25rem;
}

:deep(.prose blockquote) {
  border-left: 4px solid theme('colors.kk-purple');
  padding-left: 1rem;
  font-style: italic;
  color: theme('colors.gray.400');
}

:deep(.prose pre) {
  background-color: theme('colors.gray.900');
  border: 1px solid theme('colors.gray.800');
  overflow-x: auto;
}

:deep(.prose code) {
  font-family: 'Fira Code', monospace;
}
</style>
