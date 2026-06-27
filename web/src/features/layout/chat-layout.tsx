"use client";

import * as React from "react";
import { AnimatePresence, motion } from "framer-motion";
import { useChat } from "@/hooks/use-chat";
import { useLocation } from "@/hooks/use-location";
import { Sidebar } from "./sidebar";
import { Header } from "./header";
import { RightPanel } from "./right-panel";
import { SettingsDialog } from "./settings-dialog";
import { SearchHero } from "@/features/chat/search-hero";
import { Conversation } from "@/features/chat/conversation";
import { InputBar } from "@/features/chat/input-bar";
import type { AgentState } from "@/lib/types";
import { t } from "@/lib/i18n";

/** Latest agent snapshot across the whole conversation (for the header). */
function latestAgents(messages: ReturnType<typeof useChat>["messages"]): AgentState[] | undefined {
  let agents: AgentState[] | undefined;
  for (const m of messages) for (const b of m.blocks) if (b.kind === "agents") agents = b.agents;
  return agents;
}

export function ChatLayout() {
  const chat = useChat();
  const [location, setLocation] = useLocation();
  const [drawerOpen, setDrawerOpen] = React.useState(false);
  const [rightOpen, setRightOpen] = React.useState(true);
  const [settingsOpen, setSettingsOpen] = React.useState(false);

  const agents = latestAgents(chat.messages);
  const send = React.useCallback((text: string) => chat.send(text, location), [chat, location]);

  return (
    <div className="flex h-[100dvh] overflow-hidden">
      {/* Desktop sidebar */}
      <div className="hidden lg:block">
        <div className="glass-strong m-3 h-[calc(100dvh-1.5rem)] rounded-3xl">
          <Sidebar onNewChat={chat.reset} onOpenSettings={() => setSettingsOpen(true)} />
        </div>
      </div>

      {/* Mobile drawer */}
      <AnimatePresence>
        {drawerOpen && (
          <motion.div className="fixed inset-0 z-40 lg:hidden" initial={{ opacity: 0 }} animate={{ opacity: 1 }} exit={{ opacity: 0 }}>
            <div className="absolute inset-0 bg-black/40 backdrop-blur-sm" onClick={() => setDrawerOpen(false)} />
            <motion.div
              initial={{ x: 320 }}
              animate={{ x: 0 }}
              exit={{ x: 320 }}
              transition={{ type: "spring", stiffness: 300, damping: 30 }}
              className="glass-strong absolute right-0 top-0 h-full"
            >
              <Sidebar
                onNewChat={() => {
                  chat.reset();
                  setDrawerOpen(false);
                }}
                onOpenSettings={() => {
                  setSettingsOpen(true);
                  setDrawerOpen(false);
                }}
                onClose={() => setDrawerOpen(false)}
              />
            </motion.div>
          </motion.div>
        )}
      </AnimatePresence>

      {/* Main column */}
      <div className="flex min-w-0 flex-1 flex-col">
        <Header
          agents={agents}
          location={location}
          onLocationChange={setLocation}
          showLocation={chat.hasStarted}
          onToggleSidebar={() => setDrawerOpen(true)}
          onToggleRightPanel={() => setRightOpen((v) => !v)}
        />

        <main className="relative flex min-h-0 flex-1 flex-col">
          {!chat.hasStarted ? (
            <div className="flex-1 overflow-y-auto">
              <SearchHero location={location} onLocationChange={setLocation} onSend={send} />
            </div>
          ) : (
            <>
              <div className="flex-1 overflow-y-auto">
                <Conversation
                  messages={chat.messages}
                  phase={chat.phase}
                  onResume={chat.resume}
                  onSuggestion={send}
                />
              </div>
              <div className="mx-auto w-full max-w-3xl px-4 pb-4 pt-2 sm:px-6">
                <InputBar
                  onSend={send}
                  busy={chat.busy}
                  disabled={chat.phase === "awaiting-input"}
                  placeholder={chat.phase === "awaiting-input" ? t.pickToContinue : t.messagePlaceholder}
                />
                <p className="mt-2 text-center text-[11px] text-muted-foreground">{t.disclaimer}</p>
              </div>
            </>
          )}
        </main>
      </div>

      {/* Right panel (desktop) */}
      <AnimatePresence initial={false}>
        {rightOpen && chat.hasStarted && (
          <motion.div
            initial={{ width: 0, opacity: 0 }}
            animate={{ width: 340, opacity: 1 }}
            exit={{ width: 0, opacity: 0 }}
            transition={{ type: "spring", stiffness: 260, damping: 30 }}
            className="hidden shrink-0 xl:block"
          >
            <div className="glass-strong m-3 mr-0 h-[calc(100dvh-1.5rem)] w-[324px] rounded-3xl">
              <RightPanel messages={chat.messages} className="h-full" />
            </div>
          </motion.div>
        )}
      </AnimatePresence>

      <SettingsDialog
        open={settingsOpen}
        onClose={() => setSettingsOpen(false)}
        location={location}
        onLocationChange={setLocation}
      />
    </div>
  );
}
