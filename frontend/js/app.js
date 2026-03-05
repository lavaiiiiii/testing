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
    loadUserProfile();
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
        console.log('OAuth callback detected - session should be established');
        
        // Switch to email page
        const emailNavBtn = document.querySelector('[data-page="emails"]');
        if (emailNavBtn) {
            handlePageChange(emailNavBtn);
            showNotification('✅ Gmail đã kết nối thành công!', 'success');
            
            // Mark Gmail as connected in user profile
            apiFetch(`${API_BASE}/user/gmail-connected`, {
                method: 'POST',
                headers: { 'Content-Type': 'application/json' }
            }).catch(err => console.error('Error marking Gmail connected:', err));
            
            // Verify session was persisted by checking auth status
            setTimeout(() => {
                refreshAuthButtons();
                loadUserProfile();
                
                // Wait a bit more, then load emails with retry logic
                setTimeout(async () => {
                    try {
                        console.log('Loading emails after OAuth...');
                        await loadEmails();
                    } catch (err) {
                        console.error('First email load failed, retrying:', err);
                        // Retry after session refresh
                        setTimeout(() => loadEmails(), 1000);
                    }
                    
                    // Also auto-set date picker to today for daily report
                    const dateInput = document.getElementById('reportDate');
                    if (dateInput) {
                        const today = new Date().toISOString().split('T')[0];
                        dateInput.value = today;
                    }
                }, 300);
            }, 200);
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
    document.getElementById('editScheduleForm').addEventListener('submit', handleEditScheduleSubmit);
    
    // Modal close handlers
    const editScheduleModal = document.getElementById('editScheduleModal');
    editScheduleModal.querySelector('.close').addEventListener('click', () => {
        editScheduleModal.style.display = 'none';
    });
    
    // Clear history
    clearBtn.addEventListener('click', clearConversation);
    
    // User avatar - click to login Gmail
    const userAvatar = document.getElementById('userAvatar');
    if (userAvatar) userAvatar.addEventListener('click', gmailLogin);
    
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
            
            // Mark Gmail as disconnected in user profile
            apiFetch(`${API_BASE}/user/gmail-disconnected`, {
                method: 'POST',
                headers: { 'Content-Type': 'application/json' }
            }).catch(err => console.error('Error marking Gmail disconnected:', err));
            
            await refreshAuthButtons();
            loadUserProfile();
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
            // Add provider badge to show which AI responded
            const providerBadge = data.provider ? 
                `<span class="provider-badge" style="font-size: 11px; padding: 2px 8px; background: ${data.demo_mode ? '#FF9800' : '#4CAF50'}; color: white; border-radius: 10px; margin-left: 8px;">
                    ${data.demo_mode ? '🎭 Demo' : '🤖 ' + data.provider.toUpperCase()}
                </span>` : '';
            
            addMessage(data.response, 'assistant', providerBadge);
            
            if (data.demo_mode) {
                showNotification('⚠️ Đang dùng Demo Mode - Tất cả AI providers đang trong cooldown hoặc chưa cấu hình', 'info');
            }
        } else {
            addMessage('Xảy ra lỗi: ' + (data.error || 'Unknown error'), 'assistant');
        }
    } catch (error) {
        loadingDiv.remove();
        addMessage('Lỗi kết nối: ' + error.message, 'assistant');
    }
}

function addMessage(text, role, badge = '') {
    const messageDiv = document.createElement('div');
    messageDiv.className = `message ${role}`;
    messageDiv.innerHTML = `<div class="message-content">${renderMarkdown(escapeHtml(text))}${badge}</div>`;
    chatMessages.appendChild(messageDiv);
    chatMessages.scrollTop = chatMessages.scrollHeight;
}

async function loadUserProfile() {
    try {
        const response = await apiFetch(`${API_BASE}/user/profile`);
        const data = await response.json();
        
        if (data.success && data.user) {
            const user = data.user;
            const userAvatar = document.getElementById('userAvatar');
            const userName = document.getElementById('userName');
            
            if (userName) userName.textContent = user.name || 'Teacher';
            
            if (userAvatar) {
                if (user.avatar_url) {
                    userAvatar.src = user.avatar_url;
                } else {
                    // Default avatar with initials
                    const initials = (user.name || 'T').substring(0, 1).toUpperCase();
                    userAvatar.style.backgroundColor = '#4F46E5';
                    userAvatar.style.display = 'flex';
                    userAvatar.style.alignItems = 'center';
                    userAvatar.style.justifyContent = 'center';
                    userAvatar.style.fontSize = '20px';
                    userAvatar.style.fontWeight = 'bold';
                    userAvatar.style.color = 'white';
                    userAvatar.textContent = initials;
                }
                userAvatar.title = 'Click để đăng nhập Gmail';
            }
        }
    } catch (error) {
        console.error('Error loading user profile:', error);
    }
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

async function clearConversation() {
    if (!confirm('Bạn có chắc chắn muốn làm mới cuộc trò chuyện?')) return;
    
    try {
        const response = await apiFetch(`${API_BASE}/chat/clear`, {
            method: 'POST',
            headers: { 'Content-Type': 'application/json' }
        });
        
        const data = await response.json();
        
        if (data.success) {
            chatMessages.innerHTML = '';
            showNotification(`${data.message}`, 'success');
        } else {
            showNotification('Lỗi khi xóa lịch sử', 'error');
        }
    } catch (error) {
        showNotification('Lỗi kết nối: ' + error.message, 'error');
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
        const response = await apiFetch(`${API_BASE}/chat/providers`);
        const data = await response.json();
        
        if (data.success && data.providers) {
            const providers = data.providers;
            const statusBar = document.getElementById('providerStatus');
            
            // Show warning if no providers configured or all unhealthy
            if (providers.demo_mode) {
                if (providers.configured_providers && providers.configured_providers.length > 0) {
                    // Has providers but all in cooldown
                    const healthInfo = providers.provider_health || {};
                    const cooldowns = Object.keys(healthInfo).map(p => {
                        const h = healthInfo[p];
                        return `${p.toUpperCase()}: ${h.cooldown_remaining_minutes ? Math.round(h.cooldown_remaining_minutes) + 'min' : 'N/A'}`;
                    }).join(', ');
                    
                    console.warn(`⚠️ Demo Mode - Tất cả AI providers đang cooldown: ${cooldowns}`);
                    
                    if (statusBar) {
                        statusBar.innerHTML = `🎭 <strong>Demo Mode</strong> - Tất cả AI providers đang cooldown: ${cooldowns}`;
                        statusBar.style.background = '#FFF3E0';
                        statusBar.style.color = '#E65100';
                    }
                } else {
                    console.warn('⚠️ Demo Mode - Chưa cấu hình AI provider nào');
                    if (statusBar) {
                        statusBar.innerHTML = '🎭 <strong>Demo Mode</strong> - Chưa cấu hình AI provider';
                        statusBar.style.background = '#FFF3E0';
                        statusBar.style.color = '#E65100';
                    }
                }
            } else {
                // Show active providers with health status
                const activeProviders = providers.configured_providers || [];
                const healthInfo = providers.provider_health || {};
                
                const statusBadges = activeProviders.map(p => {
                    const health = healthInfo[p] || {};
                    const emoji = health.healthy ? '✅' : '⏸️';
                    const cooldown = health.cooldown_remaining_minutes ? ` (${Math.round(health.cooldown_remaining_minutes)}min)` : '';
                    const usageCount = health.usage_count || 0;
                    return `${emoji} <strong>${p.toUpperCase()}</strong>${cooldown} [${usageCount}]`;
                }).join(' | ');
                
                console.log(`🤖 AI Providers: ${statusBadges.replace(/<[^>]*>/g, '')}`);
                console.log(`🔄 Round-robin index: ${providers.rotation_index || 0}`);
                console.log(`📊 Usage: ${JSON.stringify(providers.provider_usage || {})}`);
                
                if (statusBar) {
                    statusBar.innerHTML = `🔄 <strong>AI Rotation:</strong> ${statusBadges} | <span style="color: #888;">Luân phiên tự động</span>`;
                    statusBar.style.background = '#E8F5E9';
                    statusBar.style.color = '#1B5E20';
                }
            }
        }
    } catch (err) {
        console.error('Không thể kiểm tra runtime config:', err);
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
                const statusClass = schedule.status === 'completed' ? 'completed' : 'pending';
                const statusText = schedule.status === 'completed' ? 'Đã hoàn thành' : 'Chưa hoàn thành';
                
                scheduleDiv.innerHTML = `
                    <div class="schedule-item-info">
                        <div class="schedule-item-title">${escapeHtml(schedule.title)}</div>
                        <span class="schedule-item-status ${statusClass}">${statusText}</span>
                        <div class="schedule-item-time">${startTime}</div>
                        ${schedule.description ? `<div style="font-size: 13px; margin-top: 4px;">${escapeHtml(schedule.description)}</div>` : ''}
                    </div>
                    <div class="schedule-item-actions">
                        ${schedule.status === 'completed' ? 
                            `<button class="btn-check" onclick="markScheduleIncomplete(${schedule.id})">↩️ Chưa xong</button>` :
                            `<button class="btn-check" onclick="markScheduleComplete(${schedule.id})">✓ Hoàn thành</button>`
                        }
                        <button class="btn-edit" onclick="openEditSchedule(${schedule.id})">✏️ Sửa</button>
                        <button class="btn-delete" onclick="deleteSchedule(${schedule.id})">🗑️ Xóa</button>
                    </div>
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

async function markScheduleComplete(scheduleId) {
    if (!confirm('Đánh dấu lịch hẹn đã hoàn thành?')) return;
    
    try {
        const response = await apiFetch(`${API_BASE}/schedule/${scheduleId}/update-status`, {
            method: 'PATCH',
            headers: { 'Content-Type': 'application/json' },
            body: JSON.stringify({ status: 'completed' })
        });
        
        const data = await response.json();
        if (data.success) {
            showNotification('✓ Đã đánh dấu hoàn thành', 'success');
            loadSchedules();
        } else {
            showNotification('Lỗi: ' + (data.error || 'Không thể cập nhật'), 'error');
        }
    } catch (error) {
        showNotification('Lỗi: ' + error.message, 'error');
    }
}

async function markScheduleIncomplete(scheduleId) {
    if (!confirm('Đánh dấu lịch hẹn chưa hoàn thành?')) return;
    
    try {
        const response = await apiFetch(`${API_BASE}/schedule/${scheduleId}/update-status`, {
            method: 'PATCH',
            headers: { 'Content-Type': 'application/json' },
            body: JSON.stringify({ status: 'pending' })
        });
        
        const data = await response.json();
        if (data.success) {
            showNotification('↩️ Đã cập nhật trạng thái', 'success');
            loadSchedules();
        } else {
            showNotification('Lỗi: ' + (data.error || 'Không thể cập nhật'), 'error');
        }
    } catch (error) {
        showNotification('Lỗi: ' + error.message, 'error');
    }
}

async function openEditSchedule(scheduleId) {
    try {
        // Fetch schedule details
        const response = await apiFetch(`${API_BASE}/schedule/list`);  // Assuming we can get from list
        const data = await response.json();
        
        if (!data.success) throw new Error('Không thể lấy dữ liệu');
        
        const schedule = data.schedules.find(s => s.id === scheduleId);
        if (!schedule) throw new Error('Lịch hẹn không tìm thấy');
        
        // Populate form
        document.getElementById('editScheduleTitle').value = schedule.title;
        document.getElementById('editScheduleDesc').value = schedule.description || '';
        document.getElementById('editScheduleTime').value = schedule.start_time;
        document.getElementById('editScheduleAttendees').value = schedule.attendees || '';
        
        // Store ID for submit handler
        document.getElementById('editScheduleForm').dataset.scheduleId = scheduleId;
        
        // Show modal
        document.getElementById('editScheduleModal').style.display = 'block';
    } catch (error) {
        showNotification('Lỗi: ' + error.message, 'error');
    }
}

async function handleEditScheduleSubmit(e) {
    e.preventDefault();
    
    const scheduleId = document.getElementById('editScheduleForm').dataset.scheduleId;
    const title = document.getElementById('editScheduleTitle').value.trim();
    const description = document.getElementById('editScheduleDesc').value.trim();
    const start_time = document.getElementById('editScheduleTime').value;
    const attendees_str = document.getElementById('editScheduleAttendees').value.trim();
    const attendees = attendees_str ? attendees_str.split(',').map(e => e.trim()) : [];
    
    try {
        const response = await apiFetch(`${API_BASE}/schedule/${scheduleId}`, {
            method: 'PUT',
            headers: { 'Content-Type': 'application/json' },
            body: JSON.stringify({ title, description, start_time, attendees })
        });
        
        const data = await response.json();
        if (data.success) {
            showNotification('✓ Đã cập nhật lịch hẹn', 'success');
            document.getElementById('editScheduleModal').style.display = 'none';
            loadSchedules();
        } else {
            showNotification('Lỗi: ' + (data.error || 'Không thể cập nhật'), 'error');
        }
    } catch (error) {
        showNotification('Lỗi: ' + error.message, 'error');
    }
}

async function deleteSchedule(scheduleId) {
    if (!confirm('Bạn có chắc chắn muốn xóa lịch hẹn này?')) return;
    
    try {
        const response = await apiFetch(`${API_BASE}/schedule/${scheduleId}`, {
            method: 'DELETE',
            headers: { 'Content-Type': 'application/json' }
        });
        
        const data = await response.json();
        if (data.success) {
            showNotification('🗑️ Đã xóa lịch hẹn', 'success');
            loadSchedules();
        } else {
            showNotification('Lỗi: ' + (data.error || 'Không thể xóa'), 'error');
        }
    } catch (error) {
        showNotification('Lỗi: ' + error.message, 'error');
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

function renderMarkdown(text) {
    // Already escaped HTML
    let result = text;
    
    // Code blocks with triple backticks
    result = result.replace(/```(.*?)```/gs, (match, code) => {
        const language = code.split('\n')[0].trim();
        const content = code.substring(language.length).trim();
        return `<pre><code class="language-${language}">${escapeHtml(content)}</code></pre>`;
    });
    
    // Inline code with single backticks
    result = result.replace(/`([^`]+)`/g, '<code>$1</code>');
    
    // Bold **text**
    result = result.replace(/\*\*([^\*]+)\*\*/g, '<strong>$1</strong>');
    result = result.replace(/__([^_]+)__/g, '<strong>$1</strong>');
    
    // Italic *text* and _text_
    result = result.replace(/\*([^\*]+)\*/g, '<em>$1</em>');
    result = result.replace(/_([^_]+)_/g, '<em>$1</em>');
    
    // Links [text](url)
    result = result.replace(/\[([^\]]+)\]\(([^\)]+)\)/g, '<a href="$2" target="_blank">$1</a>');
    
    // Line breaks
    result = result.replace(/\n/g, '<br>');
    
    // Blockquotes > text
    result = result.replace(/^&gt; (.+)$/gm, '<blockquote>$1</blockquote>');
    
    // Lists
    result = result.replace(/^\- (.+)$/gm, '<li>$1</li>');
    result = result.replace(/(<li>.*<\/li>)/s, '<ul>$1</ul>');
    
    return result;
}
