const express = require('express');
const bcrypt = require('bcryptjs'); // Switched from bcrypt to bcryptjs for better compatibility
const path = require('path');
const session = require('express-session');
require('dotenv').config(); // Load environment variables

const { OAuth2Client } = require("google-auth-library");
const client = new OAuth2Client(process.env.GOOGLE_CLIENT_ID || "612477523743-13tajd11p5fhl4q0pthp75cd50hf9jq2.apps.googleusercontent.com");

// API Bridge Configuration
const API_BRIDGE_BASE_URL = 'http://127.0.0.1:8001';

// Import PostgreSQL database
const { pool, UserModel } = require('./database');

const port = process.env.PORT || 3000;
const app = express();

// serves static files correctly with no-cache headers
app.use(express.static(__dirname, {
    setHeaders: (res, path) => {
        res.setHeader('Cache-Control', 'no-cache, no-store, must-revalidate');
        res.setHeader('Pragma', 'no-cache');
        res.setHeader('Expires', '0');
    }
}));
app.use('/src', express.static(path.join(__dirname, 'src'), {
    setHeaders: (res, path) => {
        res.setHeader('Cache-Control', 'no-cache, no-store, must-revalidate');
        res.setHeader('Pragma', 'no-cache');
        res.setHeader('Expires', '0');
    }
}));

// Serve files inside the public directory at the web root (so /favicon.ico works)
app.use(express.static(path.join(__dirname, 'public'), {
    setHeaders: (res, path) => {
        res.setHeader('Cache-Control', 'no-cache, no-store, must-revalidate');
        res.setHeader('Pragma', 'no-cache');
        res.setHeader('Expires', '0');
    }
}));

app.use(express.urlencoded({ extended: true }));
app.use(express.json());
app.use(session({
    secret: 'your-secret-key',
    resave: false,
    saveUninitialized: false,
    cookie: { secure: false }
}));

function requireAuth(req, res, next) {
    if (!req.session.userId) {
        return res.redirect('/');
    }
    next();
}

function redirectIfLoggedIn(req, res, next) {
    if (req.session.userId) {
        return res.redirect('/main-redesigned');
    }
    next();
}

function preventCache(req, res, next) {
    res.setHeader('Cache-Control', 'no-cache, no-store, must-revalidate');
    res.setHeader('Pragma', 'no-cache');
    res.setHeader('Expires', '0');
    next();
}

// MongoDB availability check middleware
function requireMongo(req, res, next) {
    if (!mongoConnected) {
        return res.status(503).json({
            success: false,
            message: 'Database service temporarily unavailable'
        });
    }
    next();
}

// PostgreSQL connection status
let pgConnected = false;

// Test PostgreSQL connection
pool.connect()
    .then(client => {
        console.log('✅ Connected to PostgreSQL database');
        pgConnected = true;
        client.release();
    })
    .catch(err => {
        console.error('❌ PostgreSQL connection failed:', err.message);
        console.log('⚠️  Running without PostgreSQL - authentication will be limited');
        pgConnected = false;
    });

// Monitor connection health
pool.on('error', (err) => {
    console.error('❌ PostgreSQL pool error:', err.message);
    pgConnected = false;
});

// PostgreSQL availability check middleware
function requireDB(req, res, next) {
    if (!pgConnected) {
        return res.status(503).json({
            success: false,
            message: 'Database service temporarily unavailable'
        });
    }
    next();
}

// routes
app.get('/', preventCache, redirectIfLoggedIn, (req, res) => {
    res.sendFile(path.join(__dirname, 'public', 'index.html'));
});

app.get('/login', redirectIfLoggedIn, (req, res) => {
    res.sendFile(path.join(__dirname, 'public', 'login.html'));
});

app.get('/register', redirectIfLoggedIn, (req, res) => {
    res.sendFile(path.join(__dirname, 'public', 'register.html'));
});

app.get('/username', (req, res) => {
    if (!req.session.tempEmail) {
        return res.redirect('/');
    }
    res.sendFile(path.join(__dirname, 'public', 'username.html'));
});

// Main chat interface - Redirect /main to redesigned version
app.get('/main', requireAuth, preventCache, (req, res) => {
    res.redirect('/main-redesigned');
});

// Redirect old enhanced route to current main interface
app.get('/main-enhanced', requireAuth, preventCache, (req, res) => {
    res.redirect('/main-redesigned');
});

// Main chat interface - Modern UI
app.get('/main-redesigned', requireAuth, preventCache, (req, res) => {
    res.sendFile(path.join(__dirname, 'public', 'main-redesigned.html'));
});

// API endpoint to get current user info
app.get('/api/user', requireAuth, async (req, res) => {
    try {
        const user = await UserModel.findById(req.session.userId);
        if (user) {
            res.json({
                id: user.id,
                email: user.email,
                first_name: user.first_name || user.username,
                last_name: user.last_name || '',
                username: user.username
            });
        } else {
            res.status(404).json({ error: 'User not found' });
        }
    } catch (error) {
        console.error('Error getting user:', error);
        res.status(500).json({ error: 'Server error' });
    }
});

// ===========================================================================
// API PROXY ROUTES TO ENHANCED BRIDGE
// ===========================================================================

// Proxy all /api/bridge/* requests to the Enhanced API Bridge
app.use('/api/bridge', async (req, res) => {
    try {
        // Build correct URL: /api/bridge/health?param=value -> http://127.0.0.1:8001/api/health?param=value
        const targetPath = req.path.startsWith('/') ? req.path : `/${req.path}`;
        const queryString = req.url.includes('?') ? req.url.substring(req.url.indexOf('?')) : '';
        const targetUrl = `${API_BRIDGE_BASE_URL}/api${targetPath}${queryString}`;
        
        console.log(`[API Proxy] ${req.method} ${req.originalUrl} -> ${targetUrl}`);
        
        const options = {
            method: req.method,
            headers: {
                'Content-Type': 'application/json',
            }
        };

        if (req.method !== 'GET' && req.method !== 'HEAD' && req.method !== 'DELETE') {
            options.body = JSON.stringify(req.body);
        }

        const response = await fetch(targetUrl, options);
        const data = await response.json();
        
        res.status(response.status).json(data);
    } catch (error) {
        console.error('API Bridge proxy error:', error);
        res.status(500).json({
            success: false,
            message: 'Error communicating with API bridge',
            error: error.message
        });
    }
});

app.post("/google-login", requireDB, async (req, res) => {
    try {
        const { token } = req.body;
        const ticket = await client.verifyIdToken({
            idToken: token,
            audience: process.env.GOOGLE_CLIENT_ID || "612477523743-13tajd11p5fhl4q0pthp75cd50hf9jq2.apps.googleusercontent.com"
        });

        const payload = ticket.getPayload();
        const email = payload.email;
        const googleId = payload.sub;

        // Check if user already exists by Google ID or email
        let user = await UserModel.findByGoogleId(googleId);
        if (!user) {
            user = await UserModel.findByEmail(email);
        }

        if (!user) {
            // Create new user
            let username = payload.name || email.split("@")[0];
            let counter = 1;
            const originalUsername = username;

            // Ensure unique username
            while (await UserModel.usernameExists(username)) {
                username = `${originalUsername}${counter}`;
                counter++;
            }

            user = await UserModel.create({
                email,
                username,
                password_hash: null, // No password for Google OAuth users
                google_id: googleId
            });

            console.log("New Google user created:", email);
        } else if (!user.google_id) {
            // Update existing user with Google ID
            await pool.query(
                'UPDATE users SET google_id = $1, last_login = NOW() WHERE id = $2',
                [googleId, user.id]
            );
        }

        // Update login info
        const sessionId = `google_${user.id}_${Date.now()}`;
        await UserModel.updateLogin(user.id, sessionId);

        req.session.userId = user.id;
        res.json({ success: true, redirect: "/main-redesigned" });

    } catch (error) {
        console.error("Google login error:", error);
        res.status(401).json({ success: false, message: "Invalid Google login" });
    }
});

// log in and sign up handler
app.post('/auth', requireDB, async (req, res) => {
    try {
        const { email, password } = req.body;

        if (!email || !password) {
            return res.status(400).json({ 
                success: false, 
                message: 'Email and password are required' 
            });
        }

        if (password.length < 6) {
            return res.status(400).json({ 
                success: false, 
                message: 'Password must be at least 6 characters long' 
            });
        }

        const emailRegex = /^[^\s@]+@[^\s@]+\.[^\s@]+$/;
        if (!emailRegex.test(email)) {
            return res.status(400).json({ 
                success: false, 
                message: 'Please enter a valid email address' 
            });
        }

        const existingUser = await UserModel.findByEmail(email.toLowerCase());

        if (existingUser) {
            // LOGIN LOGIC
            if (!existingUser.password_hash) {
                return res.status(400).json({ 
                    success: false, 
                    message: 'This account uses Google login. Please use Google OAuth to sign in.' 
                });
            }

            const passwordMatch = await bcrypt.compare(password, existingUser.password_hash);
            if (!passwordMatch) {
                return res.status(400).json({ 
                    success: false, 
                    message: 'Incorrect password' 
                });
            }

            // Update login info
            const sessionId = `login_${existingUser.id}_${Date.now()}`;
            await UserModel.updateLogin(existingUser.id, sessionId);

            req.session.userId = existingUser.id;
            
            return res.json({ 
                success: true, 
                redirect: '/main-redesigned' 
            });

        } else {
            // SIGNUP LOGIC
            const hashedPassword = await bcrypt.hash(password, 12);
            req.session.tempEmail = email.toLowerCase();
            req.session.tempPassword = hashedPassword;
            
            return res.json({ 
                success: true, 
                redirect: '/username' 
            });
        }

    } catch (error) {
        console.error('Authentication error:', error);
        return res.status(500).json({ 
            success: false, 
            message: 'Server error occurred' 
        });
    }
});

// username submission handler
app.post('/complete-registration', requireDB, async (req, res) => {
    try {
        const { username } = req.body;

        if (!req.session.tempEmail || !req.session.tempPassword) {
            return res.status(400).json({ 
                success: false, 
                message: 'Registration session expired' 
            });
        }

        if (!username || username.trim().length < 2) {
            return res.status(400).json({ 
                success: false, 
                message: 'Username must be at least 2 characters long' 
            });
        }

        const trimmedUsername = username.trim();

        // Check if username already exists
        if (await UserModel.usernameExists(trimmedUsername)) {
            return res.status(400).json({ 
                success: false, 
                message: 'Username is already taken' 
            });
        }

        // Check if email already exists
        if (await UserModel.emailExists(req.session.tempEmail)) {
            return res.status(400).json({ 
                success: false, 
                message: 'Email is already registered' 
            });
        }

        // Create new user
        const newUser = await UserModel.create({
            email: req.session.tempEmail,
            username: trimmedUsername,
            password_hash: req.session.tempPassword,
            google_id: null
        });

        console.log('New user registered:', newUser.email);

        // Update login info
        const sessionId = `register_${newUser.id}_${Date.now()}`;
        await UserModel.updateLogin(newUser.id, sessionId);

        // Clean up session
        delete req.session.tempEmail;
        delete req.session.tempPassword;
        req.session.userId = newUser.id;

        return res.json({ 
            success: true, 
            redirect: '/main-redesigned' 
        });

    } catch (error) {
        console.error('Registration completion error:', error);
        
        // Handle PostgreSQL unique constraint violations
        if (error.message.includes('already exists')) {
            return res.status(400).json({ 
                success: false, 
                message: error.message
            });
        }

        return res.status(500).json({ 
            success: false, 
            message: 'Server error occurred during registration' 
        });
    }
});

// Register endpoint - dedicated for new register page
app.post('/register', requireDB, async (req, res) => {
    try {
        const { name, email, password } = req.body;

        // Validation
        if (!name || !email || !password) {
            return res.status(400).json({ 
                success: false, 
                message: 'All fields are required' 
            });
        }

        if (name.trim().length < 2) {
            return res.status(400).json({ 
                success: false, 
                message: 'Name must be at least 2 characters long' 
            });
        }

        if (password.length < 6) {
            return res.status(400).json({ 
                success: false, 
                message: 'Password must be at least 6 characters long' 
            });
        }

        const emailRegex = /^[^\s@]+@[^\s@]+\.[^\s@]+$/;
        if (!emailRegex.test(email)) {
            return res.status(400).json({ 
                success: false, 
                message: 'Please enter a valid email address' 
            });
        }

        // Check if user already exists
        const existingUser = await UserModel.findByEmail(email.toLowerCase());
        if (existingUser) {
            return res.status(400).json({ 
                success: false, 
                message: 'Email is already registered. Please log in instead.' 
            });
        }

        // Hash password
        const hashedPassword = await bcrypt.hash(password, 12);

        // Create new user
        const newUser = await UserModel.create({
            email: email.toLowerCase(),
            username: name.trim(),
            password_hash: hashedPassword,
            google_id: null
        });

        console.log('New user registered via register page:', newUser.email);

        // Update login info
        const sessionId = `register_${newUser.id}_${Date.now()}`;
        await UserModel.updateLogin(newUser.id, sessionId);

        // Set session
        req.session.userId = newUser.id;

        return res.json({ 
            success: true, 
            redirect: '/main-redesigned' 
        });

    } catch (error) {
        console.error('Registration error:', error);
        
        // Handle PostgreSQL unique constraint violations
        if (error.message.includes('already exists')) {
            return res.status(400).json({ 
                success: false, 
                message: 'This email or username is already registered'
            });
        }

        return res.status(500).json({ 
            success: false, 
            message: 'Server error occurred during registration' 
        });
    }
});

// log out
app.post('/logout', (req, res) => {
    req.session.destroy((err) => {
        if (err) {
            console.error('Session destroy error:', err);
            return res.status(500).json({ 
                success: false, 
                message: 'Logout failed' 
            });
        }
        
        // Clear the session cookie
        res.clearCookie('connect.sid'); // Default session cookie name
        
        res.json({ 
            success: true, 
            redirect: '/' 
        });
    });
});

// ===== AI CHAT API ENDPOINTS =====
// Bridge endpoints to connect with the Python backend API

// Chat endpoint - sends messages to AI backend
app.post('/api/chat', requireAuth, async (req, res) => {
    try {
        const { message, conversation_id } = req.body;
        
        if (!message || message.trim().length === 0) {
            return res.status(400).json({
                success: false,
                message: 'Message is required'
            });
        }

        // Get user info
        const user = await UserModel.findById(req.session.userId);
        if (!user) {
            return res.status(401).json({
                success: false,
                message: 'User not found'
            });
        }

        // Forward to Python backend API bridge
        const response = await fetch(`${API_BRIDGE_BASE_URL}/api/chat`, {
            method: 'POST',
            headers: {
                'Content-Type': 'application/json',
            },
            body: JSON.stringify({
                message: message.trim(),
                user_id: user.id.toString(),
                conversation_id: conversation_id || null
            })
        });

        if (!response.ok) {
            throw new Error(`Backend API error: ${response.status}`);
        }

        const aiResponse = await response.json();
        
        res.json({
            success: true,
            response: aiResponse.response,
            conversation_id: aiResponse.conversation_id,
            timestamp: aiResponse.timestamp
        });

    } catch (error) {
        console.error('Chat API error:', error);
        res.status(500).json({
            success: false,
            message: 'Error processing chat message',
            error: error.message
        });
    }
});

// Get conversation history
app.get('/api/history', requireAuth, async (req, res) => {
    try {
        const { conversation_id, limit } = req.query;
        
        // Get user info
        const user = await UserModel.findById(req.session.userId);
        if (!user) {
            return res.status(401).json({
                success: false,
                message: 'User not found'
            });
        }

        // Forward to Python backend
        const response = await fetch(`${API_BRIDGE_BASE_URL}/api/history`, {
            method: 'POST',
            headers: {
                'Content-Type': 'application/json',
            },
            body: JSON.stringify({
                user_id: user.id.toString(),
                conversation_id: conversation_id || null,
                limit: parseInt(limit) || 50
            })
        });

        if (!response.ok) {
            throw new Error(`Backend API error: ${response.status}`);
        }

        const historyData = await response.json();
        
        res.json({
            success: true,
            conversations: historyData.conversations
        });

    } catch (error) {
        console.error('History API error:', error);
        res.status(500).json({
            success: false,
            message: 'Error retrieving conversation history',
            error: error.message
        });
    }
});

// Clear conversation history
app.delete('/api/history', requireAuth, async (req, res) => {
    try {
        // Get user info
        const user = await UserModel.findById(req.session.userId);
        if (!user) {
            return res.status(401).json({
                success: false,
                message: 'User not found'
            });
        }

        // Forward to Python backend
        const response = await fetch(`${API_BRIDGE_BASE_URL}/api/history/${user.id.toString()}`, {
            method: 'DELETE'
        });

        if (!response.ok) {
            throw new Error(`Backend API error: ${response.status}`);
        }

        const result = await response.json();
        
        res.json({
            success: true,
            message: 'Conversation history cleared'
        });

    } catch (error) {
        console.error('Clear history API error:', error);
        res.status(500).json({
            success: false,
            message: 'Error clearing conversation history',
            error: error.message
        });
    }
});

// Get user context/personalization
app.get('/api/user-context', requireAuth, async (req, res) => {
    try {
        // Get user info
        const user = await UserModel.findById(req.session.userId);
        if (!user) {
            return res.status(401).json({
                success: false,
                message: 'User not found'
            });
        }

        // Forward to Python backend
        const response = await fetch(`${API_BRIDGE_BASE_URL}/api/user-context/${user.id.toString()}`);

        if (!response.ok) {
            throw new Error(`Backend API error: ${response.status}`);
        }

        const contextData = await response.json();
        
        res.json({
            success: true,
            context: contextData.context,
            username: user.username
        });

    } catch (error) {
        console.error('User context API error:', error);
        res.status(500).json({
            success: false,
            message: 'Error retrieving user context',
            error: error.message
        });
    }
});

// Update user context/personalization
app.post('/api/user-context', requireAuth, async (req, res) => {
    try {
        const { context_data } = req.body;
        
        // Get user info
        const user = await UserModel.findById(req.session.userId);
        if (!user) {
            return res.status(401).json({
                success: false,
                message: 'User not found'
            });
        }

        // Forward to Python backend
        const response = await fetch(`${API_BRIDGE_BASE_URL}/api/user-context`, {
            method: 'POST',
            headers: {
                'Content-Type': 'application/json',
            },
            body: JSON.stringify({
                user_id: user.id.toString(),
                context_data: context_data || {}
            })
        });

        if (!response.ok) {
            throw new Error(`Backend API error: ${response.status}`);
        }

        const result = await response.json();
        
        res.json({
            success: true,
            message: 'User context updated'
        });

    } catch (error) {
        console.error('Update user context API error:', error);
        res.status(500).json({
            success: false,
            message: 'Error updating user context',
            error: error.message
        });
    }
});

// Health check for backend connectivity
app.get('/api/health', async (req, res) => {
    try {
        const response = await fetch(`${API_BRIDGE_BASE_URL}/api/health`);
        
        if (!response.ok) {
            throw new Error(`Backend API error: ${response.status}`);
        }

        const healthData = await response.json();
        
        res.json({
            success: true,
            frontend: 'healthy',
            backend: healthData
        });

    } catch (error) {
        console.error('Health check error:', error);
        res.status(500).json({
            success: false,
            frontend: 'healthy',
            backend: 'disconnected',
            error: error.message
        });
    }
});

// error handlers
app.use((err, req, res, next) => {
    console.error(err.stack);
    res.status(500).json({ 
        success: false, 
        message: 'Something went wrong!' 
    });
});

app.use((req, res) => {
    res.status(404).json({ 
        success: false, 
        message: 'Page not found' 
    });
});

app.listen(port, () => {
    console.log(`Server is running on port ${port}`);
});
