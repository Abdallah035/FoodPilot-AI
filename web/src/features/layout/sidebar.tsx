"use client";

import * as React from "react";
import { Plus, MessageSquare, Settings, Search, PanelRightClose } from "lucide-react";
import { Logo } from "@/components/brand/logo";
import { Button } from "@/components/ui/button";
import { SAMPLE_HISTORY } from "@/lib/suggestions";
import { cn, arabic } from "@/lib/utils";
import { t } from "@/lib/i18n";

interface SidebarProps {
  onNewChat: () => void;
  onOpenSettings: () => void;
  onClose?: () => void;
  className?: string;
}

function timeAgo(ts: number): string {
  const mins = Math.round((Date.now() - ts) / 60000);
  if (mins < 60) return `${arabic(mins)} د`;
  const hrs = Math.round(mins / 60);
  if (hrs < 24) return `${arabic(hrs)} س`;
  return `${arabic(Math.round(hrs / 24))} ي`;
}

export function Sidebar({ onNewChat, onOpenSettings, onClose, className }: SidebarProps) {
  const [active, setActive] = React.useState<string | null>(null);
  const [query, setQuery] = React.useState("");
  // Relative times depend on Date.now(), which differs between the server render
  // and the client. Only show them after mount to avoid a hydration mismatch.
  const [mounted, setMounted] = React.useState(false);
  React.useEffect(() => setMounted(true), []);

  const history = SAMPLE_HISTORY.filter((c) => c.title.includes(query));

  return (
    <aside className={cn("flex h-full w-72 flex-col gap-4 p-4", className)}>
      <div className="flex items-center justify-between">
        <Logo size={34} />
        {onClose && (
          <Button size="icon-sm" variant="ghost" aria-label="إغلاق القائمة" onClick={onClose}>
            <PanelRightClose className="h-5 w-5" />
          </Button>
        )}
      </div>

      <Button onClick={onNewChat} className="w-full justify-center">
        <Plus className="h-4 w-4" /> {t.newChat}
      </Button>

      {/* Search history */}
      <div className="glass-subtle flex items-center gap-2 rounded-full px-3 py-2">
        <Search className="h-4 w-4 text-muted-foreground" />
        <input
          value={query}
          onChange={(e) => setQuery(e.target.value)}
          placeholder={t.searchChats}
          className="w-full bg-transparent text-sm outline-none placeholder:text-muted-foreground"
          aria-label={t.searchChats}
        />
      </div>

      {/* History list */}
      <nav className="flex-1 space-y-1 overflow-y-auto no-scrollbar" aria-label="سجل المحادثات">
        <p className="px-2 py-1 text-xs font-medium text-muted-foreground">{t.recent}</p>
        {history.map((c) => (
          <button
            key={c.id}
            onClick={() => setActive(c.id)}
            className={cn(
              "group flex w-full items-center gap-2.5 rounded-xl px-2.5 py-2 text-right text-sm transition-colors focus-ring",
              active === c.id ? "bg-brand-gradient-soft text-foreground" : "hover:bg-muted/60"
            )}
          >
            <MessageSquare className="h-4 w-4 shrink-0 text-muted-foreground" />
            <span className="flex-1 truncate">{c.title}</span>
            <span className="shrink-0 text-[10px] text-muted-foreground">
              {mounted ? timeAgo(c.updatedAt) : ""}
            </span>
          </button>
        ))}
        {history.length === 0 && <p className="px-2 py-4 text-center text-sm text-muted-foreground">{t.noMatches}</p>}
      </nav>

      <Button variant="ghost" className="w-full justify-start" onClick={onOpenSettings}>
        <Settings className="h-4 w-4" /> {t.settings}
      </Button>
    </aside>
  );
}
