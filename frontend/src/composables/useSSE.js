import { onUnmounted } from 'vue'
import { usePipelineStore } from '../stores/pipeline.js'
import * as eventBus from '../eventBus.js'

function safeParse(e) {
  try {
    return JSON.parse(e.data)
  } catch {
    console.warn('[SSE] Failed to parse event data:', e.data)
    return null
  }
}

export function useSSE() {
  let source = null

  function connect() {
    if (source) source.close()

    const store = usePipelineStore()
    source = new EventSource('/api/events')

    source.addEventListener('state', (e) => {
      const data = safeParse(e)
      if (data) store.handleStageState(data.stage, data.data)
    })

    source.addEventListener('phase', (e) => {
      const data = safeParse(e)
      if (data) {
        store.handlePhase(data.data)
        eventBus.emit('phase', data)
      }
    })

    source.addEventListener('chunk', (e) => {
      const data = safeParse(e)
      if (data) {
        store.markActivity()
        eventBus.emit('chunk', data)
      }
    })

    source.addEventListener('task_state', (e) => {
      const data = safeParse(e)
      if (data) {
        store.updateTaskState(data.data)
        eventBus.emit('task_state', data)
      }
    })

    source.addEventListener('exec_tree', (e) => {
      const data = safeParse(e)
      if (data) store.setExecBatches(data.data)
    })

    source.addEventListener('tree', (e) => {
      const data = safeParse(e)
      if (data) store.setDecompTree(data.data)
    })

    source.addEventListener('tokens', (e) => {
      const data = safeParse(e)
      if (data) {
        store.markActivity()
        store.addTokens(data.data)
        eventBus.emit('tokens', data)
      }
    })

    source.addEventListener('document', (e) => {
      const data = safeParse(e)
      if (data) store.addDocument(data.data)
    })

    source.addEventListener('score', (e) => {
      const data = safeParse(e)
      if (data) store.addScore(data.data)
    })

    source.addEventListener('error', (e) => {
      if (e.data) {
        const data = safeParse(e)
        if (data) {
          store.addError(data.stage, data.data?.message || data.data)
          eventBus.emit('error', data)
        }
      }
    })

    source.onerror = () => {
      console.warn('[SSE] Connection lost, reconnecting...')
    }
  }

  function disconnect() {
    if (source) {
      source.close()
      source = null
    }
  }

  onUnmounted(disconnect)

  return { connect, disconnect }
}
