import { emit } from './events.js';
import { syncSystemStatus } from './shared.js';

const BASE = '/api';

export async function startPipeline(input) {
  const res = await fetch(`${BASE}/pipeline/start`, {
    method: 'POST',
    headers: { 'Content-Type': 'application/json' },
    body: JSON.stringify({ input }),
  });
  if (!res.ok) throw new Error(`Start failed: ${res.status}`);
  return res.json();
}

export async function pipelineAction(action) {
  const res = await fetch(`${BASE}/pipeline/${action}`, { method: 'POST' });
  if (!res.ok) throw new Error(`${action} failed: ${res.status}`);
  return res.json();
}

export async function fetchStatus() {
  const res = await fetch(`${BASE}/pipeline/status`);
  if (!res.ok) return null;
  return res.json();
}

export async function fetchPlanTree() {
  const res = await fetch(`${BASE}/session/plan/tree`);
  if (!res.ok) return null;
  return res.json();
}

export async function fetchPlanList() {
  const res = await fetch(`${BASE}/session/plan/list`);
  if (!res.ok) return null;
  return res.json();
}

export async function fetchMeta() {
  const res = await fetch(`${BASE}/session/meta`);
  if (!res.ok) return null;
  return res.json();
}

export async function listDocuments(prefix) {
  const res = await fetch(`${BASE}/session/documents/list/${encodeURIComponent(prefix)}`);
  if (!res.ok) return [];
  return res.json();
}

export async function fetchTaskOutput(taskId) {
  const res = await fetch(`${BASE}/session/tasks/${encodeURIComponent(taskId)}`);
  if (!res.ok) return null;
  return res.json();
}

export async function fetchDocument(name) {
  const res = await fetch(`${BASE}/session/documents/${encodeURIComponent(name)}`);
  if (!res.ok) return null;
  return res.json();
}

export function sessionArtifactUrl(relativePath) {
  const cleaned = String(relativePath || '').replace(/^artifacts\//, '').replace(/^\/+/, '');
  const encoded = cleaned
    .split('/')
    .filter(Boolean)
    .map((segment) => encodeURIComponent(segment))
    .join('/');
  return `${BASE}/session/artifacts/${encoded}`;
}

function setSSEStatus(state) {
  const el = document.getElementById('system-status');
  if (el) el.dataset.sse = state;
  syncSystemStatus();
}

export function connectSSE() {
  const source = new EventSource(`${BASE}/events`);
  source.onopen = () => {
    setSSEStatus('connected', 'SSE connected');
  };
  source.onmessage = (e) => {
    setSSEStatus('connected', 'SSE connected');
    try {
      const event = JSON.parse(e.data);
      emit('sse', event);
    } catch {
      console.warn('[SSE] Parse error:', e.data);
    }
  };
  source.onerror = () => {
    setSSEStatus('disconnected', 'SSE disconnected, reconnecting...');
    console.warn('[SSE] Connection lost, reconnecting...');
  };
  return source;
}
