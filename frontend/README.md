# Episteme Frontend

Frontend for the Episteme decision-making workspace. Built with Next.js, React, and TypeScript.

## Quick Start

### 1. Install Dependencies

```bash
cd frontend
npm install
```

### 2. Configure Environment

The `.env.local` file is already set up with:
```
NEXT_PUBLIC_API_URL=http://localhost:8000/api
```

Update if your backend runs on a different port.

### 3. Run Development Server

```bash
npm run dev
```

Open [http://localhost:3000](http://localhost:3000)

### 4. Ensure Backend is Running

The frontend requires the Django backend to be running:

```bash
# In backend directory
python manage.py runserver
```

And Celery for async tasks:

```bash
celery -A config.celery_app worker -l info
```

## Project Structure

```
src/
├── app/
│   ├── layout.tsx          # Root layout
│   ├── page.tsx            # Landing page
│   ├── providers.tsx       # React Query provider
│   ├── globals.css         # Global styles
│   └── chat/
│       └── page.tsx        # Chat interface page
│
├── components/
│   ├── chat/
│   │   ├── ChatInterface.tsx      # Main chat component
│   │   ├── MessageList.tsx        # Message display
│   │   └── MessageInput.tsx       # Input with send
│   │
│   ├── structure/
│   │   ├── StructureSidebar.tsx   # Right sidebar
│   │   ├── SignalsList.tsx        # Extracted signals
│   │   ├── InquirySuggestions.tsx # Suggested inquiries
│   │   └── CaseCard.tsx           # Active case info
│   │
│   └── ui/
│       └── button.tsx             # Button component
│
└── lib/
    ├── api/
    │   ├── client.ts     # API client
    │   ├── chat.ts       # Chat endpoints
    │   ├── signals.ts    # Signal endpoints
    │   ├── cases.ts      # Case endpoints
    │   └── inquiries.ts  # Inquiry endpoints
    │
    ├── types/
    │   ├── chat.ts       # Chat types
    │   ├── signal.ts     # Signal types
    │   └── case.ts       # Case types
    │
    └── utils.ts          # Utility functions
```

## Features Implemented

### Phase 1: Chat + Structure Visibility

**Chat Interface:**
- Send messages to AI
- Receive AI responses (polling every 2s)
- Clean, professional message display
- Markdown rendering for AI responses

**Structure Sidebar:**
- Real-time signal extraction display
- Signal types with color coding
- Confidence scores
- Inquiry suggestions when patterns detected
- Case creation from chat
- Inquiry creation from suggestions

**Real-time Updates:**
- Messages poll every 2s
- Signals poll every 3s
- Inquiry suggestions poll every 5s
- Case/inquiry info polls every 5s

## Usage Flow

### 1. Start Chatting

1. Go to `/chat`
2. Thread created automatically
3. Start chatting naturally
4. Sidebar initially empty

### 2. See Structure Emerge

1. Chat about a decision: "I'm deciding between PostgreSQL and BigQuery"
2. Signals appear in sidebar:
   - "Decision: PostgreSQL vs BigQuery" (DecisionIntent)
   - Confidence scores shown
3. Continue chatting, more signals extracted
4. User sees progress happening

### 3. Create Case

1. When you have signals, "Create Case" button appears
2. Click to create case
3. Case appears in sidebar
4. Inquiry suggestions start appearing

### 4. Create Inquiry

1. When signal mentioned 3+ times, suggestion appears
2. "Create Inquiry" button shown
3. Click to promote signal to inquiry
4. Inquiry appears in case structure

## API Integration

All API calls go through the Django backend:

```typescript
// Chat
POST /api/chat/threads/                   # Create thread
POST /api/chat/threads/{id}/messages/     # Send message
GET /api/chat/messages/?thread={id}       # Get messages

// Signals
GET /api/signals/?thread_id={id}          # Get signals for thread
GET /api/signals/promotion_suggestions/   # Get inquiry suggestions

// Cases
POST /api/cases/                          # Create case
GET /api/cases/{id}/                      # Get case details

// Inquiries  
POST /api/signals/{id}/promote_to_inquiry/  # Create inquiry from signal
GET /api/inquiries/?case={id}             # Get inquiries for case
```

## Component Details

### ChatInterface

Main chat component with message list and input.

Features:
- Optimistic updates (user message appears immediately)
- Polling for AI responses
- Auto-scroll to latest message
- Loading states

### StructureSidebar

Shows extracted structure from chat.

Features:
- Real-time signal updates
- Inquiry suggestions with context
- Case creation
- Active case display

### SignalsList

Displays extracted signals with:
- Color-coded type badges
- Confidence percentages
- Full signal text
- Scrollable list

### InquirySuggestions

Shows suggested inquiries with:
- Suggested title
- Elevation reason (repetition, etc.)
- Similar count (how many times mentioned)
- Create inquiry action

## Styling

**Design system:**
- Clean, professional (not gamified)
- Text-first (minimal icons)
- Neutral grays with blue accent
- Clear typography hierarchy
- Plenty of whitespace

**Colors:**
- Signals: Color-coded by type (subtle, not loud)
- Actions: Blue (primary)
- Text: Gray scale (readable)

## Development

### Building

```bash
npm run build
```

### Production

```bash
npm run start
```

### Linting

```bash
npm run lint
```

## Next Steps

### Phase 2: Brief Editor

Add document editing:
- Rich text editor (Tiptap)
- Citation autocomplete
- Save/load briefs
- View AI-generated docs

### Phase 3: Workspace

Add full workspace:
- Document tree navigation
- Multi-document view
- Citation graph visualization

### Phase 4: AI Generation UI

Add generation controls:
- Request research button
- Start debate interface
- Request critique button
- Generation progress

## Troubleshooting

### Backend not responding

Ensure Django is running on port 8000:
```bash
cd backend
python manage.py runserver
```

### Signals not appearing

Check Celery is running for async signal extraction:
```bash
celery -A config.celery_app worker -l info
```

### CORS errors

Backend has CORS configured for `localhost:3000`. If using different port, update:
```python
# backend/config/settings/base.py
CORS_ALLOWED_ORIGINS = [
    'http://localhost:3000',  # Add your frontend URL
]
```

## Tech Stack

- **Next.js 14+** - React framework
- **TypeScript** - Type safety
- **Tailwind CSS** - Styling
- **React Query** - Server state
- **React Markdown** - MD rendering
- **Zustand** - Client state (ready for use)

## Files Created

**Configuration (7):**
- package.json, tsconfig.json, next.config.js
- tailwind.config.ts, postcss.config.js
- .env.local, .gitignore

**API Layer (5):**
- lib/api/client.ts - API client
- lib/api/chat.ts - Chat endpoints
- lib/api/signals.ts - Signal endpoints
- lib/api/cases.ts - Case endpoints
- lib/api/inquiries.ts - Inquiry endpoints

**Types (3):**
- lib/types/chat.ts
- lib/types/signal.ts
- lib/types/case.ts

**Components (8):**
- components/chat/ChatInterface.tsx
- components/chat/MessageList.tsx
- components/chat/MessageInput.tsx
- components/structure/StructureSidebar.tsx
- components/structure/SignalsList.tsx
- components/structure/InquirySuggestions.tsx
- components/structure/CaseCard.tsx
- components/ui/button.tsx

**Pages/Layout (4):**
- app/layout.tsx
- app/page.tsx
- app/providers.tsx
- app/chat/page.tsx

**Utils (1):**
- lib/utils.ts

**Total: 28 files**

## The Experience

**What users see:**

1. **Land on home page** - Clean welcome, "Start Chatting" button

2. **Enter chat** - Professional chat interface, empty sidebar

3. **Start chatting** - Think naturally about decision

4. **See signals appear** - Sidebar updates in real-time:
   - "Claim: PostgreSQL is faster" (85% confidence)
   - "Assumption: Performance matters" (70% confidence)
   - "Question: What's the cost?" (90% confidence)

5. **Create case** - When ready, click "Create Case"

6. **See inquiries suggested** - "Is PostgreSQL fast enough?" (mentioned 3x)

7. **Create inquiry** - Click to promote

8. **Structure is visible** - Progress is concrete, not abstract

**Value delivered:**
- Thinking is captured (signals)
- Structure emerges naturally (inquiries)
- Progress is visible (counts, suggestions)
- Professional tool feel (not game-like)

Ready to run with `npm install && npm run dev`!
