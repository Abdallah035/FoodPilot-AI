"use client";

import * as React from "react";
import { motion } from "framer-motion";
import { Store, UtensilsCrossed, Ticket, Phone, BadgePercent, CheckCircle2 } from "lucide-react";
import type { OrderSummary as OrderSummaryT } from "@/lib/types";
import { Card } from "@/components/ui/card";
import { Button } from "@/components/ui/button";
import { Badge } from "@/components/ui/badge";
import { formatEGP, arabic } from "@/lib/utils";
import { t } from "@/lib/i18n";

function Row({
  icon: Icon,
  label,
  value,
  muted,
}: {
  icon: React.ElementType;
  label: string;
  value: string;
  muted?: boolean;
}) {
  return (
    <div className="flex items-center justify-between py-1.5 text-sm">
      <span className="inline-flex items-center gap-2 text-muted-foreground">
        <Icon className="h-4 w-4" /> {label}
      </span>
      <span className={muted ? "text-muted-foreground" : "font-medium"}>{value}</span>
    </div>
  );
}

export function OrderSummary({ order }: { order: OrderSummaryT }) {
  const [confirmed, setConfirmed] = React.useState(false);
  const tel = (order.phone || "").replace(/[^\d+]/g, "");
  const mealLine = order.quantity > 1 ? `${order.meal} ×${arabic(order.quantity)}` : order.meal;

  return (
    <motion.div
      initial={{ opacity: 0, y: 16, scale: 0.98 }}
      animate={{ opacity: 1, y: 0, scale: 1 }}
      transition={{ type: "spring", stiffness: 240, damping: 24 }}
    >
      <Card className="overflow-hidden">
        <div className="bg-brand-gradient px-5 py-4 text-white">
          <div className="flex items-center justify-between">
            <span className="text-xs font-medium opacity-90">{t.orderSummary}</span>
            {order.savings > 0 && (
              <Badge className="bg-white/20 text-white backdrop-blur">
                <BadgePercent className="h-3 w-3" /> {t.saved} {formatEGP(order.savings)}
              </Badge>
            )}
          </div>
          <div className="mt-1 font-display text-2xl font-bold">{formatEGP(order.total)}</div>
        </div>

        <div className="p-5">
          <Row icon={Store} label={t.restaurant} value={order.restaurant} />
          <Row icon={UtensilsCrossed} label={t.meal} value={mealLine} />
          {order.promo && (
            <Row
              icon={Ticket}
              label={t.promo}
              value={`${order.promo.code} · -${arabic(order.promo.value)}${
                order.promo.discount_type === "percentage" ? "٪" : " جنيه"
              }${order.promo.required_platform ? ` (${order.promo.required_platform})` : ""}`}
            />
          )}

          <div className="my-3 hairline" />

          <Row
            icon={UtensilsCrossed}
            label={`${t.subtotal}${order.quantity > 1 ? ` (${arabic(order.quantity)}×)` : ""}`}
            value={formatEGP(order.subtotal)}
            muted
          />
          {order.discount > 0 && (
            <div className="flex items-center justify-between py-1.5 text-sm text-leaf-600 dark:text-leaf-400">
              <span className="inline-flex items-center gap-2">
                <BadgePercent className="h-4 w-4" /> {t.discount}
              </span>
              <span className="font-medium">- {formatEGP(order.discount)}</span>
            </div>
          )}

          <div className="my-3 hairline" />

          <div className="flex items-center justify-between">
            <span className="font-display text-base font-semibold">{t.total}</span>
            <span className="font-display text-xl font-bold text-gradient">{formatEGP(order.total)}</span>
          </div>

          {/* Call the restaurant to place the order */}
          {tel ? (
            <a href={`tel:${tel}`} className="mt-4 block">
              <Button className="w-full" size="lg" variant={confirmed ? "success" : "primary"} onClick={() => setConfirmed(true)}>
                {confirmed ? <CheckCircle2 className="h-5 w-5" /> : <Phone className="h-5 w-5" />}
                {confirmed ? t.orderConfirmed : `${t.callToOrder} ${order.phone}`}
              </Button>
            </a>
          ) : (
            <Button
              className="mt-4 w-full"
              size="lg"
              variant={confirmed ? "success" : "primary"}
              onClick={() => setConfirmed(true)}
              disabled={confirmed}
            >
              {confirmed ? <CheckCircle2 className="h-5 w-5" /> : null}
              {confirmed ? t.orderConfirmed : t.confirmOrder}
            </Button>
          )}
          {!tel && (
            <p className="mt-2 text-center text-[11px] text-muted-foreground">رقم هاتف المطعم مش متوفر</p>
          )}
        </div>
      </Card>
    </motion.div>
  );
}
