# Critical Bug: Shared RAG System Instance Across Users

## Problem Identified

### Root Cause
The RAG system is initialized as a **global singleton** in `bridge_server_enhanced.py`:

```python
# Global components
rag_system = None
rag_systems = {}  # Cache for different models

@app.on_event("startup")
async def startup_event():
    rag_system = EnhancedRAGSystem(str(handbook_path), model_name="gemma3:latest")
    rag_systems["gemma3:latest"] = rag_system  # SHARED ACROSS ALL USERS!
```

### Why This Causes Issues for New Users

1. **User A** (e.g., "Robb Stark") logs in and asks questions
   - RAG system stores conversation in `self.conversation_history = [...]`
   - System works perfectly for User A

2. **User B** (new account) logs in and asks their first question
   - Gets the SAME RAG system instance
   - The instance still has `self.conversation_history` from User A
   - Follow-up detection (`_detect_follow_up_question()`) returns `True` because `len(self.conversation_history) > 0`
   - System treats User B's first question as a follow-up to User A's conversation!

3. **Result**: New users get:
   - Wrong context from previous users' conversations
   - Verbose responses that reference irrelevant previous topics
   - Generic answers instead of handbook-specific information
   - Broken conversational flow

### Evidence from Screenshot

The response to "What is the grade required for Dean's Lister?" is:
- ✅ Shows "High (80%)" confidence (good)
- ✅ Uses "University Mode: Using student handbook" (good)
- ❌ Response is verbose and generic (bad)
- ❌ Mentions "Let's talk about getting on the Dean's Lister" (suggests it thinks it's continuing a conversation)
- ❌ Says "Absolutely!" (greeting that should only appear in follow-ups)

## Solution Options

### Option 1: Per-User RAG System Instances (Memory Intensive)
Create separate RAG system for each user.

**Pros:**
- Complete isolation
- No cross-user contamination

**Cons:**
- High memory usage (each instance loads embedding models)
- Doesn't scale well

### Option 2: Per-Session RAG System Instances (Balanced)
Create separate RAG system for each session.

**Pros:**
- Good isolation
- Scales reasonably

**Cons:**
- Still memory intensive for many concurrent sessions

### Option 3: Shared RAG System with Isolated State (RECOMMENDED)
Keep global RAG system but isolate user-specific state.

**Pros:**
- Low memory usage
- Scales well
- Clean separation of concerns

**Cons:**
- Requires careful state management

## Recommended Fix: Option 3

### Architecture Change

```
Before:
RAG System (Global)
├── conversation_history (SHARED - BUG!)
├── current_user_id (SHARED - BUG!)
└── current_session_id (SHARED - BUG!)

After:
RAG System (Global)
├── vectorstore (SHARED - OK)
├── qa_chain (SHARED - OK)
└── llm (SHARED - OK)

Session State Manager (Per Request)
├── conversation_history[session_id]
├── user_id[session_id]
└── session_context[session_id]
```

### Implementation Steps

1. **Extract user/session state from RAG system**
   - Move `conversation_history` to session storage
   - Move `current_user_id` to request context
   - Move `current_session_id` to request context

2. **Create SessionStateManager**
   - Manages conversation history per session
   - Manages user context per session
   - Cleans up old sessions

3. **Update RAG system to accept state as parameters**
   - `ask_question(question, session_state)`
   - `_detect_follow_up_question(question, conversation_history)`
   - `_rewrite_followup_question(question, conversation_history)`

4. **Update bridge server to manage state**
   - Store session state in Redis or in-memory dict with TTL
   - Pass appropriate state to RAG system on each request
   - Clean up expired sessions

## Immediate Workaround (Quick Fix)

For a quick fix without refactoring, clear the conversation history when session changes:

```python
# In bridge_server_enhanced.py - chat endpoint
def chat(chat_request: ChatRequest):
    current_rag = rag_systems.get(chat_request.model, rag_system)
    
    # QUICK FIX: Clear conversation history for new sessions
    if hasattr(current_rag, 'current_session_id'):
        if current_rag.current_session_id != chat_request.session_id:
            current_rag.conversation_history = []  # Clear previous user's history
            current_rag.current_session_id = chat_request.session_id
```

## Testing the Fix

### Test Case 1: New User Isolation
1. User A logs in, asks 3 questions
2. User B (new account) logs in
3. User B asks their first question
4. **Expected**: User B's response should NOT reference User A's conversation
5. **Expected**: User B should get fresh, direct answers

### Test Case 2: Concurrent Users
1. User A logs in, asks question
2. User B logs in (different browser/session)
3. User B asks question
4. User A asks another question
5. **Expected**: Each user sees only their own conversation history

### Test Case 3: Same User, New Session
1. User A logs in, has conversation
2. User A clicks "New Chat"
3. User A asks question in new chat
4. **Expected**: New chat should start fresh, not reference old chat

## Priority: CRITICAL

This bug affects:
- ✅ All new users (first question experience)
- ✅ Concurrent users (cross-contamination)
- ✅ Session management (wrong context)
- ✅ Data privacy (users see each other's context)

## Related Files
- `api/bridge_server_enhanced.py` - Global RAG system
- `models/enhanced_rag_system.py` - Stores user state
- `core/conversation_history.py` - Database storage (OK)
- Frontend session management (OK)

## Next Steps
1. Implement immediate workaround (5 min)
2. Test with new user creation
3. Plan full refactor for proper session isolation
4. Add session state manager
5. Update documentation
