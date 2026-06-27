"use client";

import * as React from "react";
import { agentClient, type ResumeValueT } from "@/lib/agent-client";
import { AGENT_ORDER } from "@/lib/agents-meta";
import { uid } from "@/lib/utils";
import type {
  AgentState,
  ChatMessage,
  MessageBlock,
  ThinkingStep,
} from "@/lib/types";

const initialAgents = (): AgentState[] =>
  AGENT_ORDER.map((id) => ({
    id,
    name: id.charAt(0).toUpperCase() + id.slice(1),
    status: "idle",
  }));

export type ChatPhase = "idle" | "thinking" | "awaiting-input" | "done";

interface UseChatReturn {
  messages: ChatMessage[];
  phase: ChatPhase;
  busy: boolean;
  hasStarted: boolean;
  send: (text: string, location: string) => void;
  resume: (value: ResumeValueT) => void;
  reset: () => void;
}

/**
 * Drives the whole conversation: appends user turns, consumes the agent
 * event stream, and folds events into a single live assistant message with
 * typed content blocks (markdown, agent workflow, interrupts, cards…).
 */
export function useChat(): UseChatReturn {
  const [messages, setMessages] = React.useState<ChatMessage[]>([]);
  const [phase, setPhase] = React.useState<ChatPhase>("idle");
  const threadId = React.useRef<string>(uid("thread"));
  const cancelled = React.useRef(false);

  const busy = phase === "thinking";
  const hasStarted = messages.length > 0;

  const consume = React.useCallback(
    async (stream: AsyncGenerator<import("@/lib/types").AgentEvent>) => {
      setPhase("thinking");
      const assistantId = uid("msg");
      let agents = initialAgents();
      let thinking: ThinkingStep[] = [];
      let markdown = "";

      // Insert a fresh streaming assistant message.
      setMessages((prev) => [
        ...prev,
        { id: assistantId, role: "assistant", blocks: [], streaming: true, createdAt: Date.now() },
      ]);

      const flush = () => {
        const blocks: MessageBlock[] = [];
        if (agents.some((a) => a.status !== "idle")) {
          blocks.push({ kind: "agents", agents, thinking });
        }
        if (markdown.trim()) blocks.push({ kind: "markdown", text: markdown });
        for (const extra of extraBlocks) blocks.push(extra);
        setMessages((prev) =>
          prev.map((m) => (m.id === assistantId ? { ...m, blocks } : m))
        );
      };

      const extraBlocks: MessageBlock[] = [];

      try {
        for await (const ev of stream) {
          if (cancelled.current) break;
          switch (ev.type) {
            case "token":
              markdown += ev.text;
              flush();
              break;
            case "agents":
              agents = ev.agents;
              flush();
              break;
            case "thinking": {
              const i = thinking.findIndex((t) => t.id === ev.step.id);
              thinking = i === -1 ? [...thinking, ev.step] : thinking.map((t, idx) => (idx === i ? ev.step : t));
              flush();
              break;
            }
            case "interrupt": {
              const it = ev.interrupt;
              if (it.type === "select_restaurant") extraBlocks.push({ kind: "restaurants", interrupt: it });
              else if (it.type === "select_deal") extraBlocks.push({ kind: "deals", interrupt: it });
              else extraBlocks.push({ kind: "no_deals", interrupt: it });
              flush();
              setPhase("awaiting-input");
              break;
            }
            case "nutrition":
              extraBlocks.push({ kind: "nutrition", nutrition: ev.nutrition, meal: ev.meal });
              flush();
              break;
            case "order":
              extraBlocks.push({ kind: "order", order: ev.order });
              flush();
              break;
            case "error":
              markdown += `\n\n> ⚠️ ${ev.message}`;
              flush();
              break;
            case "done":
              break;
          }
        }
      } finally {
        setMessages((prev) =>
          prev.map((m) => (m.id === assistantId ? { ...m, streaming: false } : m))
        );
        setPhase((p) => (p === "awaiting-input" ? p : "done"));
      }
    },
    []
  );

  const send = React.useCallback(
    (text: string, location: string) => {
      const trimmed = text.trim();
      if (!trimmed || phase === "thinking") return;
      cancelled.current = false;
      setMessages((prev) => [
        ...prev,
        { id: uid("msg"), role: "user", blocks: [{ kind: "markdown", text: trimmed }], createdAt: Date.now() },
      ]);
      void consume(agentClient.start(threadId.current, trimmed, location));
    },
    [consume, phase]
  );

  const resume = React.useCallback(
    (value: ResumeValueT) => {
      cancelled.current = false;
      // Echo the user's selection as a compact user turn for context.
      const label = describeResume(value);
      if (label) {
        setMessages((prev) => [
          ...prev,
          { id: uid("msg"), role: "user", blocks: [{ kind: "markdown", text: label }], createdAt: Date.now() },
        ]);
      }
      void consume(agentClient.resume(threadId.current, value));
    },
    [consume]
  );

  const reset = React.useCallback(() => {
    cancelled.current = true;
    threadId.current = uid("thread");
    setMessages([]);
    setPhase("idle");
  }, []);

  return { messages, phase, busy, hasStarted, send, resume, reset };
}

function describeResume(value: ResumeValueT): string {
  switch (value.kind) {
    case "restaurant":
      return "اخترت المطعم ✓";
    case "deal":
      return value.quantity > 1 ? `اخترت الوجبة دي ×${value.quantity} ✓` : "اخترت الوجبة دي ✓";
    case "no_deals":
      return "";
  }
}
