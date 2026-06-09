import { connectSSE } from './api.js';
import { initPipelineUI, syncFromAPI } from './pipeline-ui.js';
import { initLogViewer } from './log-viewer.js';
import { initProcessViewer } from './process-viewer.js';
import { initModal } from './modal.js';
import { initSettings } from './settings.js';
import { syncSystemStatus } from './shared.js';

initPipelineUI();
initLogViewer();
initProcessViewer();
initModal();
initSettings();

connectSSE();
syncFromAPI();

async function checkRuntime() {
  const el = document.getElementById('system-status');
  if (!el) return;
  try {
    const res = await fetch('/api/runtime/status');
    const data = await res.json();
    el.dataset.runtime = data.connected ? 'connected' : 'disconnected';
  } catch {
    el.dataset.runtime = 'disconnected';
  }
  syncSystemStatus();
}
checkRuntime();
setInterval(checkRuntime, 30000);
