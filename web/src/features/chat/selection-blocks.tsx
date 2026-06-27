"use client";

import * as React from "react";
import { motion } from "framer-motion";
import { Minus, Plus, Store, RefreshCw, MapPin, Phone } from "lucide-react";
import type {
  RestaurantInterrupt,
  DealInterrupt,
  NoDealsInterrupt,
  Restaurant,
  Deal,
} from "@/lib/types";
import type { ResumeValueT } from "@/lib/agent-client";
import { RestaurantCard } from "@/features/cards/restaurant-card";
import { DealCard } from "@/features/cards/deal-card";
import { Button } from "@/components/ui/button";
import { Card } from "@/components/ui/card";
import { cn, arabic } from "@/lib/utils";
import { t } from "@/lib/i18n";

interface SelectionProps {
  resolved?: boolean; // already answered → lock the controls
  onResume: (value: ResumeValueT) => void;
}

const gridCls = "grid gap-3 sm:grid-cols-2 xl:grid-cols-3";

/** HITL #1 — choose a restaurant. */
export function RestaurantSelection({
  interrupt,
  resolved,
  onResume,
}: SelectionProps & { interrupt: RestaurantInterrupt }) {
  const [selected, setSelected] = React.useState<string | null>(null);

  const choose = (r: Restaurant) => {
    if (resolved) return;
    setSelected(r.id);
    const index = interrupt.options.findIndex((o) => o.id === r.id);
    onResume({ kind: "restaurant", index });
  };

  return (
    <section aria-label="اختر مطعم" className="space-y-3">
      <Prompt>{interrupt.prompt}</Prompt>
      <div className={gridCls}>
        {interrupt.options.map((r, i) => (
          <RestaurantCard
            key={r.id}
            restaurant={r}
            index={i}
            selected={selected === r.id}
            disabled={resolved && selected !== r.id}
            onSelect={choose}
          />
        ))}
      </div>
    </section>
  );
}

/** HITL #2 — choose a deal (with quantity stepper, no manual numbers). */
export function DealSelection({
  interrupt,
  resolved,
  onResume,
}: SelectionProps & { interrupt: DealInterrupt }) {
  const [selected, setSelected] = React.useState<string | null>(null);
  const [qty, setQty] = React.useState(1);

  const choose = (d: Deal) => {
    if (resolved) return;
    setSelected(d.id);
    const index = interrupt.options.findIndex((o) => o.id === d.id);
    onResume({ kind: "deal", index, quantity: qty });
  };

  return (
    <section aria-label="اختر وجبة" className="space-y-3">
      <div className="flex flex-wrap items-center justify-between gap-3">
        <Prompt>{interrupt.prompt}</Prompt>
        <QuantityStepper value={qty} onChange={setQty} disabled={resolved} />
      </div>
      <div className={gridCls}>
        {interrupt.options.map((d, i) => (
          <DealCard key={d.id} deal={d} index={i} selected={selected === d.id} onChoose={choose} />
        ))}
      </div>
    </section>
  );
}

/** No menu/deals found — offer to show info or pick another, all clickable. */
export function NoDealsSelection({
  interrupt,
  resolved,
  onResume,
}: SelectionProps & { interrupt: NoDealsInterrupt }) {
  const tel = (interrupt.restaurant.phone || "").replace(/[^\d+]/g, "");
  return (
    <Card className="p-5">
      <div className="mb-3 flex items-center gap-2">
        <Store className="h-5 w-5 text-brand-500" />
        <div>
          <p className="font-display font-semibold">{interrupt.restaurant.name}</p>
          <p className="text-xs text-muted-foreground">{interrupt.prompt}</p>
        </div>
      </div>

      {(interrupt.restaurant.address || tel) && (
        <div className="mb-3 space-y-1 text-sm text-muted-foreground">
          {interrupt.restaurant.address && (
            <p className="inline-flex items-center gap-1.5">
              <MapPin className="h-4 w-4" /> {interrupt.restaurant.address}
            </p>
          )}
          {tel && (
            <a href={`tel:${tel}`} className="inline-flex items-center gap-1.5 text-brand-600 dark:text-brand-300">
              <Phone className="h-4 w-4" /> {interrupt.restaurant.phone}
            </a>
          )}
        </div>
      )}

      <div className="flex flex-wrap gap-2">
        {interrupt.options.map((opt) => (
          <Button
            key={opt.index}
            variant={opt.index === 1 ? "primary" : "secondary"}
            size="sm"
            disabled={resolved}
            onClick={() => onResume({ kind: "no_deals", index: opt.index })}
          >
            {opt.index === 1 && <RefreshCw className="h-4 w-4" />}
            {opt.label}
          </Button>
        ))}
      </div>
    </Card>
  );
}

function Prompt({ children }: { children: React.ReactNode }) {
  return <p className="text-sm font-medium text-foreground/80">{children}</p>;
}

function QuantityStepper({
  value,
  onChange,
  disabled,
}: {
  value: number;
  onChange: (n: number) => void;
  disabled?: boolean;
}) {
  return (
    <div
      className={cn(
        "glass inline-flex items-center gap-1 rounded-full p-1",
        disabled && "opacity-50 pointer-events-none"
      )}
    >
      <span className="px-2 text-xs text-muted-foreground">{t.quantity}</span>
      <Button size="icon-sm" variant="ghost" aria-label="تقليل الكمية" onClick={() => onChange(Math.max(1, value - 1))}>
        <Minus className="h-4 w-4" />
      </Button>
      <motion.span key={value} initial={{ scale: 0.7 }} animate={{ scale: 1 }} className="w-8 text-center text-sm font-semibold">
        {arabic(value)}
      </motion.span>
      <Button size="icon-sm" variant="ghost" aria-label="زيادة الكمية" onClick={() => onChange(Math.min(99, value + 1))}>
        <Plus className="h-4 w-4" />
      </Button>
    </div>
  );
}
