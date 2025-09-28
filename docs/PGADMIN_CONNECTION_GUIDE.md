# 🔧 pgAdmin Connection Guide - Bulldog Buddy Database

## ✅ **Step-by-Step Connection Instructions:**

### **1. Access pgAdmin Web Interface:**
- Open browser: http://localhost:8080
- Login with:
  - **Email**: `admin@bulldogbuddy.com`
  - **Password**: `admin123`

### **2. Add Database Server:**
1. **Right-click "Servers"** in the left panel
2. Select **"Register" → "Server..."**

### **3. Fill in Connection Details:**

**🔤 General Tab:**
- **Name**: `Bulldog Buddy Database` (any name you prefer)

**🔗 Connection Tab:**
- **Host name/address**: `postgres` ⭐ (IMPORTANT: Use service name, not container name)
- **Port**: `5432`
- **Maintenance database**: `bulldog_buddy`
- **Username**: `postgres`
- **Password**: `bulldog_buddy_password_2025`

**🎯 Important Notes:**
- ✅ Use `postgres` as hostname (service name from docker-compose)
- ❌ Don't use `bulldog-buddy-db` (that's the container name)
- ✅ Use `bulldog_buddy` as database name
- ✅ Leave Role empty
- ✅ Keep SSL mode as "prefer"

### **4. Click "Save"**

---

## 📊 **What You Should See After Connecting:**

```
Servers
└── Bulldog Buddy Database
    └── Databases
        └── bulldog_buddy
            └── Schemas
                └── public
                    └── Tables (12 total)
                        ├── academic_calendar
                        ├── conversations
                        ├── current_tuition_rates
                        ├── email_verification_tokens
                        ├── financial_info
                        ├── knowledge_base ⭐ (10 entries)
                        ├── password_reset_tokens
                        ├── query_logs
                        ├── system_config
                        ├── user_preferences
                        ├── user_sessions
                        └── users ⭐ (4 users)
```

---

## 🧪 **Test Queries to Run:**

After connecting, try these queries in the Query Tool:

### **Check Users:**
```sql
SELECT id, email, username, first_name, last_name, role 
FROM users 
ORDER BY role, id;
```

### **Check Knowledge Base:**
```sql
SELECT category, title, LEFT(content, 100) as content_preview
FROM knowledge_base 
ORDER BY category, section;
```

### **Check Sample Financial Data:**
```sql
SELECT level, rate_per_unit, currency, payment_options
FROM financial_info 
ORDER BY level;
```

---

## 🚨 **If Still No Data - Troubleshooting:**

### **Option 1: Check Container Network**
```bash
# Check if containers are in same network
docker network ls
docker network inspect bulldog-buddy-network
```

### **Option 2: Use Container IP Instead**
```bash
# Get PostgreSQL container IP
docker inspect bulldog-buddy-db | grep "IPAddress"
```
Then use that IP address instead of "postgres" as hostname.

### **Option 3: Use localhost (from host machine)**
- **Host name/address**: `localhost` or `127.0.0.1`
- **Port**: `5432`
- (This works because we mapped port 5432 to host)

---

## ✅ **Database Verification:**

Your database currently contains:
- ✅ **4 Users**: 1 admin + 3 students
- ✅ **10 Knowledge Base Entries**: University handbook content
- ✅ **3 Tuition Rate Records**: Different education levels
- ✅ **7 Academic Calendar Events**: Important dates
- ✅ **All Authentication Tables**: Ready for login system

**Use `postgres` as hostname - this should connect you to your fully populated database! 🎉**