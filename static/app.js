const state = {
    jobs: [],
    stats: {},
    sources: [],
    filters: { source: '', status: '', min_score: 0, search: '', location: '', tech: '', india_friendly: '' },
    offset: 0,
    limit: 50,
    collecting: false,
};

// ── API ──
async function api(path, opts = {}) {
    const resp = await fetch(`/api${path}`, opts);
    return resp.json();
}

async function loadJobs() {
    const f = state.filters;
    const params = new URLSearchParams();
    if (f.source) params.set('source', f.source);
    if (f.status) params.set('status', f.status);
    if (f.min_score) params.set('min_score', f.min_score);
    if (f.search) params.set('search', f.search);
    if (f.location) params.set('location', f.location);
    if (f.tech) params.set('tech', f.tech);
    if (f.india_friendly) params.set('india_friendly', f.india_friendly);
    params.set('limit', state.limit);
    params.set('offset', state.offset);

    document.getElementById('job-list').innerHTML = `
        <div class="loading"><div class="spinner"></div> Loading jobs...</div>`;

    const data = await api(`/jobs?${params}`);
    state.jobs = data.jobs;
    renderJobs();
}

async function loadStats() {
    state.stats = await api('/stats');
    renderStats();
}

async function loadSources() {
    const data = await api('/sources');
    state.sources = data.sources;
    renderSourceFilter();
}

async function collectJobs() {
    if (state.collecting) return;
    state.collecting = true;
    const btn = document.getElementById('btn-collect');
    btn.disabled = true;
    btn.textContent = 'Collecting...';

    const estimateSec = await estimateCollectionTime();
    const startMs = Date.now();
    showCollectLoader(estimateSec);
    const tick = setInterval(() => updateCollectLoader(startMs, estimateSec), 500);

    try {
        const stats = await api('/collect', { method: 'POST' });
        const newCount = stats.new ?? 0;
        const outCount = stats.outreach_generated ?? 0;
        showToast(`Collection complete — ${newCount} new jobs, ${outCount} outreach items ready to email`);
        await Promise.all([loadJobs(), loadStats(), loadSources(), loadJSearchStatus()]);
    } catch (e) {
        showToast('Collection failed: ' + e.message);
    } finally {
        clearInterval(tick);
        hideCollectLoader();
        state.collecting = false;
        btn.disabled = false;
        btn.textContent = 'Collect Jobs';
    }
}

async function estimateCollectionTime() {
    // Rough estimate: parallel job boards baseline + JSearch queries (sequential)
    // + company crawl waves (concurrency 5). Keep conservative.
    let jsearchCount = 0;
    let activeCompanies = 0;
    try {
        const q = await api('/search-queries');
        jsearchCount = (q.queries || []).filter(x => x.enabled !== false && x.query).length;
    } catch {}
    try {
        const s = await api('/companies/stats');
        activeCompanies = (s.by_status && s.by_status.active) || 0;
    } catch {}
    const base = 15;                        // parallel boards (remotive/remoteok/arbeitnow)
    const jsearch = jsearchCount * 4;       // sequential, ~4s/query
    const companyWaves = Math.ceil(activeCompanies / 5) * 3; // 5-wide concurrency, ~3s/wave
    return Math.max(10, base + jsearch + companyWaves);
}

function showCollectLoader(estimateSec) {
    document.getElementById('collect-estimate').textContent = formatSeconds(estimateSec);
    document.getElementById('collect-elapsed').textContent = '0s';
    document.getElementById('collect-loader').hidden = false;
}

function hideCollectLoader() {
    document.getElementById('collect-loader').hidden = true;
}

function updateCollectLoader(startMs, estimateSec) {
    const elapsed = Math.floor((Date.now() - startMs) / 1000);
    const el = document.getElementById('collect-elapsed');
    el.textContent = formatSeconds(elapsed);
    // When we overshoot the estimate, soften the message
    if (elapsed > estimateSec) {
        document.getElementById('collect-estimate').textContent = `${formatSeconds(estimateSec)} (almost there…)`;
    }
}

function formatSeconds(total) {
    total = Math.max(0, Math.round(total));
    if (total < 60) return `${total}s`;
    const m = Math.floor(total / 60);
    const s = total % 60;
    return s ? `${m}m ${s}s` : `${m}m`;
}

async function updateStatus(jobId, status) {
    await api(`/jobs/${jobId}/status?status=${status}`, { method: 'PATCH' });
    showToast(`Status updated to ${status}`);
    await loadJobs();
}

// ── India badge helper ──
function indiaBadge(value, note) {
    const labels = {
        yes: 'India OK',
        maybe: 'Maybe India',
        no: 'Not India',
        unknown: 'Unknown',
    };
    const label = labels[value] || labels.unknown;
    const cls = `india-${value || 'unknown'}`;
    const tooltip = note ? ` title="${escapeHtml(note)}"` : '';
    return `<span class="${cls}"${tooltip}>${label}</span>`;
}

// ── Render ──
function renderStats() {
    const s = state.stats;
    const indiaStats = s.by_india || {};
    document.getElementById('stats-bar').innerHTML = `
        <div class="stat-card">
            <div class="label">Total Jobs</div>
            <div class="value">${s.total || 0}</div>
        </div>
        <div class="stat-card">
            <div class="label">Avg Score</div>
            <div class="value">${s.avg_score || 0}</div>
        </div>
        <div class="stat-card" style="border-color: var(--green);">
            <div class="label">India Friendly</div>
            <div class="value" style="color: var(--green);">${indiaStats['yes'] || 0}</div>
        </div>
        <div class="stat-card" style="border-color: var(--yellow);">
            <div class="label">Maybe India</div>
            <div class="value" style="color: var(--yellow);">${indiaStats['maybe'] || 0}</div>
        </div>
        <div class="stat-card" style="border-color: var(--red);">
            <div class="label">Not India</div>
            <div class="value" style="color: var(--red);">${indiaStats['no'] || 0}</div>
        </div>
        ${Object.entries(s.by_source || {}).map(([src, count]) => `
            <div class="stat-card">
                <div class="label">${src}</div>
                <div class="value">${count}</div>
            </div>
        `).join('')}
    `;
}

function renderSourceFilter() {
    const sel = document.getElementById('filter-source');
    sel.innerHTML = '<option value="">All Sources</option>';
    state.sources.forEach(s => {
        sel.innerHTML += `<option value="${s}">${s}</option>`;
    });
}

function scoreClass(score) {
    if (score >= 60) return 'score-high';
    if (score >= 35) return 'score-mid';
    return 'score-low';
}

function statusClass(status) {
    return `status-${status || 'new'}`;
}

function stripHtml(html) {
    const tmp = document.createElement('div');
    tmp.innerHTML = html;
    return tmp.textContent || tmp.innerText || '';
}

function truncate(str, len = 120) {
    const clean = stripHtml(str);
    return clean.length > len ? clean.substring(0, len) + '...' : clean;
}

function renderJobs() {
    const list = document.getElementById('job-list');

    if (!state.jobs.length) {
        list.innerHTML = `
            <div class="empty-state">
                <h3>No jobs found</h3>
                <p>Click "Collect Jobs" to fetch from all sources, or adjust your filters.</p>
            </div>`;
        return;
    }

    list.innerHTML = state.jobs.map(job => `
        <div class="job-card">
            <input type="checkbox" class="mark-email" title="Mark for email"
                   ${job.mark_for_email ? 'checked' : ''}
                   onclick="event.stopPropagation(); toggleMark('${job.id}')"
                   style="margin-right:8px;transform:scale(1.2);cursor:pointer;">
            <div class="score-badge ${scoreClass(job.relevance_score)}" onclick="openModal('${job.id}')" style="cursor:pointer;">
                ${job.relevance_score}
            </div>
            <div class="job-info" onclick="openModal('${job.id}')" style="cursor:pointer;">
                <h3>${escapeHtml(job.title)}</h3>
                <div class="job-meta">
                    <span>${escapeHtml(job.company)}</span>
                    <span>${escapeHtml(job.location)}</span>
                    <span>${escapeHtml(job.source)}</span>
                    ${job.salary ? `<span>${escapeHtml(job.salary)}</span>` : ''}
                    ${job.posted_date ? `<span>${formatDate(job.posted_date)}</span>` : ''}
                    ${indiaBadge(job.india_friendly, job.location_note)}
                    ${job.last_seen ? `<span style="font-size:11px;color:var(--text-muted);">Last seen: ${formatDate(job.last_seen)}</span>` : ''}
                </div>
                <div class="job-tags">
                    ${(job.tech_stack || '').split(',').filter(t => t.trim()).slice(0, 6).map(t =>
                        `<span class="tag">${escapeHtml(t.trim())}</span>`
                    ).join('')}
                </div>
            </div>
            <div class="job-actions">
                <span class="status-badge ${statusClass(job.status)}">${job.status}</span>
                ${job.mark_for_email ? '<span style="color:var(--yellow);font-size:11px;">📧 Marked</span>' : ''}
            </div>
        </div>
    `).join('');
}

function openModal(jobId) {
    const job = state.jobs.find(j => j.id === jobId);
    if (!job) return;

    document.getElementById('modal-content').innerHTML = `
        <h2>${escapeHtml(job.title)}</h2>
        <div class="modal-company">${escapeHtml(job.company)} &mdash; ${escapeHtml(job.location)}</div>
        <div class="modal-details">
            <span class="score-badge ${scoreClass(job.relevance_score)}" style="width:40px;height:40px;font-size:14px;">
                ${job.relevance_score}
            </span>
            <span class="status-badge ${statusClass(job.status)}">${job.status}</span>
            ${indiaBadge(job.india_friendly, job.location_note)}
            <span class="tag">${escapeHtml(job.source)}</span>
            ${job.salary ? `<span class="tag">${escapeHtml(job.salary)}</span>` : ''}
            ${job.experience_level ? `<span class="tag">${escapeHtml(job.experience_level)}</span>` : ''}
        </div>
        ${job.location_note ? `<div class="location-note">Location: ${escapeHtml(job.location_note)}</div>` : ''}
        <div class="job-tags" style="margin-bottom:12px;">
            ${(job.tech_stack || '').split(',').filter(t => t.trim()).map(t =>
                `<span class="tag">${escapeHtml(t.trim())}</span>`
            ).join('')}
        </div>
        <div class="modal-desc">${job.description || '<em>No description available</em>'}</div>
        <div class="modal-actions">
            <button class="btn btn-outline" onclick="updateStatus('${job.id}', 'reviewed')">Mark Reviewed</button>
            <button class="btn btn-green" onclick="updateStatus('${job.id}', 'applied')">Mark Applied</button>
            <button class="btn btn-yellow" onclick="updateStatus('${job.id}', 'stale')">Mark Stale</button>
            ${job.url ? `<a href="${escapeHtml(job.url)}" target="_blank" class="btn btn-primary">Apply</a>` : ''}
            <button class="btn btn-outline" onclick="closeModal()">Close</button>
        </div>
    `;
    document.getElementById('modal-overlay').classList.add('active');
}

function closeModal() {
    document.getElementById('modal-overlay').classList.remove('active');
}

function escapeHtml(str) {
    if (!str) return '';
    const div = document.createElement('div');
    div.textContent = str;
    return div.innerHTML;
}

function formatDate(dateStr) {
    try {
        const d = new Date(dateStr);
        if (isNaN(d.getTime())) return dateStr;
        return d.toLocaleDateString('en-US', { month: 'short', day: 'numeric', year: 'numeric' });
    } catch {
        return dateStr;
    }
}

function showToast(msg) {
    const existing = document.querySelector('.toast');
    if (existing) existing.remove();
    const toast = document.createElement('div');
    toast.className = 'toast';
    toast.textContent = msg;
    document.body.appendChild(toast);
    setTimeout(() => toast.remove(), 3000);
}

// ── Filter handlers ──
function applyFilters() {
    state.filters.source = document.getElementById('filter-source').value;
    state.filters.status = document.getElementById('filter-status').value;
    state.filters.min_score = parseInt(document.getElementById('filter-score').value) || 0;
    state.filters.search = document.getElementById('filter-search').value;
    state.filters.location = document.getElementById('filter-location').value;
    state.filters.tech = document.getElementById('filter-tech').value;
    state.filters.india_friendly = document.getElementById('filter-india').value;
    state.offset = 0;
    loadJobs();
}

function resetFilters() {
    document.getElementById('filter-source').value = '';
    document.getElementById('filter-status').value = '';
    document.getElementById('filter-score').value = '0';
    document.getElementById('filter-search').value = '';
    document.getElementById('filter-location').value = '';
    document.getElementById('filter-tech').value = '';
    document.getElementById('filter-india').value = '';
    state.filters = { source: '', status: '', min_score: 0, search: '', location: '', tech: '', india_friendly: '' };
    state.offset = 0;
    loadJobs();
}

function nextPage() {
    state.offset += state.limit;
    loadJobs();
}

function prevPage() {
    state.offset = Math.max(0, state.offset - state.limit);
    loadJobs();
}

// ── Google Sheets Export ──
async function loadJSearchStatus() {
    try {
        const s = await api('/jsearch/status');
        const el = document.getElementById('jsearch-status');
        if (!el) return;
        if (!s.configured) {
            el.textContent = 'JSearch: not configured';
            el.style.color = 'var(--red)';
            return;
        }
        const pct = Math.round((s.month / s.monthly_limit) * 100);
        let color = 'var(--text-muted)';
        if (pct >= 80) color = 'var(--red)';
        else if (pct >= 50) color = 'var(--yellow)';
        else color = 'var(--green)';
        el.innerHTML = `<span title="Today: ${s.today} calls">JSearch: <span style="color:${color};font-weight:600;">${s.month}/${s.monthly_limit}</span> this month (${s.remaining} left)</span>`;
    } catch (e) {}
}

async function checkSheetsStatus() {
    try {
        const data = await api('/export/sheets/status');
        const btn = document.getElementById('btn-export');
        if (!data.configured) {
            btn.title = 'Google Sheets not configured — add GOOGLE_SHEET_ID + credentials.json';
            btn.style.opacity = '0.6';
        }
    } catch (e) {}
}

function openExportModal() {
    document.getElementById('export-overlay').classList.add('active');
}

function closeExportModal() {
    document.getElementById('export-overlay').classList.remove('active');
}

async function doExport() {
    const btn = document.getElementById('btn-do-export');
    btn.disabled = true;
    btn.textContent = 'Exporting...';

    const params = new URLSearchParams();
    params.set('sheet_name', document.getElementById('export-sheet-name').value);
    params.set('min_score', document.getElementById('export-score').value);
    params.set('mode', document.getElementById('export-mode').value);
    const india = document.getElementById('export-india').value;
    if (india) params.set('india_friendly', india);

    try {
        const data = await api(`/export/sheets?${params}`, { method: 'POST' });
        if (data.error) {
            showToast('Export failed: ' + data.error);
        } else {
            showToast(`Exported ${data.exported} jobs to Google Sheets!`);
            closeExportModal();
        }
    } catch (e) {
        showToast('Export failed: ' + e.message);
    } finally {
        btn.disabled = false;
        btn.textContent = 'Export Now';
    }
}

// ── Search Queries Manager ──
async function openQueriesModal() {
    document.getElementById('queries-overlay').classList.add('active');
    await loadQueries();
}

function closeQueriesModal() {
    document.getElementById('queries-overlay').classList.remove('active');
}

async function loadQueries() {
    const data = await api('/search-queries');
    const list = document.getElementById('queries-list');
    if (!data.queries.length) {
        list.innerHTML = '<div style="color:var(--text-muted);padding:12px;">No queries yet. Add one below.</div>';
        return;
    }
    list.innerHTML = `
        <table style="width:100%;border-collapse:collapse;font-size:13px;">
            <thead>
                <tr style="border-bottom:1px solid var(--border);color:var(--text-muted);font-size:11px;text-transform:uppercase;">
                    <th style="text-align:left;padding:8px 4px;">On</th>
                    <th style="text-align:left;padding:8px 4px;">Query</th>
                    <th style="text-align:left;padding:8px 4px;">Country</th>
                    <th style="text-align:left;padding:8px 4px;">Posted</th>
                    <th style="text-align:left;padding:8px 4px;">Remote</th>
                    <th></th>
                </tr>
            </thead>
            <tbody>
                ${data.queries.map(q => `
                    <tr style="border-bottom:1px solid var(--border);">
                        <td style="padding:8px 4px;">
                            <input type="checkbox" ${q.enabled ? 'checked' : ''}
                                onchange="toggleQueryEnabled(${q.id}, this.checked)">
                        </td>
                        <td style="padding:8px 4px;"><input type="text" value="${escapeHtml(q.query)}"
                            onchange="updateQueryField(${q.id}, 'query', this.value)"
                            style="background:var(--surface2);border:1px solid var(--border);color:var(--text);padding:4px 8px;border-radius:4px;width:100%;font-size:13px;"></td>
                        <td style="padding:8px 4px;">
                            <select onchange="updateQueryField(${q.id}, 'country', this.value)"
                                style="background:var(--surface2);border:1px solid var(--border);color:var(--text);padding:4px 6px;border-radius:4px;font-size:13px;">
                                ${['IN','US','GB','CA','DE','SG'].map(c => `<option value="${c}" ${c===q.country?'selected':''}>${c}</option>`).join('')}
                            </select>
                        </td>
                        <td style="padding:8px 4px;">
                            <select onchange="updateQueryField(${q.id}, 'date_posted', this.value)"
                                style="background:var(--surface2);border:1px solid var(--border);color:var(--text);padding:4px 6px;border-radius:4px;font-size:13px;">
                                ${['today','3days','week','month','all'].map(d => `<option value="${d}" ${d===q.date_posted?'selected':''}>${d}</option>`).join('')}
                            </select>
                        </td>
                        <td style="padding:8px 4px;">
                            <input type="checkbox" ${q.remote_jobs_only ? 'checked' : ''}
                                onchange="updateQueryField(${q.id}, 'remote_jobs_only', this.checked)">
                        </td>
                        <td style="padding:8px 4px;">
                            <button class="btn btn-outline btn-sm" onclick="deleteQuery(${q.id})">×</button>
                        </td>
                    </tr>
                `).join('')}
            </tbody>
        </table>
    `;
}

async function addQuery() {
    const query = document.getElementById('new-query').value.trim();
    if (!query) { showToast('Query cannot be empty'); return; }
    const body = {
        query,
        country: document.getElementById('new-country').value,
        date_posted: document.getElementById('new-date').value,
        remote_jobs_only: document.getElementById('new-remote').checked,
    };
    await api('/search-queries', {
        method: 'POST',
        headers: {'Content-Type': 'application/json'},
        body: JSON.stringify(body),
    });
    document.getElementById('new-query').value = '';
    document.getElementById('new-remote').checked = false;
    showToast('Query added');
    await loadQueries();
}

async function updateQueryField(qid, field, value) {
    const body = {};
    body[field] = value;
    await api(`/search-queries/${qid}`, {
        method: 'PATCH',
        headers: {'Content-Type': 'application/json'},
        body: JSON.stringify(body),
    });
}

async function toggleQueryEnabled(qid, enabled) {
    await updateQueryField(qid, 'enabled', enabled);
    showToast(enabled ? 'Query enabled' : 'Query disabled');
}

async function deleteQuery(qid) {
    if (!confirm('Delete this query?')) return;
    await api(`/search-queries/${qid}`, {method: 'DELETE'});
    showToast('Query deleted');
    await loadQueries();
}

// ── Mark for Email ──
async function toggleMark(jobId) {
    const data = await api(`/jobs/${jobId}/mark-for-email`, { method: 'POST' });
    showToast(data.mark_for_email ? '📧 Marked for email' : 'Unmarked');
    // Update local state to reflect
    const job = state.jobs.find(j => j.id === jobId);
    if (job) {
        job.mark_for_email = data.mark_for_email ? 1 : 0;
        renderJobs();
    }
}

// ── Keyboard ──
document.addEventListener('keydown', e => {
    if (e.key === 'Escape') { closeModal(); closeExportModal(); closeQueriesModal(); }
});

// ── Init ──
async function loadActiveProfileIndicator() {
    const el = document.getElementById('active-profile-indicator');
    if (!el) return;
    try {
        const a = await api('/profiles/active');
        el.textContent = `Profile: ${a.name || '(none)'}`;
    } catch (e) {
        el.textContent = 'Profile: (none)';
    }
}

document.addEventListener('DOMContentLoaded', () => {
    loadStats();
    loadSources();
    loadJobs();
    checkSheetsStatus();
    loadJSearchStatus();
    loadActiveProfileIndicator();

    // Debounced search
    let searchTimeout;
    document.getElementById('filter-search').addEventListener('input', () => {
        clearTimeout(searchTimeout);
        searchTimeout = setTimeout(applyFilters, 400);
    });
});
