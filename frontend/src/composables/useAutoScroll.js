import { onUnmounted } from 'vue'

/**
 * Auto-scroll manager for a DOM element.
 * Scrolls to bottom on new content.
 * Unlocks ONLY on user wheel/touch scroll, not on programmatic scroll.
 * Re-locks when user scrolls back to bottom.
 */
export function useAutoScroll(elRef) {
  let locked = true
  let wheelHandler = null
  let touchHandler = null

  function attach(el) {
    if (!el) return
    wheelHandler = () => {
      const atBottom = el.scrollHeight - el.scrollTop - el.clientHeight < 30
      locked = atBottom
    }
    touchHandler = wheelHandler

    el.addEventListener('wheel', wheelHandler, { passive: true })
    el.addEventListener('touchmove', touchHandler, { passive: true })
  }

  function detach(el) {
    if (!el) return
    if (wheelHandler) el.removeEventListener('wheel', wheelHandler)
    if (touchHandler) el.removeEventListener('touchmove', touchHandler)
  }

  function scroll() {
    const el = elRef.value
    if (locked && el) {
      el.scrollTop = el.scrollHeight
    }
  }

  function reset() {
    const el = elRef.value
    locked = true
    if (el) el.scrollTop = el.scrollHeight
  }

  function isLocked() {
    return locked
  }

  // Auto-attach when ref becomes available
  let attachedEl = null
  const checkAttach = () => {
    const el = elRef.value
    if (el && el !== attachedEl) {
      if (attachedEl) detach(attachedEl)
      attach(el)
      attachedEl = el
    }
  }

  // Use a simple interval to check for element availability
  const interval = setInterval(checkAttach, 100)
  checkAttach()

  onUnmounted(() => {
    clearInterval(interval)
    if (attachedEl) detach(attachedEl)
  })

  return { scroll, reset, isLocked }
}

/**
 * Standalone auto-scroller (not tied to Vue lifecycle).
 * Used for dynamically created DOM elements inside LogViewer.
 * Call destroy() to remove event listeners when the element is discarded.
 */
export function createAutoScroller(el) {
  let locked = true

  function onUserScroll() {
    const atBottom = el.scrollHeight - el.scrollTop - el.clientHeight < 30
    locked = atBottom
  }

  el.addEventListener('wheel', onUserScroll, { passive: true })
  el.addEventListener('touchmove', onUserScroll, { passive: true })

  return {
    scroll() {
      if (locked) el.scrollTop = el.scrollHeight
    },
    reset() {
      locked = true
      el.scrollTop = el.scrollHeight
    },
    isLocked() {
      return locked
    },
    destroy() {
      el.removeEventListener('wheel', onUserScroll)
      el.removeEventListener('touchmove', onUserScroll)
    },
  }
}
