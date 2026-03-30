<template>
  <div v-if="visible" class="cmd-overlay" @click.self="close">
    <div class="cmd-panel">
      <input
        ref="inputEl"
        v-model="inputText"
        type="text"
        placeholder="Research idea or Kaggle URL..."
        autocomplete="off"
        @keydown.enter="handleStart"
      >
      <button :disabled="!canStart" @click="handleStart">Start</button>
      <button :disabled="!canPause" @click="handlePause">
        {{ store.pipelineState === 'pausing' ? 'Pausing...' : 'Pause' }}
      </button>
      <button :disabled="!canResume" @click="handleResume">Resume</button>
    </div>
  </div>
</template>

<script setup>
import { ref, computed, watch, onMounted, onUnmounted, nextTick } from 'vue'
import { usePipelineStore } from '../stores/pipeline.js'
import { startPipeline, stageAction } from '../api.js'

const store = usePipelineStore()
const visible = ref(false)
const inputText = ref('')
const inputEl = ref(null)

const canStart = computed(() => {
  const s = store.pipelineState
  return s !== 'running' && s !== 'paused' && s !== 'pausing' && inputText.value.trim().length > 0
})

const canPause = computed(() => store.pipelineState === 'running')
const canResume = computed(() => store.pipelineState === 'paused')

function open() {
  visible.value = true
  nextTick(() => { inputEl.value?.focus() })
}

function close() {
  visible.value = false
}

function toggle() {
  if (visible.value) close()
  else open()
}

async function handleStart() {
  const text = inputText.value.trim()
  if (!text) return
  close()
  try { await startPipeline(text) }
  catch (err) { console.error('Failed to start pipeline:', err) }
}

async function handlePause() {
  const running = Object.keys(store.stageStates).find((s) => store.stageStates[s] === 'running')
  if (!running) return
  store.stageStates[running] = 'pausing'
  try { await stageAction(running, 'stop') }
  catch (err) { console.error('Pause error:', err) }
}

async function handleResume() {
  const paused = Object.keys(store.stageStates).find((s) => store.stageStates[s] === 'paused')
  if (!paused) return
  try { await stageAction(paused, 'resume') }
  catch (err) { console.error('Resume error:', err) }
}

function onKeydown(e) {
  if ((e.metaKey || e.ctrlKey) && e.key === 'k') {
    e.preventDefault()
    toggle()
  }
  if (e.key === 'Escape' && visible.value) {
    close()
  }
}

onMounted(() => document.addEventListener('keydown', onKeydown))
onUnmounted(() => document.removeEventListener('keydown', onKeydown))

defineExpose({ open, close, toggle })
</script>
