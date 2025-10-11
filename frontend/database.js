/**
 * PostgreSQL Database Configuration
 * Replaces MongoDB for user authentication
 */

const { Pool } = require('pg');
require('dotenv').config();

// Database configuration
const dbConfig = {
    user: process.env.DB_USER || 'postgres',
    host: process.env.DB_HOST || 'localhost',
    database: process.env.DB_NAME || 'bulldog_buddy',
    password: process.env.DB_PASSWORD || 'your_password',
    port: process.env.DB_PORT || 5432,
    // Connection pool settings
    max: 20,
    idleTimeoutMillis: 30000,
    connectionTimeoutMillis: 2000,
};

// Create connection pool
const pool = new Pool(dbConfig);

// Test connection
pool.on('connect', () => {
    console.log('✅ Connected to PostgreSQL database');
});

pool.on('error', (err) => {
    console.error('❌ PostgreSQL connection error:', err);
});

/**
 * User model functions
 */
class UserModel {
    
    /**
     * Create a new user
     */
    static async create(userData) {
        const { email, username, password_hash, google_id, first_name, last_name } = userData;
        
        // Generate a unique session_id for the new user
        const sessionId = `user_${Date.now()}_${Math.random().toString(36).substring(2, 15)}`;
        
        const query = `
            INSERT INTO users (
                session_id, email, username, password_hash, first_name, last_name,
                google_id, is_verified, created_at, last_active
            ) 
            VALUES ($1, $2, $3, $4, $5, $6, $7, $8, NOW(), NOW())
            RETURNING id, user_uuid, email, username, first_name, last_name, role, created_at
        `;
        
        const values = [
            sessionId,
            email.toLowerCase(), 
            username || email.split('@')[0], // Use part of email as username if not provided
            password_hash, 
            first_name || '',
            last_name || '',
            google_id,
            false // is_verified defaults to false
        ];
        
        try {
            const result = await pool.query(query, values);
            return result.rows[0];
        } catch (error) {
            if (error.code === '23505') { // Unique constraint violation
                if (error.constraint === 'users_email_key') {
                    throw new Error('Email already exists');
                } else if (error.constraint === 'users_username_key') {
                    throw new Error('Username already exists');
                } else if (error.constraint === 'users_session_id_key') {
                    // This is rare but could happen with clock skew - retry with new session_id
                    throw new Error('Session ID conflict - please try again');
                }
            }
            console.error('Database error in create:', error);
            throw error;
        }
    }
    
    /**
     * Find user by email
     */
    static async findByEmail(email) {
        const query = `
            SELECT id, user_uuid, email, username, password_hash, 
                   google_id, role, is_active, created_at, last_login
            FROM users 
            WHERE email = $1 AND is_active = true
        `;
        
        try {
            const result = await pool.query(query, [email.toLowerCase()]);
            return result.rows[0] || null;
        } catch (error) {
            throw error;
        }
    }
    
    /**
     * Find user by username
     */
    static async findByUsername(username) {
        const query = `
            SELECT id, user_uuid, email, username, password_hash, 
                   google_id, role, is_active, created_at, last_login
            FROM users 
            WHERE username = $1 AND is_active = true
        `;
        
        try {
            const result = await pool.query(query, [username]);
            return result.rows[0] || null;
        } catch (error) {
            throw error;
        }
    }
    
    /**
     * Find user by ID
     */
    static async findById(id) {
        const query = `
            SELECT id, user_uuid, email, username, role, 
                   is_active, created_at, last_login, total_queries
            FROM users 
            WHERE id = $1 AND is_active = true
        `;
        
        try {
            const result = await pool.query(query, [id]);
            return result.rows[0] || null;
        } catch (error) {
            throw error;
        }
    }
    
    /**
     * Find user by Google ID
     */
    static async findByGoogleId(googleId) {
        const query = `
            SELECT id, user_uuid, email, username, google_id, 
                   role, is_active, created_at, last_login
            FROM users 
            WHERE google_id = $1 AND is_active = true
        `;
        
        try {
            const result = await pool.query(query, [googleId]);
            return result.rows[0] || null;
        } catch (error) {
            throw error;
        }
    }
    
    /**
     * Update user login info
     */
    static async updateLogin(userId, sessionId = null) {
        let query, values;
        
        if (sessionId) {
            query = `
                UPDATE users 
                SET last_login = NOW(), last_active = NOW(), session_id = $2
                WHERE id = $1
            `;
            values = [userId, sessionId];
        } else {
            query = `
                UPDATE users 
                SET last_login = NOW(), last_active = NOW()
                WHERE id = $1
            `;
            values = [userId];
        }
        
        try {
            await pool.query(query, values);
        } catch (error) {
            console.error('Error updating login:', error);
            throw error;
        }
    }
    
    /**
     * Update user activity
     */
    static async updateActivity(userId) {
        const query = `
            UPDATE users 
            SET last_active = NOW(), total_queries = total_queries + 1
            WHERE id = $1
        `;
        
        try {
            await pool.query(query, [userId]);
        } catch (error) {
            throw error;
        }
    }
    
    /**
     * Check if email exists
     */
    static async emailExists(email) {
        const query = `SELECT id FROM users WHERE email = $1`;
        try {
            const result = await pool.query(query, [email.toLowerCase()]);
            return result.rows.length > 0;
        } catch (error) {
            throw error;
        }
    }
    
    /**
     * Check if username exists
     */
    static async usernameExists(username) {
        const query = `SELECT id FROM users WHERE username = $1`;
        try {
            const result = await pool.query(query, [username]);
            return result.rows.length > 0;
        } catch (error) {
            throw error;
        }
    }
}

module.exports = {
    pool,
    UserModel
};