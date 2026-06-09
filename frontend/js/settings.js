import { fetchEnvConfig, saveEnvConfig } from './api.js';

let overlay;
let title;
let content;
let button;

function fieldId(key) {
  return `setting-${key}`;
}

function inputFor(entry) {
  const id = fieldId(entry.key);
  if (entry.type === 'select') {
    const select = document.createElement('select');
    select.id = id;
    select.name = entry.key;
    for (const optionValue of entry.options || []) {
      const option = document.createElement('option');
      option.value = optionValue;
      option.textContent = optionValue || '(inherit)';
      select.appendChild(option);
    }
    select.value = entry.value ?? '';
    return select;
  }
  if (entry.type === 'boolean') {
    const select = document.createElement('select');
    select.id = id;
    select.name = entry.key;
    for (const optionValue of ['true', 'false']) {
      const option = document.createElement('option');
      option.value = optionValue;
      option.textContent = optionValue;
      select.appendChild(option);
    }
    select.value = String(entry.value || 'false').toLowerCase() === 'true' ? 'true' : 'false';
    return select;
  }
  const input = document.createElement('input');
  input.id = id;
  input.name = entry.key;
  input.type = entry.type === 'secret' ? 'password' : entry.type === 'number' ? 'number' : 'text';
  input.value = entry.value ?? '';
  input.autocomplete = 'off';
  if (entry.type === 'secret') input.placeholder = 'empty';
  return input;
}

function entryRow(entry) {
  const row = document.createElement('label');
  row.className = 'settings-row';
  row.htmlFor = fieldId(entry.key);

  const meta = document.createElement('span');
  meta.className = 'settings-meta';

  const key = document.createElement('span');
  key.className = 'settings-key';
  key.textContent = entry.key;
  meta.appendChild(key);

  const helpText = [...(entry.notes || []), entry.comment].filter(Boolean).join(' ');
  if (helpText) {
    const help = document.createElement('span');
    help.className = 'settings-help';
    help.textContent = helpText;
    meta.appendChild(help);
  }

  row.appendChild(meta);
  row.appendChild(inputFor(entry));
  return row;
}

function renderSettings(data) {
  title.textContent = 'Settings';
  content.className = 'settings-modal';
  content.textContent = '';

  const form = document.createElement('form');
  form.id = 'settings-form';

  const intro = document.createElement('div');
  intro.className = 'settings-intro';
  intro.innerHTML = `<strong>.env</strong><span>${data.path}</span><em>Changes are saved to disk. Restart MAARS for them to take effect.</em>`;
  form.appendChild(intro);

  for (const section of data.sections || []) {
    const group = document.createElement('section');
    group.className = 'settings-section';
    const heading = document.createElement('h4');
    heading.textContent = section.title;
    group.appendChild(heading);
    for (const entry of section.entries || []) {
      group.appendChild(entryRow(entry));
    }
    form.appendChild(group);
  }

  const footer = document.createElement('div');
  footer.className = 'settings-footer';
  const status = document.createElement('span');
  status.id = 'settings-status';
  status.textContent = '';
  const save = document.createElement('button');
  save.type = 'submit';
  save.textContent = 'Save .env';
  footer.appendChild(status);
  footer.appendChild(save);
  form.appendChild(footer);

  form.addEventListener('submit', async (event) => {
    event.preventDefault();
    status.textContent = 'Saving...';
    save.disabled = true;
    const values = {};
    for (const element of form.elements) {
      if (element.name) values[element.name] = element.value;
    }
    try {
      await saveEnvConfig(values);
      status.textContent = 'Saved. Restart required.';
      status.dataset.state = 'ok';
    } catch (error) {
      status.textContent = error.message || 'Save failed';
      status.dataset.state = 'error';
    } finally {
      save.disabled = false;
    }
  });

  content.appendChild(form);
}

async function openSettings() {
  if (!overlay || !title || !content) return;
  title.textContent = 'Settings';
  content.className = 'settings-modal';
  content.textContent = 'Loading...';
  overlay.classList.remove('hidden');
  try {
    const data = await fetchEnvConfig();
    renderSettings(data);
  } catch (error) {
    content.textContent = error.message || 'Could not load settings';
  }
}

export function initSettings() {
  overlay = document.getElementById('modal-overlay');
  title = document.getElementById('modal-title');
  content = document.getElementById('modal-content');
  button = document.getElementById('settings-btn');
  if (!button) return;
  button.addEventListener('click', openSettings);
}
