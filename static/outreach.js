let outreachItems = [];

async function api(path, opts = {}) {
    const resp = await fetch(`/api${path}`, opts);
    return resp.json();
}

async function loadOutreach() {
    const status = document.getElementById('filter-status').value;
    const search = document.getElementById('filter-search').value;
    const params = new URLSearchParams();
    if (status) params.set('status', status);
    if (search) params.set('search', search);
    const data = await api(`/outreach?${params}`);
    outreachItems = data.outreach;
    render();
}

async function loadStats() {
    const s = await api('/outreach/stats');
    const by = s.by_status || {};
    document.getElementById('stats-bar').innerHTML = `
        <div class="stat-card"><div class="label">Total</div><div class="value">${s.total || 0}</div></div>
        <div class="stat-card" style="border-color:var(--blue);"><div class="label">Pending</div><div class="value" style="color:var(--blue);">${by.pending || 0}</div></div>
        <div class="stat-card" style="border-color:var(--yellow);"><div class="label">Messaged</div><div class="value" style="color:var(--yellow);">${by.messaged || 0}</div></div>
        <div class="stat-card" style="border-color:var(--green);"><div class="label">Replied</div><div class="value" style="color:var(--green);">${by.replied || 0}</div></div>
        <div class="stat-card"><div class="label">Followed Up</div><div class="value">${by.followed_up || 0}</div></div>
    `;
}

async function loadEmailStatus() {
    const s = await api('/email/status');
    const el = document.getElementById('email-status');
    if (!s.sender_configured) {
        el.textContent = '📧 Email: not configured';
        el.style.color = 'var(--red)';
    } else {
        el.textContent = `📧 Daily ${s.scheduled_hour}:00 IST → ${s.recipient}`;
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
    if (!confirm('Send the daily digest email now to Parmanand?')) return;
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
            showToast(data.message || 'No items to send');
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

async function generateOutreach() {
    const btn = document.getElementById('btn-generate');
    btn.disabled = true; btn.textContent = 'Finding contacts... (1-2 min)';
    try {
        const data = await api('/outreach/generate?min_score=40&limit=10&india_friendly=maybe', { method: 'POST' });
        if (data.error) {
            showToast(data.error);
        } else {
            showToast(`Generated ${data.generated} outreach items (${data.credits_used} credits used)`);
        }
        await Promise.all([loadOutreach(), loadStats(), loadHunterStatus()]);
    } catch (e) {
        showToast('Failed: ' + e.message);
    } finally {
        btn.disabled = false;
        btn.textContent = 'Find Contacts for Top Jobs';
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

    list.innerHTML = outreachItems.map(item => {
        const statusBadge = `<span class="status-badge status-${item.status === 'pending' ? 'new' : item.status === 'replied' ? 'applied' : 'reviewed'}">${item.status}</span>`;
        const jobUrl = item.job_url || '#';
        return `
        <div class="outreach-card">
            <div class="outreach-header">
                <div>
                    <h3>${escapeHtml(item.job_title)} <span style="color:var(--text-muted);font-weight:normal;">@ ${escapeHtml(item.company)}</span></h3>
                    <div style="color:var(--text-muted);font-size:13px;margin-top:4px;">
                        Created ${formatDate(item.created_at)}
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
                ${item.status === 'pending' ? `<button class="btn btn-yellow btn-sm" onclick="setStatus('${item.id}', 'messaged')">Mark Messaged</button>` : ''}
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

document.addEventListener('DOMContentLoaded', () => {
    loadOutreach();
    loadStats();
    loadHunterStatus();
    loadEmailStatus();
    let st;
    document.getElementById('filter-search').addEventListener('input', () => {
        clearTimeout(st); st = setTimeout(loadOutreach, 400);
    });
});
