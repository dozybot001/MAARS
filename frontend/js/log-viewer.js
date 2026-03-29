import { on } from './events.js';
import { createAutoScroller } from './autoscroll.js';
import { STAGE_LABELS, appendSeparator } from './shared.js';

let logOutput;
let scroller;
let activeStage = null;
let callBlocks = {};      // call_id → DOM text element
let callScrollers = {};   // call_id → autoscroller for chunk block
let currentSection = null;
let totalTokens = 0;
let tokenBadge = null;

// Session grouping — each agent session (Calibrate, Strategy, etc.) gets a collapsible group
let sessionGroups = {};      // session_name → DOM container
let sessionBodyScrollers = {}; // session_name → autoscroller
let currentSessionName = null;

// Known session-level labels (these create collapsible groups)
const SESSION_LABELS = new Set([
  'Calibrate', 'Strategy', 'Refine', 'Write',
  'Evaluate', 'Replan', 'Score Check',
]);

// Task grouping for Research execute phase
let taskGroups = {};
let taskDescriptions = {};
let taskBodyScrollers = {};

// Elapsed timer
let timerBadge = null;
let timerInterval = null;
let timerStart = null;

export function initLogViewer() {
  logOutput = document.getElementById('log-output');
  scroller = createAutoScroller(logOutput);
  tokenBadge = document.getElementById('token-estimate');
  timerBadge = document.getElementById('elapsed-timer');

  wireCopyButton('copy-log', document.getElementById('log-output'));
  wireCopyButton('copy-process', document.getElementById('process-body'));

  // --- Stage transitions ---
  on('stage:state', ({ stage, data }) => {
    if (data === 'idle') {
      logOutput.innerHTML = '';
      activeStage = null;
      callBlocks = {};
      callScrollers = {};
      currentSection = null;
      sessionGroups = {};
      sessionBodyScrollers = {};
      currentSessionName = null;
      taskGroups = {};
      taskDescriptions = {};
      totalTokens = 0;
      updateTokenBadge();
      stopTimer();
      scroller.reset();
    } else if (data === 'completed' && stage === 'write') {
      stopTimer();
    } else if (data === 'failed') {
      stopTimer();
    }
    if (data === 'running' && stage !== activeStage) {
      if (!timerStart) startTimer();
      // Collapse previous section (respect user-expanded)
      if (currentSection && !currentSection.classList.contains('user-expanded')) {
        currentSection.classList.add('collapsed');
        const prevSep = currentSection.previousElementSibling;
        if (prevSep) prevSep.classList.add('is-collapsed');
      }
      activeStage = stage;
      callBlocks = {};
      callScrollers = {};
      sessionGroups = {};
      sessionBodyScrollers = {};
      currentSessionName = null;
      taskGroups = {};
      taskBodyScrollers = {};
      currentSection = appendSeparator(logOutput, STAGE_LABELS[stage] || stage.toUpperCase(), scroller);
    }
  });

  // --- Task state: auto-collapse completed tasks ---
  on('task:state', ({ data }) => {
    const { task_id, status } = data;
    if ((status === 'completed' || status === 'failed') && taskGroups[task_id]) {
      const group = taskGroups[task_id];
      const body = group.querySelector('.task-group-body');
      const header = group.querySelector('.task-group-header');
      if (body && !body.classList.contains('user-expanded')) {
        body.classList.add('collapsed');
        if (header) header.classList.add('is-collapsed');
      }
    }
  });

  // --- Exec tree: capture task descriptions for group headers ---
  on('exec:tree', ({ data }) => {
    if (!data || !data.batches) return;
    for (const batch of data.batches) {
      for (const task of batch.tasks) {
        taskDescriptions[task.id] = task.description;
      }
    }
  });

  // --- Chunk streaming ---
  on('log:chunk', ({ stage, data }) => {
    const callId = data.call_id;
    const taskId = data.task_id || null;

    if (data.label && callId) {
      // Is this a session-level label?
      if (!taskId && isSessionLabel(callId)) {
        // Collapse previous session group
        collapseCurrentSession();
        // Create new session group
        currentSessionName = callId;
        getOrCreateSessionGroup(callId);
        scroller.scroll();
        return;
      }

      // Determine target container
      const appendTarget = taskId
        ? getTaskGroupBody(taskId)
        : (currentSessionName ? getSessionGroupBody(currentSessionName) : currentSection);

      if (!appendTarget) return;

      // Fold previous blocks within target
      appendTarget.querySelectorAll('.log-text:not(.folded):not(.user-expanded)').forEach(el => {
        el.classList.add('folded');
        const prev = el.previousElementSibling;
        if (prev && prev.classList.contains('log-label')) prev.classList.add('is-collapsed');
      });

      const label = document.createElement('div');
      label.className = 'log-label';
      label.textContent = data.text;
      appendTarget.appendChild(label);

      const block = document.createElement('div');
      block.className = 'log-text';
      appendTarget.appendChild(block);

      label.addEventListener('click', () => {
        const nowFolded = block.classList.toggle('folded');
        label.classList.toggle('is-collapsed');
        if (nowFolded) block.classList.remove('user-expanded');
        else block.classList.add('user-expanded');
      });

      callBlocks[callId] = block;
      callScrollers[callId] = createAutoScroller(block);
      scroller.scroll();
      return;
    }

    // Non-label chunk: append text to existing block
    const chunkText = data.text || data;

    let block;
    if (callId && callBlocks[callId]) {
      block = callBlocks[callId];
      block.appendChild(document.createTextNode(chunkText));
    } else {
      const fallback = taskId
        ? getTaskGroupBody(taskId)
        : (currentSessionName ? getSessionGroupBody(currentSessionName) : (currentSection || logOutput));
      block = fallback ? fallback.lastElementChild : null;
      if (!block || !block.classList.contains('log-text')) {
        block = document.createElement('div');
        block.className = 'log-text';
        if (fallback) fallback.appendChild(block);
      }
      block.appendChild(document.createTextNode(chunkText));
    }
    if (callId && callScrollers[callId]) {
      callScrollers[callId].scroll();
    } else if (block) {
      block.scrollTop = block.scrollHeight;
    }
    if (taskId && taskBodyScrollers[taskId]) {
      taskBodyScrollers[taskId].scroll();
    }
    if (currentSessionName && sessionBodyScrollers[currentSessionName]) {
      sessionBodyScrollers[currentSessionName].scroll();
    }
    scroller.scroll();
  });

  on('log:tokens', ({ data }) => {
    totalTokens += data.total || 0;
    updateTokenBadge();
  });

  on('stage:error', ({ stage, data }) => {
    const msg = data.message || data;
    const el = document.createElement('div');
    el.className = 'log-text';
    el.style.color = 'var(--red)';
    el.textContent = `[ERROR] ${stage}: ${msg}`;
    (currentSection || logOutput).appendChild(el);
    scroller.scroll();
  });
}

// --- Session group helpers ---

function isSessionLabel(callId) {
  return SESSION_LABELS.has(callId);
}

function getOrCreateSessionGroup(name) {
  if (sessionGroups[name]) return sessionGroups[name];
  if (!currentSection) return null;

  const group = document.createElement('div');
  group.className = 'task-group';  // Reuse task-group styling
  group.dataset.session = name;

  const header = document.createElement('div');
  header.className = 'task-group-header';
  header.textContent = name;

  const body = document.createElement('div');
  body.className = 'task-group-body';

  sessionBodyScrollers[name] = createAutoScroller(body);

  header.addEventListener('click', () => {
    const nowCollapsed = body.classList.toggle('collapsed');
    header.classList.toggle('is-collapsed');
    if (nowCollapsed) body.classList.remove('user-expanded');
    else body.classList.add('user-expanded');
  });

  group.appendChild(header);
  group.appendChild(body);
  currentSection.appendChild(group);

  sessionGroups[name] = group;
  return group;
}

function getSessionGroupBody(name) {
  const group = sessionGroups[name];
  if (!group) return currentSection;
  return group.querySelector('.task-group-body') || currentSection;
}

function collapseCurrentSession() {
  if (!currentSessionName || !sessionGroups[currentSessionName]) return;
  const group = sessionGroups[currentSessionName];
  const body = group.querySelector('.task-group-body');
  const header = group.querySelector('.task-group-header');
  if (body && !body.classList.contains('user-expanded')) {
    body.classList.add('collapsed');
    if (header) header.classList.add('is-collapsed');
  }
}

// --- Task group helpers ---

function getOrCreateTaskGroup(taskId) {
  if (taskGroups[taskId]) return taskGroups[taskId];
  if (!currentSection) return null;

  // Collapse current session when tasks start
  collapseCurrentSession();
  currentSessionName = null;

  const group = document.createElement('div');
  group.className = 'task-group';
  group.dataset.taskId = taskId;

  const header = document.createElement('div');
  header.className = 'task-group-header';
  const desc = taskDescriptions[taskId];
  header.textContent = desc ? `Task [${taskId}]: ${desc}` : `Task [${taskId}]`;

  const body = document.createElement('div');
  body.className = 'task-group-body';

  taskBodyScrollers[taskId] = createAutoScroller(body);

  header.addEventListener('click', () => {
    const nowCollapsed = body.classList.toggle('collapsed');
    header.classList.toggle('is-collapsed');
    if (nowCollapsed) body.classList.remove('user-expanded');
    else body.classList.add('user-expanded');
  });

  group.appendChild(header);
  group.appendChild(body);
  currentSection.appendChild(group);

  taskGroups[taskId] = group;
  scroller.scroll();
  return group;
}

function getTaskGroupBody(taskId) {
  const group = taskGroups[taskId];
  if (!group) return currentSection;
  return group.querySelector('.task-group-body') || currentSection;
}

// --- Timer ---

function startTimer() {
  timerStart = Date.now();
  updateTimerBadge();
  timerInterval = setInterval(updateTimerBadge, 1000);
}

function stopTimer() {
  if (timerInterval) clearInterval(timerInterval);
  timerInterval = null;
  timerStart = null;
  if (timerBadge) timerBadge.textContent = '';
}

function updateTimerBadge() {
  if (!timerBadge || !timerStart) return;
  const elapsed = Math.floor((Date.now() - timerStart) / 1000);
  const m = Math.floor(elapsed / 60);
  const s = elapsed % 60;
  timerBadge.textContent = m > 0 ? `${m}m ${s}s` : `${s}s`;
}

// --- Utilities ---

function wireCopyButton(btnId, sourceEl) {
  const btn = document.getElementById(btnId);
  if (!btn || !sourceEl) return;
  btn.addEventListener('click', () => {
    const text = sourceEl.innerText;
    try {
      // Fallback for non-HTTPS contexts
      const textarea = document.createElement('textarea');
      textarea.value = text;
      textarea.style.cssText = 'position:fixed;opacity:0';
      document.body.appendChild(textarea);
      textarea.select();
      document.execCommand('copy');
      document.body.removeChild(textarea);
      btn.textContent = 'Copied!';
    } catch {
      navigator.clipboard.writeText(text).then(() => {
        btn.textContent = 'Copied!';
      }).catch(() => {
        btn.textContent = 'Failed';
      });
    }
    setTimeout(() => { btn.textContent = 'Copy'; }, 1500);
  });
}

function updateTokenBadge() {
  if (!tokenBadge) return;
  if (totalTokens === 0) {
    tokenBadge.textContent = '';
    return;
  }
  let display;
  if (totalTokens >= 1e9)      display = `${(totalTokens / 1e9).toFixed(1)}B tokens`;
  else if (totalTokens >= 1e6) display = `${(totalTokens / 1e6).toFixed(1)}M tokens`;
  else if (totalTokens >= 1e3) display = `${(totalTokens / 1e3).toFixed(1)}k tokens`;
  else                         display = `${totalTokens} tokens`;
  tokenBadge.textContent = display;
}
