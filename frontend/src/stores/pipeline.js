import { defineStore } from 'pinia'
import { computed, ref, reactive, nextTick } from 'vue'
import * as eventBus from '../eventBus.js'

export const STAGE_LABELS = {
  refine: 'REFINE',
  research: 'RESEARCH',
  write: 'WRITE',
}

const NODE_ORDER = ['refine', 'calibrate', 'strategy', 'decompose', 'execute', 'evaluate', 'write']
const RESEARCH_PHASES = new Set(['calibrate', 'strategy', 'decompose', 'execute', 'evaluate'])

export const usePipelineStore = defineStore('pipeline', () => {
  // --- Stage & node states ---
  const stageStates = reactive({ refine: 'idle', research: 'idle', write: 'idle' })
  const nodeStates = reactive({})
  NODE_ORDER.forEach((n) => { nodeStates[n] = 'idle' })

  const activeStage = ref(null)
  const currentPhase = ref(null)

  // --- Timer & counters ---
  const timerStart = ref(null)
  const totalTokens = ref(0)
  const lastActivityTime = ref(null)

  // --- Structured data ---
  const documents = reactive({})       // name → { label, content }
  const taskDescriptions = reactive({}) // taskId → description
  const taskStates = reactive({})       // taskId → { status, summary }
  const decompTree = ref(null)
  const execBatches = ref([])
  const scores = ref([])               // [{ current, previous, improved }]
  const errors = ref([])

  // --- Docker status ---
  const dockerStatus = ref('unknown')  // 'unknown' | 'connected' | 'disconnected'
  const dockerTitle = ref('Checking Docker...')

  // --- Derived state ---
  const pipelineState = computed(() => {
    if (Object.values(stageStates).some((s) => s === 'pausing')) return 'pausing'
    if (Object.values(stageStates).some((s) => s === 'running')) return 'running'
    if (Object.values(stageStates).some((s) => s === 'paused')) return 'paused'
    return 'idle'
  })

  // --- Actions ---

  function handleStageState(stage, state) {
    stageStates[stage] = state

    // Update node states for progress bar
    if (stage === 'refine') {
      setNodeState('refine', stageToNodeState(state))
    } else if (stage === 'write') {
      setNodeState('write', stageToNodeState(state))
    } else if (stage === 'research') {
      if (state === 'completed') {
        RESEARCH_PHASES.forEach((n) => setNodeState(n, 'done'))
      } else if (state === 'failed') {
        const active = [...RESEARCH_PHASES].find((n) => nodeStates[n] === 'active')
        if (active) setNodeState(active, 'failed')
      } else if (state === 'pausing') {
        const active = [...RESEARCH_PHASES].find((n) => nodeStates[n] === 'active')
        if (active) setNodeState(active, 'pausing')
      } else if (state === 'paused') {
        const active = [...RESEARCH_PHASES].find((n) => nodeStates[n] === 'active' || nodeStates[n] === 'pausing')
        if (active) setNodeState(active, 'paused')
      } else if (state === 'idle') {
        RESEARCH_PHASES.forEach((n) => setNodeState(n, 'idle'))
      }
    }

    // Stage transitions for panels
    if (state === 'idle') {
      reset()
    } else if (state === 'running' && stage !== activeStage.value) {
      activeStage.value = stage
      currentPhase.value = null
      if (!timerStart.value) timerStart.value = Date.now()
    } else if (state === 'completed' && stage === 'write') {
      timerStart.value = null
      lastActivityTime.value = null
    } else if (state === 'failed') {
      timerStart.value = null
      lastActivityTime.value = null
    } else if (state === 'paused' || state === 'pausing') {
      lastActivityTime.value = null
    }
  }

  function handlePhase(phase) {
    currentPhase.value = phase
    if (!RESEARCH_PHASES.has(phase)) return
    for (const n of RESEARCH_PHASES) {
      if (n === phase) {
        setNodeState(n, 'active')
        break
      }
      if (nodeStates[n] === 'active' || nodeStates[n] === 'idle') {
        setNodeState(n, 'done')
      }
    }
  }

  function markActivity() {
    lastActivityTime.value = Date.now()
  }

  function addTokens(data) {
    totalTokens.value += data.total || 0
  }

  function addDocument(data) {
    if (!data || !data.name) return
    documents[data.name] = { label: data.label || data.name, content: data.content || '' }
  }

  function updateTaskState(data) {
    if (!data || !data.task_id) return
    taskStates[data.task_id] = { status: data.status, summary: data.summary || '' }
  }

  function setDecompTree(data) {
    decompTree.value = data
  }

  function setExecBatches(data) {
    if (!data || !data.batches) return
    execBatches.value = data.batches
    // Capture task descriptions
    for (const batch of data.batches) {
      for (const task of batch.tasks) {
        taskDescriptions[task.id] = task.description
      }
    }
  }

  function addScore(data) {
    if (!data) return
    scores.value.push(data)
  }

  function addError(stage, message) {
    errors.value.push({ stage, message })
  }

  function setDockerStatus(connected, error) {
    if (connected) {
      dockerStatus.value = 'connected'
      dockerTitle.value = 'Docker connected'
    } else {
      dockerStatus.value = 'disconnected'
      dockerTitle.value = `Docker: ${error || 'not available'}`
    }
  }

  function reset() {
    activeStage.value = null
    currentPhase.value = null
    timerStart.value = null
    totalTokens.value = 0
    lastActivityTime.value = null
    Object.keys(stageStates).forEach((k) => { stageStates[k] = 'idle' })
    NODE_ORDER.forEach((n) => { nodeStates[n] = 'idle' })
    Object.keys(documents).forEach((k) => delete documents[k])
    Object.keys(taskDescriptions).forEach((k) => delete taskDescriptions[k])
    Object.keys(taskStates).forEach((k) => delete taskStates[k])
    decompTree.value = null
    execBatches.value = []
    scores.value = []
    errors.value = []
  }

  // Sync from fetchStatus response (initial load, no side effects)
  function syncFromStatus(status) {
    for (const stage of status.stages) {
      stageStates[stage.name] = stage.state
      // Update progress bar nodes
      if (stage.name === 'refine' || stage.name === 'write') {
        nodeStates[stage.name] = stageToNodeState(stage.state)
      } else if (stage.name === 'research') {
        if (stage.state === 'completed') {
          RESEARCH_PHASES.forEach((n) => { nodeStates[n] = 'done' })
        } else if (stage.state === 'running') {
          // Will be refined by incoming SSE phase events
        } else if (stage.state === 'paused') {
          // Mark completed phases from what we know, leave rest idle
        }
      }
      // Set activeStage for panel context
      if (stage.state === 'running' || stage.state === 'paused') {
        activeStage.value = stage.name
      } else if (stage.state === 'completed') {
        activeStage.value = stage.name
      }
    }
  }

  // Restore full UI state from a historical session snapshot
  async function loadSessionState(state) {
    // Reset and let watchers clean up DOM
    reset()
    await nextTick()

    // Progress bar (immediate, no watcher dependency)
    for (const [k, v] of Object.entries(state.stage_states || {})) {
      stageStates[k] = v
    }
    for (const [k, v] of Object.entries(state.node_states || {})) {
      nodeStates[k] = v
    }

    // --- Pre-process log by stage ---
    const log = state.log || []
    const logByStage = { refine: [], research: [], write: [] }
    for (const ev of log) {
      if (ev.stage && logByStage[ev.stage]) logByStage[ev.stage].push(ev)
    }

    // Split research log into phase groups: [{phase, events}]
    const researchPhases = []
    let group = { phase: null, events: [] }
    for (const ev of logByStage.research) {
      if (ev.type === 'phase') {
        if (group.phase || group.events.length) researchPhases.push(group)
        group = { phase: ev.data, events: [] }
      } else {
        group.events.push(ev)
      }
    }
    if (group.phase || group.events.length) researchPhases.push(group)

    // --- Replay REFINE ---
    if (state.stage_states?.refine === 'completed') {
      activeStage.value = 'refine'
      await nextTick()
      emitLogBatch(logByStage.refine)
      await nextTick()
      if (state.documents?.refined_idea) {
        documents.refined_idea = state.documents.refined_idea
        await nextTick()
      }
    }

    // --- Replay RESEARCH ---
    if (state.stage_states?.research === 'completed') {
      activeStage.value = 'research'
      await nextTick()

      for (const pg of researchPhases) {
        if (pg.phase) {
          currentPhase.value = pg.phase
          await nextTick()
        }

        // Emit log events for this phase (chunks, task_state, error)
        emitLogBatch(pg.events)
        await nextTick()

        // Structural elements after each phase
        if (pg.phase === 'calibrate' && state.documents?.calibration) {
          documents.calibration = state.documents.calibration
          await nextTick()
        }
        if (pg.phase === 'strategy' && state.documents?.strategy) {
          documents.strategy = state.documents.strategy
          await nextTick()
        }
        if (pg.phase === 'decompose' && state.decomp_tree) {
          decompTree.value = state.decomp_tree
          await nextTick()
        }
        if (pg.phase === 'execute') {
          if (state.exec_batches?.length) {
            for (const [k, v] of Object.entries(state.task_descriptions || {})) {
              taskDescriptions[k] = v
            }
            execBatches.value = state.exec_batches
            await nextTick()
            for (const [k, v] of Object.entries(state.task_states || {})) {
              taskStates[k] = v
            }
            await nextTick()
          }
        }
        if (pg.phase === 'evaluate' && state.scores?.length) {
          for (let i = 0; i < state.scores.length; i++) {
            scores.value.push(state.scores[i])
            await nextTick()
            const evalKey = `eval_v${i}`
            if (state.documents?.[evalKey]) {
              documents[evalKey] = state.documents[evalKey]
              await nextTick()
            }
          }
        }
      }
    }

    // --- Replay WRITE ---
    if (state.stage_states?.write === 'completed') {
      activeStage.value = 'write'
      await nextTick()

      // Split write log by phase (like research)
      const writePhases = []
      let wg = { phase: null, events: [] }
      for (const ev of logByStage.write) {
        if (ev.type === 'phase') {
          if (wg.phase || wg.events.length) writePhases.push(wg)
          wg = { phase: ev.data, events: [] }
        } else {
          wg.events.push(ev)
        }
      }
      if (wg.phase || wg.events.length) writePhases.push(wg)

      for (const pg of writePhases) {
        if (pg.phase) {
          currentPhase.value = pg.phase
          await nextTick()
        }
        emitLogBatch(pg.events)
        await nextTick()
      }

      // Write uses Team mode (no phase events) — show paper directly
      if (state.documents?.paper) {
        documents.paper = state.documents.paper
        await nextTick()
      }
    }
  }

  function emitLogBatch(events) {
    for (const ev of events) {
      if (ev.type === 'chunk') {
        eventBus.emit('chunk', ev)
      } else if (ev.type === 'tokens') {
        totalTokens.value += ev.data?.total || 0
      } else if (ev.type === 'task_state') {
        if (ev.data) updateTaskState(ev.data)
        eventBus.emit('task_state', ev)
      } else if (ev.type === 'error') {
        eventBus.emit('error', ev)
      }
    }
  }

  // --- Helpers ---

  function setNodeState(name, state) {
    nodeStates[name] = state
  }

  function stageToNodeState(state) {
    if (state === 'running') return 'active'
    if (state === 'completed') return 'done'
    return state
  }

  return {
    // State
    stageStates,
    nodeStates,
    activeStage,
    currentPhase,
    timerStart,
    totalTokens,
    lastActivityTime,
    documents,
    taskDescriptions,
    taskStates,
    decompTree,
    execBatches,
    scores,
    errors,
    dockerStatus,
    dockerTitle,
    pipelineState,
    // Constants
    NODE_ORDER,
    RESEARCH_PHASES,
    // Actions
    handleStageState,
    handlePhase,
    markActivity,
    addTokens,
    addDocument,
    updateTaskState,
    setDecompTree,
    setExecBatches,
    addScore,
    addError,
    setDockerStatus,
    reset,
    syncFromStatus,
    loadSessionState,
  }
})
