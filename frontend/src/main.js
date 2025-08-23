import { createApp } from 'vue'
import App from './App.vue'
import './styles/main.css'
import hljs from 'highlight.js'
import 'highlight.js/styles/github-dark.css'

// Configure highlight.js
hljs.configure({
  languages: ['javascript', 'python', 'bash', 'yaml', 'json', 'dockerfile', 'hcl']
})

const app = createApp(App)

// Global properties
app.config.globalProperties.$hljs = hljs

app.mount('#app')
