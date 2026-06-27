"use client";

import { Menu, Moon, Sun, PanelLeftOpen } from "lucide-react";
import { Logo } from "@/components/brand/logo";
import { Button } from "@/components/ui/button";
import { Badge } from "@/components/ui/badge";
import { useTheme } from "@/components/theme-provider";
import { AGENT_META, AGENT_ORDER } from "@/lib/agents-meta";
import { LocationField } from "@/features/chat/location-field";
import type { AgentState } from "@/lib/types";
import { t } from "@/lib/i18n";

interface HeaderProps {
  agents?: AgentState[];
  location: string;
  onLocationChange: (v: string) => void;
  showLocation?: boolean;
  onToggleSidebar: () => void;
  onToggleRightPanel: () => void;
}

export function Header({
  agents,
  location,
  onLocationChange,
  showLocation,
  onToggleSidebar,
  onToggleRightPanel,
}: HeaderProps) {
  const { theme, toggle } = useTheme();
  const anyWorking = (agents?.filter((a) => a.status === "active").length ?? 0) > 0;

  return (
    <header className="sticky top-0 z-20 flex items-center justify-between gap-3 px-4 py-3 sm:px-6">
      <div className="glass-strong flex w-full items-center justify-between gap-3 rounded-2xl px-3 py-2">
        <div className="flex min-w-0 items-center gap-2">
          <Button size="icon-sm" variant="ghost" aria-label="القائمة" onClick={onToggleSidebar} className="lg:hidden">
            <Menu className="h-5 w-5" />
          </Button>
          <Logo size={30} showWord={false} className="lg:hidden" />

          <div className="hidden items-center gap-2 lg:flex">
            <Badge variant={anyWorking ? "brand" : "success"}>
              <span className="relative flex h-2 w-2">
                {anyWorking && <span className="absolute inline-flex h-full w-full animate-ping rounded-full bg-brand-500 opacity-70" />}
                <span className={`relative inline-flex h-2 w-2 rounded-full ${anyWorking ? "bg-brand-500" : "bg-leaf-500"}`} />
              </span>
              {anyWorking ? t.agentsWorking : t.ready}
            </Badge>

            <div className="flex items-center gap-1 pr-1">
              {AGENT_ORDER.map((id) => {
                const meta = AGENT_META[id];
                const on = agents?.find((x) => x.id === id)?.status !== "idle" && !!agents?.find((x) => x.id === id);
                return (
                  <span
                    key={id}
                    title={`${meta.name} — ${meta.role}`}
                    className={`grid h-6 w-6 place-items-center rounded-lg bg-gradient-to-br ${meta.gradient} text-white transition-opacity ${on ? "opacity-100" : "opacity-35"}`}
                  >
                    <meta.icon className="h-3.5 w-3.5" />
                  </span>
                );
              })}
            </div>
          </div>
        </div>

        <div className="flex min-w-0 items-center gap-1.5">
          {showLocation && (
            <LocationField value={location} onChange={onLocationChange} compact className="hidden max-w-[220px] md:inline-flex" />
          )}
          <Button size="icon-sm" variant="ghost" aria-label="تبديل الوضع" onClick={toggle}>
            {theme === "dark" ? <Sun className="h-5 w-5" /> : <Moon className="h-5 w-5" />}
          </Button>
          <Button size="icon-sm" variant="ghost" aria-label="لوحة سير العمل" onClick={onToggleRightPanel} className="hidden xl:inline-flex">
            <PanelLeftOpen className="h-5 w-5" />
          </Button>
        </div>
      </div>
    </header>
  );
}
