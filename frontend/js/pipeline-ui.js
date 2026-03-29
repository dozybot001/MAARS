import { on } from './events.js';
import { stageAction } from './api.js';

/**
 * Progress node order — maps to pipeline phases.
 * refine/write are stages; calibrate/decompose/execute/evaluate are research sub-phases.
 */
const NODE_ORDER = ['refine', 'calibrate', 'strategy', 'decompose', 'execute', 'evaluate', 'write'];

// Track node states: idle | active | done | paused | failed
const nodeStates = {};
NODE_ORDER.forEach((n) => { nodeStates[n] = 'idle'; });

// Map research sub-phases to node names
const RESEARCH_PHASES = new Set(['calibrate', 'strategy', 'decompose', 'execute', 'evaluate']);

export function initPipelineUI() {
  // --- Stage state events (refine/research/write) ---
  on('stage:state', ({ stage, data }) => {
    if (stage === 'refine') {
      updateNode('refine', stageToNodeState(data));
    } else if (stage === 'write') {
      updateNode('write', stageToNodeState(data));
    } else if (stage === 'research') {
      // Research stage state applies to all sub-phase nodes
      if (data === 'completed') {
        RESEARCH_PHASES.forEach((n) => updateNode(n, 'done'));
      } else if (data === 'failed') {
        // Mark current active sub-phase as failed, rest stay
        const active = [...RESEARCH_PHASES].find((n) => nodeStates[n] === 'active');
        if (active) updateNode(active, 'failed');
      } else if (data === 'paused') {
        const active = [...RESEARCH_PHASES].find((n) => nodeStates[n] === 'active');
        if (active) updateNode(active, 'paused');
      } else if (data === 'idle') {
        RESEARCH_PHASES.forEach((n) => updateNode(n, 'idle'));
      }
    }
    updateControls();
  });

  // --- Research sub-phase events ---
  on('stage:phase', ({ data }) => {
    const phase = data; // "calibrate" | "decompose" | "execute" | "evaluate"
    if (!RESEARCH_PHASES.has(phase)) return;

    // Mark previous sub-phases as done, current as active
    for (const n of RESEARCH_PHASES) {
      if (n === phase) {
        updateNode(n, 'active');
        break;
      }
      if (nodeStates[n] === 'active' || nodeStates[n] === 'idle') {
        updateNode(n, 'done');
      }
    }
  });

  // --- Pause/Resume buttons ---
  document.getElementById('pause-btn').addEventListener('click', async () => {
    const running = getRunningStage();
    if (running) {
      try { await stageAction(running, 'stop'); }
      catch (err) { console.error('Pause error:', err); }
    }
  });

  document.getElementById('resume-btn').addEventListener('click', async () => {
    const paused = getPausedStage();
    if (paused) {
      try { await stageAction(paused, 'resume'); }
      catch (err) { console.error('Resume error:', err); }
    }
  });

  // --- Command palette (Cmd+K / Ctrl+K) ---
  const overlay = document.getElementById('cmd-overlay');
  const input = document.getElementById('research-input');

  document.addEventListener('keydown', (e) => {
    if ((e.metaKey || e.ctrlKey) && e.key === 'k') {
      e.preventDefault();
      overlay.classList.toggle('hidden');
      if (!overlay.classList.contains('hidden')) {
        input.focus();
      }
    }
    if (e.key === 'Escape' && !overlay.classList.contains('hidden')) {
      overlay.classList.add('hidden');
    }
  });

  // Click outside panel to close
  overlay.addEventListener('click', (e) => {
    if (e.target === overlay) overlay.classList.add('hidden');
  });
}

// --- Helpers ---

/** Map stage state to node visual state */
function stageToNodeState(state) {
  if (state === 'running') return 'active';
  if (state === 'completed') return 'done';
  return state; // idle, paused, failed
}

function updateNode(name, state) {
  nodeStates[name] = state;
  const el = document.querySelector(`.progress-node[data-node="${name}"]`);
  if (el) el.dataset.state = state;

  // Update the line BEFORE this node (filled if this node is done or beyond)
  updateLines();
}

function updateLines() {
  for (let i = 0; i < NODE_ORDER.length; i++) {
    const name = NODE_ORDER[i];
    const line = document.querySelector(`.progress-line[data-after="${name}"]`);
    if (line) {
      line.dataset.filled = (nodeStates[name] === 'done') ? 'true' : 'false';
    }
  }
}

// Track which STAGE (not node) is running/paused for pause/resume
const stageStates = { refine: 'idle', research: 'idle', write: 'idle' };

// Also track stage states for controls
on('stage:state', ({ stage, data }) => { stageStates[stage] = data; });

function getRunningStage() {
  return Object.keys(stageStates).find((s) => stageStates[s] === 'running') || null;
}

function getPausedStage() {
  return Object.keys(stageStates).find((s) => stageStates[s] === 'paused') || null;
}

function updateControls() {
  document.getElementById('pause-btn').disabled = !getRunningStage();
  document.getElementById('resume-btn').disabled = !getPausedStage();
}
