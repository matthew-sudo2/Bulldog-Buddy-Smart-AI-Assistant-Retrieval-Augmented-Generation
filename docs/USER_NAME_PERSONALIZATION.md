# User Name Personalization Feature

## Overview
Bulldog Buddy now recognizes and remembers user names for personalized interactions, similar to ChatGPT's memory feature.

## Features Implemented

### 1. Enhanced Name Extraction
The system now detects names from various introduction patterns:
- "My name is Matthew"
- "I'm Sarah"
- "Call me John"
- "This is Alex"
- "You can call me Emily"
- And more natural variations

### 2. Registered Username Fallback
If a user hasn't introduced themselves in conversation, the system automatically retrieves their registered username from the database as a fallback.

### 3. Personalized Responses
When the system knows a user's name, it will:
- Greet them naturally: "Hey Matthew!" 
- Use their name conversationally throughout responses
- Only use the name when it feels natural (not forced)

### 4. Graceful Handling When Name Unknown
If the name isn't available, the system:
- Uses friendly generic greetings: "Woof!"
- Doesn't try to make up or guess a name
- Still provides helpful responses

## How It Works

### User Context Storage
```python
# Names are stored in the user_context table
{
    "user_id": 123,
    "context_key": "name",
    "context_value": "Matthew",
    "context_type": "personal_info",
    "confidence": 0.8
}
```

### Prompt Integration
The user's name is automatically injected into prompts:
```
IMPORTANT USER CONTEXT (Remember this information about the user):
Personal Information:
- Name: Matthew

The user's name is Matthew. Please use this information to personalize 
your responses. Address them naturally (e.g., "Hey Matthew!" or use 
their name conversationally).
```

### Smart Name Detection
The system extracts names using regex patterns:
```python
patterns = {
    'name': [
        r"(?:my name is|i'm|i am|call me|i'm called|this is|name's)\s+([A-Za-z]+(?:\s+[A-Za-z]+)?)",
        r"(?:^|\s)(?:i'm|i am)\s+([A-Z][a-z]+)(?:\s|$|,|\.|!)",
        r"(?:call me|refer to me as|you can call me)\s+([A-Za-z]+)",
    ]
}
```

## Updated Components

### 1. `core/user_context.py`
- **`extract_user_info()`**: Enhanced name extraction patterns
- **`get_user_registered_name()`**: NEW - Retrieves username from database
- **`build_context_prompt()`**: Updated to include name instructions

### 2. `models/enhanced_rag_system.py`
- **`get_user_name_for_prompt()`**: NEW - Utility to get user's name
- **`_handle_grading_query()`**: Updated with personalized greetings
- **`_handle_general_query()`**: Updated with name-aware prompts
- **`_handle_conversational_general_query()`**: Updated with name context

## Testing

Run the test suite to verify functionality:

```powershell
.\.venv\Scripts\python.exe scripts\test_name_personalization.py
```

This will test:
1. Name extraction from various introduction patterns
2. Context prompt building with/without names
3. Registered name fallback mechanism
4. Graceful handling of missing names

## Example Interactions

### With Name Known:
**User:** "My name is Matthew. What are the grading policies?"

**Bulldog Buddy:** "Hey Matthew! Woof! Let me tell you about the grading system at our university! 🐶..."

### Without Name (First Interaction):
**User:** "What are the grading policies?"

**Bulldog Buddy:** "Woof! Let me tell you about the grading system at our university! 🐶..."

### Follow-up (Name Remembered):
**User:** "Tell me more about incomplete grades"

**Bulldog Buddy:** "Great question, Matthew! Let me explain how incomplete grades work..."

## Configuration

No additional configuration needed. The feature works automatically when:
1. User Context Manager is initialized
2. User ID is set via `rag_system.set_user_context(user_id)`
3. The API bridge properly passes user_id in chat requests

## Database Schema

The feature uses the existing `user_context` table:
```sql
CREATE TABLE user_context (
    id SERIAL PRIMARY KEY,
    user_id INTEGER REFERENCES users(id),
    context_key VARCHAR(100),
    context_value TEXT,
    context_type VARCHAR(50),
    confidence FLOAT,
    source VARCHAR(100),
    created_at TIMESTAMP,
    updated_at TIMESTAMP
);
```

## Benefits

1. **More Personal Experience**: Users feel recognized and valued
2. **Natural Conversations**: Responses feel more human-like
3. **Memory-Like Feature**: Similar to ChatGPT's memory capabilities
4. **Automatic Operation**: Works without user configuration
5. **Privacy Conscious**: Only stores what users explicitly share

## Future Enhancements

Potential improvements:
- Remember user's preferred nickname vs formal name
- Multi-language name recognition
- Name pronunciation guidance
- Family name vs given name handling for international users
- Privacy controls for name storage
