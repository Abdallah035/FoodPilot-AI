"use client";

import { motion } from "framer-motion";
import type { ChatMessage } from "@/lib/types";
import type { ResumeValueT } from "@/lib/agent-client";
import { LogoMark } from "@/components/brand/logo";
import { Markdown } from "@/components/ui/markdown";
import { AgentWorkflow } from "@/features/agents/agent-workflow";
import { NutritionCard } from "@/features/cards/nutrition-card";
import { OrderSummary } from "@/features/cards/order-summary";
import {
  RestaurantSelection,
  DealSelection,
  NoDealsSelection,
} from "./selection-blocks";
import { cn } from "@/lib/utils";

export function MessageBubble({
  message,
  awaitingInput,
  onResume,
}: {
  message: ChatMessage;
  awaitingInput: boolean;
  onResume: (value: ResumeValueT) => void;
}) {
  const isUser = message.role === "user";

  if (isUser) {
    const text = message.blocks.map((b) => (b.kind === "markdown" ? b.text : "")).join(" ");
    return (
      <motion.div
        initial={{ opacity: 0, y: 8 }}
        animate={{ opacity: 1, y: 0 }}
        className="flex justify-end"
      >
        <div className="max-w-[85%] rounded-3xl rounded-br-lg bg-brand-gradient px-4 py-2.5 text-[15px] text-white shadow-glow-sm">
          {text}
        </div>
      </motion.div>
    );
  }

  // The last interrupt block in the latest assistant message is the live one.
  const interruptBlocks = message.blocks.filter(
    (b) => b.kind === "restaurants" || b.kind === "deals" || b.kind === "no_deals"
  );
  const liveInterrupt = interruptBlocks[interruptBlocks.length - 1];

  return (
    <motion.div
      initial={{ opacity: 0, y: 8 }}
      animate={{ opacity: 1, y: 0 }}
      className="flex gap-3"
    >
      <div className="sticky top-0 mt-1 shrink-0">
        <LogoMark size={32} />
      </div>

      <div className="min-w-0 flex-1 space-y-3">
        {message.blocks.map((block, i) => {
          switch (block.kind) {
            case "agents":
              return <AgentWorkflow key={i} agents={block.agents} thinking={block.thinking} />;
            case "markdown":
              return (
                <div key={i} className="glass inline-block max-w-full rounded-3xl rounded-tl-lg px-4 py-3">
                  <Markdown>{block.text}</Markdown>
                  {message.streaming && i === lastMarkdownIndex(message) && <Caret />}
                </div>
              );
            case "restaurants":
              return (
                <RestaurantSelection
                  key={i}
                  interrupt={block.interrupt}
                  resolved={!(awaitingInput && block === liveInterrupt)}
                  onResume={onResume}
                />
              );
            case "deals":
              return (
                <DealSelection
                  key={i}
                  interrupt={block.interrupt}
                  resolved={!(awaitingInput && block === liveInterrupt)}
                  onResume={onResume}
                />
              );
            case "no_deals":
              return (
                <NoDealsSelection
                  key={i}
                  interrupt={block.interrupt}
                  resolved={!(awaitingInput && block === liveInterrupt)}
                  onResume={onResume}
                />
              );
            case "nutrition":
              return <NutritionCard key={i} nutrition={block.nutrition} meal={block.meal} />;
            case "order":
              return <OrderSummary key={i} order={block.order} />;
            default:
              return null;
          }
        })}
      </div>
    </motion.div>
  );
}

function lastMarkdownIndex(message: ChatMessage): number {
  let idx = -1;
  message.blocks.forEach((b, i) => {
    if (b.kind === "markdown") idx = i;
  });
  return idx;
}

function Caret() {
  return <span className={cn("ml-0.5 inline-block h-4 w-[2px] -translate-y-px bg-brand-500 align-middle animate-blink")} />;
}
