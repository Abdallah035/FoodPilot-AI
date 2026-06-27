"use client";

import { motion } from "framer-motion";
import { Flame, Scale, Database, Globe, Soup } from "lucide-react";
import type { Nutrition } from "@/lib/types";
import { Card } from "@/components/ui/card";
import { Badge } from "@/components/ui/badge";
import { t, toArabicDigits } from "@/lib/i18n";

/**
 * Shows ONLY what the Food/RAG agent actually returns: calories for the chosen
 * quantity, the quantity in grams, where the number came from (RAG vs web), and
 * the ingredients from the RAG dish data. No invented macros.
 */
export function NutritionCard({ nutrition, meal }: { nutrition: Nutrition; meal: string }) {
  const cal = nutrition.calories_per_meal;
  const sourceLabel =
    nutrition.source === "rag" ? "قاعدة المعرفة" : nutrition.source === "web" ? "بحث الويب" : null;
  const SourceIcon = nutrition.source === "web" ? Globe : Database;

  return (
    <motion.div
      initial={{ opacity: 0, y: 16 }}
      animate={{ opacity: 1, y: 0 }}
      transition={{ type: "spring", stiffness: 240, damping: 24 }}
    >
      <Card className="p-5">
        <div className="mb-4 flex items-center justify-between gap-3">
          <div>
            <p className="text-xs font-medium text-muted-foreground">
              {t.nutrition} · {meal}
            </p>
            <div className="mt-1 flex items-baseline gap-2">
              <Flame className="h-5 w-5 self-center text-brand-500" />
              <span className="font-display text-3xl font-bold">
                {cal != null ? toArabicDigits(Math.round(cal)) : "—"}
              </span>
              <span className="text-sm text-muted-foreground">{t.kcal}</span>
            </div>
          </div>

          {nutrition.quantity_grams != null && (
            <div className="glass-subtle flex flex-col items-center rounded-2xl px-4 py-2 text-center">
              <Scale className="mb-1 h-4 w-4 text-brand-500" />
              <span className="font-display text-lg font-bold leading-none">
                {toArabicDigits(Math.round(nutrition.quantity_grams))}
              </span>
              <span className="text-[10px] text-muted-foreground">جرام</span>
            </div>
          )}
        </div>

        {/* calories per 100g context */}
        {nutrition.calories_per_100g != null && (
          <p className="mb-3 text-xs text-muted-foreground">
            {toArabicDigits(Math.round(nutrition.calories_per_100g))} {t.kcal} لكل ١٠٠ جرام
          </p>
        )}

        {/* ingredients from RAG */}
        {nutrition.ingredients && nutrition.ingredients.length > 0 && (
          <div>
            <p className="mb-2 inline-flex items-center gap-1.5 text-sm font-semibold">
              <Soup className="h-4 w-4 text-brand-500" /> {t.ingredients}
            </p>
            <div className="flex flex-wrap gap-1.5">
              {nutrition.ingredients.map((ing) => (
                <span
                  key={ing}
                  className="rounded-full bg-muted px-2.5 py-1 text-xs text-muted-foreground"
                >
                  {ing}
                </span>
              ))}
            </div>
          </div>
        )}

        {/* source */}
        {sourceLabel && (
          <p className="mt-4 inline-flex items-center gap-1.5 text-[11px] text-muted-foreground">
            <SourceIcon className="h-3 w-3" /> {t.source}: {sourceLabel}
          </p>
        )}
        {!nutrition.found && (
          <Badge variant="warning" className="mt-3">
            القيم الغذائية مش متوفرة للوجبة دي
          </Badge>
        )}
      </Card>
    </motion.div>
  );
}
