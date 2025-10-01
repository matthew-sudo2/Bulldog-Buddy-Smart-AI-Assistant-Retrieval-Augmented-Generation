/**
 * Bulldog Buddy - Redesigned Chat Interface
 * Complete functionality matching Streamlit UI with modern design
 */

// ============================================================================
// GLOBAL STATE
// ============================================================================

const API_BASE = '/api/bridge';
let currentUser = null;
let currentSession = null;
let currentModel = 'gemma3:latest';
let currentMode = true; // true = university, false = general
let conversations = [];
let availableModels = []; // Store models for use in settings
let userSettings = {
    theme: 'university',
    personality: 'friendly',
    responseLength: 'balanced',
    showConfidence: true,
    showSources: true,
    showTimestamps: true
};

// ============================================================================
// INITIALIZATION
// ============================================================================

document.addEventListener('DOMContentLoaded', async function() {
    await init();
    setupEventListeners();
    setupAutoResize();
});

async function init() {
    try {
        // Get current user
        const response = await fetch('/api/user');
        if (response.ok) {
            currentUser = await response.json();
            console.log('User loaded:', currentUser);
        } else {
            console.error('Failed to load user');
            window.location.href = '/login';
            return;
        }

        // Load user settings
        await loadSettings();

        // Apply theme
        applyTheme(userSettings.theme);

        // Load conversations
        await loadConversations();

        // Create or load initial conversation
        if (conversations.length === 0) {
            await createNewConversation();
        } else {
            currentSession = conversations[0].session_uuid;
            await loadConversationMessages(currentSession);
        }

        // Show welcome message if no messages
        if (!document.querySelector('.message')) {
            showWelcomeMessage();
        }

        // Load available models
        await loadModels();

    } catch (error) {
        console.error('Initialization error:', error);
        showError('Failed to initialize application');
    }
}

function setupEventListeners() {
    // Message input
    const input = document.getElementById('messageInput');
    const sendBtn = document.getElementById('btnSend');
    
    input.addEventListener('input', function() {
        const charCount = this.value.length;
        document.getElementById('charCount').textContent = charCount;
        sendBtn.disabled = charCount === 0;
    });

    input.addEventListener('keydown', function(e) {
        if (e.key === 'Enter' && !e.shiftKey) {
            e.preventDefault();
            if (!sendBtn.disabled) {
                sendMessage();
            }
        }
    });

    sendBtn.addEventListener('click', sendMessage);

    // New chat buttons
    document.getElementById('navNewChat').addEventListener('click', createNewConversation);
    document.getElementById('btnNewChat').addEventListener('click', createNewConversation);

    // Settings
    document.getElementById('navSettings').addEventListener('click', openSettings);
    document.getElementById('btnCloseSettings').addEventListener('click', closeSettings);
    document.getElementById('btnSaveSettings').addEventListener('click', saveSettings);
    document.getElementById('btnResetSettings').addEventListener('click', resetSettings);

    // Mode toggle
    document.getElementById('modeToggle').addEventListener('click', toggleMode);

    // Model selector
    document.getElementById('modelSelect').addEventListener('change', function() {
        currentModel = this.value;
        selectModel(currentModel);
    });

    // Theme options
    document.querySelectorAll('.theme-option').forEach(btn => {
        btn.addEventListener('click', function() {
            const theme = this.dataset.theme;
            document.querySelectorAll('.theme-option').forEach(b => b.classList.remove('active'));
            this.classList.add('active');
            userSettings.theme = theme;
            applyTheme(theme);
        });
    });

    // Export/Import
    document.getElementById('btnExport').addEventListener('click', exportConversations);
    document.getElementById('btnImport').addEventListener('click', importConversations);

    // Sidebar toggle (mobile)
    document.getElementById('sidebarToggle').addEventListener('click', function() {
        document.querySelector('.sidebar').classList.toggle('active');
    });
}

function setupAutoResize() {
    const textarea = document.getElementById('messageInput');
    textarea.addEventListener('input', function() {
        // Reset height to auto to get the correct scrollHeight
        this.style.height = 'auto';
        // Set new height based on content, max 150px
        const newHeight = Math.min(this.scrollHeight, 150);
        this.style.height = newHeight + 'px';
    });
}

// ============================================================================
// USER & SETTINGS
// ============================================================================

async function loadSettings() {
    try {
        const response = await fetch(`${API_BASE}/settings/${currentUser.id}`);
        if (response.ok) {
            const data = await response.json();
            if (data.settings) {
                userSettings = { ...userSettings, ...data.settings };
            }
        }
    } catch (error) {
        console.error('Failed to load settings:', error);
    }
}

async function saveSettings() {
    try {
        // Gather settings from modal
        userSettings.personality = document.getElementById('personalitySelect').value;
        userSettings.responseLength = document.getElementById('responseLengthSelect').value;
        userSettings.showConfidence = document.getElementById('showConfidence').checked;
        userSettings.showSources = document.getElementById('showSources').checked;
        userSettings.showTimestamps = document.getElementById('showTimestamps').checked;

        const response = await fetch(`${API_BASE}/settings/${currentUser.id}`, {
            method: 'POST',
            headers: { 'Content-Type': 'application/json' },
            body: JSON.stringify({ settings: userSettings })
        });

        if (response.ok) {
            showNotification('Settings saved successfully!', 'success');
            closeSettings();
        } else {
            showNotification('Failed to save settings', 'error');
        }
    } catch (error) {
        console.error('Save settings error:', error);
        showNotification('Error saving settings', 'error');
    }
}

function resetSettings() {
    userSettings = {
        theme: 'university',
        personality: 'friendly',
        responseLength: 'balanced',
        showConfidence: true,
        showSources: true,
        showTimestamps: true
    };
    
    // Update modal
    document.getElementById('personalitySelect').value = 'friendly';
    document.getElementById('responseLengthSelect').value = 'balanced';
    document.getElementById('showConfidence').checked = true;
    document.getElementById('showSources').checked = true;
    document.getElementById('showTimestamps').checked = true;
    
    // Reset theme
    document.querySelectorAll('.theme-option').forEach(btn => {
        btn.classList.toggle('active', btn.dataset.theme === 'university');
    });
    
    applyTheme('university');
    showNotification('Settings reset to defaults', 'info');
}

function applyTheme(theme) {
    // Remove all theme classes
    document.body.className = '';
    // Apply new theme
    if (theme !== 'university') {
        document.body.classList.add(`theme-${theme}`);
    }
}

function openSettings() {
    // Populate current settings
    document.getElementById('personalitySelect').value = userSettings.personality;
    document.getElementById('responseLengthSelect').value = userSettings.responseLength;
    document.getElementById('showConfidence').checked = userSettings.showConfidence;
    document.getElementById('showSources').checked = userSettings.showSources;
    document.getElementById('showTimestamps').checked = userSettings.showTimestamps;
    
    // Set active theme
    document.querySelectorAll('.theme-option').forEach(btn => {
        btn.classList.toggle('active', btn.dataset.theme === userSettings.theme);
    });
    
    // Refresh models info
    populateModelsInfo();
    
    document.getElementById('settingsModal').classList.add('active');
}

function closeSettings() {
    document.getElementById('settingsModal').classList.remove('active');
}

// ============================================================================
// CONVERSATIONS
// ============================================================================

async function loadConversations() {
    try {
        const response = await fetch(`${API_BASE}/conversations/user/${currentUser.id}`);
        if (response.ok) {
            const data = await response.json();
            conversations = data.conversations || [];
            renderConversationsList();
        }
    } catch (error) {
        console.error('Failed to load conversations:', error);
    }
}

function renderConversationsList() {
    const chatList = document.getElementById('chatList');
    const chatCount = document.getElementById('chatCount');
    
    chatCount.textContent = conversations.length;
    
    if (conversations.length === 0) {
        chatList.innerHTML = '<p style="text-align: center; color: var(--text-muted); font-size: 13px; padding: 16px;">No conversations yet</p>';
        return;
    }

    chatList.innerHTML = conversations.slice(0, 10).map(conv => {
        const isActive = currentSession === conv.session_uuid;
        const title = conv.title || 'New Conversation';
        const preview = conv.preview || 'No messages yet';
        const time = formatTime(conv.updated_at);
        const msgCount = conv.message_count || 0;

        return `
            <button class="chat-item ${isActive ? 'active' : ''}" data-session="${conv.session_uuid}">
                <div class="chat-item-header">
                    <span class="chat-item-title">${escapeHtml(title)}</span>
                    <span class="chat-item-time">${time}</span>
                </div>
                <div class="chat-item-preview">${escapeHtml(preview)}</div>
                <div class="chat-item-meta">
                    <span class="chat-item-messages">${msgCount} msgs</span>
                </div>
            </button>
        `;
    }).join('');

    // Add click handlers
    chatList.querySelectorAll('.chat-item').forEach(item => {
        item.addEventListener('click', function() {
            const sessionId = this.dataset.session;
            loadConversation(sessionId);
        });
    });
}

async function createNewConversation() {
    try {
        const response = await fetch(`${API_BASE}/conversations`, {
            method: 'POST',
            headers: { 'Content-Type': 'application/json' },
            body: JSON.stringify({
                user_id: currentUser.id,
                title: 'New Conversation'
            })
        });

        if (response.ok) {
            const data = await response.json();
            currentSession = data.session_uuid;
            
            // Clear messages
            document.getElementById('messagesWrapper').innerHTML = '';
            
            // Show welcome message
            showWelcomeMessage();
            
            // Reload conversations list
            await loadConversations();
            
            showNotification('New conversation started', 'success');
        } else {
            showNotification('Failed to create conversation', 'error');
        }
    } catch (error) {
        console.error('Create conversation error:', error);
        showNotification('Error creating conversation', 'error');
    }
}

async function loadConversation(sessionId) {
    if (sessionId === currentSession) return;
    
    currentSession = sessionId;
    await loadConversationMessages(sessionId);
    renderConversationsList();
}

async function loadConversationMessages(sessionId) {
    try {
        const response = await fetch(`${API_BASE}/conversations/${sessionId}/messages`);
        if (response.ok) {
            const data = await response.json();
            const messages = data.messages || [];
            
            const wrapper = document.getElementById('messagesWrapper');
            wrapper.innerHTML = '';
            
            messages.forEach(msg => {
                addMessageToUI(
                    msg.message_type,
                    msg.content,
                    msg.created_at,
                    msg.confidence_score,
                    msg.sources_used
                );
            });
            
            scrollToBottom();
        }
    } catch (error) {
        console.error('Load messages error:', error);
    }
}

async function deleteConversation(sessionId) {
    if (!confirm('Are you sure you want to delete this conversation?')) return;
    
    try {
        const response = await fetch(`${API_BASE}/conversations/${sessionId}`, {
            method: 'DELETE',
            headers: { 'Content-Type': 'application/json' },
            body: JSON.stringify({ user_id: currentUser.id })
        });

        if (response.ok) {
            if (sessionId === currentSession) {
                await createNewConversation();
            }
            await loadConversations();
            showNotification('Conversation deleted', 'success');
        } else {
            showNotification('Failed to delete conversation', 'error');
        }
    } catch (error) {
        console.error('Delete conversation error:', error);
        showNotification('Error deleting conversation', 'error');
    }
}

// ============================================================================
// CHAT FUNCTIONALITY
// ============================================================================

function showWelcomeMessage() {
    const userName = currentUser.first_name || currentUser.username || 'there';
    const welcomeText = `Welcome, ${userName}! I'm Bulldog Buddy, your Smart AI Assistant. I'm here to help with university questions and general knowledge. How can I assist you today?`;
    
    addMessageToUI('assistant', welcomeText, new Date().toISOString(), 1.0, []);
}

async function sendMessage() {
    const input = document.getElementById('messageInput');
    const message = input.value.trim();
    
    if (!message) return;
    
    // Add user message to UI
    addMessageToUI('user', message, new Date().toISOString());
    
    // Clear input
    input.value = '';
    document.getElementById('charCount').textContent = '0';
    document.getElementById('btnSend').disabled = true;
    input.style.height = 'auto';
    
    // Show typing indicator
    showTypingIndicator();
    
    try {
        const requestBody = {
            user_id: currentUser.id,
            session_id: currentSession,
            message: message,
            model: currentModel,
            mode: currentMode ? "university" : "general"
        };
        
        console.log('📤 Sending chat request:', requestBody);
        
        const response = await fetch(`${API_BASE}/chat`, {
            method: 'POST',
            headers: { 'Content-Type': 'application/json' },
            body: JSON.stringify(requestBody)
        });

        removeTypingIndicator();

        if (response.ok) {
            const data = await response.json();
            console.log('📥 Chat response:', data);
            
            addMessageToUI(
                'assistant',
                data.response,
                new Date().toISOString(),
                data.confidence || 0,
                data.sources || []
            );
            
            // Update conversation list
            await loadConversations();
        } else {
            const errorText = await response.text();
            console.error('❌ Chat response error:', response.status, errorText);
            throw new Error(`Server responded with ${response.status}: ${errorText}`);
        }
    } catch (error) {
        console.error('Send message error:', error);
        removeTypingIndicator();
        addMessageToUI(
            'assistant',
            'Sorry, I encountered an error. Please try again.',
            new Date().toISOString(),
            0,
            []
        );
    }
    
    scrollToBottom();
}

function addMessageToUI(role, content, timestamp, confidence = 0, sources = []) {
    const wrapper = document.getElementById('messagesWrapper');
    const messageDiv = document.createElement('div');
    messageDiv.className = `message ${role}`;
    
    const isUser = role === 'user';
    const sender = isUser ? (currentUser.first_name || 'You') : 'Bulldog Buddy';
    const time = userSettings.showTimestamps ? formatTime(timestamp) : '';
    
    // Avatar HTML
    let avatarHTML = '';
    if (isUser) {
        avatarHTML = '<i class="fas fa-user"></i>';
    } else {
        avatarHTML = '<img src="/src/assets/images/bulldog-logo.png" alt="Bulldog Buddy">';
    }
    
    let confidenceBadge = '';
    if (userSettings.showConfidence && role === 'assistant' && confidence > 0) {
        confidenceBadge = `<span class="message-confidence">High (${Math.round(confidence * 100)}%)</span>`;
    }
    
    messageDiv.innerHTML = `
        <div class="message-avatar">${avatarHTML}</div>
        <div class="message-content">
            <div class="message-header">
                <span class="message-sender">${sender}</span>
                ${time ? `<span class="message-time">${time}</span>` : ''}
                ${confidenceBadge}
            </div>
            <div class="message-bubble">
                ${formatMessage(content)}
            </div>
        </div>
    `;
    
    wrapper.appendChild(messageDiv);
    scrollToBottom();
}

function showTypingIndicator() {
    const wrapper = document.getElementById('messagesWrapper');
    const indicator = document.createElement('div');
    indicator.className = 'message assistant';
    indicator.id = 'typingIndicator';
    indicator.innerHTML = `
        <div class="message-avatar">
            <img src="/src/assets/images/bulldog-logo.png" alt="Bulldog Buddy">
        </div>
        <div class="message-content">
            <div class="message-bubble">
                <div class="typing-indicator">
                    <div class="typing-dot"></div>
                    <div class="typing-dot"></div>
                    <div class="typing-dot"></div>
                </div>
            </div>
        </div>
    `;
    wrapper.appendChild(indicator);
    scrollToBottom();
}

function removeTypingIndicator() {
    const indicator = document.getElementById('typingIndicator');
    if (indicator) {
        indicator.remove();
    }
}

// ============================================================================
// MODE & MODEL SELECTION
// ============================================================================

async function toggleMode() {
    currentMode = !currentMode;
    
    const toggleBtn = document.getElementById('modeToggle');
    const indicator = document.getElementById('modeIndicator');
    
    if (currentMode) {
        toggleBtn.classList.remove('off');
        toggleBtn.querySelector('.toggle-state').textContent = 'ON';
        indicator.innerHTML = '<i class="fas fa-graduation-cap mode-icon"></i><span class="mode-text">University Mode: Using student handbook</span>';
    } else {
        toggleBtn.classList.add('off');
        toggleBtn.querySelector('.toggle-state').textContent = 'OFF';
        indicator.innerHTML = '<i class="fas fa-globe mode-icon"></i><span class="mode-text">General Mode: Using AI knowledge</span>';
    }
    
    try {
        await fetch(`${API_BASE}/rag/mode`, {
            method: 'POST',
            headers: { 'Content-Type': 'application/json' },
            body: JSON.stringify({
                user_id: currentUser.id,
                university_mode: currentMode
            })
        });
        
        showNotification(currentMode ? 'University mode enabled' : 'General mode enabled', 'info');
    } catch (error) {
        console.error('Toggle mode error:', error);
    }
}

async function loadModels() {
    try {
        const response = await fetch(`${API_BASE}/models`);
        if (response.ok) {
            const data = await response.json();
            availableModels = data.models || [];
            
            const select = document.getElementById('modelSelect');
            const modelLabel = document.querySelector('.model-label');
            
            // Build options with rich data
            select.innerHTML = availableModels.map(model => {
                const displayName = model.name || formatModelName(model.id);
                return `<option value="${model.id}" data-description="${model.description || ''}">${displayName}</option>`;
            }).join('');
            
            // Set current model
            select.value = currentModel;
            
            // Update label with current model
            const selectedModel = availableModels.find(m => m.id === currentModel);
            if (selectedModel) {
                modelLabel.innerHTML = `<i class="fas ${selectedModel.icon || 'fa-robot'}"></i> ${selectedModel.name}`;
            }
            
            // Populate models info in settings
            populateModelsInfo();
            
            console.log('✅ Models loaded:', availableModels);
        }
    } catch (error) {
        console.error('Load models error:', error);
    }
}

function populateModelsInfo() {
    const modelsInfo = document.getElementById('modelsInfo');
    
    if (availableModels.length === 0) {
        modelsInfo.innerHTML = '<p class="loading-text">No models available</p>';
        return;
    }
    
    modelsInfo.innerHTML = availableModels.map(model => {
        const isActive = model.id === currentModel;
        const icon = model.icon || 'fa-robot';
        
        return `
            <div class="model-card ${isActive ? 'active' : ''}" data-model="${model.id}">
                <div class="model-card-header">
                    <div class="model-card-title">
                        <div class="model-card-icon">
                            <i class="fas ${icon}"></i>
                        </div>
                        <span class="model-card-name">${model.name}</span>
                    </div>
                    ${isActive ? '<span class="model-card-badge">Active</span>' : ''}
                </div>
                <p class="model-card-description">${model.description}</p>
                <div class="model-card-meta">
                    <div class="model-card-meta-item">
                        <i class="fas fa-thermometer-half"></i>
                        <span>Temp: ${model.temperature || 0.3}</span>
                    </div>
                    <div class="model-card-meta-item">
                        <i class="fas fa-microchip"></i>
                        <span>${model.id.split(':')[0]}</span>
                    </div>
                </div>
            </div>
        `;
    }).join('');
    
    // Add click handlers to model cards
    modelsInfo.querySelectorAll('.model-card').forEach(card => {
        card.addEventListener('click', async function() {
            const modelId = this.dataset.model;
            if (modelId !== currentModel) {
                await selectModel(modelId);
                
                // Update active state
                modelsInfo.querySelectorAll('.model-card').forEach(c => {
                    c.classList.remove('active');
                    c.querySelector('.model-card-badge')?.remove();
                });
                
                this.classList.add('active');
                const badge = document.createElement('span');
                badge.className = 'model-card-badge';
                badge.textContent = 'Active';
                this.querySelector('.model-card-header').appendChild(badge);
            }
        });
    });
}

async function selectModel(model) {
    try {
        const response = await fetch(`${API_BASE}/models/select`, {
            method: 'POST',
            headers: { 'Content-Type': 'application/json' },
            body: JSON.stringify({
                user_id: currentUser.id,
                model_name: model
            })
        });

        if (response.ok) {
            currentModel = model;
            
            // Update dropdown and label
            const modelLabel = document.querySelector('.model-label');
            const select = document.getElementById('modelSelect');
            select.value = model;
            
            const selectedModel = availableModels.find(m => m.id === model);
            if (selectedModel) {
                modelLabel.innerHTML = `<i class="fas ${selectedModel.icon || 'fa-robot'}"></i> ${selectedModel.name}`;
            }
            
            showNotification(`Switched to ${selectedModel ? selectedModel.name : formatModelName(model)}`, 'success');
        } else {
            showNotification('Failed to switch model', 'error');
        }
    } catch (error) {
        console.error('Select model error:', error);
        showNotification('Error switching model', 'error');
    }
}

// ============================================================================
// EXPORT / IMPORT
// ============================================================================

async function exportConversations() {
    try {
        const data = {
            user: currentUser,
            conversations: conversations,
            settings: userSettings,
            exported_at: new Date().toISOString()
        };
        
        const blob = new Blob([JSON.stringify(data, null, 2)], { type: 'application/json' });
        const url = URL.createObjectURL(blob);
        const a = document.createElement('a');
        a.href = url;
        a.download = `bulldog-buddy-export-${Date.now()}.json`;
        a.click();
        URL.revokeObjectURL(url);
        
        showNotification('Conversations exported successfully', 'success');
    } catch (error) {
        console.error('Export error:', error);
        showNotification('Failed to export conversations', 'error');
    }
}

function importConversations() {
    const input = document.createElement('input');
    input.type = 'file';
    input.accept = 'application/json';
    
    input.onchange = async (e) => {
        try {
            const file = e.target.files[0];
            const text = await file.text();
            const data = JSON.parse(text);
            
            if (data.conversations && data.settings) {
                // This would need backend support to properly import
                showNotification('Import functionality coming soon', 'info');
            } else {
                showNotification('Invalid export file', 'error');
            }
        } catch (error) {
            console.error('Import error:', error);
            showNotification('Failed to import conversations', 'error');
        }
    };
    
    input.click();
}

// ============================================================================
// UTILITY FUNCTIONS
// ============================================================================

function formatMessage(content) {
    // Basic markdown-like formatting
    content = escapeHtml(content);
    
    // Bold
    content = content.replace(/\*\*(.*?)\*\*/g, '<strong>$1</strong>');
    
    // Links
    content = content.replace(/(https?:\/\/[^\s]+)/g, '<a href="$1" target="_blank">$1</a>');
    
    // Line breaks
    content = content.replace(/\n/g, '<br>');
    
    return content;
}

function formatTime(timestamp) {
    if (!timestamp) return '';
    
    const date = new Date(timestamp);
    const now = new Date();
    const diff = now - date;
    
    // Less than 1 minute
    if (diff < 60000) {
        return 'Just now';
    }
    
    // Less than 1 hour
    if (diff < 3600000) {
        const mins = Math.floor(diff / 60000);
        return `${mins}m ago`;
    }
    
    // Less than 24 hours
    if (diff < 86400000) {
        const hours = Math.floor(diff / 3600000);
        return `${hours}h ago`;
    }
    
    // Less than 7 days
    if (diff < 604800000) {
        const days = Math.floor(diff / 86400000);
        return `${days}d ago`;
    }
    
    // Format as date
    return date.toLocaleDateString();
}

function formatModelName(model) {
    // Convert "gemma3:latest" to "Matt 3" format
    return model
        .split(':')[0]
        .replace(/(\d+)/, ' $1')
        .split('-')
        .map(word => word.charAt(0).toUpperCase() + word.slice(1))
        .join(' ');
}

function escapeHtml(text) {
    const div = document.createElement('div');
    div.textContent = text;
    return div.innerHTML;
}

function scrollToBottom() {
    const container = document.getElementById('chatContainer');
    container.scrollTop = container.scrollHeight;
}

function showNotification(message, type = 'info') {
    // Simple notification system
    const notification = document.createElement('div');
    notification.style.cssText = `
        position: fixed;
        top: 20px;
        right: 20px;
        padding: 16px 24px;
        background: ${type === 'success' ? '#28A745' : type === 'error' ? '#DC3545' : '#17A2B8'};
        color: white;
        border-radius: 8px;
        box-shadow: 0 4px 12px rgba(0,0,0,0.15);
        z-index: 3000;
        animation: slideIn 0.3s ease;
    `;
    notification.textContent = message;
    
    document.body.appendChild(notification);
    
    setTimeout(() => {
        notification.style.animation = 'slideOut 0.3s ease';
        setTimeout(() => notification.remove(), 300);
    }, 3000);
}

function showError(message) {
    console.error(message);
    showNotification(message, 'error');
}

// Add CSS animations for notifications
const style = document.createElement('style');
style.textContent = `
    @keyframes slideIn {
        from {
            transform: translateX(400px);
            opacity: 0;
        }
        to {
            transform: translateX(0);
            opacity: 1;
        }
    }
    
    @keyframes slideOut {
        from {
            transform: translateX(0);
            opacity: 1;
        }
        to {
            transform: translateX(400px);
            opacity: 0;
        }
    }
`;
document.head.appendChild(style);
