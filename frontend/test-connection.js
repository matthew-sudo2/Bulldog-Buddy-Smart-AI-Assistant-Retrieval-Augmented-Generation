const { Pool } = require('pg');
require('dotenv').config();

const pool = new Pool({
    user: process.env.DB_USER || 'postgres',
    host: process.env.DB_HOST || 'localhost',
    database: process.env.DB_NAME || 'bulldog_buddy',
    password: process.env.DB_PASSWORD || 'bulldog_buddy_password_2025',
    port: process.env.DB_PORT || 5432,
});

console.log('Testing PostgreSQL connection...');
console.log('Config:', {
    user: process.env.DB_USER || 'postgres',
    host: process.env.DB_HOST || 'localhost',
    database: process.env.DB_NAME || 'bulldog_buddy',
    password: '***' + (process.env.DB_PASSWORD || 'bulldog_buddy_password_2025').slice(-4),
    port: process.env.DB_PORT || 5432,
});

pool.query('SELECT NOW() as now, current_user, current_database()')
    .then(result => {
        console.log('✅ Connection successful!');
        console.log('Server time:', result.rows[0].now);
        console.log('Connected as:', result.rows[0].current_user);
        console.log('Database:', result.rows[0].current_database);
        pool.end();
    })
    .catch(err => {
        console.error('❌ Connection failed:', err.message);
        pool.end();
        process.exit(1);
    });
