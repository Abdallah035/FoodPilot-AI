"use client";

import * as React from "react";
import { AnimatePresence } from "framer-motion";
import type { ChatMessage } from "@/lib/types";
import type { ResumeValueT } from "@/lib/agent-client";
import type { ChatPhase } from "@/hooks/use-chat";
import { MessageBubble } from "./message-bubble";
import { TypingBubble } from "./typing-bubble";
import { PromptSuggestions } from "./prompt-suggestions";

export function Conversation({
  messages,
  phase,
  onResume,
  onSuggestion,
}: {
  messages: ChatMessage[];
  phase: ChatPhase;
  onResume: (value: ResumeValueT) => void;
  onSuggestion: (text: string) => void;
}) {
  const bottomRef = React.useRef<HTMLDivElement>(null);
  const last = messages[messages.length - 1];
  const showTyping =
    phase === "thinking" &&
    last?.role === "assistant" &&
    last.blocks.length === 0;
  const showFollowUps = phase === "done" && last?.role === "assistant" && !last.streaming;

  React.useEffect(() => {
    bottomRef.current?.scrollIntoView({ behavior: "smooth", block: "end" });
  }, [messages, phase]);

  return (
    <div className="mx-auto flex w-full max-w-3xl flex-col gap-6 px-4 py-6 sm:px-6">
      <AnimatePresence initial={false}>
        {messages.map((m) => (
          <MessageBubble
            key={m.id}
            message={m}
            awaitingInput={phase === "awaiting-input" && m.id === last?.id}
            onResume={onResume}
          />
        ))}
      </AnimatePresence>

      {showTyping && <TypingBubble />}

      {showFollowUps && (
        <div className="pr-11">
          <PromptSuggestions onPick={onSuggestion} />
        </div>
      )}

      <div ref={bottomRef} className="h-px" />
    </div>
  );
}
