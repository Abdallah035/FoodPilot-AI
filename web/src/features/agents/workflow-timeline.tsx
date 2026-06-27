"use client";

import { motion } from "framer-motion";
import type { AgentState } from "@/lib/types";
import { AGENT_META, AGENT_ORDER } from "@/lib/agents-meta";
import { AgentAvatar } from "./agent-card";
import { StatusIndicator } from "./status-indicator";

/** Vertical timeline of the agent pipeline — used in the right panel. */
export function WorkflowTimeline({ agents }: { agents: AgentState[] }) {
  const byId = new Map(agents.map((a) => [a.id, a]));
  return (
    <ol className="relative space-y-1">
      {AGENT_ORDER.map((id, i) => {
        const agent = byId.get(id) ?? { id, name: AGENT_META[id].name, status: "idle" as const };
        const meta = AGENT_META[id];
        const isLast = i === AGENT_ORDER.length - 1;
        return (
          <li key={id} className="relative flex gap-3 pb-3">
            {!isLast && (
              <span
                className="absolute left-[21px] top-11 h-[calc(100%-1.5rem)] w-0.5 rounded-full"
                style={{
                  background:
                    agent.status === "done" ? meta.accent : "hsl(var(--border))",
                }}
              />
            )}
            <AgentAvatar id={id} status={agent.status} size={44} />
            <motion.div layout className="min-w-0 flex-1 pt-0.5">
              <div className="flex items-center justify-between gap-2">
                <span className="font-display text-sm font-semibold">{meta.name}</span>
                <StatusIndicator status={agent.status} />
              </div>
              <p className="truncate text-xs text-muted-foreground">{agent.step ?? meta.role}</p>
              {agent.tool && agent.status === "active" && (
                <p className="mt-0.5 text-[11px] text-brand-600 dark:text-brand-300">⚙ {agent.tool}</p>
              )}
            </motion.div>
          </li>
        );
      })}
    </ol>
  );
}
