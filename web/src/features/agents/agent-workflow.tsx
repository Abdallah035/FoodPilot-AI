"use client";

import { motion } from "framer-motion";
import { ChevronRight } from "lucide-react";
import type { AgentState, ThinkingStep } from "@/lib/types";
import { AGENT_META, AGENT_ORDER } from "@/lib/agents-meta";
import { AgentAvatar } from "./agent-card";
import { StatusIndicator } from "./status-indicator";
import { ThinkingAnimation } from "./thinking-animation";
import { cn } from "@/lib/utils";
import { t } from "@/lib/i18n";

/**
 * The signature multi-agent visualization: a horizontal pipeline of the four
 * agents with animated connectors that "flow" while work is in progress, plus
 * the live thinking-step feed beneath.
 */
export function AgentWorkflow({
  agents,
  thinking,
}: {
  agents: AgentState[];
  thinking: ThinkingStep[];
}) {
  const byId = new Map(agents.map((a) => [a.id, a]));
  const activeAgent = agents.find((a) => a.status === "active");

  return (
    <motion.div
      layout
      initial={{ opacity: 0, y: 8 }}
      animate={{ opacity: 1, y: 0 }}
      className="glass-strong rounded-3xl p-4 sm:p-5"
    >
      <div className="mb-4 flex items-center justify-between">
        <div className="flex items-center gap-2">
          <span className="relative flex h-2 w-2">
            <span className="absolute inline-flex h-full w-full animate-ping rounded-full bg-brand-500 opacity-70" />
            <span className="relative inline-flex h-2 w-2 rounded-full bg-brand-500" />
          </span>
          <span className="font-display text-sm font-semibold">
            {activeAgent ? t.agentWorking(AGENT_META[activeAgent.id].name) : t.agentsCollaborating}
          </span>
        </div>
        <span className="text-[11px] text-muted-foreground">{t.multiAgentPipeline}</span>
      </div>

      {/* Pipeline row */}
      <div className="flex items-stretch gap-1 overflow-x-auto no-scrollbar pb-1">
        {AGENT_ORDER.map((id, i) => {
          const agent = byId.get(id) ?? { id, name: AGENT_META[id].name, status: "idle" as const };
          const meta = AGENT_META[id];
          const isLast = i === AGENT_ORDER.length - 1;
          const nextActive =
            byId.get(AGENT_ORDER[i + 1])?.status && byId.get(AGENT_ORDER[i + 1])?.status !== "idle";
          const flowing = agent.status === "active" || (agent.status === "done" && nextActive);
          return (
            <div key={id} className="flex min-w-[88px] flex-1 items-center">
              <div className="flex w-full flex-col items-center gap-1.5 text-center">
                <AgentAvatar id={id} status={agent.status} />
                <span className="text-[11px] font-medium leading-tight">{meta.name}</span>
                <StatusIndicator status={agent.status} className="text-[10px]" />
              </div>

              {!isLast && (
                <div className="relative mx-0.5 hidden h-0.5 flex-1 sm:block">
                  <div className="absolute inset-0 rounded-full bg-border" />
                  {flowing && (
                    <motion.div
                      className="absolute inset-y-0 left-0 rounded-full"
                      style={{ background: `linear-gradient(90deg, ${meta.accent}, ${AGENT_META[AGENT_ORDER[i + 1]].accent})` }}
                      initial={{ width: "0%" }}
                      animate={{ width: "100%" }}
                      transition={{ duration: 1.2, repeat: Infinity, ease: "easeInOut" }}
                    />
                  )}
                </div>
              )}
              {!isLast && (
                <ChevronRight className={cn("h-4 w-4 shrink-0 sm:hidden", flowing ? "text-brand-500" : "text-border")} />
              )}
            </div>
          );
        })}
      </div>

      {/* Live thinking feed */}
      {thinking.length > 0 && (
        <div className="mt-4 rounded-2xl bg-surface/60 p-3">
          <ThinkingAnimation steps={thinking} />
        </div>
      )}
    </motion.div>
  );
}
