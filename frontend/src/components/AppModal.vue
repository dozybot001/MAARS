<template>
  <div v-if="visible" class="modal-overlay" @click.self="close">
    <div class="modal-panel">
      <div class="modal-header">
        <h3>{{ title }}</h3>
        <button class="modal-close" @click="close">&times;</button>
      </div>
      <pre class="modal-content">{{ content }}</pre>
    </div>
  </div>
</template>

<script setup>
import { ref, onMounted, onUnmounted } from 'vue'

const visible = ref(false)
const title = ref('')
const content = ref('')

function open(titleText, bodyText) {
  title.value = titleText
  content.value = bodyText
  visible.value = true
}

function close() {
  visible.value = false
}

function onKeydown(e) {
  if (e.key === 'Escape' && visible.value) close()
}

onMounted(() => document.addEventListener('keydown', onKeydown))
onUnmounted(() => document.removeEventListener('keydown', onKeydown))

defineExpose({ open, close })
</script>
