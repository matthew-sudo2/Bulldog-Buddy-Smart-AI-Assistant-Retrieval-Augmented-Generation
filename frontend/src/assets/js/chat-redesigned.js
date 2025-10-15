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
        // Get current user - MUST be authenticated to proceed
        const response = await fetch('/api/user');
        if (response.ok) {
            currentUser = await response.json();
            console.log('✅ User loaded:', currentUser);
            
            if (!currentUser || !currentUser.id) {
                console.error('❌ Invalid user data received');
                window.location.href = '/login';
                return;
            }
        } else {
            console.error('❌ User authentication failed:', response.status);
            // Redirect to login if not authenticated
            window.location.href = '/login';
            return;
        }

        // Load user settings
        await loadSettings();

        // Apply theme
        applyTheme(userSettings.theme);

        // Load conversations
        await loadConversations();

        console.log('🔍 After loading conversations:', conversations.length, 'conversations found');

        // Create or load initial conversation
        if (conversations.length === 0) {
            console.log('📝 No conversations found, creating first conversation...');
            await createNewConversation();
        } else {
            console.log('📂 Loading most recent conversation:', conversations[0].session_uuid);
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

    // Logout
    document.getElementById('btnLogout').addEventListener('click', handleLogout);

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
        // Ensure user is authenticated
        if (!currentUser || !currentUser.id) {
            console.error('❌ No authenticated user found');
            window.location.href = '/login';
            return;
        }
        
        // Gather settings from modal
        userSettings.personality = document.getElementById('personalitySelect').value;
        userSettings.responseLength = document.getElementById('responseLengthSelect').value;
        userSettings.showConfidence = document.getElementById('showConfidence').checked;
        userSettings.showSources = document.getElementById('showSources').checked;
        userSettings.showTimestamps = document.getElementById('showTimestamps').checked;

        console.log('💾 Saving settings:', userSettings);

        const response = await fetch(`${API_BASE}/settings/${currentUser.id}`, {
            method: 'PUT',
            headers: { 'Content-Type': 'application/json' },
            body: JSON.stringify(userSettings)
        });

        if (response.ok) {
            showNotification('Settings saved successfully!', 'success');
            applyTheme(userSettings.theme);
            closeSettings();
        } else {
            const errorText = await response.text();
            console.error('Failed to save settings:', errorText);
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
        console.log('📋 Loading conversations...');
        
        // Ensure user is authenticated
        if (!currentUser || !currentUser.id) {
            console.error('❌ No authenticated user found');
            window.location.href = '/login';
            return;
        }
        
        const userId = currentUser.id;
        console.log('👤 Using user ID:', userId);
        
        const apiUrl = `${API_BASE}/conversations/user/${userId}`;
        console.log('🌐 Conversations API URL:', apiUrl);
        
        const response = await fetch(apiUrl);
        console.log('📡 Conversations response status:', response.status);
        
        if (response.ok) {
            const data = await response.json();
            console.log('📦 Conversations data:', data);
            conversations = data.conversations || [];
            console.log('💼 Conversations count:', conversations.length);
            renderConversationsList();
        } else {
            const errorText = await response.text();
            console.error('❌ Failed to load conversations:', response.status, response.statusText, errorText);
        }
    } catch (error) {
        console.error('💥 Failed to load conversations:', error);
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
            <div class="chat-item ${isActive ? 'active' : ''}" data-session="${conv.session_uuid}">
                <div class="chat-item-header">
                    <span class="chat-item-title">${escapeHtml(title)}</span>
                    <span class="chat-item-time">${time}</span>
                    <button class="delete-chat-btn" title="Delete Conversation" data-delete-session="${conv.session_uuid}">
                        <i class="fas fa-trash"></i>
                    </button>
                </div>
                <div class="chat-item-preview">${escapeHtml(preview)}</div>
                <div class="chat-item-meta">
                    <span class="chat-item-messages">${msgCount} msgs</span>
                </div>
            </div>
        `;
    }).join('');

    // Add click handlers for chat selection
    chatList.querySelectorAll('.chat-item').forEach(item => {
        item.addEventListener('click', function(e) {
            // Prevent click if delete button was pressed
            if (e.target.closest('.delete-chat-btn')) return;
            const sessionId = this.dataset.session;
            loadConversation(sessionId);
        });
    });
    // Add click handlers for delete buttons
    chatList.querySelectorAll('.delete-chat-btn').forEach(btn => {
        btn.addEventListener('click', function(e) {
            e.stopPropagation();
            const sessionId = this.dataset.deleteSession;
            deleteConversation(sessionId);
        });
    });
}

async function createNewConversation() {
    try {
        console.log('➕ Creating new conversation for user:', currentUser);
        
        // Ensure user is authenticated
        if (!currentUser || !currentUser.id) {
            console.error('❌ No authenticated user found');
            window.location.href = '/login';
            return;
        }
        
        // Check if there's already an empty "New Conversation" at the top
        if (conversations.length > 0 && 
            conversations[0].title === 'New Conversation' && 
            conversations[0].message_count === 0) {
            console.log('⚠️  Already have an empty "New Conversation", switching to it instead');
            currentSession = conversations[0].session_uuid;
            document.getElementById('messagesWrapper').innerHTML = '';
            showWelcomeMessage();
            renderConversationsList();
            return;
        }
        
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
            console.log('✅ New conversation created:', currentSession);
            
            // Add the new conversation to the local array at the beginning
            const newConversation = {
                session_uuid: data.session_uuid,
                title: data.title || 'New Conversation',
                preview: 'No messages yet',
                message_count: 0,
                created_at: new Date().toISOString(),
                updated_at: new Date().toISOString()
            };
            conversations.unshift(newConversation);
            console.log('📊 Conversations count:', conversations.length);
            
            // Clear messages and show welcome
            document.getElementById('messagesWrapper').innerHTML = '';
            showWelcomeMessage();
            
            // Re-render the conversations list with the new conversation
            renderConversationsList();
            
            showNotification('New conversation started', 'success');
        } else {
            const errorText = await response.text();
            console.error('❌ Failed to create conversation:', response.status, errorText);
            showNotification(`Failed to create conversation: ${response.status}`, 'error');
        }
    } catch (error) {
        console.error('💥 Create conversation error:', error);
        showNotification(`Error creating conversation: ${error.message}`, 'error');
    }
}

async function loadConversation(sessionId) {
    if (sessionId === currentSession) return;
    
    currentSession = sessionId;
    await loadConversationMessages(sessionId);
    renderConversationsList();
}

function updateCurrentConversationMetadata(userMessage, assistantResponse) {
    if (!currentSession) return;
    
    // Find the current conversation in the array
    const conversationIndex = conversations.findIndex(conv => conv.session_uuid === currentSession);
    
    if (conversationIndex !== -1) {
        // Update the conversation metadata
        conversations[conversationIndex].message_count = (conversations[conversationIndex].message_count || 0) + 2; // user + assistant
        conversations[conversationIndex].preview = userMessage.substring(0, 50); // First 50 chars of user message
        conversations[conversationIndex].updated_at = new Date().toISOString();
        
        // If title is still "New Conversation", update it with first message
        if (conversations[conversationIndex].title === 'New Conversation') {
            conversations[conversationIndex].title = userMessage.substring(0, 30) + (userMessage.length > 30 ? '...' : '');
        }
        
        console.log('✏️ Updated conversation metadata:', conversations[conversationIndex]);
        
        // Re-render the conversation list to show updated info
        renderConversationsList();
    }
}

async function loadConversationMessages(sessionId) {
    try {
        console.log('🔍 Loading messages for session:', sessionId);
        
        // Ensure user is authenticated
        if (!currentUser || !currentUser.id) {
            console.error('❌ No authenticated user found');
            window.location.href = '/login';
            return;
        }
        
        const userId = currentUser.id;
        console.log('👤 Using user ID:', userId);
        
        const apiUrl = `${API_BASE}/conversations/${sessionId}/messages?user_id=${userId}`;
        console.log('🌐 API URL:', apiUrl);
        
        const response = await fetch(apiUrl);
        console.log('📡 Response status:', response.status);
        
        if (response.ok) {
            const data = await response.json();
            console.log('📦 Response data:', data);
            const messages = data.messages || [];
            console.log('💬 Messages count:', messages.length);
            
            const wrapper = document.getElementById('messagesWrapper');
            if (!wrapper) {
                console.error('❌ messagesWrapper element not found!');
                return;
            }
            
            wrapper.innerHTML = '';
            console.log('🧹 Cleared messages wrapper');
            
            if (messages.length === 0) {
                console.log('📭 No messages to display');
                wrapper.innerHTML = '<div class="no-messages stylish-no-messages"><i class="fas fa-comments"></i> No messages in this conversation yet.</div>';
                return;
            }
            // Always clear and show all messages
            messages.forEach((msg, index) => {
                console.log(`📝 Adding message ${index + 1}:`, msg);
                addMessageToUI(
                    msg.message_type || msg.role || 'assistant',
                    msg.content,
                    msg.created_at,
                    msg.confidence_score || 1.0,
                    msg.sources_used || []
                );
            });
            scrollToBottom();
            console.log('✅ Messages loaded successfully');
        } else {
            const errorText = await response.text();
            console.error('❌ Failed to load messages:', response.status, response.statusText, errorText);
            
            // Show error in UI
            const wrapper = document.getElementById('messagesWrapper');
            if (wrapper) {
                wrapper.innerHTML = `<div class="error-message">Failed to load messages: ${response.status} ${response.statusText}</div>`;
            }
        }
    } catch (error) {
        console.error('💥 Load messages error:', error);
        
        // Show error in UI
        const wrapper = document.getElementById('messagesWrapper');
        if (wrapper) {
            wrapper.innerHTML = `<div class="error-message">Error loading messages: ${error.message}</div>`;
        }
    }
}

async function deleteConversation(sessionId) {
    if (!confirm('Are you sure you want to delete this conversation?')) return;
    
    try {
        console.log('🗑️ Deleting conversation:', sessionId);
        
        // Ensure user is authenticated
        if (!currentUser || !currentUser.id) {
            console.error('❌ No authenticated user found');
            window.location.href = '/login';
            return;
        }
        
        const userId = currentUser.id;
        console.log('👤 Current user:', currentUser);
        console.log('🔑 Using user_id:', userId);
        
        // Show loading indicator on the chat item
        const chatItem = document.querySelector(`.chat-item[data-session="${sessionId}"]`);
        if (chatItem) {
            chatItem.style.opacity = '0.5';
            chatItem.style.pointerEvents = 'none';
        }
        
        const deleteUrl = `${API_BASE}/conversations/${sessionId}?user_id=${userId}`;
        console.log('📡 DELETE URL:', deleteUrl);
        
        const response = await fetch(deleteUrl, {
            method: 'DELETE',
            headers: { 
                'Content-Type': 'application/json',
                'Cache-Control': 'no-cache'
            }
        });

        console.log('📊 Response status:', response.status);
        
        if (response.ok) {
            console.log('✅ Conversation deleted from database');
            
            // Remove from local conversations array immediately
            const oldLength = conversations.length;
            conversations = conversations.filter(conv => conv.session_uuid !== sessionId);
            console.log(`📊 Conversations: ${oldLength} → ${conversations.length}`);
            
            // Immediately remove the DOM element
            if (chatItem) {
                chatItem.remove();
            }
            
            // Update the count immediately
            const chatCount = document.getElementById('chatCount');
            if (chatCount) {
                chatCount.textContent = conversations.length;
            }
            
            // Handle if we deleted the current conversation
            if (sessionId === currentSession) {
                console.log('🔄 Deleted the active conversation');
                // Clear current session first
                currentSession = null;
                
                // Clear the messages display
                const messagesWrapper = document.getElementById('messagesWrapper');
                if (messagesWrapper) {
                    messagesWrapper.innerHTML = '';
                }
                
                // If there are other conversations, load the first one
                if (conversations.length > 0) {
                    // Get the first conversation that still exists
                    const nextConversation = conversations[0];
                    console.log('📍 Switching to conversation:', nextConversation.session_uuid);
                    currentSession = nextConversation.session_uuid;
                    
                    // Load messages for the new current conversation
                    await loadConversationMessages(currentSession);
                    
                    // Re-render list to update active state
                    renderConversationsList();
                } else {
                    // No conversations left, show welcome message
                    console.log('📭 No conversations remaining');
                    showWelcomeMessage();
                    
                    // Show empty state in sidebar
                    const chatList = document.getElementById('chatList');
                    if (chatList) {
                        chatList.innerHTML = '<p style="text-align: center; color: var(--text-muted); font-size: 13px; padding: 16px;">No conversations yet</p>';
                    }
                }
            }
            
            showNotification('Conversation deleted successfully', 'success');
        } else {
            const errorData = await response.json().catch(() => ({ detail: 'Unknown error' }));
            console.error('❌ Failed to delete conversation:', errorData);
            
            // Restore UI if deletion failed
            if (chatItem) {
                chatItem.style.opacity = '1';
                chatItem.style.pointerEvents = 'auto';
            }
            
            showNotification(`Failed to delete conversation: ${errorData.detail || response.statusText}`, 'error');
        }
    } catch (error) {
        console.error('💥 Delete conversation error:', error);
        showNotification('Error deleting conversation', 'error');
    }
}

// ============================================================================
// CHAT FUNCTIONALITY
// ============================================================================

function showWelcomeMessage() {
    const userName = currentUser.first_name || currentUser.username || 'there';
    const welcomeText = `Welcome, ${userName}! I'm Bulldog Buddy, your Smart AI Assistant. I'm here to help with university questions and general knowledge. How can I assist you today?`;
    
    addMessageToUI('assistant', welcomeText, new Date().toISOString(), 1.0, [], true);
}

async function sendMessage() {
    const input = document.getElementById('messageInput');
    const message = input.value.trim();
    
    if (!message) return;
    
    // Ensure user is authenticated
    if (!currentUser || !currentUser.id) {
        console.error('❌ No authenticated user found');
        window.location.href = '/login';
        return;
    }
    
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
            
            // CRITICAL: Update currentSession if backend created/changed it
            if (data.session_id && data.session_id !== currentSession) {
                console.log(`🔄 Session updated: ${currentSession} → ${data.session_id}`);
                currentSession = data.session_id;
                
                // Check if this session exists in our conversations list
                const existsInList = conversations.some(c => c.session_uuid === currentSession);
                if (!existsInList) {
                    console.log('➕ Adding new session to conversations list');
                    // Add to conversations list
                    conversations.unshift({
                        session_uuid: currentSession,
                        title: 'New Conversation',
                        preview: message.substring(0, 100),
                        message_count: 1,
                        created_at: new Date().toISOString(),
                        updated_at: new Date().toISOString()
                    });
                    renderConversationsList();
                }
            }
            
            addMessageToUI(
                'assistant',
                data.response,
                new Date().toISOString(),
                data.confidence || 0,
                data.sources || [],
                true // Enable typing effect for new messages
            );
            
            // Update the current conversation in the local array
            updateCurrentConversationMetadata(message, data.response);
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

function addMessageToUI(role, content, timestamp, confidence = 0, sources = [], useTypingEffect = false) {
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
    
    // Apply typing effect ONLY for NEW assistant messages (not on reload)
    if (!isUser && useTypingEffect) {
        const bubble = messageDiv.querySelector('.message-bubble');
        typeMessage(bubble, content);
    } else {
        scrollToBottom();
    }
}

function typeMessage(element, content) {
    // Format the content first (convert to HTML with formatting)
    const formattedHTML = formatMessage(content);
    
    // Set up the element with full HTML but hidden
    element.innerHTML = formattedHTML;
    
    // Get all text nodes
    const textNodes = getTextNodes(element);
    
    // Store original text content for each node
    const originalTexts = textNodes.map(node => node.textContent);
    
    // Clear all text nodes
    textNodes.forEach(node => node.textContent = '');
    
    let nodeIndex = 0;
    let charIndex = 0;
    const speed = 5; // milliseconds per character (faster: was 15ms, now 5ms)
    
    function typeNextChar() {
        if (nodeIndex >= textNodes.length) {
            // Typing complete
            scrollToBottom();
            return;
        }
        
        const currentNode = textNodes[nodeIndex];
        const fullText = originalTexts[nodeIndex];
        
        if (charIndex < fullText.length) {
            // Add next character
            currentNode.textContent = fullText.substring(0, charIndex + 1);
            charIndex++;
            scrollToBottom();
            setTimeout(typeNextChar, speed);
        } else {
            // Move to next text node
            nodeIndex++;
            charIndex = 0;
            typeNextChar(); // Continue immediately to next node
        }
    }
    
    // Start typing
    typeNextChar();
}

function getTextNodes(element) {
    // Get all text nodes from an element recursively
    const textNodes = [];
    const walker = document.createTreeWalker(
        element,
        NodeFilter.SHOW_TEXT,
        null,
        false
    );
    
    let node;
    while (node = walker.nextNode()) {
        // Include all text nodes (even whitespace ones for formatting)
        textNodes.push(node);
    }
    
    return textNodes;
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

async function handleLogout() {
    try {
        // Show confirmation dialog
        const confirmed = confirm('Are you sure you want to logout?');
        if (!confirmed) return;

        // Call logout endpoint
        const response = await fetch('/logout', {
            method: 'POST',
            headers: {
                'Content-Type': 'application/json'
            }
        });

        if (response.ok) {
            // Clear any local storage
            localStorage.clear();
            sessionStorage.clear();
            
            // Redirect to landing page with logout success parameter
            window.location.href = '/?logout=success';
        } else {
            showNotification('Logout failed. Please try again.', 'error');
        }
    } catch (error) {
        console.error('Logout error:', error);
        showNotification('Logout failed. Please try again.', 'error');
    }
}

// ============================================================================
// UTILITY FUNCTIONS
// ============================================================================

function formatMessage(content) {
    // Enhanced markdown formatting with code block support
    content = escapeHtml(content);
    
    // Handle code blocks first (triple backticks with optional language)
    content = content.replace(/```(\w+)?\n?([\s\S]*?)```/g, function(match, language, code) {
        const lang = language || 'text';
        const codeId = 'code-' + Math.random().toString(36).substr(2, 9);
        const highlightedCode = highlightSyntax(code.trim(), lang);
        return `
            <div class="code-block-container">
                <div class="code-block-header">
                    <span class="code-language">${lang}</span>
                    <button class="copy-code-btn" onclick="copyCode('${codeId}')" title="Copy code">
                        <i class="fas fa-copy"></i>
                    </button>
                </div>
                <pre class="code-block"><code id="${codeId}" class="language-${lang}">${highlightedCode}</code></pre>
            </div>
        `;
    });
    
    // Handle inline code (single backticks)
    content = content.replace(/`([^`]+)`/g, '<code class="inline-code">$1</code>');
    
    // Bold
    content = content.replace(/\*\*(.*?)\*\*/g, '<strong>$1</strong>');
    
    // Italic
    content = content.replace(/\*(.*?)\*/g, '<em>$1</em>');
    
    // Links
    content = content.replace(/(https?:\/\/[^\s]+)/g, '<a href="$1" target="_blank" rel="noopener noreferrer">$1</a>');
    
    // Line breaks (preserve paragraph structure)
    content = content.replace(/\n\n/g, '</p><p>');
    content = content.replace(/\n/g, '<br>');
    content = '<p>' + content + '</p>';
    
    // Clean up empty paragraphs
    content = content.replace(/<p><\/p>/g, '');
    content = content.replace(/<p><br><\/p>/g, '');
    
    return content;
}

function highlightSyntax(code, language) {
    // Simple syntax highlighting for Python and common languages
    if (language === 'python' || language === 'py') {
        return highlightPython(code);
    } else if (language === 'javascript' || language === 'js') {
        return highlightJavaScript(code);
    } else if (language === 'html') {
        return highlightHTML(code);
    } else if (language === 'css') {
        return highlightCSS(code);
    }
    return code; // Return as-is for unsupported languages
}

function highlightPython(code) {
    // Python keywords
    const keywords = ['def', 'class', 'import', 'from', 'if', 'else', 'elif', 'for', 'while', 'try', 'except', 'finally', 'return', 'yield', 'lambda', 'with', 'as', 'pass', 'break', 'continue', 'and', 'or', 'not', 'in', 'is', 'True', 'False', 'None'];
    const builtins = ['print', 'input', 'len', 'range', 'str', 'int', 'float', 'list', 'dict', 'tuple', 'set'];
    
    // Apply syntax highlighting
    let highlighted = code;
    
    // Comments
    highlighted = highlighted.replace(/(#.*$)/gm, '<span class="comment">$1</span>');
    
    // Strings
    highlighted = highlighted.replace(/(".*?"|'.*?'|"""[\s\S]*?"""|'''[\s\S]*?''')/g, '<span class="string">$1</span>');
    
    // Keywords
    keywords.forEach(keyword => {
        highlighted = highlighted.replace(new RegExp(`\\b${keyword}\\b`, 'g'), `<span class="keyword">${keyword}</span>`);
    });
    
    // Built-ins
    builtins.forEach(builtin => {
        highlighted = highlighted.replace(new RegExp(`\\b${builtin}\\b`, 'g'), `<span class="builtin">${builtin}</span>`);
    });
    
    // Numbers
    highlighted = highlighted.replace(/\b(\d+\.?\d*)\b/g, '<span class="number">$1</span>');
    
    return highlighted;
}

function highlightJavaScript(code) {
    const keywords = ['function', 'var', 'let', 'const', 'if', 'else', 'for', 'while', 'return', 'class', 'extends', 'import', 'export', 'default', 'async', 'await', 'try', 'catch', 'finally', 'throw', 'new', 'this', 'super'];
    
    let highlighted = code;
    
    // Comments
    highlighted = highlighted.replace(/(\/\/.*$|\/\*[\s\S]*?\*\/)/gm, '<span class="comment">$1</span>');
    
    // Strings
    highlighted = highlighted.replace(/(".*?"|'.*?'|`.*?`)/g, '<span class="string">$1</span>');
    
    // Keywords
    keywords.forEach(keyword => {
        highlighted = highlighted.replace(new RegExp(`\\b${keyword}\\b`, 'g'), `<span class="keyword">${keyword}</span>`);
    });
    
    // Numbers
    highlighted = highlighted.replace(/\b(\d+\.?\d*)\b/g, '<span class="number">$1</span>');
    
    return highlighted;
}

function highlightHTML(code) {
    let highlighted = code;
    
    // HTML tags
    highlighted = highlighted.replace(/(&lt;[^&]*&gt;)/g, '<span class="tag">$1</span>');
    
    // Attributes
    highlighted = highlighted.replace(/(\w+)=("[^"]*")/g, '<span class="attribute">$1</span>=<span class="string">$2</span>');
    
    return highlighted;
}

function highlightCSS(code) {
    let highlighted = code;
    
    // CSS selectors
    highlighted = highlighted.replace(/([.#]?[\w-]+)(\s*{)/g, '<span class="selector">$1</span>$2');
    
    // CSS properties
    highlighted = highlighted.replace(/([\w-]+)(\s*:)/g, '<span class="property">$1</span>$2');
    
    // CSS values
    highlighted = highlighted.replace(/(:[\s]*)([^;{}]+)(;?)/g, '$1<span class="value">$2</span>$3');
    
    return highlighted;
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

function copyCode(codeId) {
    const codeElement = document.getElementById(codeId);
    if (codeElement) {
        const textToCopy = codeElement.textContent;
        
        if (navigator.clipboard && window.isSecureContext) {
            // Use modern clipboard API
            navigator.clipboard.writeText(textToCopy).then(() => {
                showNotification('Code copied to clipboard!', 'success');
            }).catch(() => {
                fallbackCopyText(textToCopy);
            });
        } else {
            // Fallback for older browsers
            fallbackCopyText(textToCopy);
        }
    }
}

function fallbackCopyText(text) {
    const textArea = document.createElement('textarea');
    textArea.value = text;
    textArea.style.position = 'fixed';
    textArea.style.left = '-999999px';
    textArea.style.top = '-999999px';
    document.body.appendChild(textArea);
    textArea.focus();
    textArea.select();
    
    try {
        document.execCommand('copy');
        showNotification('Code copied to clipboard!', 'success');
    } catch (err) {
        showNotification('Failed to copy code', 'error');
    }
    
    document.body.removeChild(textArea);
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
