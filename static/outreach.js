let outreachItems = [];
let currentBatch = 'new';          // 'new' | 'old' | 'all'
let selectedIds = new Set();
let lastBatchAt = null;

async function api(path, opts = {}) {
    const init = { headers: {}, ...opts };
    if (init.body && typeof init.body !== 'string') {
        init.body = JSON.stringify(init.body);
        init.headers['Content-Type'] = 'application/json';
    }
    const resp = await fetch(`/api${path}`, init);
    return resp.json();
}

async function loadOutreach() {
    const status = document.getElementById('filter-status').value;
    const search = document.getElementById('filter-search').value;
    const params = new URLSearchParams();
    if (status) params.set('status', status);
    if (search) params.set('search', search);
    params.set('batch', currentBatch);
    const data = await api(`/outreach?${params}`);
    outreachItems = data.outreach || [];
    lastBatchAt = data.last_batch_at || null;
    // Drop stale selections that no longer exist in this list
    const ids = new Set(outreachItems.map(o => o.id));
    selectedIds = new Set([...selectedIds].filter(id => ids.has(id)));
    updateBatchInfo();
    updateBulkUI();
    render();
}

function switchBatch(batch) {
    currentBatch = batch;
    selectedIds.clear();
    document.querySelectorAll('.tab-link[data-batch]').forEach(el => {
        el.classList.toggle('active', el.dataset.batch === batch);
    });
    // Bulk actions only make sense on a scoped list (Old or All)
    const show = batch === 'old' || batch === 'all';
    document.getElementById('bulk-actions').hidden = !show;
    loadOutreach();
}

function updateBatchInfo() {
    const el = document.getElementById('batch-info');
    if (!el) return;
    if (currentBatch === 'new') {
        el.textContent = lastBatchAt
            ? `Latest generation: ${formatDate(lastBatchAt)} · ${outreachItems.length} items`
            : 'No generation yet — click "Find Contacts for Top Jobs"';
    } else if (currentBatch === 'old') {
        el.textContent = `${outreachItems.length} older items`;
    } else {
        el.textContent = `${outreachItems.length} items total`;
    }
}

function updateBulkUI() {
    const sel = document.getElementById('selected-count');
    if (sel) sel.textContent = `${selectedIds.size} selected`;
    const all = document.getElementById('select-all');
    if (all) {
        all.checked = outreachItems.length > 0 && selectedIds.size === outreachItems.length;
    }
}

function toggleSelectAll(checked) {
    if (checked) {
        outreachItems.forEach(o => selectedIds.add(o.id));
    } else {
        selectedIds.clear();
    }
    updateBulkUI();
    render();
}

function toggleSelectOne(id, checked) {
    if (checked) selectedIds.add(id);
    else selectedIds.delete(id);
    updateBulkUI();
}

async function bulkDeleteSelected() {
    if (selectedIds.size === 0) { showToast('Nothing selected'); return; }
    if (!confirm(`Delete ${selectedIds.size} outreach item(s)? This is not reversible.`)) return;
    try {
        const data = await api('/outreach/bulk-delete', {
            method: 'POST',
            body: { ids: [...selectedIds] },
        });
        showToast(`Deleted ${data.deleted} item(s)`);
        selectedIds.clear();
        await Promise.all([loadOutreach(), loadStats()]);
    } catch (e) {
        showToast('Delete failed: ' + e.message);
    }
}

async function loadStats() {
    const s = await api('/outreach/stats');
    const by = s.by_status || {};
    document.getElementById('stats-bar').innerHTML = `
        <div class="stat-card"><div class="label">Total</div><div class="value">${s.total || 0}</div></div>
        <div class="stat-card" style="border-color:var(--blue);"><div class="label">Pending</div><div class="value" style="color:var(--blue);">${by.pending || 0}</div></div>
        <div class="stat-card" style="border-color:var(--primary);"><div class="label">Emailed</div><div class="value" style="color:var(--primary);">${by.emailed || 0}</div></div>
        <div class="stat-card" style="border-color:var(--yellow);"><div class="label">Messaged</div><div class="value" style="color:var(--yellow);">${by.messaged || 0}</div></div>
        <div class="stat-card" style="border-color:var(--green);"><div class="label">Replied</div><div class="value" style="color:var(--green);">${by.replied || 0}</div></div>
        <div class="stat-card"><div class="label">Followed Up</div><div class="value">${by.followed_up || 0}</div></div>
    `;
}

let _emailStatus = {};
async function loadEmailStatus() {
    const s = await api('/email/status');
    _emailStatus = s;
    const el = document.getElementById('email-status');
    if (!s.sender_configured) {
        el.textContent = '📧 Email: not configured';
        el.style.color = 'var(--red)';
    } else if (!s.recipient) {
        el.textContent = '📧 Recipient not set';
        el.style.color = 'var(--red)';
    } else {
        el.textContent = `📧 Daily ${s.scheduled_hour}:00 IST · ${s.sender} → ${s.recipient}`;
        el.style.color = 'var(--text-muted)';
    }
}

async function previewEmail() {
    const btn = document.getElementById('btn-preview');
    btn.disabled = true; btn.textContent = 'Checking...';
    try {
        const data = await api('/email/send-now?dry_run=true', { method: 'POST' });
        if (data.error) {
            showToast(data.error);
        } else if (data.items_count === 0 || data.sent === 0) {
            showToast(data.message || 'No new items to email');
        } else {
            showToast(`Would send ${data.items_count} items: ${data.preview.map(p => p.company).join(', ')}`);
        }
    } catch (e) { showToast('Failed: ' + e.message); }
    finally { btn.disabled = false; btn.textContent = 'Preview Email'; }
}

async function sendEmailNow() {
    const who = _emailStatus.candidate_name || 'the recipient';
    const to = _emailStatus.recipient || '(recipient)';
    if (!confirm(`Send the daily digest email now to ${who} (${to})?`)) return;
    const btn = document.getElementById('btn-send');
    btn.disabled = true; btn.textContent = 'Sending...';
    try {
        const data = await api('/email/send-now', { method: 'POST' });
        if (data.error) {
            showToast('Failed: ' + data.error);
        } else if (data.sent) {
            showToast(`✓ Sent ${data.sent} items to ${data.recipient}`);
            await loadOutreach();
        } else {
            showToast((data.message || 'No items to send') + ' — click "Find Contacts for Top Jobs" to generate more.');
        }
    } catch (e) { showToast('Failed: ' + e.message); }
    finally { btn.disabled = false; btn.textContent = 'Send Email Now'; }
}

async function loadHunterStatus() {
    const s = await api('/hunter/status');
    const el = document.getElementById('hunter-status');
    if (!s.configured) {
        el.textContent = 'Hunter: not configured';
        el.style.color = 'var(--red)';
    } else if (s.error) {
        el.textContent = `Hunter: ${s.error}`;
    } else {
        el.textContent = `Hunter: ${s.used}/${s.used + s.available} used (${s.plan})`;
    }
}

function switchToNewTab() {
    currentBatch = 'new';
    document.querySelectorAll('.tab-link[data-batch]').forEach(el =>
        el.classList.toggle('active', el.dataset.batch === 'new'));
    document.getElementById('bulk-actions').hidden = true;
}

async function refreshOutreach() {
    // Collect fresh jobs from all sources, then generate 15 outreach items
    // scoped to what the collection returned.
    if (!confirm('Run a fresh Collect Jobs and generate 15 new outreach items? Takes 1–3 minutes.')) return;
    const btn = document.getElementById('btn-refresh');
    btn.disabled = true;
    const original = btn.innerHTML;
    btn.textContent = 'Refreshing… (1–3 min)';
    try {
        const data = await api('/outreach/refresh?limit=15', { method: 'POST' });
        const newJobs = data.collected?.new ?? 0;
        showToast(`Collected ${newJobs} new jobs · generated ${data.generated} outreach items`);
        switchToNewTab();
        await Promise.all([loadOutreach(), loadStats(), loadHunterStatus()]);
    } catch (e) {
        showToast('Refresh failed: ' + e.message);
    } finally {
        btn.disabled = false;
        btn.innerHTML = original;
    }
}

async function syncOutreach() {
    // Generate 15 outreach items from jobs already in the DB — no collection.
    const btn = document.getElementById('btn-sync');
    btn.disabled = true;
    const original = btn.innerHTML;
    btn.textContent = 'Syncing…';
    try {
        const data = await api('/outreach/generate?min_score=40&limit=15&india_friendly=maybe', { method: 'POST' });
        if (data.error) {
            showToast(data.error);
        } else if (data.generated === 0) {
            showToast(data.message || 'No new jobs eligible for outreach — try Refresh to collect fresh jobs');
        } else {
            showToast(`Generated ${data.generated} outreach items`);
            switchToNewTab();
        }
        await Promise.all([loadOutreach(), loadStats(), loadHunterStatus()]);
    } catch (e) {
        showToast('Sync failed: ' + e.message);
    } finally {
        btn.disabled = false;
        btn.innerHTML = original;
    }
}

function escapeHtml(str) {
    if (!str) return '';
    const div = document.createElement('div');
    div.textContent = str;
    return div.innerHTML;
}

function formatDate(d) {
    if (!d) return '';
    try { return new Date(d).toLocaleDateString('en-US', { month:'short', day:'numeric', hour:'numeric', minute:'2-digit' }); }
    catch { return d; }
}

function render() {
    const list = document.getElementById('outreach-list');
    if (!outreachItems.length) {
        list.innerHTML = `
            <div class="empty-state">
                <h3>No outreach items yet</h3>
                <p>Click "Find Contacts for Top Jobs" to scan your top-scoring jobs and pull hiring contacts.</p>
            </div>`;
        return;
    }

    const showSelect = currentBatch === 'old' || currentBatch === 'all';

    list.innerHTML = outreachItems.map(item => {
        const statusClassMap = { pending: 'new', emailed: 'reviewed', messaged: 'reviewed', replied: 'applied', followed_up: 'reviewed' };
        const statusBadge = `<span class="status-badge status-${statusClassMap[item.status] || 'reviewed'}">${item.status.replace('_', ' ')}</span>`;
        const jobUrl = item.job_url || '#';
        const checked = selectedIds.has(item.id) ? 'checked' : '';
        const selectBox = showSelect
            ? `<input type="checkbox" ${checked} onchange="toggleSelectOne('${item.id}', this.checked)" style="margin-right:10px;transform:scale(1.2);">`
            : '';
        return `
        <div class="outreach-card">
            <div class="outreach-header">
                <div style="display:flex;align-items:flex-start;">
                    ${selectBox}
                    <div>
                        <h3>${escapeHtml(item.job_title)} <span style="color:var(--text-muted);font-weight:normal;">@ ${escapeHtml(item.company)}</span></h3>
                        <div style="color:var(--text-muted);font-size:13px;margin-top:4px;">
                            Created ${formatDate(item.created_at)}
                        </div>
                    </div>
                </div>
                ${statusBadge}
            </div>

            <div class="outreach-contact">
                <div style="font-size:11px;color:var(--text-muted);text-transform:uppercase;letter-spacing:0.5px;margin-bottom:8px;">Find someone at ${escapeHtml(item.company)}</div>
                ${(() => {
                    let searches = [];
                    try { searches = JSON.parse(item.notes || '[]'); } catch {}
                    if (!searches.length) searches = [{label:'Search LinkedIn', url: item.contact_linkedin, category:'engineering'}];

                    const colors = {
                        engineering: '#0a66c2',  // LinkedIn blue
                        executive: '#6c5ce7',    // purple
                        hr: '#00b894',           // green
                    };
                    const categoryLabels = {
                        engineering: 'Engineering',
                        executive: 'C-Level',
                        hr: 'HR / Recruiters',
                    };

                    // Group by category
                    const grouped = {};
                    searches.forEach(s => {
                        const cat = s.category || 'engineering';
                        if (!grouped[cat]) grouped[cat] = [];
                        grouped[cat].push(s);
                    });

                    return Object.entries(grouped).map(([cat, group]) => `
                        <div style="margin-bottom:8px;">
                            <div style="font-size:10px;color:var(--text-muted);margin-bottom:4px;">${categoryLabels[cat] || cat}</div>
                            ${group.map(s => `
                                <a href="${escapeHtml(s.url)}" target="_blank" class="btn btn-sm" style="background:${colors[cat] || '#0a66c2'};color:white;margin:2px 4px 2px 0;">🔍 ${escapeHtml(s.label)}</a>
                            `).join('')}
                        </div>
                    `).join('');
                })()}
            </div>

            <div class="outreach-dm">
                <div class="dm-label">LinkedIn DM (short — for connection request):</div>
                <div class="dm-text" id="dm-short-${item.id}">${escapeHtml(item.dm_short)}</div>
            </div>

            <details style="margin-top:8px;">
                <summary style="cursor:pointer;color:var(--primary);font-size:13px;">Show long version (for direct message)</summary>
                <div class="dm-text" style="margin-top:8px;white-space:pre-wrap;" id="dm-long-${item.id}">${escapeHtml(item.dm_long)}</div>
            </details>

            <div class="outreach-actions">
                ${item.job_url ? `<a href="${escapeHtml(item.job_url)}" target="_blank" class="btn btn-primary btn-sm">Apply to Job</a>` : ''}
                <button class="btn btn-outline btn-sm" onclick="copyDM('${item.id}', 'short')">Copy Short DM</button>
                <button class="btn btn-outline btn-sm" onclick="copyDM('${item.id}', 'long')">Copy Long DM</button>
                ${(item.status === 'pending' || item.status === 'emailed') ? `<button class="btn btn-yellow btn-sm" onclick="setStatus('${item.id}', 'messaged')">Mark Messaged</button>` : ''}
                ${item.status === 'messaged' ? `<button class="btn btn-green btn-sm" onclick="setStatus('${item.id}', 'replied')">Mark Replied</button>` : ''}
                ${item.status === 'messaged' ? `<button class="btn btn-outline btn-sm" onclick="setStatus('${item.id}', 'followed_up')">Mark Followed Up</button>` : ''}
            </div>
        </div>
    `}).join('');
}

async function setStatus(id, status) {
    await api(`/outreach/${id}/status?status=${status}`, { method: 'PATCH' });
    showToast(`Marked as ${status}`);
    await Promise.all([loadOutreach(), loadStats()]);
}

function copyDM(id, variant) {
    const text = document.getElementById(`dm-${variant}-${id}`).innerText;
    navigator.clipboard.writeText(text).then(() => showToast(`${variant} DM copied!`));
}

function showToast(msg) {
    const existing = document.querySelector('.toast');
    if (existing) existing.remove();
    const t = document.createElement('div');
    t.className = 'toast';
    t.textContent = msg;
    document.body.appendChild(t);
    setTimeout(() => t.remove(), 3000);
}

async function loadActiveProfileIndicator() {
    const el = document.getElementById('active-profile-indicator');
    if (!el) return;
    try {
        const resp = await fetch('/api/profiles/active');
        const a = await resp.json();
        el.textContent = `Profile: ${a.name || '(none)'}`;
    } catch (e) {
        el.textContent = 'Profile: (none)';
    }
}

document.addEventListener('DOMContentLoaded', () => {
    loadOutreach();
    loadStats();
    loadHunterStatus();
    loadEmailStatus();
    loadActiveProfileIndicator();
    let st;
    document.getElementById('filter-search').addEventListener('input', () => {
        clearTimeout(st); st = setTimeout(loadOutreach, 400);
    });
});
