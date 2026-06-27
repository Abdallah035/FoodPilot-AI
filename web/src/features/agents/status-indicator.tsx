"use client";

import { cn } from "@/lib/utils";
import type { AgentStatus } from "@/lib/types";
import { t } from "@/lib/i18n";

const STATUS_STYLES: Record<AgentStatus, { dot: string; label: string; text: string }> = {
  idle: { dot: "bg-muted-foreground/40", label: t.status.idle, text: "text-muted-foreground" },
  active: { dot: "bg-brand-500", label: t.status.active, text: "text-brand-600 dark:text-brand-300" },
  waiting: { dot: "bg-sun-500", label: t.status.waiting, text: "text-sun-600 dark:text-sun-400" },
  done: { dot: "bg-leaf-500", label: t.status.done, text: "text-leaf-600 dark:text-leaf-400" },
  error: { dot: "bg-red-500", label: t.status.error, text: "text-red-500" },
};

export function StatusIndicator({
  status,
  label,
  className,
}: {
  status: AgentStatus;
  label?: string;
  className?: string;
}) {
  const s = STATUS_STYLES[status];
  return (
    <span className={cn("inline-flex items-center gap-1.5 text-xs font-medium", s.text, className)}>
      <span className="relative flex h-2 w-2">
        {(status === "active" || status === "waiting") && (
          <span className={cn("absolute inline-flex h-full w-full rounded-full opacity-70 animate-ping", s.dot)} />
        )}
        <span className={cn("relative inline-flex h-2 w-2 rounded-full", s.dot)} />
      </span>
      {label ?? s.label}
    </span>
  );
}
