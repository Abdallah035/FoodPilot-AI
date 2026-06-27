"use client";

import { motion } from "framer-motion";
import { Activity, Workflow, Phone } from "lucide-react";
import type { ChatMessage, AgentState, OrderSummary as OrderSummaryT, Nutrition } from "@/lib/types";
import { AGENT_ORDER } from "@/lib/agents-meta";
import { WorkflowTimeline } from "@/features/agents/workflow-timeline";
import { formatEGP, arabic } from "@/lib/utils";
import { t, toArabicDigits } from "@/lib/i18n";

/** Derive the most recent agent state + artifacts from the conversation. */
function deriveContext(messages: ChatMessage[]) {
  let agents: AgentState[] | null = null;
  let order: OrderSummaryT | null = null;
  let nutrition: { nutrition: Nutrition; meal: string } | null = null;

  for (const m of messages) {
    for (const b of m.blocks) {
      if (b.kind === "agents") agents = b.agents;
      if (b.kind === "order") order = b.order;
      if (b.kind === "nutrition") nutrition = { nutrition: b.nutrition, meal: b.meal };
    }
  }
  return { agents, order, nutrition };
}

export function RightPanel({ messages, className }: { messages: ChatMessage[]; className?: string }) {
  const { agents, order, nutrition } = deriveContext(messages);
  const idle = AGENT_ORDER.map((id) => ({ id, name: id, status: "idle" as const }));

  return (
    <aside className={className}>
      <div className="flex h-full flex-col gap-4 overflow-y-auto p-4 no-scrollbar">
        <div className="glass-strong rounded-3xl p-4">
          <div className="mb-3 flex items-center gap-2">
            <Workflow className="h-4 w-4 text-brand-500" />
            <h2 className="font-display text-sm font-semibold">{t.multiAgentPipeline}</h2>
          </div>
          <WorkflowTimeline agents={agents ?? idle} />
        </div>

        {nutrition && (
          <motion.div initial={{ opacity: 0, y: 8 }} animate={{ opacity: 1, y: 0 }} className="glass rounded-3xl p-4">
            <h3 className="mb-2 font-display text-sm font-semibold">{t.nutrition} · {nutrition.meal}</h3>
            <div className="space-y-1 text-sm">
              <Stat
                label={t.calories}
                value={
                  nutrition.nutrition.calories_per_meal != null
                    ? `${toArabicDigits(Math.round(nutrition.nutrition.calories_per_meal))} ${t.kcal}`
                    : "—"
                }
              />
              {nutrition.nutrition.quantity_grams != null && (
                <Stat label="الوزن" value={`${toArabicDigits(Math.round(nutrition.nutrition.quantity_grams))} جرام`} />
              )}
            </div>
          </motion.div>
        )}

        {order && (
          <motion.div initial={{ opacity: 0, y: 8 }} animate={{ opacity: 1, y: 0 }} className="glass rounded-3xl p-4">
            <h3 className="mb-2 font-display text-sm font-semibold">{t.orderSummary}</h3>
            <div className="space-y-1 text-sm">
              <Stat label={t.restaurant} value={order.restaurant} />
              <Stat label={t.meal} value={order.quantity > 1 ? `${order.meal} ×${arabic(order.quantity)}` : order.meal} />
              <Stat label={t.total} value={formatEGP(order.total)} accent />
            </div>
            {order.phone && (
              <a
                href={`tel:${order.phone.replace(/[^\d+]/g, "")}`}
                className="mt-3 inline-flex items-center gap-1.5 text-sm text-brand-600 dark:text-brand-300"
              >
                <Phone className="h-4 w-4" /> {order.phone}
              </a>
            )}
          </motion.div>
        )}

        {!order && !nutrition && (
          <div className="glass-subtle flex flex-col items-center gap-2 rounded-3xl p-6 text-center text-sm text-muted-foreground">
            <Activity className="h-6 w-6 text-brand-500/60" />
            تفاصيل المطعم والوجبة والطلب هتظهر هنا مع شغل الوكلاء.
          </div>
        )}
      </div>
    </aside>
  );
}

function Stat({ label, value, accent }: { label: string; value: string; accent?: boolean }) {
  return (
    <div className="flex items-center justify-between gap-2">
      <span className="text-muted-foreground">{label}</span>
      <span className={accent ? "font-display font-bold text-gradient" : "truncate font-medium"}>{value}</span>
    </div>
  );
}
