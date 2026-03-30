const BASE = '/api'

export async function startPipeline(input) {
  const res = await fetch(`${BASE}/pipeline/start`, {
    method: 'POST',
    headers: { 'Content-Type': 'application/json' },
    body: JSON.stringify({ input }),
  })
  if (!res.ok) throw new Error(`Start failed: ${res.status}`)
  return res.json()
}

export async function fetchStatus() {
  const res = await fetch(`${BASE}/pipeline/status`)
  if (!res.ok) throw new Error(`Status fetch failed: ${res.status}`)
  return res.json()
}

export async function stageAction(stageName, action) {
  const res = await fetch(`${BASE}/stage/${stageName}/${action}`, {
    method: 'POST',
  })
  if (!res.ok) throw new Error(`${action} failed: ${res.status}`)
  return res.json()
}

export async function checkDockerStatus() {
  const res = await fetch(`${BASE}/docker/status`)
  if (!res.ok) throw new Error(`Docker status failed: ${res.status}`)
  return res.json()
}
