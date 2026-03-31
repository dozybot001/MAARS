const BASE = '/api'

/**
 * Read API key from localStorage (set via settings UI or console).
 * Returns auth headers object, empty if no key configured.
 */
function authHeaders() {
  const key = localStorage.getItem('maars_api_key')
  return key ? { Authorization: `Bearer ${key}` } : {}
}

export async function startPipeline(input) {
  const res = await fetch(`${BASE}/pipeline/start`, {
    method: 'POST',
    headers: { 'Content-Type': 'application/json', ...authHeaders() },
    body: JSON.stringify({ input }),
  })
  if (!res.ok) throw new Error(`Start failed: ${res.status}`)
  return res.json()
}

export async function fetchStatus() {
  const res = await fetch(`${BASE}/pipeline/status`, {
    headers: authHeaders(),
  })
  if (!res.ok) throw new Error(`Status fetch failed: ${res.status}`)
  return res.json()
}

export async function stopPipeline() {
  const res = await fetch(`${BASE}/pipeline/stop`, {
    method: 'POST',
    headers: authHeaders(),
  })
  if (!res.ok) throw new Error(`Stop failed: ${res.status}`)
  return res.json()
}

export async function stageAction(stageName, action) {
  const res = await fetch(`${BASE}/stage/${stageName}/${action}`, {
    method: 'POST',
    headers: authHeaders(),
  })
  if (!res.ok) throw new Error(`${action} failed: ${res.status}`)
  return res.json()
}

export async function checkDockerStatus() {
  const res = await fetch(`${BASE}/docker/status`, {
    headers: authHeaders(),
  })
  if (!res.ok) throw new Error(`Docker status failed: ${res.status}`)
  return res.json()
}

// --- Session management ---

export async function listSessions() {
  const res = await fetch(`${BASE}/sessions`, {
    headers: authHeaders(),
  })
  if (!res.ok) throw new Error(`List sessions failed: ${res.status}`)
  return res.json()
}

export async function getSession(id) {
  const res = await fetch(`${BASE}/sessions/${encodeURIComponent(id)}`, {
    headers: authHeaders(),
  })
  if (!res.ok) throw new Error(`Get session failed: ${res.status}`)
  return res.json()
}

export async function getSessionState(id) {
  const res = await fetch(`${BASE}/sessions/${encodeURIComponent(id)}/state`, {
    headers: authHeaders(),
  })
  if (!res.ok) throw new Error(`Get session state failed: ${res.status}`)
  return res.json()
}

export async function deleteSession(id) {
  const res = await fetch(`${BASE}/sessions/${encodeURIComponent(id)}`, {
    method: 'DELETE',
    headers: authHeaders(),
  })
  if (!res.ok) throw new Error(`Delete session failed: ${res.status}`)
  return res.json()
}
