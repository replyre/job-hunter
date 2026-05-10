// profile.js — drives the /profile page

const state = {
    profiles: [],
    presets: [],
    activeId: null,
    currentId: null,
    config: null,          // config of currently loaded profile (mutable)
    profileMeta: null,     // {name, description, source}
};

async function api(path, opts = {}) {
    const init = { headers: {}, ...opts };
    if (init.body && typeof init.body !== 'string') {
        init.body = JSON.stringify(init.body);
        init.headers['Content-Type'] = 'application/json';
    } else if (init.method && init.method !== 'GET' && !init.headers['Content-Type'] && init.body) {
        init.headers['Content-Type'] = 'application/json';
    }
    const resp = await fetch(`/api${path}`, init);
    if (!resp.ok) {
        let detail = resp.statusText;
        try { const j = await resp.json(); detail = j.detail || j.error || JSON.stringify(j); } catch {}
        throw new Error(`${resp.status}: ${detail}`);
    }
    const ct = resp.headers.get('content-type') || '';
    return ct.includes('application/json') ? resp.json() : resp.text();
}

function showToast(msg, variant = 'ok') {
    const el = document.createElement('div');
    el.className = 'toast';
    if (variant === 'err') { el.style.borderColor = 'var(--red)'; el.style.color = 'var(--red)'; }
    el.textContent = msg;
    document.body.appendChild(el);
    setTimeout(() => el.remove(), 3500);
}

// ── Boot ──────────────────────────────────────────────────────

async function boot() {
    await loadProfiles();
    await loadActive();
    if (state.currentId == null && state.profiles.length) {
        state.currentId = state.activeId || state.profiles[0].id;
    }
    if (state.currentId != null) await selectProfile(state.currentId);
    renderSidebar();
}

async function loadProfiles() {
    const data = await api('/profiles');
    state.profiles = data.profiles || [];
    state.presets = data.presets || [];
    const act = state.profiles.find(p => p.is_active);
    state.activeId = act ? act.id : null;
}

async function loadActive() {
    try {
        const a = await api('/profiles/active');
        state.activeId = a.id;
        const el = document.getElementById('active-indicator');
        el.textContent = `Active: ${a.name || '(none)'}`;
    } catch (e) {
        document.getElementById('active-indicator').textContent = 'Active: (none)';
    }
}

function renderSidebar() {
    const list = document.getElementById('profile-list');
    if (!state.profiles.length) {
        list.innerHTML = '<div class="help">No profiles. Import a preset below.</div>';
    } else {
        list.innerHTML = state.profiles.map(p => `
            <div class="profile-item ${p.id === state.currentId ? 'selected' : ''}" onclick="selectProfile(${p.id})">
                <div class="name">${escapeHtml(p.name)}${p.is_active ? '<span class="active-pill">ACTIVE</span>' : ''}</div>
                <div class="desc">${escapeHtml(p.description || p.source || '')}</div>
            </div>
        `).join('');
    }

    const presetList = document.getElementById('preset-list');
    presetList.innerHTML = state.presets.map(p => `
        <div class="preset-item" onclick="importPresetFlow('${escapeAttr(p.slug)}')">
            <div class="name">${escapeHtml(p.name)}</div>
            <div class="desc">${escapeHtml(p.description || p.slug)}</div>
        </div>
    `).join('') || '<div class="help">No presets found in profiles/ directory.</div>';
}

// ── Profile load / render ─────────────────────────────────────

async function selectProfile(pid) {
    const row = await api(`/profiles/${pid}`);
    state.currentId = pid;
    state.config = row.config;
    state.profileMeta = { name: row.name, description: row.description, source: row.source };
    renderEditor();
    renderSidebar();
}

function renderEditor() {
    document.getElementById('profile-name').value = state.profileMeta.name || '';
    document.getElementById('profile-description').value = state.profileMeta.description || '';
    const chip = document.getElementById('profile-source-chip');
    chip.textContent = state.profileMeta.source || '';
    chip.style.display = state.profileMeta.source ? 'inline-block' : 'none';

    // Scoring scalars
    const sc = state.config.scoring || {};
    setRadio('exp-target', sc.experience_target || 'mid');
    document.getElementById('min-relevance-score').value = sc.min_relevance_score ?? 50;
    document.getElementById('min-score-to-store').value = sc.min_score_to_store ?? 25;
    const w = sc.weights || {};
    document.getElementById('w-title').value = w.title ?? 35;
    document.getElementById('w-tech').value = w.tech ?? 35;
    document.getElementById('w-experience').value = w.experience ?? 15;
    document.getElementById('w-signal').value = w.signal ?? 15;
    updateWeightsTotal();

    // Outreach scalars
    const o = state.config.outreach || {};
    document.getElementById('candidate-name').value = o.candidate_name || '';
    document.getElementById('email-role-word').value = o.email_digest_subject_role || '';
    document.getElementById('email-greeting').value = o.email_greeting || '';
    document.getElementById('sender-email').value = o.sender_email || '';
    document.getElementById('recipient-email').value = o.recipient_email || '';
    document.getElementById('bio-short').value = o.bio_short || '';
    document.getElementById('achievements').value = (o.achievements || []).join('\n');
    document.getElementById('dm-short').value = o.dm_short_template || '';
    document.getElementById('dm-long').value = o.dm_long_template || '';

    // Tag editors
    document.querySelectorAll('.tag-editor[data-path]').forEach(el => {
        const path = el.getAttribute('data-path');
        const values = getPath(state.config, path) || [];
        renderTagEditor(el, values);
    });

    // JSearch queries
    renderJsearchRows(state.config.search?.jsearch_default_queries || []);

    // LinkedIn titles
    renderLinkedinTitles(o.linkedin_search_titles || []);
}

// ── Tag editor ────────────────────────────────────────────────

function renderTagEditor(container, values) {
    container.innerHTML = '';
    (values || []).forEach(v => container.appendChild(chipEl(v, container)));
    const input = document.createElement('input');
    input.type = 'text';
    input.className = 'chip-input';
    input.placeholder = 'type + Enter';
    input.addEventListener('keydown', (e) => {
        if (e.key === 'Enter' || e.key === ',') {
            e.preventDefault();
            const v = input.value.trim();
            if (v) {
                container.insertBefore(chipEl(v, container), input);
                input.value = '';
            }
        } else if (e.key === 'Backspace' && !input.value) {
            const chips = container.querySelectorAll('.chip');
            if (chips.length) chips[chips.length - 1].remove();
        }
    });
    container.appendChild(input);
}

function chipEl(value, container) {
    const s = document.createElement('span');
    s.className = 'chip';
    s.dataset.value = value;
    s.innerHTML = `${escapeHtml(value)}<button type="button" aria-label="remove">×</button>`;
    s.querySelector('button').onclick = () => s.remove();
    return s;
}

function readTagEditor(container) {
    return Array.from(container.querySelectorAll('.chip')).map(c => c.dataset.value);
}

// ── JSearch queries ───────────────────────────────────────────

function renderJsearchRows(queries) {
    const root = document.getElementById('jsearch-queries-editor');
    root.innerHTML = '';
    (queries || []).forEach(q => root.appendChild(jsearchRow(q)));
}

function jsearchRow(q = {}) {
    const div = document.createElement('div');
    div.className = 'query-row jsearch';
    div.innerHTML = `
        <input class="q-query" placeholder="query text" value="${escapeAttr(q.query || '')}">
        <select class="q-country">
            ${['IN','US','GB','CA','DE','SG'].map(c =>
                `<option value="${c}" ${q.country === c ? 'selected' : ''}>${c}</option>`).join('')}
        </select>
        <select class="q-date">
            ${['today','3days','week','month','all'].map(d =>
                `<option value="${d}" ${q.date_posted === d ? 'selected' : ''}>${d}</option>`).join('')}
        </select>
        <label class="checkbox-cell"><input type="checkbox" class="q-remote" ${q.remote_jobs_only ? 'checked' : ''}>Remote</label>
        <button class="row-remove" type="button" onclick="this.parentElement.remove()">×</button>
    `;
    return div;
}

function addJsearchRow() {
    document.getElementById('jsearch-queries-editor').appendChild(jsearchRow());
}

function readJsearchRows() {
    return Array.from(document.querySelectorAll('#jsearch-queries-editor .query-row')).map(row => ({
        query: row.querySelector('.q-query').value.trim(),
        country: row.querySelector('.q-country').value,
        date_posted: row.querySelector('.q-date').value,
        remote_jobs_only: row.querySelector('.q-remote').checked,
    })).filter(q => q.query);
}

// ── LinkedIn titles ───────────────────────────────────────────

function renderLinkedinTitles(titles) {
    const root = document.getElementById('linkedin-titles-editor');
    root.innerHTML = '';
    (titles || []).forEach(t => root.appendChild(linkedinTitleRow(t)));
}

function linkedinTitleRow(t = {}) {
    const div = document.createElement('div');
    div.className = 'query-row linkedin';
    div.innerHTML = `
        <input class="lt-title" placeholder="Title (e.g. Engineering Manager)" value="${escapeAttr(t.title || '')}">
        <input class="lt-label" placeholder="Short label" value="${escapeAttr(t.label || '')}">
        <select class="lt-cat">
            ${['engineering','executive','hr'].map(c =>
                `<option value="${c}" ${t.category === c ? 'selected' : ''}>${c}</option>`).join('')}
        </select>
        <button class="row-remove" type="button" onclick="this.parentElement.remove()">×</button>
    `;
    return div;
}

function addLinkedinTitleRow() {
    document.getElementById('linkedin-titles-editor').appendChild(linkedinTitleRow());
}

function readLinkedinTitles() {
    return Array.from(document.querySelectorAll('#linkedin-titles-editor .query-row')).map(row => ({
        title: row.querySelector('.lt-title').value.trim(),
        label: row.querySelector('.lt-label').value.trim(),
        category: row.querySelector('.lt-cat').value,
    })).filter(t => t.title);
}

// ── Save / actions ────────────────────────────────────────────

function buildConfigFromForm() {
    const cfg = JSON.parse(JSON.stringify(state.config));

    // Tag editors
    document.querySelectorAll('.tag-editor[data-path]').forEach(el => {
        const path = el.getAttribute('data-path');
        setPath(cfg, path, readTagEditor(el));
    });

    // Scoring scalars
    cfg.scoring.experience_target = getRadio('exp-target') || 'mid';
    cfg.scoring.min_relevance_score = parseInt(document.getElementById('min-relevance-score').value || 50, 10);
    cfg.scoring.min_score_to_store = parseInt(document.getElementById('min-score-to-store').value || 25, 10);
    cfg.scoring.weights = {
        title: parseInt(document.getElementById('w-title').value || 0, 10),
        tech: parseInt(document.getElementById('w-tech').value || 0, 10),
        experience: parseInt(document.getElementById('w-experience').value || 0, 10),
        signal: parseInt(document.getElementById('w-signal').value || 0, 10),
    };

    // Outreach scalars
    cfg.outreach.candidate_name = document.getElementById('candidate-name').value;
    cfg.outreach.email_digest_subject_role = document.getElementById('email-role-word').value;
    cfg.outreach.email_greeting = document.getElementById('email-greeting').value;
    cfg.outreach.sender_email = document.getElementById('sender-email').value.trim();
    cfg.outreach.recipient_email = document.getElementById('recipient-email').value.trim();
    cfg.outreach.bio_short = document.getElementById('bio-short').value;
    cfg.outreach.achievements = document.getElementById('achievements').value
        .split('\n').map(s => s.trim()).filter(Boolean);
    cfg.outreach.dm_short_template = document.getElementById('dm-short').value;
    cfg.outreach.dm_long_template = document.getElementById('dm-long').value;

    // Dynamic rows
    cfg.search.jsearch_default_queries = readJsearchRows();
    cfg.outreach.linkedin_search_titles = readLinkedinTitles();

    return cfg;
}

async function saveProfile(activate) {
    if (state.currentId == null) { showToast('No profile selected', 'err'); return; }
    const name = document.getElementById('profile-name').value.trim();
    if (!name) { showToast('Name is required', 'err'); return; }
    const description = document.getElementById('profile-description').value.trim();
    const config = buildConfigFromForm();

    try {
        await api(`/profiles/${state.currentId}`, {
            method: 'PUT',
            body: { name, description, config },
        });
        if (activate) {
            await api(`/profiles/${state.currentId}/activate`, { method: 'POST' });
            showToast('Saved and activated (JSearch queries synced)');
        } else {
            showToast('Saved');
        }
        await loadProfiles();
        await loadActive();
        renderSidebar();
    } catch (e) {
        showToast(e.message, 'err');
    }
}

async function deleteActiveProfile() {
    if (state.currentId == null) return;
    if (!confirm(`Delete profile "${state.profileMeta.name}"? This is not reversible.`)) return;
    try {
        await api(`/profiles/${state.currentId}`, { method: 'DELETE' });
        showToast('Deleted');
        state.currentId = null;
        state.config = null;
        await boot();
    } catch (e) {
        showToast(e.message, 'err');
    }
}

async function duplicateProfile() {
    if (state.currentId == null) return;
    const newName = prompt('Name for the copy:', `${state.profileMeta.name} (copy)`);
    if (!newName) return;
    try {
        const res = await api(`/profiles/${state.currentId}/duplicate?name=${encodeURIComponent(newName)}`, { method: 'POST' });
        showToast('Duplicated');
        await loadProfiles();
        await selectProfile(res.id);
    } catch (e) {
        showToast(e.message, 'err');
    }
}

async function createBlankProfile() {
    const name = prompt('New profile name:');
    if (!name) return;
    try {
        const res = await api('/profiles', {
            method: 'POST',
            body: { name, description: '', config: {} },
        });
        await loadProfiles();
        await selectProfile(res.id);
        showToast('Created (starts with defaults — customize and save)');
    } catch (e) {
        showToast(e.message, 'err');
    }
}

async function importPresetFlow(slug) {
    const activate = confirm(`Import preset "${slug}" and activate immediately?\n\n[OK] = activate (JSearch queries will be replaced)\n[Cancel] = import only (without activating)`);
    try {
        const res = await api('/profiles/import', {
            method: 'POST',
            body: { preset_slug: slug, activate, overwrite: false },
        });
        showToast(activate ? 'Imported and activated' : 'Imported');
        await loadProfiles();
        await loadActive();
        await selectProfile(res.id);
    } catch (e) {
        showToast(e.message, 'err');
    }
}

async function rescoreAll(deleteBelowMin) {
    if (!confirm('Re-score all jobs against the active profile?')) return;
    try {
        const qs = deleteBelowMin ? '?delete_below_min=true' : '';
        const res = await api(`/profiles/rescore-all${qs}`, { method: 'POST' });
        showToast(`Re-scored ${res.updated} jobs (deleted ${res.deleted})`);
    } catch (e) {
        showToast(e.message, 'err');
    }
}

async function exportActiveProfile() {
    if (state.currentId == null) return;
    const url = `/api/profiles/${state.currentId}/export`;
    window.open(url, '_blank');
}

// ── Tabs + helpers ────────────────────────────────────────────

function switchTab(name) {
    document.querySelectorAll('.tab-link').forEach(el =>
        el.classList.toggle('active', el.dataset.tab === name));
    document.querySelectorAll('.tab-pane').forEach(el =>
        el.classList.toggle('active', el.dataset.tab === name));
}

function updateWeightsTotal() {
    const total = ['w-title', 'w-tech', 'w-experience', 'w-signal']
        .reduce((acc, id) => acc + (parseInt(document.getElementById(id).value || 0, 10) || 0), 0);
    const el = document.getElementById('weights-total');
    el.textContent = `Total: ${total}${total === 100 ? '' : ' (should be 100)'}`;
    el.style.color = total === 100 ? 'var(--text-muted)' : 'var(--yellow)';
}
['w-title','w-tech','w-experience','w-signal'].forEach(id =>
    document.addEventListener('input', e => {
        if (e.target && e.target.id === id) updateWeightsTotal();
    })
);

function setRadio(name, value) {
    document.querySelectorAll(`input[name="${name}"]`).forEach(r => r.checked = (r.value === value));
}
function getRadio(name) {
    const r = document.querySelector(`input[name="${name}"]:checked`);
    return r ? r.value : null;
}

function getPath(obj, path) {
    return path.split('.').reduce((o, k) => (o == null ? undefined : o[k]), obj);
}
function setPath(obj, path, value) {
    const parts = path.split('.');
    const last = parts.pop();
    const target = parts.reduce((o, k) => {
        o[k] = o[k] || {};
        return o[k];
    }, obj);
    target[last] = value;
}

function escapeHtml(s) {
    return String(s == null ? '' : s)
        .replace(/&/g, '&amp;').replace(/</g, '&lt;').replace(/>/g, '&gt;')
        .replace(/"/g, '&quot;').replace(/'/g, '&#39;');
}
function escapeAttr(s) { return escapeHtml(s); }

// ── Kickoff ──
boot();
