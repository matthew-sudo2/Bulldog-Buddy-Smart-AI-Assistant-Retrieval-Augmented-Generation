# Context Cache System - Visual Flow

## System Architecture

```
┌─────────────────────────────────────────────────────────────┐
│                    User Ask Question                         │
└─────────────────────────┬───────────────────────────────────┘
                          │
                          ▼
            ┌─────────────────────────────┐
            │   Is Follow-up Question?    │
            └──────────┬──────────────────┘
                       │
           ┌───────────┴───────────┐
           │                       │
           ▼ No                    ▼ Yes
┌──────────────────────┐  ┌──────────────────────┐
│  Check Cache         │  │  Rewrite Follow-up   │
│  Relatedness         │  │  Question            │
└──────────┬───────────┘  └──────────┬───────────┘
           │                          │
           │                          │
    ┌──────▼──────┐                  │
    │ Related?    │                  │
    │ >30%        │                  │
    │ overlap?    │                  │
    └──┬────┬─────┘                  │
       │    │                        │
    No │    │ Yes                    │
       │    │                        │
       ▼    ▼                        ▼
    ┌──────────────────────────────────────┐
    │   CLEAR CACHE                        │  ← Also clears on >5min timeout
    │   (New topic detected)               │
    └──────────────────┬───────────────────┘
                       │
                       ▼
            ┌──────────────────────┐
            │  Retrieve Chunks     │
            │  from VectorDB       │
            └──────────┬───────────┘
                       │
                       ▼
            ┌──────────────────────┐
            │  UPDATE CACHE        │
            │  - Store query       │
            │  - Store chunks      │
            │  - Update timestamp  │
            └──────────┬───────────┘
                       │
                       ▼
            ┌──────────────────────┐
            │  Generate Response   │
            │  with Formatting     │
            │  Instructions        │
            └──────────┬───────────┘
                       │
                       ▼
            ┌──────────────────────┐
            │  Return to User      │
            └──────────────────────┘
```

## Cache State Transitions

```
Initial State:
┌───────────────────────────┐
│ current_query: None       │
│ current_chunks: []        │
│ previous_query: None      │
│ previous_chunks: []       │
│ timestamp: None           │
└───────────────────────────┘

After First Question "What's the tuition fee?":
┌─────────────────────────────────────────────┐
│ current_query: "What's the tuition fee?"    │
│ current_chunks: [Section 4.1 Financial...]  │
│ previous_query: None                        │
│ previous_chunks: []                         │
│ timestamp: 2025-10-15 14:00:00             │
└─────────────────────────────────────────────┘

After Related Question "What about payment options?":
┌──────────────────────────────────────────────────┐
│ current_query: "What about payment options?"     │
│ current_chunks: [Section 4.2 Payments...]       │
│ previous_query: "What's the tuition fee?"       │
│ previous_chunks: [Section 4.1 Financial...]     │
│ timestamp: 2025-10-15 14:01:00                  │
└──────────────────────────────────────────────────┘

After Unrelated Question "What's the grading scale?":
┌──────────────────────────────────────────────────┐
│ CACHE CLEARED!                                   │
│ current_query: "What's the grading scale?"      │
│ current_chunks: [Section 3.2 Grading...]        │
│ previous_query: "What about payment options?"   │
│ previous_chunks: [Section 4.2 Payments...]      │
│ timestamp: 2025-10-15 14:02:00                  │
└──────────────────────────────────────────────────┘
```

## Query Relatedness Detection

```
┌────────────────────────────────────────────────┐
│  Question 1: "What's the tuition fee?"         │
│  Keywords: [tuition, fee]                      │
└──────────────────┬─────────────────────────────┘
                   │
                   ▼
┌────────────────────────────────────────────────┐
│  Question 2: "What about payment options?"     │
│  Keywords: [payment, options]                  │
└──────────────────┬─────────────────────────────┘
                   │
                   ▼
┌────────────────────────────────────────────────┐
│  Keyword Comparison                            │
│  - Remove stop words (what, about, the)        │
│  - Compare: [tuition, fee] vs [payment,       │
│    options]                                    │
│  - Overlap: 0 words                            │
│  - Ratio: 0% < 30%                             │
│  - Result: UNRELATED → CLEAR CACHE             │
└────────────────────────────────────────────────┘

┌────────────────────────────────────────────────┐
│  Question 1: "What's the tuition fee?"         │
│  Keywords: [tuition, fee]                      │
└──────────────────┬─────────────────────────────┘
                   │
                   ▼
┌────────────────────────────────────────────────┐
│  Question 2: "How much is tuition?"            │
│  Keywords: [much, tuition]                     │
└──────────────────┬─────────────────────────────┘
                   │
                   ▼
┌────────────────────────────────────────────────┐
│  Keyword Comparison                            │
│  - Compare: [tuition, fee] vs [much, tuition] │
│  - Overlap: 1 word (tuition)                   │
│  - Ratio: 50% > 30%                            │
│  - Result: RELATED → KEEP CACHE                │
└────────────────────────────────────────────────┘
```

## Time-Based Cache Expiration

```
Timeline:
─────────────────────────────────────────────────────────►
0:00          3:00          5:00         6:00

│             │             │            │
▼             │             ▼            ▼
Question      │        Timeout      Question
Asked         │        Point        Asked
              │
Cache         │
Created       │
              ▼
              Still Valid
              (< 5 min)

At 6:00: Cache expired, will be cleared automatically
```

## Prompt Format Enhancement

```
┌─────────────────────────────────────────────────────────────┐
│                     OLD PROMPT (Before)                      │
├─────────────────────────────────────────────────────────────┤
│ You are Bulldog Buddy...                                    │
│                                                              │
│ Context: [handbook content]                                 │
│                                                              │
│ Question: What's the tuition?                               │
│                                                              │
│ Instructions:                                               │
│ - Answer based on context                                   │
│ - Be helpful                                                │
│                                                              │
│ Answer:                                                      │
└─────────────────────────────────────────────────────────────┘
                              │
                              ▼
                    RESPONSE (Compact):
                    "The tuition fee is $10,000 per 
                    semester for undergraduate students. 
                    This covers all course fees and 
                    materials. Payment options include..."
                    
                    ❌ No line breaks, hard to read


┌─────────────────────────────────────────────────────────────┐
│                     NEW PROMPT (After)                       │
├─────────────────────────────────────────────────────────────┤
│ You are Bulldog Buddy...                                    │
│                                                              │
│ Context: [handbook content]                                 │
│                                                              │
│ Question: What's the tuition?                               │
│                                                              │
│ Instructions:                                               │
│ - Answer based on context                                   │
│ - Be helpful                                                │
│                                                              │
│ FORMATTING RULES (IMPORTANT):                               │
│ - Use proper line breaks between paragraphs                 │
│ - For lists, use bullet points with proper spacing         │
│ - Add spacing after sentences for readability               │
│ - Structure your response with clear paragraphs             │
│ - Don't make the text too compact - add breathing room     │
│                                                              │
│ Answer:                                                      │
└─────────────────────────────────────────────────────────────┘
                              │
                              ▼
                    RESPONSE (Formatted):
                    "The tuition fee is $10,000 per semester 
                    for undergraduate students.
                    
                    This covers all course fees and materials. 
                    
                    Payment options include:
                    • Full payment upfront
                    • Semester installments
                    • Monthly payment plans..."
                    
                    ✅ Proper spacing, easy to read
```

## Cache vs No Cache Behavior

```
WITHOUT CACHE (Old System):
──────────────────────────────────────────────────
Q1: "What's the tuition?"
→ Retrieves Financial chunks
→ Stores in LLM context only

Q2: "What's the grading scale?"
→ Retrieves Grading chunks
→ LLM still has residual financial context in memory
→ ❌ May mix contexts in response


WITH CACHE (New System):
──────────────────────────────────────────────────
Q1: "What's the tuition?"
→ Retrieves Financial chunks
→ Stores in cache + LLM context

Q2: "What's the grading scale?"
→ Detects unrelated (0% keyword overlap)
→ CLEARS cache
→ Clears LLM context
→ Retrieves Grading chunks
→ Stores fresh in cache
→ ✅ Clean separation, no mixing
```

## Integration with Conversation Flow

```
┌─────────────────────────────────────────────────────────┐
│                   ask_question()                         │
├─────────────────────────────────────────────────────────┤
│                                                          │
│  1. Extract user info (if context manager available)    │
│  2. Detect if follow-up question                        │
│  3. Check for URLs (web scraping)                       │
│  4. Initialize database if needed                       │
│                                                          │
│  ┌────────────────────────────────────────┐            │
│  │  IF FOLLOW-UP:                          │            │
│  │  - Rewrite question with context        │            │
│  │  - Use conversational chain             │            │
│  │  - Update cache with retrieved chunks   │◄───NEW    │
│  └────────────────────────────────────────┘            │
│                                                          │
│  ┌────────────────────────────────────────┐            │
│  │  IF NEW TOPIC:                          │            │
│  │  - Check cache relatedness              │◄───NEW    │
│  │  - Clear if unrelated                   │◄───NEW    │
│  │  - Retrieve fresh chunks                │            │
│  │  - Update cache                         │◄───NEW    │
│  └────────────────────────────────────────┘            │
│                                                          │
│  5. Generate response with formatting rules             │
│  6. Store in conversation history                       │
│  7. Return result                                       │
│                                                          │
└─────────────────────────────────────────────────────────┘
```

## Memory Management

```
System Memory Components:

┌──────────────────────────────────────────┐
│  LangChain Conversation Memory           │
│  (10 message window)                     │
│  - User messages                         │
│  - Assistant responses                   │
└──────────────────────────────────────────┘
                │
                │ works with
                ▼
┌──────────────────────────────────────────┐
│  Conversation History List               │
│  (20 exchanges max)                      │
│  - Questions + answers                   │
│  - Timestamps                            │
└──────────────────────────────────────────┘
                │
                │ now synchronized with
                ▼
┌──────────────────────────────────────────┐
│  Retrieved Context Cache (NEW)           │
│  - Current query + chunks                │
│  - Previous query + chunks               │
│  - Timestamp                             │
└──────────────────────────────────────────┘

All three cleared together via:
clear_conversation_history()
```

## Legend

```
┌─────┐
│     │  Process/State
└─────┘

   ▼     Flow Direction

  ─►     Alternative Path

  │      Sequential Flow

  NEW    New Feature Added

  ❌     Problem/Incorrect

  ✅     Fixed/Correct
```
