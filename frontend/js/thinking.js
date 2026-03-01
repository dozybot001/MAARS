/**
 * MAARS thinking - AI thinking stream (plan + task) and task output.
 * Inline createThinkingArea logic; single thinking area; output in Output view.
 */
(function () {
    'use strict';

    const escapeHtml = window.MAARS?.utils?.escapeHtml || ((s) => (s == null ? '' : String(s).replace(/&/g, '&amp;').replace(/</g, '&lt;').replace(/>/g, '&gt;')));
    const escapeHtmlAttr = window.MAARS?.utils?.escapeHtmlAttr || ((s) => (s == null ? '' : String(s).replace(/&/g, '&amp;').replace(/"/g, '&quot;').replace(/</g, '&lt;').replace(/>/g, '&gt;')));
    const truncateForDisplay = (s, maxLen) => {
        if (s == null || typeof s !== 'string') return '';
        const str = String(s).trim();
        if (str.length <= maxLen) return str;
        return str.slice(0, maxLen - 3) + '...';
    };
    const RENDER_THROTTLE_MS = 120;
    const RENDER_THROTTLE_LARGE_MS = 250;
    const LARGE_CONTENT_CHARS = 6000;

    const PREFIX = 'thinking';
    const CONTENT_EL = 'planAgentThinkingContent';
    const AREA_EL = 'planAgentThinkingArea';
    const BLOCK_CLASS = 'plan-agent-thinking-block';

    const state = window.MAARS.state || {};
    state[`${PREFIX}ThinkingBlocks`] = state[`${PREFIX}ThinkingBlocks`] || [];
    state[`${PREFIX}ThinkingUserScrolled`] = state[`${PREFIX}ThinkingUserScrolled`] ?? false;
    state[`${PREFIX}ThinkingBlockUserScrolled`] = state[`${PREFIX}ThinkingBlockUserScrolled`] || {};
    state[`${PREFIX}LastUpdatedBlockKey`] = state[`${PREFIX}LastUpdatedBlockKey`] || '';
    state[`${PREFIX}ScheduleCounter`] = state[`${PREFIX}ScheduleCounter`] ?? 0;
    state[`${PREFIX}PlanCounter`] = state[`${PREFIX}PlanCounter`] ?? 0;
    state[`${PREFIX}PlanStreamingKey`] = state[`${PREFIX}PlanStreamingKey`] ?? '';
    state[`${PREFIX}IdeaCounter`] = state[`${PREFIX}IdeaCounter`] ?? 0;
    state[`${PREFIX}IdeaStreamingKey`] = state[`${PREFIX}IdeaStreamingKey`] ?? '';
    state.taskOutputs = state.taskOutputs || {};
    state.outputUserScrolled = state.outputUserScrolled ?? false;
    state.outputBlockUserScrolled = state.outputBlockUserScrolled || {};
    state.outputLastUpdatedKey = state.outputLastUpdatedKey || '';
    window.MAARS.state = state;

    let _renderScheduled = null;

    function renderThinking(skipHighlight) {
        const el = document.getElementById(CONTENT_EL);
        const area = document.getElementById(AREA_EL);
        if (!el) return;
        const blocks = state[`${PREFIX}ThinkingBlocks`];
        let html = '';
        let i = 0;
        while (i < blocks.length) {
            const block = blocks[i];
            if (block.blockType === 'schedule') {
                const scheduleBlocks = [];
                while (i < blocks.length && blocks[i].blockType === 'schedule') {
                    scheduleBlocks.push(blocks[i]);
                    i++;
                }
                const scheduleHtml = scheduleBlocks.map((b) => {
                    const si = b.scheduleInfo || {};
                    const parts = [];
                    if (si.task_id) parts.push(`Task ${si.task_id}`);
                    if (si.operation) parts.push(si.operation);
                    if (si.turn != null) parts.push(`Turn ${si.turn}${si.max_turns != null ? `/${si.max_turns}` : ''}`);
                    if (si.tool_name) {
                        const argsDisplay = si.tool_args_preview || (si.tool_args ? truncateForDisplay(si.tool_args, 60) : null);
                        parts.push(si.tool_name + (argsDisplay ? `(${argsDisplay})` : ''));
                    }
                    const scheduleText = parts.length ? parts.join(' · ') : 'Scheduling';
                    return `<div class="${BLOCK_CLASS} ${BLOCK_CLASS}--schedule" data-block-key="${(b.key || '').replace(/"/g, '&quot;')}"><div class="${BLOCK_CLASS}-schedule-text">${escapeHtml(scheduleText)}</div></div>`;
                }).join('');
                html += `<div class="plan-agent-schedule-group">${scheduleHtml}</div>`;
                continue;
            }
            i++;
            const agentLabel = (block.source || 'Thinking').charAt(0).toUpperCase() + (block.source || 'thinking').slice(1);
            const op = block.operation || '—';
            const tid = block.taskId != null ? String(block.taskId) : '—';
            let headerText = `${agentLabel} | ${op} | ${tid}`;
            const si = block.scheduleInfo;
            if (si) {
                const parts = [];
                if (si.operation) parts.push(si.operation);
                if (si.turn != null) parts.push(`Turn ${si.turn}${si.max_turns != null ? `/${si.max_turns}` : ''}`);
                if (si.tool_name) {
                    const argsDisplay = si.tool_args_preview || (si.tool_args ? truncateForDisplay(si.tool_args, 50) : null);
                    parts.push(si.tool_name + (argsDisplay ? `(${argsDisplay})` : ''));
                }
                if (parts.length) headerText += ' · ' + parts.join(' · ');
            }
            const raw = block.content || '';
            let blockHtml = raw ? (typeof marked !== 'undefined' ? marked.parse(raw) : raw) : '';
            if (blockHtml && typeof DOMPurify !== 'undefined') blockHtml = DOMPurify.sanitize(blockHtml);
            html += `<div class="${BLOCK_CLASS}" data-block-key="${(block.key || '').replace(/"/g, '&quot;')}"><div class="${BLOCK_CLASS}-header">${escapeHtml(headerText || '')}</div><div class="${BLOCK_CLASS}-body">${blockHtml}</div></div>`;
        }
        const wasNearBottom = el.scrollHeight - el.scrollTop - el.clientHeight < 80;
        const savedScrollTops = {};
        el.querySelectorAll(`.${BLOCK_CLASS}`).forEach((blockEl) => {
            const key = blockEl.getAttribute('data-block-key') || '';
            const body = blockEl.querySelector(`.${BLOCK_CLASS}-body`);
            if (body) savedScrollTops[key] = body.scrollTop;
        });
        try {
            el.innerHTML = html || '';
            if (!skipHighlight && typeof hljs !== 'undefined') {
                const codeBlocks = el.querySelectorAll('pre code');
                if (codeBlocks.length > 0 && codeBlocks.length <= 15) {
                    codeBlocks.forEach((node) => { try { hljs.highlightElement(node); } catch (_) {} });
                }
            }
        } catch (_) {
            el.textContent = blocks.map((b) => b.content || '').join('\n\n');
        }
        if (!state[`${PREFIX}ThinkingUserScrolled`] && wasNearBottom) {
            requestAnimationFrame(() => { requestAnimationFrame(() => { el.scrollTop = el.scrollHeight; }); });
        }
        state[`${PREFIX}ThinkingBlockUserScrolled`] = state[`${PREFIX}ThinkingBlockUserScrolled`] || {};
        const lastKey = state[`${PREFIX}LastUpdatedBlockKey`] || '';
        el.querySelectorAll(`.${BLOCK_CLASS}`).forEach((blockEl) => {
            const key = blockEl.getAttribute('data-block-key') || '';
            const body = blockEl.querySelector(`.${BLOCK_CLASS}-body`);
            if (!body) return;
            const shouldAutoScroll = key === lastKey && !state[`${PREFIX}ThinkingBlockUserScrolled`][key];
            if (shouldAutoScroll) requestAnimationFrame(() => { body.scrollTop = body.scrollHeight; });
            else if (savedScrollTops[key] != null) body.scrollTop = savedScrollTops[key];
            body.addEventListener('scroll', function onBlockScroll() {
                const nearBottom = body.scrollHeight - body.scrollTop - body.clientHeight < 40;
                state[`${PREFIX}ThinkingBlockUserScrolled`][key] = !nearBottom;
            }, { passive: true });
        });
        if (area && blocks.length) area.classList.add('has-content');
    }

    function scheduleRender() {
        if (_renderScheduled) return;
        const totalChars = state[`${PREFIX}ThinkingBlocks`].reduce((s, b) => s + (b.content || '').length, 0);
        const throttle = totalChars > LARGE_CONTENT_CHARS ? RENDER_THROTTLE_LARGE_MS : RENDER_THROTTLE_MS;
        _renderScheduled = setTimeout(() => {
            _renderScheduled = null;
            renderThinking(true);
        }, throttle);
    }

    function clearThinking(opts) {
        const keepOutputs = opts && opts.keepOutputs === true;
        state[`${PREFIX}ThinkingBlocks`] = [];
        state[`${PREFIX}ThinkingUserScrolled`] = false;
        state[`${PREFIX}ThinkingBlockUserScrolled`] = {};
        state[`${PREFIX}LastUpdatedBlockKey`] = '';
        state[`${PREFIX}ScheduleCounter`] = 0;
        state[`${PREFIX}PlanCounter`] = 0;
        state[`${PREFIX}PlanStreamingKey`] = '';
        state[`${PREFIX}IdeaCounter`] = 0;
        state[`${PREFIX}IdeaStreamingKey`] = '';
        if (!keepOutputs) {
            state.taskOutputs = {};
            state.outputUserScrolled = false;
            state.outputBlockUserScrolled = {};
            state.outputLastUpdatedKey = '';
        }
        const el = document.getElementById(CONTENT_EL);
        const area = document.getElementById(AREA_EL);
        if (el) el.innerHTML = '';
        if (area) area.classList.remove('has-content');
        renderOutput();
    }

    function appendChunk(chunk, taskId, operation, scheduleInfo, source) {
        const blocksKey = `${PREFIX}ThinkingBlocks`;
        const planStreamingKey = `${PREFIX}PlanStreamingKey`;
        const ideaStreamingKey = `${PREFIX}IdeaStreamingKey`;
        const scheduleCounterKey = `${PREFIX}ScheduleCounter`;
        const planCounterKey = `${PREFIX}PlanCounter`;
        const ideaCounterKey = `${PREFIX}IdeaCounter`;
        const lastUpdatedKey = `${PREFIX}LastUpdatedBlockKey`;
        const isIdea = source === 'idea' || operation === 'Refine';

        if (!chunk && scheduleInfo != null) {
            state[planStreamingKey] = '';
            state[ideaStreamingKey] = '';
            if (scheduleInfo.tool_name) {
                state[scheduleCounterKey] = (state[scheduleCounterKey] || 0) + 1;
                const key = `schedule_${state[scheduleCounterKey]}`;
                state[blocksKey].push({ key, blockType: 'schedule', scheduleInfo });
                state[lastUpdatedKey] = key;
                scheduleRender();
            }
            return;
        }
        if (taskId == null && isIdea && chunk) {
            let block = state[ideaStreamingKey] ? state[blocksKey].find((b) => b.key === state[ideaStreamingKey]) : null;
            state[planStreamingKey] = '';
            if (block) {
                block.content += chunk;
                if (scheduleInfo != null) block.scheduleInfo = scheduleInfo;
                state[lastUpdatedKey] = block.key;
            } else {
                state[ideaCounterKey] = (state[ideaCounterKey] || 0) + 1;
                const key = `idea_${state[ideaCounterKey]}`;
                block = { key, taskId: null, operation: operation || 'Refine', content: chunk, scheduleInfo: scheduleInfo || null, source: 'idea' };
                state[blocksKey].push(block);
                state[ideaStreamingKey] = key;
                state[lastUpdatedKey] = key;
            }
            scheduleRender();
            return;
        }
        if (taskId == null && chunk) {
            let block = state[planStreamingKey] ? state[blocksKey].find((b) => b.key === state[planStreamingKey]) : null;
            state[ideaStreamingKey] = '';
            if (block) {
                block.content += chunk;
                if (scheduleInfo != null) block.scheduleInfo = scheduleInfo;
                state[lastUpdatedKey] = block.key;
            } else {
                state[planCounterKey] = (state[planCounterKey] || 0) + 1;
                const key = `plan_${state[planCounterKey]}`;
                block = { key, taskId: null, operation: operation || 'Plan', content: chunk, scheduleInfo: scheduleInfo || null, source: 'plan' };
                state[blocksKey].push(block);
                state[planStreamingKey] = key;
                state[lastUpdatedKey] = key;
            }
            scheduleRender();
            return;
        }
        state[planStreamingKey] = '';
        state[ideaStreamingKey] = '';
        const key = (taskId != null && operation != null) ? `${String(taskId)}::${String(operation)}` : '_default';
        let block = state[blocksKey].find((b) => b.key === key);
        if (!block) {
            block = { key, taskId, operation, content: '', scheduleInfo: null, source: source || 'task' };
            state[blocksKey].push(block);
        }
        if (chunk) block.content += chunk;
        if (scheduleInfo != null) block.scheduleInfo = scheduleInfo;
        state[lastUpdatedKey] = key;
        scheduleRender();
    }

    function applyHighlight() {
        const el = document.getElementById(CONTENT_EL);
        if (!el || typeof hljs === 'undefined') return;
        requestIdleCallback(() => {
            el.querySelectorAll('pre code').forEach((node) => { try { hljs.highlightElement(node); } catch (_) {} });
        }, { timeout: 500 });
    }

    (function initThinkingArea() {
        const el = document.getElementById(CONTENT_EL);
        if (!el) return;
        el.addEventListener('scroll', () => {
            const nearBottom = el.scrollHeight - el.scrollTop - el.clientHeight < 80;
            state[`${PREFIX}ThinkingUserScrolled`] = !nearBottom;
        }, { passive: true });
        const area = document.getElementById(AREA_EL);
        if (!area) return;
        const scheduleModifier = `${BLOCK_CLASS}--schedule`;
        area.addEventListener('click', (e) => {
            const block = e.target.closest(`.${BLOCK_CLASS}`);
            if (!block || block.classList.contains(scheduleModifier)) return;
            const allBlocks = area.querySelectorAll(`.${BLOCK_CLASS}:not(.${scheduleModifier})`);
            const wasFocused = block.classList.contains('is-focused');
            allBlocks.forEach((b) => b.classList.remove('is-focused'));
            if (!wasFocused) block.classList.add('is-focused');
        });
    })();

    function renderOutput() {
        const el = document.getElementById('taskAgentOutputContent');
        const area = document.getElementById('taskAgentOutputArea');
        if (!el || !area) return;
        const outputs = state.taskOutputs;
        if (outputs.refine !== undefined) {
            outputs.idea = outputs.refine;
            delete outputs.refine;
        }
        const keys = Object.keys(outputs).sort((a, b) => {
            if (a === 'idea') return -1;
            if (b === 'idea') return 1;
            if (a.startsWith('task_') && b.startsWith('task_')) {
                const na = parseInt(a.slice(6), 10);
                const nb = parseInt(b.slice(6), 10);
                if (!isNaN(na) && !isNaN(nb)) return na - nb;
            }
            return String(a).localeCompare(b);
        });
        const wasNearBottom = el.scrollHeight - el.scrollTop - el.clientHeight < 80;
        const savedScrollTops = {};
        el.querySelectorAll('.task-agent-output-block').forEach((blockEl) => {
            const key = blockEl.getAttribute('data-task-id') || '';
            const body = blockEl.querySelector('.task-agent-output-block-body');
            if (body) savedScrollTops[key] = body.scrollTop;
        });
        if (keys.length === 0) {
            el.innerHTML = '';
            return;
        }
        let html = '';
        for (const taskId of keys) {
            const raw = outputs[taskId];
            let content = '';
            let displayLabel = taskId === 'idea' ? 'Refine' : (taskId.startsWith('task_') ? 'Task ' + taskId.slice(6) : 'Task ' + (taskId || ''));
            if (typeof raw === 'object' && raw !== null && raw.label) {
                displayLabel = raw.label;
                // Object with 'content' string (e.g. from Agent Finish tool) → render content as markdown
                if ('content' in raw && typeof raw.content === 'string') {
                    const text = raw.content || '';
                    content = text ? (typeof marked !== 'undefined' ? marked.parse(text) : text) : '';
                } else {
                    const str = JSON.stringify(raw, null, 2);
                    content = typeof marked !== 'undefined' ? marked.parse('```json\n' + str + '\n```') : '<pre>' + str + '</pre>';
                }
            } else {
                content = (raw || '') ? (typeof marked !== 'undefined' ? marked.parse(String(raw)) : String(raw)) : '';
            }
            if (content && typeof DOMPurify !== 'undefined') content = DOMPurify.sanitize(content);
            html += `<div class="task-agent-output-block" data-task-id="${escapeHtml(taskId || '')}" data-label="${escapeHtmlAttr(displayLabel || '')}"><div class="task-agent-output-block-header">${escapeHtml(displayLabel)}<button type="button" class="task-agent-output-block-expand" aria-label="Expand" title="Expand">⤢</button></div><div class="task-agent-output-block-body">${content}</div></div>`;
        }
        try {
            el.innerHTML = html || '';
            if (typeof hljs !== 'undefined') {
                requestIdleCallback(() => {
                    el.querySelectorAll('pre code').forEach((node) => { try { hljs.highlightElement(node); } catch (_) {} });
                }, { timeout: 100 });
            }
        } catch (_) {
            el.textContent = keys.map((k) => `Task ${k}: ${outputs[k]}`).join('\n\n');
        }
        if (!state.outputUserScrolled && wasNearBottom) {
            requestAnimationFrame(() => { requestAnimationFrame(() => { el.scrollTop = el.scrollHeight; }); });
        }
        state.outputBlockUserScrolled = state.outputBlockUserScrolled || {};
        const lastKey = state.outputLastUpdatedKey || '';
        el.querySelectorAll('.task-agent-output-block').forEach((blockEl) => {
            const key = blockEl.getAttribute('data-task-id') || '';
            const body = blockEl.querySelector('.task-agent-output-block-body');
            if (!body) return;
            const shouldAutoScroll = key === lastKey && !state.outputBlockUserScrolled[key];
            if (shouldAutoScroll) requestAnimationFrame(() => { body.scrollTop = body.scrollHeight; });
            else if (savedScrollTops[key] != null) body.scrollTop = savedScrollTops[key];
            body.addEventListener('scroll', function onBlockScroll() {
                const nearBottom = body.scrollHeight - body.scrollTop - body.clientHeight < 40;
                state.outputBlockUserScrolled[key] = !nearBottom;
            }, { passive: true });
        });
    }

    function initOutputScrollTracking() {
        const el = document.getElementById('taskAgentOutputContent');
        if (!el) return;
        el.addEventListener('scroll', () => {
            const nearBottom = el.scrollHeight - el.scrollTop - el.clientHeight < 80;
            state.outputUserScrolled = !nearBottom;
        }, { passive: true });
    }

    function setTaskOutput(taskId, output) {
        if (!taskId) return;
        state.taskOutputs[taskId] = output;
        state.outputLastUpdatedKey = String(taskId);
        renderOutput();
    }

    let _outputModalOpen = false;
    function openOutputModal(taskId, contentHtml, scrollTop, titleLabel) {
        const modal = document.getElementById('taskAgentOutputModal');
        const titleEl = document.getElementById('taskAgentOutputModalTitle');
        const bodyEl = document.getElementById('taskAgentOutputModalBody');
        const closeBtn = document.getElementById('taskAgentOutputModalClose');
        const backdrop = modal?.querySelector('.task-agent-output-modal-backdrop');
        if (!modal || !bodyEl) return;
        if (_outputModalOpen) return;
        _outputModalOpen = true;
        modal.setAttribute('data-current-task-id', taskId || '');
        titleEl.textContent = titleLabel || (taskId ? 'Task ' + taskId : 'Task Output');
        bodyEl.innerHTML = contentHtml || '';
        bodyEl.scrollTop = scrollTop || 0;
        if (typeof hljs !== 'undefined') {
            requestAnimationFrame(() => {
                bodyEl.querySelectorAll('pre code').forEach((node) => { try { hljs.highlightElement(node); } catch (_) {} });
            });
        }
        modal.classList.add('is-open');
        modal.setAttribute('aria-hidden', 'false');
        document.body.style.overflow = 'hidden';
        function closeModal() {
            _outputModalOpen = false;
            modal.classList.remove('is-open');
            modal.setAttribute('aria-hidden', 'true');
            document.body.style.overflow = '';
            document.removeEventListener('keydown', keydownHandler);
        }
        const keydownHandler = (ev) => { if (ev.key === 'Escape') closeModal(); };
        closeBtn?.addEventListener('click', closeModal, { once: true });
        backdrop?.addEventListener('click', closeModal, { once: true });
        document.addEventListener('keydown', keydownHandler);
    }

    function applyOutputHighlight() {
        const el = document.getElementById('taskAgentOutputContent');
        if (!el || typeof hljs === 'undefined') return;
        requestIdleCallback(() => {
            el.querySelectorAll('pre code').forEach((node) => { try { hljs.highlightElement(node); } catch (_) {} });
        }, { timeout: 500 });
    }

    function downloadTaskOutput(taskId) {
        const raw = state.taskOutputs[taskId];
        let text = '', ext = 'txt';
        if (raw != null) {
            if (typeof raw === 'string') { text = raw; ext = 'md'; }
            else if (typeof raw === 'object' && raw !== null && 'content' in raw && typeof raw.content === 'string') { text = raw.content; ext = 'md'; }
            else { text = JSON.stringify(raw, null, 2); ext = 'json'; }
        }
        const filename = `task-${(taskId || 'output').replace(/[^a-zA-Z0-9_-]/g, '_')}.${ext}`;
        const blob = new Blob([text], { type: ext === 'json' ? 'application/json' : 'text/markdown' });
        const a = document.createElement('a');
        a.href = URL.createObjectURL(blob);
        a.download = filename;
        a.click();
        URL.revokeObjectURL(a.href);
    }

    function initOutputAreaClick() {
        const area = document.getElementById('taskAgentOutputArea');
        if (!area) return;
        area.addEventListener('click', (e) => {
            const expandBtn = e.target.closest('.task-agent-output-block-expand');
            if (expandBtn) {
                e.stopPropagation();
                const block = expandBtn.closest('.task-agent-output-block');
                if (block) {
                    const bodyEl = block.querySelector('.task-agent-output-block-body');
                    const label = block.getAttribute('data-label') || '';
                    const taskId = block.getAttribute('data-task-id') || '';
                    openOutputModal(taskId, bodyEl?.innerHTML || '', bodyEl?.scrollTop || 0, label || (taskId ? 'Task ' + taskId : 'Task Output'));
                }
                return;
            }
            const block = e.target.closest('.task-agent-output-block');
            if (!block) return;
            const allBlocks = area.querySelectorAll('.task-agent-output-block');
            const wasFocused = block.classList.contains('is-focused');
            allBlocks.forEach((b) => b.classList.remove('is-focused'));
            if (!wasFocused) block.classList.add('is-focused');
        });
    }

    function initOutputModalDownload() {
        const downloadBtn = document.getElementById('taskAgentOutputModalDownload');
        const modal = document.getElementById('taskAgentOutputModal');
        if (!downloadBtn || !modal) return;
        downloadBtn.addEventListener('click', (e) => {
            e.stopPropagation();
            downloadTaskOutput(modal.getAttribute('data-current-task-id') || '');
        });
    }

    initOutputScrollTracking();
    initOutputAreaClick();
    initOutputModalDownload();

    window.MAARS.thinking = { clear: clearThinking, appendChunk, applyHighlight };
    window.MAARS.output = { setTaskOutput, renderOutput, applyOutputHighlight };
})();
