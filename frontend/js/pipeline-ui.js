import { on } from './events.js';
import { startPipeline, pipelineAction, fetchStatus } from './api.js';
import { pauseTimers, resumeTimers } from './log-viewer.js';

const NODE_ORDER = ['refine', 'calibrate', 'strategy', 'decompose', 'execute', 'evaluate', 'write'];
const NODE_SET = new Set(NODE_ORDER);
const RESEARCH_PHASES = new Set(['calibrate', 'strategy', 'decompose', 'execute', 'evaluate']);
const nodeStates = {};
NODE_ORDER.forEach((n) => { nodeStates[n] = 'idle'; });
let seenNodes = new Set();
let inputEl, startBtn, pauseBtn, resumeBtn, overlay;

export function initPipelineUI() {
  inputEl = document.getElementById('research-input');
  startBtn = document.getElementById('start-btn');
  pauseBtn = document.getElementById('pause-btn');
  resumeBtn = document.getElementById('resume-btn');
  overlay = document.getElementById('cmd-overlay');

  on('sse', (event) => {
    const { stage, phase } = event;
    if (!stage) return;
    const node = (stage === 'research' && phase) ? phase : stage;
    if (!NODE_SET.has(node)) return;
    if (seenNodes.has(node)) return;
    seenNodes.add(node);
    for (const n of NODE_ORDER) {
      if (n === node) { updateNode(n, 'active'); break; }
      if (nodeStates[n] !== 'done') updateNode(n, 'done');
    }
    syncButtons();
  });

  startBtn.addEventListener('click', handleStart);
  pauseBtn.addEventListener('click', handlePause);
  resumeBtn.addEventListener('click', handleResume);
  inputEl.addEventListener('input', syncButtons);
  inputEl.addEventListener('keydown', (e) => { if (e.key === 'Enter') handleStart(); });

  document.addEventListener('keydown', (e) => {
    if ((e.metaKey || e.ctrlKey) && e.key === 'k') {
      e.preventDefault();
      overlay.classList.toggle('hidden');
      if (!overlay.classList.contains('hidden')) inputEl.focus();
    }
    if (e.key === 'Escape' && !overlay.classList.contains('hidden')) overlay.classList.add('hidden');
  });
  overlay.addEventListener('click', (e) => { if (e.target === overlay) overlay.classList.add('hidden'); });
  syncButtons();
}

export async function syncFromAPI() {
  const status = await fetchStatus();
  if (!status) return;
  for (const st of status.stages) {
    if (st.state === 'completed') {
      if (st.name === 'refine') { updateNode('refine', 'done'); seenNodes.add('refine'); }
      else if (st.name === 'research') { RESEARCH_PHASES.forEach((n) => { updateNode(n, 'done'); seenNodes.add(n); }); }
      else if (st.name === 'write') { updateNode('write', 'done'); seenNodes.add('write'); }
    } else if (st.state === 'running') {
      if (st.name === 'refine') { updateNode('refine', 'active'); seenNodes.add('refine'); }
      else if (st.name === 'write') { updateNode('write', 'active'); seenNodes.add('write'); }
      else if (st.name === 'research' && st.phase) {
        for (const n of ['calibrate', 'strategy', 'decompose', 'execute', 'evaluate']) {
          seenNodes.add(n);
          if (n === st.phase) { updateNode(n, 'active'); break; }
          updateNode(n, 'done');
        }
      }
    } else if (st.state === 'paused') {
      const active = NODE_ORDER.find((n) => nodeStates[n] === 'active');
      if (active) updateNode(active, 'paused');
    }
  }
  syncButtons();
}

function syncButtons() {
  const hasInput = inputEl && inputEl.value.trim().length > 0;
  const hasActive = NODE_ORDER.some((n) => nodeStates[n] === 'active');
  const hasPaused = NODE_ORDER.some((n) => nodeStates[n] === 'paused');
  startBtn.disabled = !(hasInput && !hasActive && !hasPaused);
  pauseBtn.disabled = !hasActive;
  resumeBtn.disabled = !hasPaused;
  pauseBtn.textContent = 'Pause';
}

async function handleStart() {
  const text = inputEl.value.trim();
  if (!text) return;
  overlay.classList.add('hidden');
  seenNodes.clear();
  NODE_ORDER.forEach((n) => updateNode(n, 'idle'));
  syncButtons();
  try { await startPipeline(text); }
  catch (err) { console.error('Failed to start pipeline:', err); }
}

async function handlePause() {
  pauseBtn.disabled = true;
  pauseBtn.textContent = 'Pausing...';
  try { await pipelineAction('stop'); pauseTimers(); await syncFromAPI(); }
  catch (err) { console.error('Pause error:', err); }
}

async function handleResume() {
  try {
    resumeTimers();
    await pipelineAction('resume');
    const paused = NODE_ORDER.find((n) => nodeStates[n] === 'paused');
    if (paused) updateNode(paused, 'active');
    syncButtons();
  } catch (err) { console.error('Resume error:', err); }
}

function updateNode(name, state) {
  nodeStates[name] = state;
  const el = document.querySelector(`.progress-node[data-node="${name}"]`);
  if (el) el.dataset.state = state;
  updateLines();
}

function updateLines() {
  for (let i = 0; i < NODE_ORDER.length; i++) {
    const name = NODE_ORDER[i];
    const line = document.querySelector(`.progress-line[data-after="${name}"]`);
    if (line) line.dataset.filled = (nodeStates[name] === 'done') ? 'true' : 'false';
  }
}
