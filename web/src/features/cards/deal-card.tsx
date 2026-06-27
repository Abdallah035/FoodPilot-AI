"use client";

import { motion } from "framer-motion";
import { Check, UtensilsCrossed } from "lucide-react";
import type { Deal } from "@/lib/types";
import { Button } from "@/components/ui/button";
import { Badge } from "@/components/ui/badge";
import { cn, formatEGP } from "@/lib/utils";
import { t } from "@/lib/i18n";

interface DealCardProps {
  deal: Deal;
  index?: number;
  selected?: boolean;
  onChoose?: (deal: Deal) => void;
}

/**
 * A menu item from Talabat/Tavily. Backend provides: item_name, price, currency,
 * deal_description, portion. We show exactly those — no invented calories here
 * (calories come later from the Food/RAG agent for the chosen item).
 */
export function DealCard({ deal, index = 0, selected, onChoose }: DealCardProps) {
  return (
    <motion.article
      layout
      initial={{ opacity: 0, y: 16, scale: 0.98 }}
      animate={{ opacity: 1, y: 0, scale: 1 }}
      transition={{ delay: index * 0.06, type: "spring", stiffness: 260, damping: 24 }}
      whileHover={{ y: -3 }}
      className={cn(
        "group glass flex flex-col overflow-hidden rounded-3xl p-4 transition-shadow hover:shadow-soft-lg",
        selected && "ring-2 ring-brand-500 shadow-glow"
      )}
    >
      <div className="flex items-start justify-between gap-2">
        <div className="flex min-w-0 items-center gap-2">
          <span className="grid h-9 w-9 shrink-0 place-items-center rounded-xl bg-brand-gradient-soft">
            <UtensilsCrossed className="h-4 w-4 text-brand-600 dark:text-brand-300" />
          </span>
          <h3 className="font-display text-base font-semibold leading-tight">{deal.item_name}</h3>
        </div>
        {deal.portion && (
          <Badge variant="glass" className="shrink-0">
            {deal.portion}
          </Badge>
        )}
      </div>

      {deal.deal_description && (
        <p className="mt-2 text-xs text-muted-foreground line-clamp-2">{deal.deal_description}</p>
      )}

      <div className="mt-auto flex items-end justify-between gap-2 pt-3">
        <div className="font-display text-xl font-bold text-gradient">{formatEGP(deal.price)}</div>
        <Button size="sm" variant={selected ? "success" : "primary"} onClick={() => onChoose?.(deal)}>
          {selected ? <Check className="h-4 w-4" /> : null}
          {selected ? t.chosen : t.chooseMeal}
        </Button>
      </div>
    </motion.article>
  );
}
