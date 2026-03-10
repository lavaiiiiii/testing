// API Configuration
const API_BASE = '/api';

// DOM Elements - Cached for performance
const chatMessages = document.getElementById('chatMessages');
const userInput = document.getElementById('userInput');
const sendBtn = document.getElementById('sendBtn');
const navBtns = document.querySelectorAll('[data-page]');
const tabBtns = document.querySelectorAll('[data-tab]');
const emailDetailModal = document.getElementById('emailDetailModal');
const closeModal = document.querySelector('.close');
const clearBtn = document.getElementById('clearBtn');
const composeForm = document.getElementById('composeForm');
const scheduleForm = document.getElementById('scheduleForm');
const scheduleDetailModal = document.getElementById('scheduleDetailModal');
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
let currentEmailPage = 1;
let currentWeekOffset = 0;
let currentScheduleDetail = null;
let latestSchedules = [];

// Initialize
document.addEventListener('DOMContentLoaded', initApp);

async function initApp() {
    console.log('🚀 Initializing app...');
    setupEventListeners();
    await loadUserProfile();
    await loadChatHistory();
    checkOAuthCallback();
    await refreshAuthButtons();
    checkRuntimeConfig();
    
    // Auto-load emails if user is on emails page and authenticated
    if (currentPage === 'emails') {
        console.log('📧 Auto-loading emails on init...');
        setTimeout(() => loadEmails(), 500);
    }
    
    console.log('✅ App initialized');
}

async function apiFetch(url, options = {}) {
    return fetch(url, {
        credentials: 'include',
        ...options
    });
}

function checkOAuthCallback() {
    const urlParams = new URLSearchParams(window.location.search);
    if (urlParams.get('gmail_auth') === 'success') {
        console.log('✅ OAuth callback detected');
        
        const emailNavBtn = document.querySelector('[data-page="emails"]');
        if (emailNavBtn) {
            handlePageChange(emailNavBtn);
            showNotification('✅ Gmail đã kết nối thành công!', 'success');
            
            apiFetch(`${API_BASE}/user/gmail-connected`, {
                method: 'POST',
                headers: { 'Content-Type': 'application/json' }
            }).catch(err => console.error('Error marking Gmail connected:', err));
            
            setTimeout(() => {
                refreshAuthButtons();
                loadUserProfile();
                setTimeout(() => {
                    loadEmails().catch(err => {
                        console.error('First email load failed:', err);
                        setTimeout(() => loadEmails(), 1000);
                    });
                }, 300);
            }, 200);
        }
        window.history.replaceState({}, document.title, window.location.pathname);
    }
}

function showNotification(message, type = 'info') {
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
    
    setTimeout(() => {
        notification.style.animation = 'slideOut 0.3s ease-out';
        setTimeout(() => notification.remove(), 300);
    }, 3000);
}

function setupEventListeners() {
    console.log('📋 Setting up event listeners');
    
    // Navigation buttons
    navBtns.forEach(btn => {
        btn.addEventListener('click', () => {
            console.log(`📍 Nav click: ${btn.dataset.page}`);
            handlePageChange(btn);
        });
    });
    
    // Chat send
    if (sendBtn) {
        sendBtn.addEventListener('click', () => {
            console.log('📨 Send button clicked');
            sendMessage();
        });
    }
    
    // Enter to send
    if (userInput) {
        userInput.addEventListener('keypress', (e) => {
            if (e.key === 'Enter' && !e.shiftKey) {
                e.preventDefault();
                console.log('⌨️ Enter pressed');
                sendMessage();
            }
        });
    }
    
    // Tab buttons
    tabBtns.forEach(btn => {
        btn.addEventListener('click', () => {
            console.log(`📂 Tab click: ${btn.dataset.tab}`);
            handleTabChange(btn);
        });
    });
    
    // Modal close
    if (closeModal) {
        closeModal.addEventListener('click', closeModalWindow);
    }
    if (emailDetailModal) {
        emailDetailModal.addEventListener('click', (e) => {
            if (e.target === emailDetailModal) closeModalWindow();
        });
    }
    
    // Forms
    if (composeForm) composeForm.addEventListener('submit', handleComposeSubmit);
    if (scheduleForm) scheduleForm.addEventListener('submit', handleScheduleSubmit);
    
    const editForm = document.getElementById('editScheduleForm');
    if (editForm) editForm.addEventListener('submit', handleEditScheduleSubmit);
    
    const editModal = document.getElementById('editScheduleModal');
    if (editModal) {
        const closeBtn = editModal.querySelector('.close');
        if (closeBtn) closeBtn.addEventListener('click', () => editModal.style.display = 'none');
    }

    if (scheduleDetailModal) {
        const detailCloseBtn = scheduleDetailModal.querySelector('.close');
        if (detailCloseBtn) detailCloseBtn.addEventListener('click', closeScheduleDetailModal);
        scheduleDetailModal.addEventListener('click', (e) => {
            if (e.target === scheduleDetailModal) closeScheduleDetailModal();
        });
    }

    const scheduleDetailToggleBtn = document.getElementById('scheduleDetailToggleBtn');
    if (scheduleDetailToggleBtn) {
        scheduleDetailToggleBtn.addEventListener('click', async () => {
            if (!currentScheduleDetail) return;
            if (currentScheduleDetail.status === 'completed') {
                await markScheduleIncomplete(currentScheduleDetail.id);
                currentScheduleDetail.status = 'pending';
            } else {
                await markScheduleComplete(currentScheduleDetail.id);
                currentScheduleDetail.status = 'completed';
            }
            closeScheduleDetailModal();
        });
    }

    const scheduleDetailEditBtn = document.getElementById('scheduleDetailEditBtn');
    if (scheduleDetailEditBtn) {
        scheduleDetailEditBtn.addEventListener('click', async () => {
            if (!currentScheduleDetail) return;
            const scheduleToEdit = { ...currentScheduleDetail };
            if (!scheduleToEdit.id && scheduleDetailModal?.dataset?.scheduleId) {
                scheduleToEdit.id = Number(scheduleDetailModal.dataset.scheduleId);
            }
            closeScheduleDetailModal();
            await openEditSchedule(scheduleToEdit);
        });
    }

    const scheduleDetailDeleteBtn = document.getElementById('scheduleDetailDeleteBtn');
    if (scheduleDetailDeleteBtn) {
        scheduleDetailDeleteBtn.addEventListener('click', async () => {
            if (!currentScheduleDetail) return;
            await deleteSchedule(currentScheduleDetail.id);
            closeScheduleDetailModal();
        });
    }
    
    // Clear history
    if (clearBtn) {
        clearBtn.addEventListener('click', clearConversation);
    }
    
    // Gmail buttons
    const userAvatar = document.getElementById('userAvatar');
    if (userAvatar) userAvatar.addEventListener('click', gmailLogin);
    if (gmailLoginBtn) gmailLoginBtn.addEventListener('click', gmailLogin);
    if (gmailLogoutBtn) gmailLogoutBtn.addEventListener('click', gmailLogout);
    if (openGmailBtn) openGmailBtn.addEventListener('click', () => window.open('https://mail.google.com', '_blank'));
    
    // Email filter
    if (emailFilterSelect) {
        emailFilterSelect.addEventListener('change', () => {
            console.log(`🔍 Filter changed: ${emailFilterSelect.value}`);
            currentEmailPage = 1;
            loadEmails();
        });
    }
    
    // Include read checkbox
    const includeReadCheckbox = document.getElementById('includeReadCheckbox');
    if (includeReadCheckbox) {
        includeReadCheckbox.addEventListener('change', () => {
            console.log(`📬 Include read: ${includeReadCheckbox.checked}`);
            currentEmailPage = 1;
            loadEmails();
        });
    }
    
    // Refresh emails
    const refreshBtn = document.getElementById('refreshEmailsBtn');
    if (refreshBtn) {
        refreshBtn.addEventListener('click', () => {
            console.log('🔄 Refreshing emails');
            loadEmails();
        });
    }

    const prevWeekBtn = document.getElementById('prevWeekBtn');
    if (prevWeekBtn) {
        prevWeekBtn.addEventListener('click', () => {
            currentWeekOffset -= 1;
            loadSchedules();
        });
    }

    const nextWeekBtn = document.getElementById('nextWeekBtn');
    if (nextWeekBtn) {
        nextWeekBtn.addEventListener('click', () => {
            currentWeekOffset += 1;
            loadSchedules();
        });
    }

    const syncCalendarBtn = document.getElementById('syncCalendarBtn');
    if (syncCalendarBtn) {
        syncCalendarBtn.addEventListener('click', syncSchedulesToCalendar);
    }
    
    // Generate report
    const reportBtn = document.getElementById('generateReportBtn');
    if (reportBtn) {
        reportBtn.addEventListener('click', generateDailyReport);
    }
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

        const sidebarUserName = document.getElementById('userName');
        const sidebarGmailStatus = document.getElementById('gmailStatus');
        const sidebarAvatar = document.getElementById('userAvatar');

        if (gmailAccountBadge) {
            gmailAccountBadge.textContent = isAuth ? 'Đã kết nối Gmail' : 'Chưa đăng nhập Gmail';
            gmailAccountBadge.style.display = isAuth ? 'none' : 'inline-block';
        }

        if (gmailProfileCard) gmailProfileCard.style.display = isAuth ? 'inline-flex' : 'none';
        if (gmailName) gmailName.textContent = profileName;
        if (gmailEmail) gmailEmail.textContent = profileEmail;
        if (gmailAvatar) gmailAvatar.src = profilePicture || 'https://www.gravatar.com/avatar/?d=mp&s=64';

        if (sidebarUserName) {
            sidebarUserName.textContent = isAuth
                ? `${profileName}${profileEmail ? ` (${profileEmail})` : ''}`
                : 'Teacher';
        }

        if (sidebarGmailStatus) {
            sidebarGmailStatus.textContent = isAuth ? 'Đã kết nối Gmail' : 'Chưa kết nối Gmail';
        }

        if (sidebarAvatar) {
            if (isAuth && profilePicture) {
                sidebarAvatar.src = profilePicture;
                sidebarAvatar.textContent = '';
            } else {
                const fallbackSource = isAuth ? (profileName || profileEmail || 'U') : 'Teacher';
                const initials = fallbackSource.substring(0, 1).toUpperCase();
                sidebarAvatar.src = '';
                sidebarAvatar.style.backgroundColor = '#4F46E5';
                sidebarAvatar.style.display = 'flex';
                sidebarAvatar.style.alignItems = 'center';
                sidebarAvatar.style.justifyContent = 'center';
                sidebarAvatar.style.fontSize = '20px';
                sidebarAvatar.style.fontWeight = 'bold';
                sidebarAvatar.style.color = 'white';
                sidebarAvatar.textContent = initials;
            }
            sidebarAvatar.title = isAuth ? 'Tài khoản Gmail đã kết nối' : 'Click để đăng nhập Gmail';
        }
    } catch (err) {
        console.error('Auth status check failed:', err);
        if (gmailLoginBtn) gmailLoginBtn.style.display = 'inline-block';
        if (gmailLogoutBtn) gmailLogoutBtn.style.display = 'none';
        if (openGmailBtn) openGmailBtn.style.display = 'none';

        const sidebarGmailStatus = document.getElementById('gmailStatus');
        if (sidebarGmailStatus) {
            sidebarGmailStatus.textContent = 'Chưa kết nối Gmail';
        }
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
            apiFetch(`${API_BASE}/user/gmail-disconnected`, {
                method: 'POST',
                headers: { 'Content-Type': 'application/json' }
            }).catch(err => console.error('Error marking Gmail disconnected:', err));
            
            await refreshAuthButtons();
            await loadUserProfile();
            const emailsList = document.getElementById('emailsList');
            if (emailsList) emailsList.innerHTML = '<p>Đã đăng xuất Gmail. Vui lòng đăng nhập lại.</p>';
        }
    } catch (err) {
        alert('Lỗi: ' + err.message);
    }
}

// PAGE MANAGEMENT (CRITICAL FIX)
function handlePageChange(btn) {
    const page = btn.dataset.page;
    console.log(`🔄 Changing page to: ${page}`);
    
    // Update nav buttons
    navBtns.forEach(b => b.classList.remove('active'));
    btn.classList.add('active');
    
    // Hide all pages
    document.querySelectorAll('.page').forEach(p => {
        p.style.display = 'none';
        p.classList.remove('active');
    });
    
    // Show target page - Try both ID variants for robustness
    let targetPage = document.getElementById(`${page}-page`);
    if (!targetPage) targetPage = document.querySelector(`[data-page="${page}"]`);
    
    if (targetPage) {
        targetPage.style.display = 'block';
        targetPage.classList.add('active');
        console.log(`✅ Page ${page} displayed`);
    } else {
        console.error(`❌ Page element not found for: ${page}`);
        return;
    }
    
    currentPage = page;
    
    // Load page data
    if (page === 'emails') {
        loadEmails().catch(err => console.error('Email load error:', err));
    } else if (page === 'schedule') {
        loadSchedules().catch(err => console.error('Schedule load error:', err));
    } else if (page === 'history') {
        loadActivityHistory().catch(err => console.error('History load error:', err));
    }
}

// TAB MANAGEMENT
function handleTabChange(btn) {
    const tabName = btn.dataset.tab;
    console.log(`🔄 Changing tab to: ${tabName}`);
    
    const tabsContainer = btn.closest('.tabs');
    if (!tabsContainer) {
        console.error('❌ Tabs container not found');
        return;
    }
    
    // Update tab buttons
    tabsContainer.querySelectorAll('[data-tab]').forEach(b => b.classList.remove('active'));
    btn.classList.add('active');
    
    // Hide all tabs in this container
    const pageContainer = tabsContainer.closest('.page');
    if (pageContainer) {
        pageContainer.querySelectorAll('.tab-content').forEach(content => {
            content.style.display = 'none';
        });
    }
    
    // Show target tab
    const tabContent = document.getElementById(`${tabName}-tab`);
    if (tabContent) {
        tabContent.style.display = 'block';
        console.log(`✅ Tab ${tabName} displayed`);
    } else {
        console.error(`❌ Tab content not found for: ${tabName}`);
    }
}

// CHAT FUNCTIONS (CRITICAL FIX)
async function sendMessage() {
    const message = userInput.value.trim();
    if (!message) {
        console.warn('⚠️ Empty message');
        return;
    }
    
    console.log(`📨 Sending message: ${message.substring(0, 50)}...`);
    
    addMessage(message, 'user');
    userInput.value = '';
    
    // Show loading
    const loadingDiv = document.createElement('div');
    loadingDiv.className = 'message assistant';
    loadingDiv.innerHTML = '<div class="message-content"><div class="loading"></div></div>';
    chatMessages.appendChild(loadingDiv);
    chatMessages.scrollTop = chatMessages.scrollHeight;
    
    try {
        console.log(`🔗 POST ${API_BASE}/chat/message`);
        const response = await apiFetch(`${API_BASE}/chat/message`, {
            method: 'POST',
            headers: { 'Content-Type': 'application/json' },
            body: JSON.stringify({ message })
        });
        
        console.log(`⚙️ Response status: ${response.status}`);
        
        if (!response.ok) {
            throw new Error(`HTTP ${response.status}: ${response.statusText}`);
        }
        
        const data = await response.json();
        console.log('✅ Response received:', data);
        
        loadingDiv.remove();
        
        if (data.success) {
            const providerBadge = data.provider ? 
                `<span class="provider-badge" style="font-size: 11px; padding: 2px 8px; background: ${data.demo_mode ? '#FF9800' : '#4CAF50'}; color: white; border-radius: 10px; margin-left: 8px;">
                    ${data.demo_mode ? '🎭 Demo' : '🤖 ' + data.provider.toUpperCase()}
                </span>` : '';
            
            addMessage(data.response, 'assistant', providerBadge);

            if (data.command_effect) {
                await applyCommandEffect(data.command_effect);
            }
            
            if (data.demo_mode) {
                showNotification('⚠️ Demo Mode - Tất cả AI providers đang cooldown', 'info');
            }
            
            if (data.schedule_created) {
                showNotification(
                    `✅ Lịch hẹn "${data.schedule_created.title}" đã được tạo`,
                    'success'
                );
                try {
                    await loadSchedules();
                } catch (e) {
                    console.log('Schedule refresh noted');
                }
            }
        } else {
            addMessage('❌ Lỗi: ' + (data.error || 'Unknown error'), 'assistant');
            console.error('AI error:', data.error);
        }
    } catch (error) {
        loadingDiv.remove();
        console.error('❌ Message send error:', error);
        addMessage('❌ Lỗi kết nối: ' + error.message, 'assistant');
        
        // Detailed error message
        const errorMsg = `
Lỗi: ${error.message}
Endpoint: ${API_BASE}/chat/message
Status: Not reached
        `.trim();
        console.error(errorMsg);
    }
}

async function applyCommandEffect(effect) {
    if (!effect) return;

    const targetPage = effect.target_page;
    if (targetPage) {
        const navBtn = document.querySelector(`[data-page="${targetPage}"]`);
        if (navBtn) handlePageChange(navBtn);
    }

    const refreshList = Array.isArray(effect.refresh) ? effect.refresh : [];
    if (refreshList.includes('email')) {
        await loadEmails(currentEmailPage || 1);
    }
    if (refreshList.includes('schedule')) {
        await loadSchedules();
    }
    if (refreshList.includes('history')) {
        await loadActivityHistory();
    }
    if (refreshList.includes('chat')) {
        await loadChatHistory();
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
            const userName = document.getElementById('userName');
            const userAvatar = document.getElementById('userAvatar');
            
            if (userName) userName.textContent = user.name || 'Teacher';
            
            if (userAvatar) {
                if (user.avatar_url) {
                    userAvatar.src = user.avatar_url;
                } else {
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
            showNotification('✅ Lịch sử đã bị xóa', 'success');
        }
    } catch (error) {
        showNotification('❌ Lỗi: ' + error.message, 'error');
    }
}

// EMAIL FUNCTIONS
async function gmailLogin() {
    try {
        const response = await apiFetch(`${API_BASE}/email/auth_url`, { cache: 'no-store' });
        const data = await response.json();

        if (!response.ok || !data.auth_url) {
            alert('Lỗi: ' + (data.error || 'OAuth chưa được cấu hình'));
            return;
        }

        window.location.href = data.auth_url;
    } catch (err) {
        alert('Lỗi: ' + err.message);
    }
}

async function toggleEmailReadStatus(emailId, isUnread) {
    try {
        const endpoint = isUnread ? 'mark-as-read' : 'mark-as-unread';
        const response = await apiFetch(`${API_BASE}/email/${endpoint}/${emailId}`, {
            method: 'POST'
        });
        
        const data = await response.json();
        
        if (data.success) {
            const action = isUnread ? 'đã đọc' : 'chưa đọc';
            showNotification(`✅ Đã đánh dấu email ${action}`, 'success');
            // Reload emails to reflect the change
            await loadEmails(currentEmailPage);
        } else {
            showNotification(`❌ Lỗi: ${data.error || 'Không thể đánh dấu email'}`, 'error');
        }
    } catch (error) {
        console.error('Error toggling email read status:', error);
        showNotification(`❌ Lỗi: ${error.message}`, 'error');
    }
}

async function checkRuntimeConfig() {
    try {
        const response = await apiFetch(`${API_BASE}/chat/providers`);
        const data = await response.json();
        
        if (data.success && data.providers) {
            const providers = data.providers;
            if (providers.demo_mode) {
                console.warn('⚠️ Demo Mode - Tất cả AI providers đang cooldown hoặc chưa cấu hình');
            } else {
                console.log('✅ AI providers configured and active');
            }
        }
    } catch (err) {
        console.error('Config check failed:', err);
    }
}

async function loadEmails(page = 1) {
    const emailsList = document.getElementById('emailsList');
    if (!emailsList) {
        console.error('❌ emailsList element not found');
        return;
    }
    
    emailsList.innerHTML = '<p style="padding: 20px; text-align: center; color: #666;">⏳ Đang tải email...</p>';
    const selectedFilter = emailFilterSelect ? emailFilterSelect.value : 'all';
    const includeReadCheckbox = document.getElementById('includeReadCheckbox');
    const includeRead = includeReadCheckbox ? includeReadCheckbox.checked : false;
    currentEmailPage = page;

    await refreshAuthButtons();
    
    try {
        const url = `${API_BASE}/email/get-unread?max_results=20&page=${page}&filter=${encodeURIComponent(selectedFilter)}&include_read=${includeRead}`;
        console.log(`📧 Loading emails: ${url}`);
        console.log(`🔍 Filter: ${selectedFilter}, Page: ${page}, Include read: ${includeRead}`);
        
        const response = await apiFetch(url);
        console.log(`📡 Response status: ${response.status}`);
        
        if (!response.ok) {
            throw new Error(`HTTP ${response.status}: ${response.statusText}`);
        }
        
        const data = await response.json();
        console.log('📦 Email data received:', data);
        
        if (data && data.error === 'not_authenticated') {
            emailsList.innerHTML = `
                <div style="padding: 30px; text-align: center; background: #FFF3E0; border-radius: 8px; margin: 20px;">
                    <p style="font-size: 16px; color: #E65100; margin-bottom: 15px;">⚠️ Chưa đăng nhập Gmail</p>
                    <button id="loginPromptBtn" class="btn-primary">Đăng nhập Gmail</button>
                </div>
            `;
            document.getElementById('loginPromptBtn').addEventListener('click', gmailLogin);
            return;
        }

        if (!data.success) {
            console.error('❌ API returned error:', data.error);
            emailsList.innerHTML = `
                <div style="padding: 20px; background: #FFEBEE; border-radius: 8px; margin: 20px;">
                    <p style="color: #C62828; font-weight: bold;">❌ Lỗi: ${escapeHtml(data.error || 'Unknown error')}</p>
                    <button onclick="loadEmails(1)" class="btn-primary" style="margin-top: 10px;">🔄 Thử lại</button>
                </div>
            `;
            return;
        }
        
        if (!data.emails || data.emails.length === 0) {
            console.warn('⚠️ No emails found');
            emailsList.innerHTML = `
                <div style="padding: 30px; text-align: center; background: #E8F5E9; border-radius: 8px; margin: 20px;">
                    <p style="font-size: 16px; color: #2E7D32; margin-bottom: 10px;">📭 Không tìm thấy email</p>
                    <p style="color: #666; font-size: 14px; margin-bottom: 15px;">
                        Filter hiện tại: <strong>${selectedFilter}</strong><br>
                        ${data.debug ? `Tổng email quét: ${data.debug.raw_email_count || 0}` : ''}
                    </p>
                    <div style="display: flex; gap: 10px; justify-content: center;">
                        <button onclick="emailFilterSelect.value='all'; loadEmails(1);" class="btn-primary">🔍 Xem tất cả</button>
                        <button onclick="loadEmails(1)" class="btn-secondary">🔄 Làm mới</button>
                    </div>
                </div>
            `;
            return;
        }
        
        console.log(`✅ Loaded ${data.emails.length} emails`);
        
        emailsList.innerHTML = '';
        data.emails.forEach(email => {
            const emailDiv = document.createElement('div');
            emailDiv.className = 'email-item';
            
            // Add visual indicator for unread emails
            const readStatus = email.is_unread ? 
                '<span style="display: inline-block; width: 8px; height: 8px; background: #4CAF50; border-radius: 50%; margin-right: 6px;" title="Chưa đọc"></span>' : 
                '<span style="display: inline-block; width: 8px; height: 8px; background: #ccc; border-radius: 50%; margin-right: 6px;" title="Đã đọc"></span>';
            
            const markButtonText = email.is_unread ? '✅ Đánh dấu đã đọc' : '📧 Đánh dấu chưa đọc';
            const markButtonClass = email.is_unread ? 'mark-read-btn' : 'mark-unread-btn';
            
            emailDiv.innerHTML = `
                <div class="email-item-header">
                    <span class="email-item-subject">${readStatus}${escapeHtml(email.subject)}</span>
                </div>
                <div class="email-item-sender">Từ: ${escapeHtml(email.sender)}</div>
                <div class="email-item-snippet">${escapeHtml(email.snippet)}</div>
                <div class="email-item-actions" style="margin-top: 8px; display: flex; gap: 6px;">
                    <button class="email-view-detail-btn" style="padding: 4px 12px; font-size: 12px; background: #666; color: white; border: none; border-radius: 4px; cursor: pointer;">👁️ Xem</button>
                    <button class="${markButtonClass}" data-email-id="${email.id}" data-is-unread="${email.is_unread}" style="padding: 4px 12px; font-size: 12px; background: ${email.is_unread ? '#4CAF50' : '#FF9800'}; color: white; border: none; border-radius: 4px; cursor: pointer;">${markButtonText}</button>
                </div>
            `;
            
            emailDiv.querySelector('.email-view-detail-btn').addEventListener('click', (e) => {
                e.stopPropagation();
                showEmailDetail(email);
            });
            
            // Add mark as read/unread handler
            const markButton = emailDiv.querySelector(`.${markButtonClass}`);
            markButton.addEventListener('click', async (e) => {
                e.stopPropagation();
                await toggleEmailReadStatus(email.id, email.is_unread);
            });
            
            emailsList.appendChild(emailDiv);
        });
        
        // Pagination
        if (data.pagination && data.pagination.total_pages > 1) {
            const { current_page, total_pages } = data.pagination;
            const paginationDiv = document.createElement('div');
            paginationDiv.style.cssText = 'padding: 16px; display: flex; justify-content: center; gap: 8px; margin-top: 16px;';
            
            const prevBtn = document.createElement('button');
            prevBtn.textContent = '◀ Trang trước';
            prevBtn.disabled = current_page === 1;
            prevBtn.addEventListener('click', () => loadEmails(current_page - 1));
            paginationDiv.appendChild(prevBtn);
            
            const pageInfo = document.createElement('span');
            pageInfo.textContent = `Trang ${current_page} / ${total_pages}`;
            pageInfo.style.cssText = 'font-weight: bold; padding: 0 16px;';
            paginationDiv.appendChild(pageInfo);
            
            const nextBtn = document.createElement('button');
            nextBtn.textContent = 'Trang sau ▶';
            nextBtn.disabled = current_page === total_pages;
            nextBtn.addEventListener('click', () => loadEmails(current_page + 1));
            paginationDiv.appendChild(nextBtn);
            
            emailsList.appendChild(paginationDiv);
        }
    } catch (error) {
        console.error('Email load error:', error);
        emailsList.innerHTML = `<p>❌ Lỗi: ${error.message}</p>`;
    }
}

async function showEmailDetail(email) {
    const emailDetail = document.getElementById('emailDetail');
    if (!emailDetail) return;
    
    emailDetail.innerHTML = `
        <div class="email-detail-subject">${escapeHtml(email.subject)}</div>
        <div class="email-detail-meta">
            <strong>Từ:</strong> ${escapeHtml(email.sender)}<br>
            <strong>Ngày:</strong> ${escapeHtml(email.date)}
        </div>
        <div class="email-detail-body" style="color: #666; font-style: italic;">Đang tải nội dung...</div>
    `;
    
    if (emailDetailModal) emailDetailModal.classList.add('show');
    
    // Lazy load body
    if (!email.body) {
        try {
            const response = await apiFetch(`${API_BASE}/email/get-email-body/${email.id}`);
            const data = await response.json();
            email.body = data.success ? data.body : 'Không thể tải nội dung';
        } catch (error) {
            email.body = 'Lỗi: ' + error.message;
        }
    }
    
    emailDetail.innerHTML = `
        <div class="email-detail-subject">${escapeHtml(email.subject)}</div>
        <div class="email-detail-meta">
            <strong>Từ:</strong> ${escapeHtml(email.sender)}<br>
            <strong>Ngày:</strong> ${escapeHtml(email.date)}
        </div>
        <div class="email-detail-body">${escapeHtml(email.body)}</div>
    `;
}

// SCHEDULE FUNCTIONS
async function loadSchedules() {
    const weekGrid = document.getElementById('scheduleWeekGrid');
    const weekMeta = document.getElementById('scheduleWeekMeta');
    if (!weekGrid || !weekMeta) return;
    
    try {
        const response = await apiFetch(`${API_BASE}/schedule/list`);
        const data = await response.json();

        const schedules = data.success && Array.isArray(data.schedules) ? data.schedules : [];
        latestSchedules = schedules;
        const now = new Date();
        const baseDate = new Date(now);
        baseDate.setDate(now.getDate() + (currentWeekOffset * 7));
        const currentDay = now.getDay();
        const baseDay = baseDate.getDay();
        const mondayOffset = baseDay === 0 ? -6 : 1 - baseDay;
        const weekStart = new Date(baseDate);
        weekStart.setHours(0, 0, 0, 0);
        weekStart.setDate(baseDate.getDate() + mondayOffset);

        const weekDates = [];
        for (let i = 0; i < 7; i++) {
            const date = new Date(weekStart);
            date.setDate(weekStart.getDate() + i);
            weekDates.push(date);
        }

        const weekEnd = new Date(weekDates[6]);
        const weekEndLimit = new Date(weekEnd);
        weekEndLimit.setHours(23, 59, 59, 999);
        weekMeta.textContent = `Tuần: ${weekStart.toLocaleDateString('vi-VN')} - ${weekEnd.toLocaleDateString('vi-VN')}`;
        weekGrid.innerHTML = '';

        const dayNames = ['Thứ 2', 'Thứ 3', 'Thứ 4', 'Thứ 5', 'Thứ 6', 'Thứ 7', 'Chủ nhật'];

        const weekSchedules = schedules
            .filter((item) => {
                const itemDate = new Date(item.start_time);
                return itemDate >= weekStart && itemDate <= weekEndLimit;
            })
            .sort((a, b) => new Date(a.start_time) - new Date(b.start_time));

        const outOfRangeHours = new Set();
        weekSchedules.forEach((item) => {
            const itemDate = new Date(item.start_time);
            const hour = itemDate.getHours();
            if (hour < 7 || hour > 20) {
                outOfRangeHours.add(hour);
            }
        });

        const defaultHours = Array.from({ length: 14 }, (_, idx) => idx + 7); // 07:00 -> 20:00
        const extraHours = Array.from(outOfRangeHours)
            .filter((hour) => !defaultHours.includes(hour))
            .sort((a, b) => a - b);
        const displayHours = [...defaultHours, ...extraHours].sort((a, b) => a - b);

        const scheduleMap = new Map();
        weekSchedules.forEach((item) => {
            const itemDate = new Date(item.start_time);
            const jsDay = itemDate.getDay();
            const dayIndex = jsDay === 0 ? 6 : jsDay - 1;
            const hour = itemDate.getHours();
            const key = `${dayIndex}-${hour}`;
            if (!scheduleMap.has(key)) {
                scheduleMap.set(key, []);
            }
            scheduleMap.get(key).push(item);
        });

        weekGrid.innerHTML = '';

        const corner = document.createElement('div');
        corner.className = 'time-grid-corner';
        weekGrid.appendChild(corner);

        dayNames.forEach((dayName) => {
            const header = document.createElement('div');
            header.className = 'time-grid-day-header';
            header.textContent = dayName;
            weekGrid.appendChild(header);
        });

        displayHours.forEach((hour) => {
            const hourLabel = document.createElement('div');
            hourLabel.className = 'time-grid-time-label';
            hourLabel.textContent = `${String(hour).padStart(2, '0')}:00`;
            weekGrid.appendChild(hourLabel);

            for (let dayIndex = 0; dayIndex < 7; dayIndex += 1) {
                const cell = document.createElement('div');
                cell.className = 'time-grid-cell';

                const cellSchedules = scheduleMap.get(`${dayIndex}-${hour}`) || [];
                cellSchedules.forEach((schedule) => {
                    const note = document.createElement('div');
                    const statusClass = schedule.status === 'completed' ? 'completed' : 'pending';
                    const timeLabel = new Date(schedule.start_time).toLocaleTimeString('vi-VN', {
                        hour: '2-digit',
                        minute: '2-digit'
                    });

                    note.className = `schedule-note ${statusClass}`;
                    note.innerHTML = `
                        <div class="schedule-note-title">${escapeHtml(schedule.title || 'Lịch hẹn')}</div>
                        <div class="schedule-note-time">${timeLabel}</div>
                    `;
                    note.addEventListener('click', () => openScheduleDetail(schedule));
                    cell.appendChild(note);
                });

                weekGrid.appendChild(cell);
            }
        });
    } catch (error) {
        weekGrid.innerHTML = `<p>❌ Lỗi: ${error.message}</p>`;
        weekMeta.textContent = '';
    }
}

function openScheduleDetail(schedule) {
    const content = document.getElementById('scheduleDetailContent');
    if (!content || !scheduleDetailModal) return;
    currentScheduleDetail = { ...schedule };
    scheduleDetailModal.dataset.scheduleId = String(schedule.id || '');

    const startLabel = formatScheduleDateTime(schedule.start_time);
    const durationMinutes = computeDurationMinutes(schedule);
    const statusLabel = schedule.status === 'completed' ? 'Đã hoàn thành' : 'Chưa hoàn thành';
    const attendees = schedule.attendees || 'Không có';
    const shortDescription = simplifyReminderDescription(schedule.description, schedule.title);
    const toggleBtn = document.getElementById('scheduleDetailToggleBtn');
    if (toggleBtn) {
        toggleBtn.textContent = schedule.status === 'completed' ? '↩️ Đánh dấu chưa hoàn thành' : '✓ Đánh dấu hoàn thành';
    }

    content.innerHTML = `
        <div><strong>Tiêu đề:</strong> ${escapeHtml(schedule.title || '')}</div>
        <div><strong>Thời gian:</strong> ${escapeHtml(startLabel)}</div>
        <div><strong>Thời lượng:</strong> ${escapeHtml(String(durationMinutes))} phút</div>
        <div><strong>Trạng thái:</strong> ${escapeHtml(statusLabel)}</div>
        <div><strong>Người tham dự:</strong> ${escapeHtml(attendees)}</div>
        <div><strong>Mô tả:</strong><br>${escapeHtml(shortDescription)}</div>
    `;

    scheduleDetailModal.classList.add('show');
}

function closeScheduleDetailModal() {
    if (!scheduleDetailModal) return;
    scheduleDetailModal.classList.remove('show');
    currentScheduleDetail = null;
}

function formatScheduleDateTime(value) {
    if (!value) return 'N/A';
    const dateObj = new Date(value);
    if (Number.isNaN(dateObj.getTime())) return 'N/A';

    const time = dateObj.toLocaleTimeString('vi-VN', {
        hour: '2-digit',
        minute: '2-digit'
    });
    const date = dateObj.toLocaleDateString('vi-VN');
    return `${time}, ${date}`;
}

function computeDurationMinutes(schedule) {
    const start = new Date(schedule.start_time);
    const end = new Date(schedule.end_time);
    if (!Number.isNaN(start.getTime()) && !Number.isNaN(end.getTime()) && end > start) {
        return Math.round((end - start) / 60000);
    }
    return 30;
}

function toDateTimeLocalValue(value) {
    if (!value) return '';
    const dateObj = new Date(value);
    if (Number.isNaN(dateObj.getTime())) {
        return String(value).slice(0, 16);
    }

    const pad = (num) => String(num).padStart(2, '0');
    const year = dateObj.getFullYear();
    const month = pad(dateObj.getMonth() + 1);
    const day = pad(dateObj.getDate());
    const hour = pad(dateObj.getHours());
    const minute = pad(dateObj.getMinutes());
    return `${year}-${month}-${day}T${hour}:${minute}`;
}

function simplifyReminderDescription(description, title) {
    const raw = (description || '').toString().replace(/\s+/g, ' ').trim();
    if (!raw) {
        return `Nhắc bản thân: ${title || 'Lịch hẹn'}`;
    }

    const cleaned = raw
        .replace(/Dưới đây là nội dung email để tạo lịch hẹn\.?/gi, '')
        .replace(/Thân gửi.*$/gi, '')
        .replace(/Trân trọng.*$/gi, '')
        .replace(/\[.*?\]/g, '')
        .replace(/\s+/g, ' ')
        .trim();

    const shortText = cleaned || raw;
    if (shortText.length <= 160) return shortText;
    return `${shortText.slice(0, 157).trim()}...`;
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
            await loadSchedules();
        }
    } catch (error) {
        showNotification('❌ Lỗi: ' + error.message, 'error');
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
            await loadSchedules();
        }
    } catch (error) {
        showNotification('❌ Lỗi: ' + error.message, 'error');
    }
}

async function openEditSchedule(scheduleId) {
    try {
        let schedule = null;
        let normalizedId = null;
        if (typeof scheduleId === 'object' && scheduleId !== null) {
            normalizedId = Number(scheduleId.id || 0);
            if (scheduleId.start_time || scheduleId.title || scheduleId.description) {
                schedule = scheduleId;
            }
        } else {
            normalizedId = Number(scheduleId || 0);
        }

        if (!normalizedId && scheduleDetailModal?.dataset?.scheduleId) {
            normalizedId = Number(scheduleDetailModal.dataset.scheduleId || 0);
        }

        if (!schedule && normalizedId) {
            schedule = latestSchedules.find(s => Number(s.id) === normalizedId);
            if (!schedule && currentScheduleDetail && Number(currentScheduleDetail.id) === normalizedId) {
                schedule = currentScheduleDetail;
            }
            if (!schedule) {
                const response = await apiFetch(`${API_BASE}/schedule/list`);
                const data = await response.json();
                if (!data.success) throw new Error('Lỗi lấy dữ liệu');
                latestSchedules = Array.isArray(data.schedules) ? data.schedules : [];
                schedule = latestSchedules.find(s => Number(s.id) === normalizedId);
            }
        }

        if (!schedule) throw new Error('Lịch hẹn không tìm thấy');
        
        const editForm = document.getElementById('editScheduleForm');
        document.getElementById('editScheduleTitle').value = schedule.title;
        document.getElementById('editScheduleDesc').value = schedule.description || '';
        document.getElementById('editScheduleTime').value = toDateTimeLocalValue(schedule.start_time);
        const editDurationSelect = document.getElementById('editScheduleDuration');
        if (editDurationSelect) {
            const durationValue = String(computeDurationMinutes(schedule));
            const hasOption = Array.from(editDurationSelect.options).some(opt => opt.value === durationValue);
            editDurationSelect.value = hasOption ? durationValue : '30';
        }
        document.getElementById('editScheduleAttendees').value = schedule.attendees || '';
        editForm.dataset.scheduleId = String(schedule.id);
        
        document.getElementById('editScheduleModal').style.display = 'block';
    } catch (error) {
        showNotification('❌ Lỗi: ' + error.message, 'error');
    }
}

async function handleEditScheduleSubmit(e) {
    e.preventDefault();
    
    const scheduleId = Number(document.getElementById('editScheduleForm').dataset.scheduleId);
    if (!scheduleId) {
        showNotification('❌ Không xác định được lịch hẹn để sửa', 'error');
        return;
    }
    const title = document.getElementById('editScheduleTitle').value.trim();
    const description = document.getElementById('editScheduleDesc').value.trim();
    const start_time = document.getElementById('editScheduleTime').value;
    const editDurationSelect = document.getElementById('editScheduleDuration');
    const duration_minutes = parseInt((editDurationSelect && editDurationSelect.value) || '30', 10);
    const attendees_str = document.getElementById('editScheduleAttendees').value.trim();
    const attendees = attendees_str ? attendees_str.split(',').map(e => e.trim()) : [];
    let timeoutId = null;
    
    try {
        const controller = new AbortController();
        timeoutId = setTimeout(() => controller.abort(), 15000);
        const response = await apiFetch(`${API_BASE}/schedule/${scheduleId}`, {
            method: 'PUT',
            headers: { 'Content-Type': 'application/json' },
            signal: controller.signal,
            body: JSON.stringify({ title, description, start_time, duration_minutes, attendees })
        });
        
        const data = await response.json();
        if (data.success) {
            showNotification('✓ Đã cập nhật lịch hẹn', 'success');
            document.getElementById('editScheduleModal').style.display = 'none';
            await loadSchedules();
        } else {
            showNotification('❌ ' + (data.error || 'Không thể cập nhật lịch hẹn'), 'error');
        }
    } catch (error) {
        if (error.name === 'AbortError') {
            showNotification('❌ Lưu lịch bị quá thời gian chờ. Vui lòng thử lại.', 'error');
            return;
        }
        showNotification('❌ Lỗi: ' + error.message, 'error');
    } finally {
        if (timeoutId) clearTimeout(timeoutId);
    }
}

async function deleteSchedule(scheduleId) {
    if (!confirm('Xóa lịch hẹn này?')) return;
    
    try {
        const response = await apiFetch(`${API_BASE}/schedule/${scheduleId}`, {
            method: 'DELETE',
            headers: { 'Content-Type': 'application/json' }
        });
        
        const data = await response.json();
        if (data.success) {
            showNotification('🗑️ Đã xóa', 'success');
            await loadSchedules();
        }
    } catch (error) {
        showNotification('❌ Lỗi: ' + error.message, 'error');
    }
}

async function handleScheduleSubmit(e) {
    e.preventDefault();
    
    const title = document.getElementById('scheduleTitle').value.trim();
    const description = document.getElementById('scheduleDesc').value.trim();
    const start_time = document.getElementById('scheduleTime').value;
    const duration_minutes = parseInt(document.getElementById('scheduleDuration').value || '30', 10);
    const attendees_str = document.getElementById('scheduleAttendees').value.trim();
    const attendees = attendees_str ? attendees_str.split(',').map(e => e.trim()) : [];
    
    try {
        const response = await apiFetch(`${API_BASE}/schedule/create`, {
            method: 'POST',
            headers: { 'Content-Type': 'application/json' },
            body: JSON.stringify({ title, description, start_time, duration_minutes, attendees })
        });
        
        const data = await response.json();
        if (data.success) {
            showNotification('✅ Lịch hẹn đã được tạo', 'success');
            scheduleForm.reset();
            await loadSchedules();
        } else {
            showNotification('❌ ' + (data.error || 'Không thể tạo lịch hẹn'), 'error');
        }
    } catch (error) {
        showNotification('❌ Lỗi: ' + error.message, 'error');
    }
}

async function syncSchedulesToCalendar() {
    const syncBtn = document.getElementById('syncCalendarBtn');
    const originalText = syncBtn ? syncBtn.textContent : '';

    try {
        if (syncBtn) {
            syncBtn.disabled = true;
            syncBtn.textContent = 'Đang đồng bộ...';
        }

        const response = await apiFetch(`${API_BASE}/schedule/sync-calendar`, {
            method: 'POST',
            headers: { 'Content-Type': 'application/json' }
        });

        const data = await response.json();
        if (data.success) {
            showNotification(`✅ Đồng bộ thành công: ${data.synced}/${data.total} lịch hẹn`, 'success');
            await loadSchedules();
            return;
        }

        showNotification('❌ ' + (data.error || 'Không thể đồng bộ Google Calendar'), 'error');
    } catch (error) {
        showNotification('❌ Lỗi đồng bộ: ' + error.message, 'error');
    } finally {
        if (syncBtn) {
            syncBtn.disabled = false;
            syncBtn.textContent = originalText || '🔔 Đồng bộ Google Calendar';
        }
    }
}

// HISTORY FUNCTIONS
async function loadActivityHistory() {
    const historyList = document.getElementById('historyList');
    if (!historyList) return;
    
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
                    <div style="font-weight: 600;">${getActionLabel(record.action_type)}</div>
                    <div style="font-size: 12px; color: var(--text-secondary); margin-top: 4px;">${date}</div>
                    <div style="font-size: 13px; margin-top: 8px; color: var(--text-secondary);">${escapeHtml(record.user_message.substring(0, 100))}...</div>
                `;
                historyList.appendChild(historyDiv);
            });
        } else {
            historyList.innerHTML = '<p>Không có lịch sử</p>';
        }
    } catch (error) {
        historyList.innerHTML = `<p>❌ Lỗi: ${error.message}</p>`;
    }
}

function getActionLabel(actionType) {
    const labels = {
        'chat': '💬 Chat',
        'email_summary': '📧 Tóm tắt',
        'schedule_created': '📅 Tạo lịch'
    };
    return labels[actionType] || actionType;
}

// MODAL
function closeModalWindow() {
    if (emailDetailModal) emailDetailModal.classList.remove('show');
}

// UTILITIES
function escapeHtml(text) {
    const div = document.createElement('div');
    div.textContent = text;
    return div.innerHTML;
}

function renderMarkdown(text) {
    let result = text;
    result = result.replace(/\*\*([^\*]+)\*\*/g, '<strong>$1</strong>');
    result = result.replace(/\*([^\*]+)\*/g, '<em>$1</em>');
    result = result.replace(/\[([^\]]+)\]\(([^\)]+)\)/g, '<a href="$2" target="_blank">$1</a>');
    result = result.replace(/\n/g, '<br>');
    return result;
}

// COMPOSE
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
            showNotification('✅ Email đã gửi', 'success');
            composeForm.reset();
        }
    } catch (error) {
        showNotification('❌ Lỗi: ' + error.message, 'error');
    }
}

// DAILY REPORT
async function generateDailyReport() {
    const dateInput = document.getElementById('reportDate');
    const container = document.getElementById('dailyReportContainer');
    const btn = document.getElementById('generateReportBtn');
    
    if (!dateInput || !container) return;

    if (!dateInput.value) {
        alert('Vui lòng chọn ngày');
        return;
    }

    const [yyyy, mm, dd] = dateInput.value.split('-');
    const dateForApi = `${dd}/${mm}/${yyyy}`;

    container.innerHTML = '<p style="padding: 20px; text-align: center; color: #666;">⏳ Đang tải email và tạo báo cáo...</p>';
    if (btn) btn.disabled = true;

    try {
        console.log(`📊 Generating report for: ${dateForApi}`);
        const response = await apiFetch(`${API_BASE}/email/summarize-by-date`, {
            method: 'POST',
            headers: { 'Content-Type': 'application/json' },
            body: JSON.stringify({ date: dateForApi, max_results: 50 })
        });

        if (!response.ok) {
            throw new Error(`HTTP ${response.status}: ${response.statusText}`);
        }

        const data = await response.json();
        console.log('Report data:', data);

        if (data && data.error === 'not_authenticated') {
            container.innerHTML = `
                <div style="padding: 20px; text-align: center; background: #FFF3E0; border-radius: 8px; margin: 20px;">
                    <p style="font-size: 16px; color: #E65100; margin-bottom: 10px;">⚠️ Chưa đăng nhập Gmail</p>
                    <button onclick="gmailLogin()" class="btn-primary">Đăng nhập Gmail</button>
                </div>
            `;
            return;
        }

        if (!data.success) {
            container.innerHTML = `
                <div style="padding: 20px; background: #FFEBEE; border-radius: 8px; margin: 20px;">
                    <p style="color: #C62828; font-weight: bold;">❌ Lỗi: ${escapeHtml(data.error || 'Không thể tạo báo cáo')}</p>
                    <p style="color: #666; font-size: 14px; margin-top: 10px;">Hãy thử: Kiểm tra kết nối Gmail, chọn ngày khác, hoặc xem F12 console</p>
                </div>
            `;
            return;
        }

        if (!data.rows || data.rows.length === 0) {
            container.innerHTML = `
                <div style="padding: 20px; text-align: center; background: #E8F5E9; border-radius: 8px; margin: 20px;">
                    <p style="font-size: 16px; color: #2E7D32; margin-bottom: 10px;">📭 Không có email trong ngày ${escapeHtml(data.date)}</p>
                    <p style="color: #666; font-size: 14px;">Hãy thử chọn ngày khác có nhiều email hơn</p>
                </div>
            `;
            return;
        }

        const rowsHtml = data.rows.map((row, i) => `
            <tr>
                <td style="padding: 12px 8px; border-bottom: 1px solid #e0e0e0; text-align: center;">${i + 1}</td>
                <td style="padding: 12px; border-bottom: 1px solid #e0e0e0;">${escapeHtml(row.sender || 'N/A')}</td>
                <td style="padding: 12px; border-bottom: 1px solid #e0e0e0;">${escapeHtml(row.summary || 'Không có tóm tắt')}</td>
            </tr>
        `).join('');

        container.innerHTML = `
            <div style="padding: 20px;">
                <div style="margin-bottom: 16px; padding: 12px; background: #E8F5E9; border-radius: 8px;">
                    <strong style="color: #2E7D32;">📧 Báo cáo email ngày ${escapeHtml(data.date)}</strong><br>
                    <span style="color: #666; font-size: 14px;">Tổng: ${data.total_emails} email</span>
                </div>
                <table style="width: 100%; border-collapse: collapse; background: white; border-radius: 8px; overflow: hidden; box-shadow: 0 2px 4px rgba(0,0,0,0.1);">
                    <thead>
                        <tr style="background: #4F46E5; color: white;">
                            <th style="padding: 12px 8px; text-align: center; width: 60px;">STT</th>
                            <th style="padding: 12px; text-align: left; width: 30%;">Người gửi</th>
                            <th style="padding: 12px; text-align: left;">Nội dung tóm tắt</th>
                        </tr>
                    </thead>
                    <tbody>
                        ${rowsHtml}
                    </tbody>
                </table>
            </div>
        `;
        showNotification(`✅ Đã tạo báo cáo ${data.total_emails} email`, 'success');
    } catch (error) {
        console.error('❌ Report generation error:', error);
        container.innerHTML = `
            <div style="padding: 20px; background: #FFEBEE; border-radius: 8px; margin: 20px;">
                <p style="color: #C62828; font-weight: bold;">❌ Lỗi kết nối: ${escapeHtml(error.message)}</p>
                <p style="color: #666; font-size: 14px; margin-top: 10px;">Kiểm tra:</p>
                <ul style="color: #666; font-size: 14px; margin-left: 20px;">
                    <li>Server đang chạy (http://localhost:5000)</li>
                    <li>Đã đăng nhập Gmail</li>
                    <li>Console (F12) để xem chi tiết</li>
                </ul>
            </div>
        `;
    } finally {
        if (btn) btn.disabled = false;
    }
}
