<template>
  <Teleport to="body">
    <div 
      v-if="isVisible"
      class="fixed inset-0 z-50 flex items-center justify-center p-4 bg-black/50"
      @click="handleBackdropClick"
    >
      <div 
        class="bg-gray-900 rounded-lg border border-gray-700 shadow-xl max-w-md w-full"
        @click.stop
        role="dialog"
        :aria-labelledby="titleId"
        aria-modal="true"
      >
        <!-- Header -->
        <div class="px-6 py-4 border-b border-gray-700">
          <h2 :id="titleId" class="text-lg font-semibold text-kk-text">
            {{ title }}
          </h2>
        </div>
        
        <!-- Content -->
        <div class="px-6 py-4">
          <p class="text-gray-300">{{ message }}</p>
        </div>
        
        <!-- Actions -->
        <div class="px-6 py-4 border-t border-gray-700 flex justify-end gap-3">
          <button
            @click="handleCancel"
            class="px-4 py-2 text-gray-300 hover:text-white hover:bg-gray-800 rounded-lg transition-colors"
            tabindex="0"
            aria-label="Cancel action"
          >
            {{ cancelText }}
          </button>
          <button
            @click="handleConfirm"
            :class="[
              'px-4 py-2 rounded-lg transition-colors',
              variant === 'danger' 
                ? 'bg-red-600 hover:bg-red-700 text-white' 
                : 'bg-kk-purple hover:bg-kk-purple/80 text-white'
            ]"
            tabindex="0"
            :aria-label="`Confirm ${confirmText.toLowerCase()}`"
          >
            {{ confirmText }}
          </button>
        </div>
      </div>
    </div>
  </Teleport>
</template>

<script setup>
import { computed } from 'vue'

const props = defineProps({
  isVisible: {
    type: Boolean,
    default: false
  },
  title: {
    type: String,
    required: true
  },
  message: {
    type: String,
    required: true
  },
  confirmText: {
    type: String,
    default: 'Confirm'
  },
  cancelText: {
    type: String,
    default: 'Cancel'
  },
  variant: {
    type: String,
    default: 'primary', // 'primary' | 'danger'
    validator: (value) => ['primary', 'danger'].includes(value)
  },
  closeOnBackdrop: {
    type: Boolean,
    default: true
  }
})

const emit = defineEmits(['confirm', 'cancel', 'close'])

const titleId = computed(() => `modal-title-${Math.random().toString(36).substr(2, 9)}`)

const handleConfirm = () => {
  emit('confirm')
}

const handleCancel = () => {
  emit('cancel')
}

const handleBackdropClick = () => {
  if (props.closeOnBackdrop) {
    emit('close')
  }
}
</script>
