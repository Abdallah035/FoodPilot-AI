"use client";

import * as React from "react";
import { motion } from "framer-motion";
import { LogoMark } from "@/components/brand/logo";
import { InputBar } from "./input-bar";
import { LocationField } from "./location-field";
import { SUGGESTION_CHIPS, HERO_PLACEHOLDERS } from "@/lib/suggestions";
import { AGENT_META, AGENT_ORDER } from "@/lib/agents-meta";
import { t } from "@/lib/i18n";

/** The empty / landing state shown before the first message. */
export function SearchHero({
  location,
  onLocationChange,
  onSend,
}: {
  location: string;
  onLocationChange: (v: string) => void;
  onSend: (text: string) => void;
}) {
  const placeholder = useRotatingPlaceholder();

  return (
    <div className="relative mx-auto flex min-h-full w-full max-w-2xl flex-col items-center justify-center px-4 py-12 text-center">
      <div className="pointer-events-none absolute inset-0 -z-10 bg-mesh opacity-70" />

      <motion.div
        initial={{ opacity: 0, scale: 0.9, y: 10 }}
        animate={{ opacity: 1, scale: 1, y: 0 }}
        transition={{ type: "spring", stiffness: 200, damping: 18 }}
      >
        <LogoMark size={72} animated />
      </motion.div>

      <motion.h1
        initial={{ opacity: 0, y: 10 }}
        animate={{ opacity: 1, y: 0 }}
        transition={{ delay: 0.1 }}
        className="mt-6 font-display text-4xl font-extrabold tracking-tight sm:text-5xl"
      >
        فود<span className="text-gradient animate-gradient-text">بايلوت</span>
      </motion.h1>

      <motion.p
        initial={{ opacity: 0, y: 10 }}
        animate={{ opacity: 1, y: 0 }}
        transition={{ delay: 0.18 }}
        className="mt-3 text-lg text-muted-foreground"
      >
        {t.tagline}
      </motion.p>

      {/* Location */}
      <motion.div
        initial={{ opacity: 0, y: 12 }}
        animate={{ opacity: 1, y: 0 }}
        transition={{ delay: 0.22 }}
        className="mt-6 w-full max-w-sm"
      >
        <LocationField value={location} onChange={onLocationChange} className="w-full" />
      </motion.div>

      {/* Search */}
      <motion.div
        initial={{ opacity: 0, y: 14 }}
        animate={{ opacity: 1, y: 0 }}
        transition={{ delay: 0.28 }}
        className="mt-3 w-full"
      >
        <InputBar onSend={onSend} placeholder={placeholder} autoFocus />
      </motion.div>

      {/* Suggestion chips */}
      <motion.div
        initial="hidden"
        animate="show"
        variants={{ show: { transition: { staggerChildren: 0.04, delayChildren: 0.36 } } }}
        className="mt-6 flex flex-wrap items-center justify-center gap-2"
      >
        {SUGGESTION_CHIPS.map((chip) => (
          <motion.button
            key={chip.label}
            variants={{ hidden: { opacity: 0, y: 8 }, show: { opacity: 1, y: 0 } }}
            whileHover={{ y: -3, scale: 1.03 }}
            whileTap={{ scale: 0.97 }}
            onClick={() => onSend(chip.query)}
            className="glass inline-flex items-center gap-1.5 rounded-full px-4 py-2 text-sm font-medium transition-colors hover:text-brand-600 focus-ring dark:hover:text-brand-300"
          >
            <span className="text-base">{chip.emoji}</span>
            {chip.label}
          </motion.button>
        ))}
      </motion.div>

      {/* Agent intro */}
      <motion.div
        initial={{ opacity: 0 }}
        animate={{ opacity: 1 }}
        transition={{ delay: 0.6 }}
        className="mt-10 flex flex-wrap items-center justify-center gap-x-5 gap-y-2 text-xs text-muted-foreground"
      >
        <span className="font-medium">{t.poweredBy}</span>
        {AGENT_ORDER.map((id) => {
          const meta = AGENT_META[id];
          return (
            <span key={id} className="inline-flex items-center gap-1.5">
              <span className={`grid h-5 w-5 place-items-center rounded-md bg-gradient-to-br ${meta.gradient} text-white`}>
                <meta.icon className="h-3 w-3" />
              </span>
              {t.agents[id].name}
            </span>
          );
        })}
      </motion.div>
    </div>
  );
}

function useRotatingPlaceholder(): string {
  const [i, setI] = React.useState(0);
  React.useEffect(() => {
    const id = setInterval(() => setI((v) => (v + 1) % HERO_PLACEHOLDERS.length), 2800);
    return () => clearInterval(id);
  }, []);
  return HERO_PLACEHOLDERS[i];
}
