/**
 * Lightweight pub/sub event bus.
 * High-frequency data (chunks, tokens) bypasses Vue reactivity via this bus.
 */
const listeners = {}

export function on(event, fn) {
  if (!listeners[event]) listeners[event] = []
  listeners[event].push(fn)
}

export function off(event, fn) {
  if (!listeners[event]) return
  listeners[event] = listeners[event].filter((f) => f !== fn)
}

export function emit(event, data) {
  if (!listeners[event]) return
  for (const fn of listeners[event]) fn(data)
}
