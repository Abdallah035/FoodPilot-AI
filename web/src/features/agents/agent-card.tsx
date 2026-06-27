"use client";

import { motion } from "framer-motion";
import { Wrench } from "lucide-react";
import type { AgentState } from "@/lib/types";
import { AGENT_META } from "@/lib/agents-meta";
import { StatusIndicator } from "./status-indicator";
import { cn } from "@/lib/utils";

export function AgentAvatar({
  id,
  status,
  size = 44,
}: {
  id: AgentState["id"];
  status: AgentState["status"];
  size?: number;
}) {
  const meta = AGENT_META[id];
  const Icon = meta.icon;
  const active = status === "active";
  return (
    <div className="relative grid place-items-center" style={{ width: size, height: size }}>
      {active && (
        <span
          className="absolute inset-0 rounded-2xl animate-pulse-ring"
          style={{ boxShadow: `0 0 0 2px ${meta.accent}55` }}
        />
      )}
      <div
        className={cn(
          "grid h-full w-full place-items-center rounded-2xl bg-gradient-to-br text-white shadow-soft transition-transform",
          meta.gradient,
          active && "scale-105",
          status === "idle" && "opacity-40 grayscale"
        )}
      >
        <Icon className="h-1/2 w-1/2" />
      </div>
    </div>
  );
}

export function AgentCard({ agent, compact }: { agent: AgentState; compact?: boolean }) {
  const meta = AGENT_META[agent.id];
  return (
    <motion.div
      layout
      className={cn(
        "glass flex items-center gap-3 rounded-2xl p-3 transition-all",
        agent.status === "active" && "ring-1 ring-brand-500/40"
      )}
    >
      <AgentAvatar id={agent.id} status={agent.status} size={compact ? 38 : 44} />
      <div className="min-w-0 flex-1">
        <div className="flex items-center justify-between gap-2">
          <span className="truncate font-display text-sm font-semibold">{meta.name}</span>
          <StatusIndicator status={agent.status} />
        </div>
        <p className="truncate text-xs text-muted-foreground">
          {agent.step ?? meta.role}
        </p>
        {agent.tool && agent.status === "active" && (
          <p className="mt-0.5 inline-flex items-center gap-1 text-[11px] text-brand-600 dark:text-brand-300">
            <Wrench className="h-3 w-3" /> {agent.tool}
          </p>
        )}
        {typeof agent.progress === "number" && agent.status === "active" && (
          <div className="mt-1.5 h-1 overflow-hidden rounded-full bg-muted">
            <motion.div
              className="h-full rounded-full"
              style={{ backgroundColor: meta.accent }}
              animate={{ width: `${Math.round((agent.progress ?? 0) * 100)}%` }}
              transition={{ ease: "easeOut" }}
            />
          </div>
        )}
      </div>
    </motion.div>
  );
}
