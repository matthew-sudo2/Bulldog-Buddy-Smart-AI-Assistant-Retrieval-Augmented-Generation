# Quick Reference: User Name Personalization

## For Developers

### How to Use in Code

```python
# In any RAG query handler or prompt building function:

# 1. Get user's name safely
user_name = ""
if self.context_manager and self.current_user_id:
    context_data = self.context_manager.get_user_context(self.current_user_id)
    if context_data and 'name' in context_data:
        user_name = context_data['name']['value']

# 2. Create personalized greeting
greeting = f"Hey {user_name}! " if user_name else "Woof! "

# 3. Use in prompt
prompt = f"""You are Bulldog Buddy!

{greeting}[rest of prompt...]"""
```

### Or Use the Helper Method

```python
# In enhanced_rag_system.py methods:
user_name = self.get_user_name_for_prompt()
greeting = f"Hey {user_name}! " if user_name else "Woof! "
```

## For Users

### How to Introduce Yourself

Any of these will work:
- "My name is Sarah"
- "I'm John"
- "Call me Mike"
- "This is Alex"
- "You can call me Emily"
- "Hi! My name is Taylor"

### What Happens

1. **First time:** System extracts and stores your name
2. **Later conversations:** System remembers your name automatically
3. **New sessions:** No need to re-introduce yourself
4. **If you never introduce:** System uses your registered username

## Testing Checklist

- [ ] Run `scripts\quick_name_test.py` - Verify extraction patterns
- [ ] Run `scripts\demo_name_feature.py` - See complete workflow
- [ ] Run `scripts\test_name_personalization.py` - Full test suite
- [ ] Test live: Introduce yourself and ask questions
- [ ] Test live: Start new session without re-introducing
- [ ] Test live: Ask questions without ever introducing (uses registered name)

## Key Files

- `core/user_context.py` - Name extraction and storage
- `models/enhanced_rag_system.py` - Personalized responses
- `docs/USER_NAME_PERSONALIZATION.md` - Full documentation
- `docs/IMPLEMENTATION_SUMMARY_NAME_PERSONALIZATION.md` - Technical details

## Common Patterns

### Pattern 1: Grading Query
```python
user_name = self.get_user_name_for_prompt()
greeting = f"Hey {user_name}! " if user_name else "Woof! "

prompt = f"""You are Bulldog Buddy!

{user_context}

Instructions:
- Start with: "{greeting}"
- Answer the grading question...
"""
```

### Pattern 2: General Query
```python
greeting = f"Hey {user_name}! " if user_name else "Woof! "

prompt = f"""You are Bulldog Buddy!

{user_context}

Instructions:
- Start naturally (use "{greeting}" if it fits)
- Use the user's name naturally when appropriate
"""
```

### Pattern 3: Conversational Query
```python
prompt = f"""You are Bulldog Buddy!

{user_context}

Instructions:
- Use the user's name ({user_name}) naturally when appropriate
- Reference previous conversation...
"""
```

## Database Schema

```sql
-- Names are stored in user_context table
SELECT * FROM user_context 
WHERE user_id = 1 AND context_key = 'name';

-- Result:
-- id | user_id | context_key | context_value | confidence
-- 1  | 1       | name        | Matthew       | 0.8
```

## Troubleshooting

### Name not being extracted?
- Check if user introduced themselves with a supported pattern
- Run `scripts\quick_name_test.py` to verify patterns
- Check logs for "Stored context for user" messages

### Name not being used in responses?
- Verify `set_user_context(user_id)` was called on RAG system
- Check that `context_manager` is initialized
- Verify the query handler uses the personalization code

### Name extracted incorrectly?
- The regex patterns filter out common false positives
- If needed, update patterns in `core/user_context.py` lines ~75-85

## API Integration

Ensure the API bridge passes user_id:

```python
# In bridge_server_enhanced.py
current_rag.set_user_context(chat_request.user_id)
result = current_rag.ask_question(chat_request.message)
```

## Privacy Note

Names are only stored when:
- User explicitly introduces themselves in conversation
- OR system falls back to registered username

Users can clear their context if needed (future feature).
