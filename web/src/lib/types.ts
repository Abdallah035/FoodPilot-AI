/**
 * Domain types for Food Pilot — mirror the backend contracts in:
 *   - agent1_scout/state.py        (Restaurant, Deal, OrderPayload, interrupt payloads)
 *   - order_finalizer/state.py     (VerifiedPromo, FinalizerState)
 *   - pipeline.py                  (rag_enrichment shape)
 *
 * Keep these in sync with the Python side. The FastAPI bridge (server/app.py)
 * serializes these shapes over SSE.
 */

export interface Coordinates {
  lat: number;
  lon: number;
}

/** Restaurant as returned by Scout (Apify + scoring). */
export interface Restaurant {
  id: string;
  name: string;
  address?: string;
  phone?: string;
  coordinates?: Coordinates;
  rating: number; // 0–5
  reviews?: number;
  price_level?: string | null; // "$" | "$$" | "$$$"
  distance_km?: number | null;
  score?: number | null; // 0–1
  reason?: string | null;
  cuisine?: string;
  image?: string;
  open?: boolean;
  favorite?: boolean;
}

/** A menu item / deal discovered via Tavily. */
export interface Deal {
  id: string;
  item_name: string;
  price: string | number;
  currency: string; // "EGP"
  deal_description?: string;
  source_url?: string;
  quantity?: number;
  portion?: string;
  discount?: string; // e.g. "-20%"
  image?: string;
  calories?: number;
  ingredients?: string[];
}

/**
 * Nutrition for a meal — mirrors what the RAG/Food agent ACTUALLY returns
 * (RAG/Rag.py `calculate_order_calories`): calories only, plus ingredients
 * from the RAG dish data. No macros/health-score are produced by the backend.
 */
export interface Nutrition {
  calories_per_meal: number | null; // total for the chosen quantity
  calories_per_100g?: number | null;
  quantity_grams?: number | null;
  ingredients?: string[];
  found: boolean;
  source?: "rag" | "web" | null; // where calories came from
}

export interface VerifiedPromo {
  code: string;
  discount_type: "percentage" | "flat";
  value: number;
  required_platform?: string; // "Talabat" | "Elmenus" | "Direct"
}

/** Final order summary assembled from the finalizer state. */
export interface OrderSummary {
  restaurant: string;
  phone?: string; // so the user can CALL the restaurant to order
  address?: string;
  meal: string;
  quantity: number;
  unit_price: number; // price of one item
  promo?: VerifiedPromo | null;
  subtotal: number; // unit_price × quantity (before promo)
  discount: number;
  total: number; // final price from the finalizer
  currency: string;
  savings: number;
  receipt?: string; // markdown receipt from the Order agent
}

// --------------------------------------------------------------------------- //
// Multi-agent workflow visualization
// --------------------------------------------------------------------------- //
export type AgentId = "orchestrator" | "scout" | "food" | "order";

export type AgentStatus = "idle" | "active" | "waiting" | "done" | "error";

export interface AgentState {
  id: AgentId;
  name: string;
  status: AgentStatus;
  step?: string; // human-readable current step
  tool?: string; // current tool, e.g. "Apify Google Maps"
  progress?: number; // 0–1
}

/** A single thinking/progress line shown while agents work. */
export interface ThinkingStep {
  id: string;
  agent: AgentId;
  label: string; // "Scout searching Google Maps…"
  done?: boolean;
}

// --------------------------------------------------------------------------- //
// Human-in-the-loop interrupts (mirror main.py `_print_interrupt`)
// --------------------------------------------------------------------------- //
export type InterruptType = "select_restaurant" | "select_deal" | "no_deals";

export interface RestaurantInterrupt {
  type: "select_restaurant";
  prompt: string;
  options: Restaurant[];
}

export interface DealInterrupt {
  type: "select_deal";
  prompt: string;
  options: Deal[];
}

export interface NoDealsInterrupt {
  type: "no_deals";
  prompt: string;
  restaurant: Restaurant;
  options: { index: number; label: string }[];
}

export type Interrupt = RestaurantInterrupt | DealInterrupt | NoDealsInterrupt;

// --------------------------------------------------------------------------- //
// Chat message model — messages can carry rich, typed content blocks
// --------------------------------------------------------------------------- //
export type Role = "user" | "assistant";

export type MessageBlock =
  | { kind: "markdown"; text: string }
  | { kind: "agents"; agents: AgentState[]; thinking: ThinkingStep[] }
  | { kind: "restaurants"; interrupt: RestaurantInterrupt }
  | { kind: "deals"; interrupt: DealInterrupt }
  | { kind: "no_deals"; interrupt: NoDealsInterrupt }
  | { kind: "nutrition"; nutrition: Nutrition; meal: string }
  | { kind: "order"; order: OrderSummary };

export interface ChatMessage {
  id: string;
  role: Role;
  blocks: MessageBlock[];
  streaming?: boolean; // assistant message still streaming
  createdAt: number;
}

export interface Conversation {
  id: string;
  title: string;
  updatedAt: number;
  messages: ChatMessage[];
}

// --------------------------------------------------------------------------- //
// SSE event protocol between FastAPI bridge and the client
// --------------------------------------------------------------------------- //
export type AgentEvent =
  | { type: "token"; text: string }
  | { type: "agents"; agents: AgentState[] }
  | { type: "thinking"; step: ThinkingStep }
  | { type: "interrupt"; interrupt: Interrupt }
  | { type: "nutrition"; nutrition: Nutrition; meal: string }
  | { type: "order"; order: OrderSummary }
  | { type: "done" }
  | { type: "error"; message: string };

export interface SuggestionChip {
  emoji: string;
  label: string;
  query: string;
}
