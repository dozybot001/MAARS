/**
 * Simple modal for displaying document content (markdown + KaTeX math).
 */

import { sessionArtifactUrl } from './api.js';

let overlay, title, content;

function getRenderMathInElement() {
  if (typeof globalThis.renderMathInElement === 'function') {
    return globalThis.renderMathInElement;
  }
  return undefined;
}

/**
 * After markdown HTML is in `root`, replace TeX delimiters with KaTeX.
 * Skips pre/code (and other ignored tags) so fenced code is untouched.
 */
function renderModalMath(root) {
  const render = getRenderMathInElement();
  if (!render || typeof globalThis.katex === 'undefined') return;
  try {
    render(root, {
      delimiters: [
        { left: '$$', right: '$$', display: true },
        { left: '\\[', right: '\\]', display: true },
        { left: '\\(', right: '\\)', display: false },
        { left: '$', right: '$', display: false },
      ],
      ignoredTags: ['script', 'noscript', 'style', 'textarea', 'pre', 'code'],
      throwOnError: false,
      strict: false,
      trust: false,
      errorHandler: () => {},
    });
  } catch (_) {
    /* broken LaTeX — leave raw text */
  }
}

function rewriteSessionAssetUrls(root) {
  if (!root) return;
  for (const img of root.querySelectorAll('img')) {
    const src = img.getAttribute('src') || '';
    if (src.startsWith('artifacts/')) {
      img.src = sessionArtifactUrl(src);
      img.loading = 'lazy';
    }
  }
  for (const link of root.querySelectorAll('a')) {
    const href = link.getAttribute('href') || '';
    if (href.startsWith('artifacts/')) {
      link.href = sessionArtifactUrl(href);
      link.target = '_blank';
      link.rel = 'noopener noreferrer';
    }
  }
}

export function initModal() {
  overlay = document.getElementById('modal-overlay');
  title = document.getElementById('modal-title');
  content = document.getElementById('modal-content');

  document.getElementById('modal-close').addEventListener('click', hideModal);
  overlay.addEventListener('click', (e) => {
    if (e.target === overlay) hideModal();
  });
  document.addEventListener('keydown', (e) => {
    if (e.key === 'Escape' && !overlay.classList.contains('hidden')) hideModal();
  });
}

export function showModal(titleText, bodyText) {
  title.textContent = titleText;
  if (typeof marked !== 'undefined' && marked.parse) {
    content.innerHTML = marked.parse(bodyText || '');
    content.classList.remove('plain-text');
    rewriteSessionAssetUrls(content);
    renderModalMath(content);
  } else {
    content.textContent = bodyText;
    content.classList.add('plain-text');
  }
  overlay.classList.remove('hidden');
}

export function hideModal() {
  overlay.classList.add('hidden');
}
