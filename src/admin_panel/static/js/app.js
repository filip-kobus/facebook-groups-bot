// State management
let paginationState = {
    leads: { currentPage: 1, perPage: 20 },
    contacted: { currentPage: 1, perPage: 20 },
    messages: { currentPage: 1, perPage: 20 },
    groups: { currentPage: 1, perPage: 20 }
};

let currentBot = null;
let eventSource = null;
let currentEditGroup = { botId: null, groupId: null };

// Pagination helper
function createPagination(page, totalPages, callback) {
    let html = '<ul class="pagination pagination-sm mb-0">';
    
    html += `<li class="page-item ${page === 1 ? 'disabled' : ''}">
        <a class="page-link" href="#" data-page="${page - 1}">«</a>
    </li>`;
    
    const maxVisible = 5;
    let startPage = Math.max(1, page - Math.floor(maxVisible / 2));
    let endPage = Math.min(totalPages, startPage + maxVisible - 1);
    
    if (endPage - startPage < maxVisible - 1) {
        startPage = Math.max(1, endPage - maxVisible + 1);
    }
    
    if (startPage > 1) {
        html += `<li class="page-item"><a class="page-link" href="#" data-page="1">1</a></li>`;
        if (startPage > 2) html += `<li class="page-item disabled"><span class="page-link">...</span></li>`;
    }
    
    for (let i = startPage; i <= endPage; i++) {
        html += `<li class="page-item ${i === page ? 'active' : ''}">
            <a class="page-link" href="#" data-page="${i}">${i}</a>
        </li>`;
    }
    
    if (endPage < totalPages) {
        if (endPage < totalPages - 1) html += `<li class="page-item disabled"><span class="page-link">...</span></li>`;
        html += `<li class="page-item"><a class="page-link" href="#" data-page="${totalPages}">${totalPages}</a></li>`;
    }
    
    html += `<li class="page-item ${page === totalPages ? 'disabled' : ''}">
        <a class="page-link" href="#" data-page="${page + 1}">»</a>
    </li>`;
    
    html += '</ul>';
    return html;
}

// Generic load function with pagination
async function loadData(endpoint, page, state) {
    try {
        const response = await fetch(`${endpoint}?page=${page}&per_page=${state.perPage}`);
        const result = await response.json();
        return result;
    } catch (error) {
        console.error(`Error loading ${endpoint}:`, error);
        return null;
    }
}

// Load leads
async function loadLeads(page = 1) {
    const botId = currentBot ? currentBot.bot_id : null;
    const endpoint = botId ? `/api/leads?bot_id=${botId}` : '/api/leads';
    const result = await loadData(endpoint, page, paginationState.leads);
    if (!result) return;
    
    paginationState.leads.currentPage = page;
    const tbody = document.getElementById('leads-tbody');
    
    if (result.data.length === 0) {
        tbody.innerHTML = `
            <tr>
                <td colspan="5" class="text-center text-muted py-4">
                    Brak leadów do kontaktu
                </td>
            </tr>
        `;
    } else {
        tbody.innerHTML = result.data.map(lead => `
            <tr id="lead-${lead.post_id}">
                <td>${lead.author}</td>
                <td>
                    <div class="post-content">${lead.content}</div>
                </td>
                <td class="text-nowrap">${lead.created_at}</td>
                <td>${lead.group_id}</td>
                <td class="text-nowrap">
                    <button class="btn btn-sm btn-warning"
                            hx-post="/api/leads/${lead.post_id}/unmark"
                            hx-target="closest tr"
                            hx-confirm="Odznaczyć ten lead?">
                        ✖️ Odznacz
                    </button>
                    <button class="btn btn-sm btn-danger"
                            hx-delete="/api/leads/${lead.post_id}"
                            hx-target="closest tr"
                            hx-confirm="Usunąć ten lead?">
                        🗑️ Usuń
                    </button>
                </td>
            </tr>
        `).join('');
        htmx.process(tbody);
    }
    
    document.getElementById('leads-info').textContent = 
        `Wyświetlam ${result.data.length > 0 ? ((page - 1) * result.per_page + 1) : 0}-${Math.min(page * result.per_page, result.total)} z ${result.total}`;
    
    const pagination = createPagination(page, result.total_pages, loadLeads);
    document.getElementById('leads-pagination').innerHTML = pagination;
    
    document.querySelectorAll('#leads-pagination .page-link').forEach(link => {
        link.addEventListener('click', (e) => {
            e.preventDefault();
            const newPage = parseInt(e.target.dataset.page);
            if (newPage && newPage !== page) loadLeads(newPage);
        });
    });
}

// Other load functions...
async function loadContacted(page = 1) {
    const result = await loadData('/api/contacted', page, paginationState.contacted);
    if (!result) return;
    
    paginationState.contacted.currentPage = page;
    const tbody = document.getElementById('contacted-tbody');
    
    if (result.data.length === 0) {
        tbody.innerHTML = `<tr><td colspan="5" class="text-center text-muted py-4">Brak skontaktowanych leadów</td></tr>`;
    } else {
        tbody.innerHTML = result.data.map(lead => `
            <tr id="contacted-${lead.post_id}">
                <td>${lead.author}</td>
                <td><div class="post-content">${lead.content}</div></td>
                <td class="text-nowrap">${lead.created_at}</td>
                <td>${lead.group_id}</td>
                <td class="text-nowrap">
                    <button class="btn btn-sm btn-success"
                            hx-post="/api/contacted/${lead.post_id}/reset"
                            hx-target="closest tr"
                            hx-confirm="Zresetować status kontaktu? Bot skontaktuje się ponownie.">
                        🔄 Resetuj
                    </button>
                </td>
            </tr>
        `).join('');
        htmx.process(tbody);
    }
    
    document.getElementById('contacted-info').textContent = 
        `Wyświetlam ${result.data.length > 0 ? ((page - 1) * result.per_page + 1) : 0}-${Math.min(page * result.per_page, result.total)} z ${result.total}`;
    
    const pagination = createPagination(page, result.total_pages, loadContacted);
    document.getElementById('contacted-pagination').innerHTML = pagination;
    
    document.querySelectorAll('#contacted-pagination .page-link').forEach(link => {
        link.addEventListener('click', (e) => {
            e.preventDefault();
            const newPage = parseInt(e.target.dataset.page);
            if (newPage && newPage !== page) loadContacted(newPage);
        });
    });
}

async function loadMessages(page = 1) {
    const result = await loadData('/api/messages', page, paginationState.messages);
    if (!result) return;
    
    paginationState.messages.currentPage = page;
    const tbody = document.getElementById('messages-tbody');
    
    if (result.data.length === 0) {
        tbody.innerHTML = `<tr><td colspan="5" class="text-center text-muted py-4">Brak wysłanych wiadomości</td></tr>`;
    } else {
        tbody.innerHTML = result.data.map(msg => `
            <tr>
                <td class="text-nowrap">${msg.sent_at}</td>
                <td>${msg.post_author}</td>
                <td><div class="post-content small">${msg.post_content}</div></td>
                <td><div class="message-content">${msg.content}</div></td>
                <td class="small">${msg.group_id}</td>
            </tr>
        `).join('');
    }
    
    document.getElementById('messages-info').textContent = 
        `Wyświetlam ${result.data.length > 0 ? ((page - 1) * result.per_page + 1) : 0}-${Math.min(page * result.per_page, result.total)} z ${result.total}`;
    
    const pagination = createPagination(page, result.total_pages, loadMessages);
    document.getElementById('messages-pagination').innerHTML = pagination;
    
    document.querySelectorAll('#messages-pagination .page-link').forEach(link => {
        link.addEventListener('click', (e) => {
            e.preventDefault();
            const newPage = parseInt(e.target.dataset.page);
            if (newPage && newPage !== page) loadMessages(newPage);
        });
    });
}

async function loadGroups(page = 1) {
    const botId = currentBot ? currentBot.bot_id : null;
    const url = botId ? `/api/groups?bot_id=${botId}` : '/api/groups';
    const result = await loadData(url, page, paginationState.groups);
    if (!result) return;
    
    paginationState.groups.currentPage = page;
    const tbody = document.getElementById('groups-tbody');
    
    tbody.innerHTML = result.data.map(group => `
        <tr>
            <td class="text-break small">${group.group_id}</td>
            <td class="text-nowrap small">${group.bot_id}</td>
            <td class="text-nowrap small" id="scrape-date-${group.bot_id}-${group.group_id}">
                ${group.last_scrape_date !== 'Never' ? group.last_scrape_date.substring(0, 16) : 'Nigdy'}
            </td>
            <td>
                ${group.last_run_error ? 
                    `<span class="badge error-badge" title="${group.last_error_message}">❌ Błąd</span>` :
                    `<span class="badge success-badge">✅ OK</span>`
                }
            </td>
            <td>
                <button class="btn btn-sm btn-outline-primary" 
                        onclick="openEditScrapeDate('${group.bot_id}', '${group.group_id}', '${group.last_scrape_date_iso}')">
                    📅 Edytuj datę
                </button>
            </td>
        </tr>
    `).join('');
    
    document.getElementById('groups-info').textContent = 
        `Wyświetlam ${result.data.length > 0 ? ((page - 1) * result.per_page + 1) : 0}-${Math.min(page * result.per_page, result.total)} z ${result.total}`;
    
    const pagination = createPagination(page, result.total_pages, loadGroups);
    document.getElementById('groups-pagination').innerHTML = pagination;
    
    document.querySelectorAll('#groups-pagination .page-link').forEach(link => {
        link.addEventListener('click', (e) => {
            e.preventDefault();
            const newPage = parseInt(e.target.dataset.page);
            if (newPage && newPage !== page) loadGroups(newPage);
        });
    });
}

// Bot management
async function loadBots() {
    try {
        const response = await fetch('/api/bots?enabled_only=false');
        const data = await response.json();
        const select = document.getElementById('botSelect');
        
        select.innerHTML = '<option value="">-- Wybierz bota --</option>';
        data.bots.forEach(bot => {
            const option = document.createElement('option');
            option.value = bot.bot_id;
            option.textContent = `${bot.name} (${bot.bot_type})`;
            option.dataset.botType = bot.bot_type;
            select.appendChild(option);
        });
        
        const firstEnabled = data.bots.find(b => b.enabled);
        if (firstEnabled) {
            select.value = firstEnabled.bot_id;
            onBotChange();
        }
    } catch (error) {
        console.error('Failed to load bots:', error);
        showNotification('Błąd ładowania botów', 'danger');
    }
}

async function onBotChange() {
    const select = document.getElementById('botSelect');
    const botId = select.value;
    
    if (!botId) {
        document.getElementById('botInfo').style.display = 'none';
        currentBot = null;
        return;
    }
    
    try {
        const response = await fetch(`/api/bots/${botId}`);
        const bot = await response.json();
        currentBot = bot;
        
        document.getElementById('botName').textContent = bot.name;
        document.getElementById('botDescription').textContent = bot.description;
        document.getElementById('botGroups').textContent = bot.groups.length + ' grup';
        
        const typeBadge = document.getElementById('botType');
        typeBadge.textContent = bot.bot_type === 'lead_bot' ? 'Lead Bot' : 'Inviter Bot';
        typeBadge.className = `bot-type-badge badge ${bot.bot_type === 'lead_bot' ? 'bg-primary' : 'bg-success'}`;
        
        const processBtn = document.getElementById('btn-process');
        processBtn.innerHTML = bot.bot_type === 'lead_bot' 
            ? '<i class="bi bi-send"></i> Process'
            : '<i class="bi bi-person-plus"></i> Invite';
        
        document.getElementById('botInfo').style.display = 'block';
        
        loadStats(botId);
        loadGroups(1);
    } catch (error) {
        console.error('Failed to load bot details:', error);
        showNotification('Błąd ładowania szczegółów bota', 'danger');
    }
}

// Job control
async function startJob(jobType) {
    if (!currentBot) {
        showNotification('Wybierz bota', 'warning');
        return;
    }
    
    const botId = currentBot.bot_id;
    let endpoint = `/api/bots/${botId}/${jobType === 'full' ? 'run-full' : jobType}`;
    
    disableActionButtons(true);
    
    try {
        const response = await fetch(endpoint, { method: 'POST' });
        const data = await response.json();
        
        if (response.ok) {
            showNotification(`✓ Zadanie uruchomione: ${data.job_id.substring(0, 8)}...`, 'success');
        } else {
            showNotification(`Błąd: ${data.detail || 'Unknown error'}`, 'danger');
            disableActionButtons(false);
        }
    } catch (error) {
        console.error('Failed to start job:', error);
        showNotification('Błąd uruchamiania zadania', 'danger');
        disableActionButtons(false);
    }
}

function disableActionButtons(disabled) {
    ['btn-scrape', 'btn-classify', 'btn-process', 'btn-full'].forEach(id => {
        const btn = document.getElementById(id);
        if (btn) btn.disabled = disabled;
    });
}

async function cancelJob(jobId) {
    if (!confirm('Czy na pewno anulować to zadanie?')) return;
    
    try {
        const response = await fetch(`/api/jobs/${jobId}/cancel`, { method: 'POST' });
        if (response.ok) {
            showNotification('✓ Zadanie anulowane', 'info');
        } else {
            showNotification('Nie udało się anulować zadania', 'danger');
        }
    } catch (error) {
        console.error('Failed to cancel job:', error);
        showNotification('Błąd anulowania zadania', 'danger');
    }
}

function showNotification(message, type = 'info') {
    const container = document.createElement('div');
    container.className = `alert alert-${type} alert-dismissible fade show position-fixed top-0 end-0 m-3`;
    container.style.zIndex = '9999';
    container.innerHTML = `
        ${message}
        <button type="button" class="btn-close" data-bs-dismiss="alert"></button>
    `;
    document.body.appendChild(container);
    
    setTimeout(() => container.remove(), 5000);
}

async function loadStats(botId) {
    try {
        const [leadsResp, contactedResp, groupsResp, messagesResp] = await Promise.all([
            fetch(`/api/leads?per_page=1${botId ? '&bot_id=' + botId : ''}`),
            fetch('/api/contacted?per_page=1'),
            fetch('/api/groups?per_page=1'),
            fetch('/api/messages?per_page=1')
        ]);
        
        const [leadsData, contactedData, groupsData, messagesData] = await Promise.all([
            leadsResp.json(),
            contactedResp.json(),
            groupsResp.json(),
            messagesResp.json()
        ]);
        
        document.getElementById('statLeads').textContent = leadsData.total || 0;
        document.getElementById('statContacted').textContent = contactedData.total || 0;
        document.getElementById('statGroups').textContent = groupsData.total || 0;
        document.getElementById('statMessages').textContent = messagesData.total || 0;
    } catch (error) {
        console.error('Failed to load stats:', error);
    }
}

function renderActiveJobs(jobs) {
    const container = document.getElementById('activeJobsContainer');
    const count = document.getElementById('activeJobsCount');
    
    if (!jobs || jobs.length === 0) {
        container.innerHTML = `
            <div class="no-jobs">
                <i class="bi bi-inbox" style="font-size: 3rem; opacity: 0.3;"></i>
                <p>Brak aktywnych zadań</p>
            </div>
        `;
        count.textContent = '0';
        disableActionButtons(false);
        return;
    }
    
    count.textContent = jobs.length;
    
    container.innerHTML = jobs.map(job => {
        const progressPercent = Math.round(job.progress || 0);
        const statusIcon = {
            'pending': 'hourglass-split',
            'running': 'arrow-repeat',
            'completed': 'check-circle',
            'failed': 'x-circle',
            'cancelled': 'dash-circle'
        }[job.status] || 'question-circle';
        
        const statusColor = {
            'pending': 'secondary',
            'running': 'primary',
            'completed': 'success',
            'failed': 'danger',
            'cancelled': 'secondary'
        }[job.status] || 'info';
        
        return `
            <div class="job-item ${job.status}">
                <div class="d-flex justify-content-between align-items-center mb-2">
                    <div>
                        <strong>${job.bot_id}</strong>
                        <span class="badge bg-${statusColor} ms-2">
                            <i class="bi bi-${statusIcon}"></i> ${job.job_type}
                        </span>
                    </div>
                    <div>
                        <small class="text-muted">${new Date(job.started_at).toLocaleTimeString()}</small>
                        ${job.status === 'running' ? `
                            <button class="btn btn-sm btn-outline-danger ms-2" onclick="cancelJob('${job.job_id}')">
                                <i class="bi bi-stop-circle"></i> Anuluj
                            </button>
                        ` : ''}
                    </div>
                </div>
                <div class="progress">
                    <div class="progress-bar progress-bar-striped ${job.status === 'running' ? 'progress-bar-animated' : ''} bg-${statusColor}" 
                         style="width: ${progressPercent}%">
                        ${progressPercent}%
                    </div>
                </div>
            </div>
        `;
    }).join('');
    
    const hasRunningJob = jobs.some(j => j.status === 'running' && j.bot_id === currentBot?.bot_id);
    disableActionButtons(hasRunningJob);
}

function setupLiveUpdates() {
    if (eventSource) {
        eventSource.close();
    }
    
    eventSource = new EventSource('/api/jobs/stream');
    
    eventSource.onmessage = function(event) {
        try {
            const data = JSON.parse(event.data);
            if (data.jobs) {
                renderActiveJobs(data.jobs);
            }
        } catch (error) {
            console.error('SSE parse error:', error);
        }
    };
    
    eventSource.onerror = function(error) {
        console.error('SSE error:', error);
        document.getElementById('connectionStatus').innerHTML = '<i class="bi bi-circle-fill text-danger"></i> Rozłączony';
        
        setTimeout(() => {
            console.log('Reconnecting SSE...');
            setupLiveUpdates();
        }, 5000);
    };
    
    eventSource.onopen = function() {
        document.getElementById('connectionStatus').innerHTML = '<i class="bi bi-circle-fill text-success"></i> Połączony';
    };
}

function openEditScrapeDate(botId, groupId, currentDate) {
    currentEditGroup = { botId, groupId };
    
    let dateValue = '';
    if (currentDate) {
        const date = new Date(currentDate);
        dateValue = date.toISOString().slice(0, 16);
    } else {
        const date = new Date();
        date.setDate(date.getDate() - 7);
        dateValue = date.toISOString().slice(0, 16);
    }
    
    document.getElementById('scrapeDateInput').value = dateValue;
    document.getElementById('editGroupInfo').textContent = `Bot: ${botId}, Grupa: ${groupId}`;
    
    const modal = new bootstrap.Modal(document.getElementById('editScrapeDateModal'));
    modal.show();
}

async function saveScrapeDate() {
    const newDate = document.getElementById('scrapeDateInput').value;
    
    if (!newDate) {
        alert('Proszę wybrać datę');
        return;
    }
    
    try {
        const response = await fetch(`/api/groups/${currentEditGroup.botId}/${currentEditGroup.groupId}/scrape-date`, {
            method: 'PATCH',
            headers: { 'Content-Type': 'application/json' },
            body: JSON.stringify({ scrape_date: new Date(newDate).toISOString() })
        });
        
        if (!response.ok) {
            const error = await response.json();
            throw new Error(error.detail || 'Błąd podczas aktualizacji daty');
        }
        
        const result = await response.json();
        
        const dateCell = document.getElementById(`scrape-date-${currentEditGroup.botId}-${currentEditGroup.groupId}`);
        if (dateCell) {
            const formattedDate = new Date(result.new_scrape_date).toLocaleString('pl-PL', {
                year: 'numeric', month: '2-digit', day: '2-digit',
                hour: '2-digit', minute: '2-digit'
            }).replace(',', '');
            dateCell.textContent = formattedDate;
        }
        
        const modal = bootstrap.Modal.getInstance(document.getElementById('editScrapeDateModal'));
        modal.hide();
        
        alert('Data została zaktualizowana pomyślnie');
    } catch (error) {
        alert(`Błąd: ${error.message}`);
    }
}

function setQuickDate(daysAgo) {
    const date = new Date();
    date.setDate(date.getDate() - daysAgo);
    document.getElementById('scrapeDateInput').value = date.toISOString().slice(0, 16);
}

// Event listeners
document.addEventListener('DOMContentLoaded', function() {
    loadLeads(1);
    loadBots();
    loadStats();
    setupLiveUpdates();
    
    document.getElementById('contacted-tab')?.addEventListener('shown.bs.tab', function() {
        loadContacted(paginationState.contacted.currentPage);
    });
    
    document.getElementById('messages-tab')?.addEventListener('shown.bs.tab', function() {
        loadMessages(paginationState.messages.currentPage);
    });
    
    document.getElementById('groups-tab')?.addEventListener('shown.bs.tab', function() {
        loadGroups(paginationState.groups.currentPage);
    });
    
    setInterval(() => {
        if (currentBot) loadStats(currentBot.bot_id);
    }, 30000);
});

document.body.addEventListener('htmx:afterRequest', function(event) {
    if (event.detail.successful) {
        const target = event.detail.target;
        if (target && target.tagName === 'TR') {
            target.remove();
            const activeTab = document.querySelector('.nav-link.active')?.id;
            if (activeTab === 'leads-tab') loadLeads(paginationState.leads.currentPage);
            if (activeTab === 'contacted-tab') loadContacted(paginationState.contacted.currentPage);
        }
    }
});

window.addEventListener('beforeunload', function() {
    if (eventSource) {
        eventSource.close();
    }
});
