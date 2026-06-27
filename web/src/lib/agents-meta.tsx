import { Compass, Apple, Receipt, Sparkles, type LucideIcon } from "lucide-react";
import type { AgentId } from "./types";
import { t } from "./i18n";

export interface AgentMeta {
  id: AgentId;
  name: string;
  role: string;
  icon: LucideIcon;
  emoji: string;
  /** Tailwind gradient classes for the avatar. */
  gradient: string;
  /** Accent color (CSS) for rings/progress. */
  accent: string;
}

export const AGENT_META: Record<AgentId, AgentMeta> = {
  orchestrator: {
    id: "orchestrator",
    name: t.agents.orchestrator.name,
    role: t.agents.orchestrator.role,
    icon: Sparkles,
    emoji: "🧠",
    gradient: "from-violet-500 to-fuchsia-500",
    accent: "#a855f7",
  },
  scout: {
    id: "scout",
    name: t.agents.scout.name,
    role: t.agents.scout.role,
    icon: Compass,
    emoji: "🧭",
    gradient: "from-brand-500 to-sun-500",
    accent: "#FF7A00",
  },
  food: {
    id: "food",
    name: t.agents.food.name,
    role: t.agents.food.role,
    icon: Apple,
    emoji: "🥗",
    gradient: "from-leaf-500 to-emerald-400",
    accent: "#22C55E",
  },
  order: {
    id: "order",
    name: t.agents.order.name,
    role: t.agents.order.role,
    icon: Receipt,
    emoji: "🧾",
    gradient: "from-sky-500 to-cyan-400",
    accent: "#0ea5e9",
  },
};

export const AGENT_ORDER: AgentId[] = ["orchestrator", "scout", "food", "order"];
