import { connectSSE } from './api.js';
import { initPipelineUI } from './pipeline-ui.js';
import { initLogViewer } from './log-viewer.js';
import { initProcessViewer } from './process-viewer.js';
import { initModal } from './modal.js';

initPipelineUI();
initLogViewer();
initProcessViewer();
initModal();

connectSSE();

async function checkDocker() {
  const el = document.getElementById('docker-status');
  if (!el) return;
  try {
    const res = await fetch('/api/docker/status');
    const data = await res.json();
    el.classList.remove('status-unknown', 'status-connected', 'status-disconnected');
    if (data.connected) {
      el.classList.add('status-connected');
      el.title = 'Docker connected';
    } else {
      el.classList.add('status-disconnected');
      el.title = `Docker: ${data.error || 'not available'}`;
    }
  } catch {
    el.classList.remove('status-unknown', 'status-connected', 'status-disconnected');
    el.classList.add('status-disconnected');
    el.title = 'Cannot check Docker status';
  }
}
checkDocker();
setInterval(checkDocker, 30000);
