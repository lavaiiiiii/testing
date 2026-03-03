// API Configuration
const API_BASE = '/api';

// DOM Elements
const chatMessages = document.getElementById('chatMessages');
const userInput = document.getElementById('userInput');
const sendBtn = document.getElementById('sendBtn');
const navBtns = document.querySelectorAll('.nav-btn');
const tabBtns = document.querySelectorAll('.tab-btn');
const emailDetailModal = document.getElementById('emailDetailModal');
const closeModal = document.querySelector('.close');
const clearBtn = document.getElementById('clearBtn');
const composeForm = document.getElementById('composeForm');
const scheduleForm = document.getElementById('scheduleForm');
const gmailLoginBtn = document.getElementById('gmailLoginBtn');
const gmailLogoutBtn = document.getElementById('gmailLogoutBtn');
const gmailAccountBadge = document.getElementById('gmailAccountBadge');
const gmailProfileCard = document.getElementById('gmailProfileCard');
const gmailAvatar = document.getElementById('gmailAvatar');
const gmailName = document.getElementById('gmailName');
const gmailEmail = document.getElementById('gmailEmail');
const openGmailBtn = document.getElementById('openGmailBtn');
const emailFilterSelect = document.getElementById('emailFilterSelect');

// State
let currentPage = 'chat';
let currentTab = {};

// Initialize
document.addEventListener('DOMContentLoaded', () => {
    setupEventListeners();
    loadChatHistory();
    checkOAuthCallback();
    refreshAuthButtons();
    checkRuntimeConfig();
});

async function apiFetch(url, options = {}) {
    return fetch(url, {
        credentials: 'include',
        ...options
    });
}

function checkOAuthCallback() {
    // Check if redirected from Gmail OAuth
    const urlParams = new URLSearchParams(window.location.search);
    if (urlParams.get('gmail_auth') === 'success') {
        // Switch to email page
        const emailNavBtn = document.querySelector('[data-page="emails"]');
        if (emailNavBtn) {
            handlePageChange(emailNavBtn);
            // Show success message
            showNotification('✅ Gmail đã kết nối thành công!', 'success');
            refreshAuthButtons();
            
            // Auto-load today's emails after successful login
            setTimeout(() => {
                loadEmails();
                
                // Also auto-set date picker to today for daily report
                const dateInput = document.getElementById('reportDate');
                if (dateInput) {
                    const today = new Date().toISOString().split('T')[0];
                    dateInput.value = today;
                }
            }, 500);
        }
        // Clean URL
        window.history.replaceState({}, document.title, window.location.pathname);
    }
}

function showNotification(message, type = 'info') {
    // Create notification element
    const notification = document.createElement('div');
    notification.style.cssText = `
        position: fixed;
        top: 20px;
        right: 20px;
        padding: 16px 24px;
        background: ${type === 'success' ? '#4CAF50' : '#2196F3'};
        color: white;
        border-radius: 8px;
        box-shadow: 0 4px 12px rgba(0,0,0,0.15);
        z-index: 10000;
        animation: slideIn 0.3s ease-out;
    `;
    notification.textContent = message;
    document.body.appendChild(notification);
    
    // Auto remove after 3 seconds
    setTimeout(() => {
        notification.style.animation = 'slideOut 0.3s ease-out';
        setTimeout(() => notification.remove(), 300);
    }, 3000);
}

function setupEventListeners() {
    // Navigation
    navBtns.forEach(btn => {
        btn.addEventListener('click', () => handlePageChange(btn));
    });
    
    // Chat
    sendBtn.addEventListener('click', sendMessage);
    userInput.addEventListener('keypress', (e) => {
        if (e.key === 'Enter' && !e.shiftKey) {
            e.preventDefault();
            sendMessage();
        }
    });
    
    // Tabs
    tabBtns.forEach(btn => {
        btn.addEventListener('click', () => handleTabChange(btn));
    });
    
    // Modal
    closeModal.addEventListener('click', () => closeModalWindow());
    window.addEventListener('click', (e) => {
        if (e.target === emailDetailModal) {
            closeModalWindow();
        }
    });
    
    // Forms
    composeForm.addEventListener('submit', handleComposeSubmit);
    scheduleForm.addEventListener('submit', handleScheduleSubmit);
    
    // Clear history
    clearBtn.addEventListener('click', () => {
        if (confirm('Bạn có chắc chắn muốn xóa lịch sử?')) {
            chatMessages.innerHTML = '';
        }
    });
    
    // Other buttons
    document.getElementById('refreshEmailsBtn').addEventListener('click', loadEmails);
    if (openGmailBtn) openGmailBtn.addEventListener('click', () => window.open('https://mail.google.com', '_blank'));
    if (gmailLoginBtn) gmailLoginBtn.addEventListener('click', gmailLogin);
    if (gmailLogoutBtn) gmailLogoutBtn.addEventListener('click', gmailLogout);
    if (emailFilterSelect) emailFilterSelect.addEventListener('change', loadEmails);
    const generateReportBtn = document.getElementById('generateReportBtn');
    if (generateReportBtn) generateReportBtn.addEventListener('click', generateDailyReport);
}

async function refreshAuthButtons() {
    if (!gmailLoginBtn || !gmailLogoutBtn) return;
    try {
        const response = await apiFetch(`${API_BASE}/email/auth-status`);
        const data = await response.json();
        const isAuth = !!(data && data.success && data.authenticated);
        gmailLoginBtn.style.display = isAuth ? 'none' : 'inline-block';
        gmailLogoutBtn.style.display = isAuth ? 'inline-block' : 'none';
        if (openGmailBtn) openGmailBtn.style.display = isAuth ? 'inline-block' : 'none';

        const profileName = (data && data.gmail_name) ? data.gmail_name : 'Google User';
        const profileEmail = (data && data.gmail_email) ? data.gmail_email : '';
        const profilePicture = (data && data.gmail_picture) ? data.gmail_picture : '';
        const connectedAt = (data && data.connected_at) ? new Date(data.connected_at * 1000).toLocaleString('vi-VN') : '';

        if (gmailAccountBadge) {
            gmailAccountBadge.textContent = isAuth
                ? 'Đã kết nối Gmail'
                : 'Chưa đăng nhập Gmail';
            gmailAccountBadge.style.display = isAuth ? 'none' : 'inline-block';
        }

        if (gmailProfileCard) {
            gmailProfileCard.style.display = isAuth ? 'inline-flex' : 'none';
        }
        if (gmailName) gmailName.textContent = profileName;
        if (gmailEmail) gmailEmail.textContent = profileEmail;
        if (gmailAvatar) {
            gmailAvatar.src = profilePicture || 'https://www.gravatar.com/avatar/?d=mp&s=64';
        }
        if (gmailProfileCard) {
            gmailProfileCard.title = connectedAt ? `Đã kết nối từ: ${connectedAt}` : '';
        }
    } catch {
        gmailLoginBtn.style.display = 'inline-block';
        gmailLogoutBtn.style.display = 'none';
        if (openGmailBtn) openGmailBtn.style.display = 'none';
        if (gmailAccountBadge) gmailAccountBadge.textContent = 'Chưa đăng nhập Gmail';
        if (gmailAccountBadge) gmailAccountBadge.style.display = 'inline-block';
        if (gmailProfileCard) gmailProfileCard.style.display = 'none';
    }
}

async function gmailLogout() {
    if (!confirm('Bạn có chắc muốn đăng xuất Gmail?')) return;

    try {
        const response = await apiFetch(`${API_BASE}/email/logout`, {
            method: 'POST',
            headers: { 'Content-Type': 'application/json' }
        });
        const data = await response.json();

        if (data.success) {
            showNotification('✅ Đã đăng xuất Gmail', 'success');
            await refreshAuthButtons();
            const emailsList = document.getElementById('emailsList');
            if (emailsList) {
                emailsList.innerHTML = '<p>Đã đăng xuất Gmail. Vui lòng đăng nhập lại.</p>';
            }
        } else {
            alert('Lỗi: ' + (data.error || 'Không thể đăng xuất'));
        }
    } catch (err) {
        alert('Lỗi khi đăng xuất Gmail: ' + err.message);
    }
}

// Page Management
function handlePageChange(btn) {
    const page = btn.dataset.page;
    
    // Update navigation
    navBtns.forEach(b => b.classList.remove('active'));
    btn.classList.add('active');
    
    // Update pages
    document.querySelectorAll('.page').forEach(p => p.classList.remove('active'));
    document.getElementById(`${page}-page`).classList.add('active');
    
    currentPage = page;
    
    // Load page data
    if (page === 'emails') {
        loadEmails();
    } else if (page === 'schedule') {
        loadSchedules();
    } else if (page === 'history') {
        loadActivityHistory();
    }
}

// Tab Management
function handleTabChange(btn) {
    const tabName = btn.dataset.tab;
    const parentTabs = btn.parentElement;
    
    // Update active tab button
    parentTabs.querySelectorAll('.tab-btn').forEach(b => b.classList.remove('active'));
    btn.classList.add('active');
    
    // Update tab content visibility
    const tabContentId = `${tabName}-tab`;
    parentTabs.parentElement.querySelectorAll('.tab-content').forEach(content => {
        content.style.display = 'none';
    });
    document.getElementById(tabContentId).style.display = 'block';
}

// Chat Functions
async function sendMessage() {
    const message = userInput.value.trim();
    if (!message) return;
    
    // Add user message to UI
    addMessage(message, 'user');
    userInput.value = '';
    
    // Show loading
    const loadingDiv = document.createElement('div');
    loadingDiv.className = 'message assistant';
    loadingDiv.innerHTML = '<div class="message-content"><div class="loading"></div></div>';
    chatMessages.appendChild(loadingDiv);
    chatMessages.scrollTop = chatMessages.scrollHeight;
    
    try {
        const response = await apiFetch(`${API_BASE}/chat/message`, {
            method: 'POST',
            headers: { 'Content-Type': 'application/json' },
            body: JSON.stringify({ message })
        });
        
        const data = await response.json();
        loadingDiv.remove();
        
        if (data.success) {
            addMessage(data.response, 'assistant');
            if (data.demo_mode) {
                showNotification('⚠️ Đang dùng Demo Mode (chưa có AI key trên server).', 'info');
            }
        } else {
            addMessage('Xảy ra lỗi: ' + (data.error || 'Unknown error'), 'assistant');
        }
    } catch (error) {
        loadingDiv.remove();
        addMessage('Lỗi kết nối: ' + error.message, 'assistant');
    }
}

function addMessage(text, role) {
    const messageDiv = document.createElement('div');
    messageDiv.className = `message ${role}`;
    messageDiv.innerHTML = `<div class="message-content">${escapeHtml(text)}</div>`;
    chatMessages.appendChild(messageDiv);
    chatMessages.scrollTop = chatMessages.scrollHeight;
}

async function loadChatHistory() {
    try {
        const response = await apiFetch(`${API_BASE}/chat/history?limit=20`);
        const data = await response.json();
        
        if (data.success && data.history.length > 0) {
            chatMessages.innerHTML = '';
            data.history.reverse().forEach(record => {
                addMessage(record.user_message, 'user');
                addMessage(record.assistant_response, 'assistant');
            });
        }
    } catch (error) {
        console.error('Error loading chat history:', error);
    }
}

// Email Functions
async function gmailLogin() {
    try {
        const response = await apiFetch(`${API_BASE}/email/auth_url`);
        const data = await response.json();

        if (!response.ok || !data.auth_url) {
            let detail = data.error || 'OAuth chưa được cấu hình trên server.';
            try {
                const statusResp = await apiFetch(`${API_BASE}/status`);
                const status = await statusResp.json();
                if (status && !status.gmail_configured) {
                    detail += '\n\nThiếu cấu hình Gmail trên Vercel. Hãy set:\n- GMAIL_CLIENT_ID + GMAIL_CLIENT_SECRET\nhoặc\n- GMAIL_CREDENTIALS_JSON (toàn bộ JSON OAuth)';
                }
            } catch {}
            alert('Chưa thể đăng nhập Gmail: ' + detail);
            return;
        }

        window.location.href = data.auth_url;
    } catch (err) {
        alert('Lỗi khi tạo đường dẫn đăng nhập Gmail: ' + err.message);
        console.error('gmailLogin error:', err);
    }
}

async function checkRuntimeConfig() {
    try {
        const [providersResp, statusResp] = await Promise.all([
            apiFetch(`${API_BASE}/chat/providers`),
            apiFetch(`${API_BASE}/status`)
        ]);

        const providersData = await providersResp.json();
        const statusData = await statusResp.json();

        const providers = providersData?.providers?.configured_providers || [];
        const demoMode = !!providersData?.providers?.demo_mode;

        if (demoMode || providers.length === 0) {
            const missingProviders = providersData?.providers?.missing_providers || [];
            const hint = missingProviders.length > 0 ? ` Thiếu: ${missingProviders.join(', ')}.` : '';
            showNotification(`⚠️ Chat đang ở Demo Mode.${hint}`, 'info');
        }

        if (statusData && statusData.gmail_configured === false) {
            showNotification('⚠️ Gmail OAuth chưa cấu hình. Set GMAIL_CLIENT_ID + GMAIL_CLIENT_SECRET hoặc GMAIL_CREDENTIALS_JSON.', 'info');
        }
    } catch (error) {
        console.error('Runtime config check failed:', error);
    }
}

async function loadEmails() {
    const emailsList = document.getElementById('emailsList');
    emailsList.innerHTML = '<p>Đang tải email...</p>';
    const selectedFilter = emailFilterSelect ? emailFilterSelect.value : 'education';

    refreshAuthButtons();
    
    try {
        const response = await apiFetch(`${API_BASE}/email/get-unread?max_results=10&filter=${encodeURIComponent(selectedFilter)}`);
        const data = await response.json();
        
        if (data && data.error === 'not_authenticated') {
            emailsList.innerHTML = `<p>Chưa đăng nhập Gmail.</p><p><button id="loginPromptBtn" class="btn-primary">Đăng nhập Gmail</button></p>`;
            const lp = document.getElementById('loginPromptBtn');
            if (lp) lp.addEventListener('click', gmailLogin);
            return;
        }

        if (data.success && data.emails.length > 0) {
            emailsList.innerHTML = '';
            // Show filter stats
            if (data.total_filtered) {
                const filterLabelMap = {
                    all: 'tất cả',
                    education: 'giáo dục',
                    work: 'công việc',
                    meeting: 'họp',
                    promotion: 'khuyến mãi',
                    finance: 'tài chính',
                    personal: 'cá nhân',
                    other: 'khác'
                };
                const label = filterLabelMap[selectedFilter] || selectedFilter;
                const statsDiv = document.createElement('div');
                statsDiv.style.cssText = 'padding: 12px; background: #E8F5E9; border-radius: 8px; margin-bottom: 16px; font-size: 14px;';
                statsDiv.innerHTML = `
                    <strong>🔎 Bộ lọc email (${label}):</strong> 
                    ${data.matched_count} email khớp / ${data.total_filtered} đã quét
                `;
                emailsList.appendChild(statsDiv);
            }
            
            data.emails.forEach(email => {
                const emailDiv = document.createElement('div');
                emailDiv.className = 'email-item';
                
                // Show classification keywords if available
                let keywordBadges = '';
                if (email.classification && email.classification.keywords) {
                    keywordBadges = `<div style="margin-top: 8px;">
                        ${email.classification.keywords.map(kw => 
                            `<span style="display: inline-block; padding: 2px 8px; background: #4CAF50; color: white; border-radius: 12px; font-size: 11px; margin-right: 4px;">${kw}</span>`
                        ).join('')}
                    </div>`;
                }
                
                emailDiv.innerHTML = `
                    <div class="email-item-header">
                        <span class="email-item-subject">${escapeHtml(email.subject)}</span>
                    </div>
                    <div class="email-item-sender">Từ: ${escapeHtml(email.sender)}</div>
                    <div class="email-item-snippet">${escapeHtml(email.snippet)}</div>
                    ${keywordBadges}
                    <div class="email-item-actions" style="margin-top: 8px; display: flex; gap: 6px;">
                        <button class="email-quick-summarize-btn" style="padding: 4px 12px; font-size: 12px; background: #2196F3; color: white; border: none; border-radius: 4px; cursor: pointer;">📝 Tóm tắt</button>
                        <button class="email-view-detail-btn" style="padding: 4px 12px; font-size: 12px; background: #666; color: white; border: none; border-radius: 4px; cursor: pointer;">👁️ Xem</button>
                    </div>
                `;
                
                // Quick summarize button
                const summarizeBtn = emailDiv.querySelector('.email-quick-summarize-btn');
                summarizeBtn.addEventListener('click', (e) => {
                    e.stopPropagation();
                    quickSummarizeEmail(email, summarizeBtn);
                });
                
                // View detail button
                const viewBtn = emailDiv.querySelector('.email-view-detail-btn');
                viewBtn.addEventListener('click', (e) => {
                    e.stopPropagation();
                    showEmailDetail(email);
                });
                
                emailsList.appendChild(emailDiv);
            });
        } else {
            emailsList.innerHTML = `<p>Không có email phù hợp bộ lọc: ${escapeHtml(selectedFilter)}</p>`;
        }
    } catch (error) {
        emailsList.innerHTML = `<p>Lỗi: ${error.message}</p>`;
    }
}

function showEmailDetail(email) {
    const emailDetail = document.getElementById('emailDetail');
    emailDetail.innerHTML = `
        <div class="email-detail-subject">${escapeHtml(email.subject)}</div>
        <div class="email-detail-meta">
            <strong>Từ:</strong> ${escapeHtml(email.sender)}<br>
            <strong>Ngày:</strong> ${escapeHtml(email.date)}
        </div>
        <div class="email-detail-body">${escapeHtml(email.body)}</div>
    `;
    
    // Setup modal actions
    document.getElementById('summarizeBtn').onclick = () => summarizeEmail(email);
    document.getElementById('replyBtn').onclick = () => showReplyOptions(email);
    
    emailDetailModal.classList.add('show');
}

async function summarizeEmail(email) {
    const summarizeBtn = document.getElementById('summarizeBtn');
    const originalText = summarizeBtn.textContent;
    summarizeBtn.textContent = 'Đang tóm tắt...';
    summarizeBtn.disabled = true;
    
    try {
        const response = await apiFetch(`${API_BASE}/chat/summarize-email`, {
            method: 'POST',
            headers: { 'Content-Type': 'application/json' },
            body: JSON.stringify({ content: email.body })
        });
        
        const data = await response.json();
        if (data.success) {
            alert('Tóm tắt:\n\n' + data.summary);
        }
    } catch (error) {
        alert('Lỗi: ' + error.message);
    } finally {
        summarizeBtn.textContent = originalText;
        summarizeBtn.disabled = false;
    }
}

async function quickSummarizeEmail(email, btn) {
    const originalText = btn.textContent;
    btn.textContent = '⏳ Đang tóm tắt...';
    btn.disabled = true;
    
    try {
        const response = await apiFetch(`${API_BASE}/chat/summarize-email`, {
            method: 'POST',
            headers: { 'Content-Type': 'application/json' },
            body: JSON.stringify({ content: email.body })
        });
        
        const data = await response.json();
        if (data.success) {
            // Show summary in a styled popup instead of alert
            showSummaryPopup(email.subject, data.summary);
        } else {
            alert('Lỗi: ' + (data.error || 'Không thể tóm tắt'));
        }
    } catch (error) {
        alert('Lỗi: ' + error.message);
    } finally {
        btn.textContent = originalText;
        btn.disabled = false;
    }
}

function showSummaryPopup(subject, summary) {
    // Create a simple overlay popup for summary
    const overlay = document.createElement('div');
    overlay.style.cssText = `
        position: fixed;
        top: 0;
        left: 0;
        right: 0;
        bottom: 0;
        background: rgba(0,0,0,0.5);
        display: flex;
        align-items: center;
        justify-content: center;
        z-index: 5000;
    `;
    
    const popup = document.createElement('div');
    popup.style.cssText = `
        background: white;
        border-radius: 12px;
        padding: 24px;
        max-width: 600px;
        max-height: 70vh;
        overflow-y: auto;
        box-shadow: 0 8px 32px rgba(0,0,0,0.2);
    `;
    
    popup.innerHTML = `
        <h3 style="margin: 0 0 12px 0; color: #333;">📝 Tóm tắt: ${escapeHtml(subject)}</h3>
        <div style="color: #666; line-height: 1.6; white-space: pre-wrap;">${escapeHtml(summary)}</div>
        <div style="margin-top: 20px; text-align: right;">
            <button id="closeSummaryBtn" class="btn-primary" style="padding: 8px 16px; cursor: pointer;">Đóng</button>
        </div>
    `;
    
    overlay.appendChild(popup);
    document.body.appendChild(overlay);
    
    // Close handlers
    document.getElementById('closeSummaryBtn').addEventListener('click', () => overlay.remove());
    overlay.addEventListener('click', (e) => {
        if (e.target === overlay) overlay.remove();
    });
}

function showReplyOptions(email) {
    const context = `Email từ ${email.sender}: ${email.subject}`;
    const choice = prompt('Chọn hành động:\n1. Đồng ý\n2. Từ chối\n3. Yêu cầu thông tin thêm\n\n(Nhập 1, 2 hoặc 3)');
    
    if (choice) {
        const choiceMap = {
            '1': 'Đồng ý với yêu cầu',
            '2': 'Từ chối yêu cầu một cách chuyên nghiệp',
            '3': 'Yêu cầu thông tin thêm và chi tiết'
        };
        
        if (choiceMap[choice]) {
            generateReply(context, choiceMap[choice], email.sender);
        }
    }
}

async function generateReply(context, choice, recipient) {
    try {
        const response = await apiFetch(`${API_BASE}/chat/generate-reply`, {
            method: 'POST',
            headers: { 'Content-Type': 'application/json' },
            body: JSON.stringify({ context, choice })
        });
        
        const data = await response.json();
        if (data.success) {
            closeModalWindow();
            showReplyCompose(recipient, data.reply);
        }
    } catch (error) {
        alert('Lỗi: ' + error.message);
    }
}

function showReplyCompose(recipient, body) {
    const tabBtn = document.querySelector('[data-tab="compose"]');
    tabBtn.click();
    
    document.getElementById('emailTo').value = recipient;
    document.getElementById('emailBody').value = body;
}

async function handleComposeSubmit(e) {
    e.preventDefault();
    
    const to = document.getElementById('emailTo').value.trim();
    const subject = document.getElementById('emailSubject').value.trim();
    const body = document.getElementById('emailBody').value.trim();
    
    try {
        const response = await apiFetch(`${API_BASE}/email/send-reply`, {
            method: 'POST',
            headers: { 'Content-Type': 'application/json' },
            body: JSON.stringify({ to, subject, body })
        });
        
        const data = await response.json();
        if (data.success) {
            alert('Email đã được gửi!');
            composeForm.reset();
        } else {
            alert('Lỗi: ' + (data.error || 'Không thể gửi email'));
        }
    } catch (error) {
        alert('Lỗi: ' + error.message);
    }
}

async function generateDailyReport() {
    const dateInput = document.getElementById('reportDate');
    const container = document.getElementById('dailyReportContainer');
    const btn = document.getElementById('generateReportBtn');

    if (!dateInput || !container || !btn) return;

    if (!dateInput.value) {
        alert('Vui lòng chọn ngày');
        return;
    }

    const [yyyy, mm, dd] = dateInput.value.split('-');
    const dateForApi = `${dd}/${mm}/${yyyy}`;

    container.innerHTML = '<p>Đang tạo báo cáo...</p>';
    btn.disabled = true;

    try {
        const response = await apiFetch(`${API_BASE}/email/summarize-by-date`, {
            method: 'POST',
            headers: { 'Content-Type': 'application/json' },
            body: JSON.stringify({ date: dateForApi, max_results: 30 })
        });

        const data = await response.json();

        if (data && data.error === 'not_authenticated') {
            container.innerHTML = `<p>Chưa đăng nhập Gmail.</p><p><button id="loginPromptBtn2" class="btn-primary">Đăng nhập Gmail</button></p>`;
            const lp = document.getElementById('loginPromptBtn2');
            if (lp) lp.addEventListener('click', gmailLogin);
            return;
        }

        if (!data.success) {
            container.innerHTML = `<p>Lỗi: ${escapeHtml(data.error || 'Không thể tạo báo cáo')}</p>`;
            return;
        }

        if (!data.rows || data.rows.length === 0) {
            container.innerHTML = `<p>Không có email trong ngày ${escapeHtml(data.date)}.</p>`;
            return;
        }

        const rowsHtml = data.rows.map((row, index) => `
            <tr>
                <td>${index + 1}</td>
                <td>${escapeHtml(row.sender || '')}</td>
                <td>${escapeHtml(row.summary || '')}</td>
            </tr>
        `).join('');

        container.innerHTML = `
            <div class="report-meta">
                <strong>Ngày:</strong> ${escapeHtml(data.date)} &nbsp;|&nbsp;
                <strong>Tổng email:</strong> ${data.total_emails}
            </div>
            <table class="report-table">
                <thead>
                    <tr>
                        <th>#</th>
                        <th>Người gửi</th>
                        <th>Nội dung tóm tắt</th>
                    </tr>
                </thead>
                <tbody>
                    ${rowsHtml}
                </tbody>
            </table>
        `;
    } catch (error) {
        container.innerHTML = `<p>Lỗi: ${escapeHtml(error.message)}</p>`;
    } finally {
        btn.disabled = false;
    }
}

// Schedule Functions
async function loadSchedules() {
    const schedulesList = document.getElementById('schedulesList');
    schedulesList.innerHTML = '<p>Đang tải lịch hẹn...</p>';
    
    try {
        const response = await apiFetch(`${API_BASE}/schedule/upcoming`);
        const data = await response.json();
        
        if (data.success && data.schedules.length > 0) {
            schedulesList.innerHTML = '';
            data.schedules.forEach(schedule => {
                const scheduleDiv = document.createElement('div');
                scheduleDiv.className = 'schedule-item';
                const startTime = new Date(schedule.start_time).toLocaleString('vi-VN');
                scheduleDiv.innerHTML = `
                    <div style="font-weight: 600;">${escapeHtml(schedule.title)}</div>
                    <div style="font-size: 12px; color: var(--text-secondary); margin-top: 4px;">
                        ${startTime}
                    </div>
                    ${schedule.description ? `<div style="font-size: 13px; margin-top: 8px;">${escapeHtml(schedule.description)}</div>` : ''}
                `;
                schedulesList.appendChild(scheduleDiv);
            });
        } else {
            schedulesList.innerHTML = '<p>Không có lịch hẹn sắp tới</p>';
        }
    } catch (error) {
        schedulesList.innerHTML = `<p>Lỗi: ${error.message}</p>`;
    }
}

async function handleScheduleSubmit(e) {
    e.preventDefault();
    
    const title = document.getElementById('scheduleTitle').value.trim();
    const description = document.getElementById('scheduleDesc').value.trim();
    const start_time = document.getElementById('scheduleTime').value;
    const attendees_str = document.getElementById('scheduleAttendees').value.trim();
    const attendees = attendees_str ? attendees_str.split(',').map(e => e.trim()) : [];
    
    try {
        const response = await apiFetch(`${API_BASE}/schedule/create`, {
            method: 'POST',
            headers: { 'Content-Type': 'application/json' },
            body: JSON.stringify({ title, description, start_time, attendees })
        });
        
        const data = await response.json();
        if (data.success) {
            alert('Lịch hẹn đã được tạo!');
            scheduleForm.reset();
            loadSchedules();
        } else {
            alert('Lỗi: ' + (data.error || 'Không thể tạo lịch hẹn'));
        }
    } catch (error) {
        alert('Lỗi: ' + error.message);
    }
}

// History Functions
async function loadActivityHistory() {
    const historyList = document.getElementById('historyList');
    historyList.innerHTML = '<p>Đang tải lịch sử...</p>';
    
    try {
        const response = await apiFetch(`${API_BASE}/chat/history?limit=50`);
        const data = await response.json();
        
        if (data.success && data.history.length > 0) {
            historyList.innerHTML = '';
            data.history.forEach(record => {
                const historyDiv = document.createElement('div');
                historyDiv.className = 'history-item';
                const date = new Date(record.created_at).toLocaleString('vi-VN');
                historyDiv.innerHTML = `
                    <div style="font-weight: 600;">
                        ${getActionLabel(record.action_type)}
                    </div>
                    <div style="font-size: 12px; color: var(--text-secondary); margin-top: 4px;">
                        ${date}
                    </div>
                    <div style="font-size: 13px; margin-top: 8px; color: var(--text-secondary);">
                        ${escapeHtml(record.user_message.substring(0, 100))}...
                    </div>
                `;
                historyList.appendChild(historyDiv);
            });
        } else {
            historyList.innerHTML = '<p>Không có lịch sử hoạt động</p>';
        }
    } catch (error) {
        historyList.innerHTML = `<p>Lỗi: ${error.message}</p>`;
    }
}

function getActionLabel(actionType) {
    const labels = {
        'chat': '💬 Chat',
        'email_summary': '📧 Tóm tắt email',
        'email_daily_summary': '📊 Báo cáo email theo ngày',
        'email_reply': '📧 Trả lời email',
        'email_sent': '📧 Gửi email',
        'schedule_created': '📅 Tạo lịch hẹn',
        'schedule_updated': '📅 Cập nhật lịch hẹn'
    };
    return labels[actionType] || actionType;
}

// Modal Functions
function closeModalWindow() {
    emailDetailModal.classList.remove('show');
}

// Utility Functions
function escapeHtml(text) {
    const div = document.createElement('div');
    div.textContent = text;
    return div.innerHTML;
}
