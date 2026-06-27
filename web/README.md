# Food Pilot — Web UI 🍔✈️

A premium, multi-agent **AI Food Concierge** interface for the Food Pilot agents.
Built to feel like a blend of ChatGPT, Perplexity, Apple Intelligence, Uber Eats
and Notion AI — not a generic chatbot.

> Discover restaurants → pick one → choose a deal → see nutrition → confirm your
> order, with four AI agents visibly collaborating the whole way.

---

## ✨ Highlights

- **Multi-agent workflow visualization** — an animated pipeline (Orchestrator →
  Scout → Food → Order) with live status, current tool, progress, and a
  streaming "thinking" feed.
- **Human-in-the-loop, fully clickable** — Scout's two interrupts render as
  beautiful **restaurant** and **deal** selection cards. Quantity uses a stepper;
  users never type numbers.
- **Rich content blocks** — restaurant cards, deal cards, a nutrition dashboard
  (rings + macro bars), and a checkout-style order summary.
- **Streaming assistant messages** with markdown, typing indicator, and caret.
- **Landing hero** — animated logo, rotating placeholders, suggestion chips that
  send instantly.
- **Glassmorphism design system**, soft shadows, gradients, micro-interactions,
  full **dark mode**, and a responsive layout (sidebar → drawer on mobile).
- **Accessible** — keyboard nav, ARIA labels, focus rings, reduced-motion support.

---

## 🧱 Tech stack

React 18 · Next.js 14 (App Router) · TypeScript (strict) · Tailwind CSS ·
Framer Motion · lucide-react · react-markdown. No inline styles; component-driven.

---

## 🚀 Getting started

```bash
cd web
npm install
cp .env.example .env.local   # optional
npm run dev                  # http://localhost:3000
```

By default the UI runs against a **scripted mock agent flow** — a complete,
runnable demo with no backend required (`NEXT_PUBLIC_USE_MOCK=true`).

### Connect to the live agents

Run the FastAPI bridge (from the repo root) and flip one env flag:

```bash
# repo root — starts the bridge over the real LangGraph pipeline
uv run uvicorn server.app:app --reload --port 8000
```

```env
# web/.env.local
NEXT_PUBLIC_USE_MOCK=false
NEXT_PUBLIC_API_BASE=http://localhost:8000
```

The UI talks SSE to the bridge via a Next.js rewrite (`/api/agent/*`).

### Full stack with Podman / Docker

```bash
podman compose up --build       # bridge :8000 + web :3000
```

---

## 🗂 Architecture

The UI never touches transport details. Everything flows through one seam:

```
SearchHero / Conversation
        │  user query / selection
        ▼
   useChat()  ──>  agentClient  ──┬─ MockAgentClient  (scripted demo)
   (state machine)                └─ LiveAgentClient  (SSE → FastAPI bridge)
        │  AgentEvent stream
        ▼
   typed MessageBlocks ──> MessageBubble renders each block kind
```

- **`useChat`** ([src/hooks/use-chat.ts](src/hooks/use-chat.ts)) folds the event
  stream (`token`, `agents`, `thinking`, `interrupt`, `nutrition`, `order`,
  `done`) into a single live assistant message of typed content blocks.
- **`agentClient`** ([src/lib/agent-client.ts](src/lib/agent-client.ts)) is the
  integration seam. Both implementations expose the same async-generator API.
- **Types** ([src/lib/types.ts](src/lib/types.ts)) mirror the Python contracts in
  `agent1_scout/state.py`, `order_finalizer/state.py`, and `pipeline.py`.

### Folder structure

```
web/src/
  app/                     # Next.js App Router (layout, page, globals.css)
  components/
    brand/                 # Logo / wordmark
    ui/                    # Button, Card, Badge, Skeleton, Rating, Markdown
    theme-provider.tsx     # dark-mode context
  features/
    agents/                # AgentWorkflow, AgentCard, WorkflowTimeline,
                           # ThinkingAnimation, StatusIndicator
    cards/                 # RestaurantCard, DealCard, NutritionCard, OrderSummary
    chat/                  # SearchHero, Conversation, MessageBubble, TypingBubble,
                           # InputBar, PromptSuggestions, selection-blocks (HITL)
    layout/                # ChatLayout, Sidebar, Header, RightPanel, SettingsDialog
  hooks/use-chat.ts        # conversation state machine
  lib/                     # types, utils, agent-client, mock-data, agents-meta
```

---

## 🎨 Design system

- **Brand:** orange `#FF7A00` → yellow `#FFB800` gradients, green for healthy.
- **Tokens** are CSS variables in [globals.css](src/app/globals.css) (light/dark),
  surfaced through [tailwind.config.ts](tailwind.config.ts).
- **Glass utilities:** `.glass`, `.glass-strong`, `.glass-subtle`.
- **Helpers:** `.text-gradient`, `.focus-ring`, `.skeleton`, custom keyframes
  (`fade-up`, `pulse-ring`, `shimmer`, `gradient-pan`, `blink`).

---

## 🔌 Backend contract (SSE `AgentEvent`)

The bridge (`server/app.py`) streams newline-delimited SSE frames:

```
data: {"type":"token","text":"…"}
data: {"type":"agents","agents":[{"id":"scout","name":"Scout","status":"active",...}]}
data: {"type":"thinking","step":{"id":"…","agent":"scout","label":"…","done":false}}
data: {"type":"interrupt","interrupt":{"type":"select_restaurant","options":[…]}}
data: {"type":"nutrition","nutrition":{…},"meal":"…"}
data: {"type":"order","order":{…}}
data: {"type":"done"}
data: [DONE]
```

Resume a paused (HITL) run by POSTing the user's choice to `/resume`:

```json
{ "thread_id": "…", "resume": { "kind": "restaurant", "index": 0 } }
{ "thread_id": "…", "resume": { "kind": "deal", "index": 2, "quantity": 1 } }
```

See [src/lib/types.ts](src/lib/types.ts) for the authoritative shapes.

---

## 📜 Scripts

| Command             | Description                    |
| ------------------- | ------------------------------ |
| `npm run dev`       | Dev server                     |
| `npm run build`     | Production build               |
| `npm run start`     | Serve the production build     |
| `npm run typecheck` | `tsc --noEmit` (strict)        |
| `npm run lint`      | Next.js lint                   |
