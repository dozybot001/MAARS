<template>
  <div class="panel">
    <div class="panel-header">
      <h3>Reasoning Log</h3>
      <span
        v-if="activityText"
        class="activity-badge"
        :data-state="activityState"
      >{{ activityText }}</span>
      <span class="token-badge">{{ tokenDisplay }}</span>
      <button class="copy-btn" @click="copyLog">Copy</button>
    </div>
    <div ref="logOutput" class="panel-body log-output"></div>
  </div>
</template>

<script setup>
import { ref, computed, watch, onMounted, onUnmounted } from 'vue'
import { usePipelineStore } from '../stores/pipeline.js'
import { STAGE_LABELS } from '../stores/pipeline.js'
import * as eventBus from '../eventBus.js'
import { createAutoScroller } from '../composables/useAutoScroll.js'

const store = usePipelineStore()
const logOutput = ref(null)

// --- Header: reactive computed from store ---

const tokenDisplay = computed(() => {
  const t = store.totalTokens
  if (t === 0) return ''
  if (t >= 1e9) return `${(t / 1e9).toFixed(1)}B tokens`
  if (t >= 1e6) return `${(t / 1e6).toFixed(1)}M tokens`
  if (t >= 1e3) return `${(t / 1e3).toFixed(1)}k tokens`
  return `${t} tokens`
})

const activityText = ref('')
const activityState = ref('')
let activityInterval = null

function updateActivityBadge() {
  if (!store.lastActivityTime) {
    activityText.value = ''
    activityState.value = ''
    return
  }
  const idle = Math.floor((Date.now() - store.lastActivityTime) / 1000)
  if (idle < 5) {
    activityText.value = 'Active'
    activityState.value = 'active'
  } else if (idle < 60) {
    activityText.value = `Waiting ${idle}s`
    activityState.value = 'waiting'
  } else {
    const m = Math.floor(idle / 60)
    const s = idle % 60
    activityText.value = `No output ${m}m${s}s`
    activityState.value = 'stale'
  }
}

// --- Content: non-reactive DOM state ---
let scroller = null
let activeStage = null
let currentSection = null
let phaseGroups = {}
let currentPhaseName = null
let taskGroups = {}
let callBlocks = {}
let callScrollers = {}

// --- DOM helpers (ported from old log-viewer.js) ---

function createFold(parent, labelText, level) {
  const label = document.createElement('div')
  label.className = 'fold-label'
  if (level) label.dataset.level = level
  label.textContent = labelText

  const body = document.createElement('div')
  body.className = 'fold-body'

  label.addEventListener('click', () => {
    const collapsed = body.classList.toggle('collapsed')
    label.classList.toggle('is-collapsed')
    if (collapsed) body.classList.remove('user-expanded')
    else body.classList.add('user-expanded')
  })

  parent.appendChild(label)
  parent.appendChild(body)
  return { label, body }
}

function appendSeparator(container, label) {
  const sep = document.createElement('div')
  sep.className = 'log-separator'
  sep.textContent = `\u2500\u2500 ${label} \u2500\u2500`
  sep.addEventListener('click', () => {
    const section = sep.nextElementSibling
    if (section && section.classList.contains('log-section')) {
      const nowCollapsed = section.classList.toggle('collapsed')
      sep.classList.toggle('is-collapsed')
      if (nowCollapsed) section.classList.remove('user-expanded')
      else section.classList.add('user-expanded')
    }
  })
  container.appendChild(sep)

  const section = document.createElement('div')
  section.className = 'log-section'
  container.appendChild(section)
  if (scroller) scroller.scroll()
  return section
}

function currentTarget(taskId) {
  if (taskId && taskGroups[taskId]) return taskGroups[taskId].body
  if (currentPhaseName && phaseGroups[currentPhaseName]) return phaseGroups[currentPhaseName].body
  return currentSection
}

function collapsePrevFold(parent) {
  const bodies = parent.querySelectorAll(':scope > .fold-body')
  if (bodies.length === 0) return
  const last = bodies[bodies.length - 1]
  if (last.classList.contains('user-expanded')) return
  last.classList.add('collapsed')
  const label = last.previousElementSibling
  if (label && label.classList.contains('fold-label')) {
    label.classList.add('is-collapsed')
  }
}

function resetPhaseState() {
  for (const s of Object.values(callScrollers)) s.destroy()
  callBlocks = {}
  callScrollers = {}
  phaseGroups = {}
  currentPhaseName = null
  taskGroups = {}
}

function clearChildren(el) {
  while (el && el.firstChild) el.removeChild(el.firstChild)
}

function resetAll() {
  activeStage = null
  currentSection = null
  resetPhaseState()
  clearChildren(logOutput.value)
  if (scroller) scroller.reset()
}

// --- EventBus handlers ---

function onChunk({ stage, data }) {
  const callId = data.call_id
  const taskId = data.task_id || null

  if (data.label && callId) {
    const level = data.level || 4
    let parent
    if (level <= 2) {
      if (!currentSection) return
      parent = currentSection
    } else {
      parent = currentTarget(taskId)
      if (!parent) return
    }

    collapsePrevFold(parent)

    let text = data.text
    if (level === 3 && taskId) {
      const desc = store.taskDescriptions[taskId]
      text = desc ? `Task [${taskId}]: ${desc}` : `Task [${taskId}]`
    }

    const fold = createFold(parent, text, level)

    if (level <= 2) {
      currentPhaseName = callId
      phaseGroups[callId] = fold
    }
    if (level === 3 && taskId) {
      taskGroups[taskId] = fold
    }

    const block = document.createElement('div')
    block.className = 'fold-text'
    fold.body.appendChild(block)
    callBlocks[callId] = block
    callScrollers[callId] = createAutoScroller(block)
    if (scroller) scroller.scroll()
    return
  }

  // Non-label chunk: append text
  const chunkText = data.text || data
  let block

  if (callId && callBlocks[callId]) {
    block = callBlocks[callId]
    const parent = block.parentElement
    if (parent && parent.lastElementChild !== block) {
      collapsePrevFold(parent)
      block = document.createElement('div')
      block.className = 'fold-text'
      parent.appendChild(block)
      callBlocks[callId] = block
      callScrollers[callId] = createAutoScroller(block)
    }
    block.appendChild(document.createTextNode(chunkText))
  } else {
    const t = currentTarget(taskId) || logOutput.value
    block = t.lastElementChild
    if (!block || !block.classList.contains('fold-text')) {
      block = document.createElement('div')
      block.className = 'fold-text'
      t.appendChild(block)
    }
    block.appendChild(document.createTextNode(chunkText))
  }

  if (callId && callScrollers[callId]) callScrollers[callId].scroll()
  else if (block) block.scrollTop = block.scrollHeight
  if (scroller) scroller.scroll()
}

function onTaskState({ data }) {
  const { task_id, status } = data
  const group = taskGroups[task_id]
  if (!group) return
  if ((status === 'completed' || status === 'failed') && !group.body.classList.contains('user-expanded')) {
    group.body.classList.add('collapsed')
    group.label.classList.add('is-collapsed')
  }
}

function onError({ stage, data }) {
  const msg = data.message || data
  const el = document.createElement('div')
  el.className = 'fold-text'
  el.style.color = 'var(--red)'
  el.textContent = `[ERROR] ${stage}: ${msg}`
  const t = currentTarget(null) || logOutput.value
  if (t) t.appendChild(el)
  if (scroller) scroller.scroll()
}

// --- Watch store for stage transitions (drives section creation) ---

watch(() => store.activeStage, (stage) => {
  if (!stage) return
  if (!logOutput.value) return

  if (currentSection && !currentSection.classList.contains('user-expanded')) {
    currentSection.classList.add('collapsed')
    const prevSep = currentSection.previousElementSibling
    if (prevSep) prevSep.classList.add('is-collapsed')
  }

  activeStage = stage
  resetPhaseState()
  currentSection = appendSeparator(logOutput.value, STAGE_LABELS[stage] || stage.toUpperCase())
})

// Reset on idle
watch(() => store.pipelineState, (state) => {
  if (state === 'idle' && !store.activeStage) {
    resetAll()
  }
})

// --- Copy ---
function copyLog() {
  const el = logOutput.value
  if (!el) return
  const text = el.innerText
  navigator.clipboard.writeText(text).catch(() => {
    const textarea = document.createElement('textarea')
    textarea.value = text
    textarea.style.cssText = 'position:fixed;opacity:0'
    document.body.appendChild(textarea)
    textarea.select()
    document.execCommand('copy')
    document.body.removeChild(textarea)
  })
}

// --- Lifecycle ---

onMounted(() => {
  scroller = createAutoScroller(logOutput.value)

  eventBus.on('chunk', onChunk)
  eventBus.on('task_state', onTaskState)
  eventBus.on('error', onError)

  activityInterval = setInterval(updateActivityBadge, 1000)
})

onUnmounted(() => {
  eventBus.off('chunk', onChunk)
  eventBus.off('task_state', onTaskState)
  eventBus.off('error', onError)

  if (activityInterval) clearInterval(activityInterval)
  if (scroller) scroller.destroy()
  for (const s of Object.values(callScrollers)) s.destroy()
})
</script>
