/**
 * Shared DOM helpers used by multiple viewer modules.
 */

/**
 * Wire a click toggle: clicking `trigger` collapses/expands `target`.
 */
function setupToggle(trigger, target) {
  trigger.addEventListener('click', () => {
    const collapsed = target.classList.toggle('collapsed');
    trigger.classList.toggle('is-collapsed');
    target.classList.toggle('user-expanded', !collapsed);
  });
}

/**
 * Create a fold group (label + body) inside a parent container.
 * Used for all collapsible levels: phase, task, tool calls.
 * Returns { label, body }.
 */
export function createFold(parent, labelText, level) {
  const label = document.createElement('div');
  label.className = 'fold-label';
  if (level) label.dataset.level = level;
  label.textContent = labelText;

  const body = document.createElement('div');
  body.className = 'fold-body';

  setupToggle(label, body);

  parent.appendChild(label);
  parent.appendChild(body);
  return { label, body };
}

/**
 * Append a collapsible separator + section to a container.
 * Returns the new section element.
 */
export function appendSeparator(container, label, scroller) {
  const sep = document.createElement('div');
  sep.className = 'log-separator';
  sep.textContent = `── ${label} ──`;

  const section = document.createElement('div');
  section.className = 'log-section';

  setupToggle(sep, section);

  container.appendChild(sep);
  container.appendChild(section);
  scroller.scroll();
  return section;
}

/**
 * Wire a copy-to-clipboard button.
 */
export function wireCopyButton(btnId, sourceEl) {
  const btn = document.getElementById(btnId);
  if (!btn || !sourceEl) return;
  btn.addEventListener('click', () => {
    const text = sourceEl.innerText;
    navigator.clipboard.writeText(text)
      .then(() => { btn.textContent = 'Copied!'; setTimeout(() => { btn.textContent = 'Copy'; }, 1500); })
      .catch(() => { btn.textContent = 'Failed'; setTimeout(() => { btn.textContent = 'Copy'; }, 1500); });
  });
}
