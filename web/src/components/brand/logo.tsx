"use client";

import { motion } from "framer-motion";
import { cn } from "@/lib/utils";

/**
 * Food Pilot mark — a stylized paper-plane / fork hybrid inside an orange
 * gradient orb. Animated variant gently floats and pulses for the hero.
 */
export function LogoMark({
  size = 36,
  animated = false,
  className,
}: {
  size?: number;
  animated?: boolean;
  className?: string;
}) {
  return (
    <motion.div
      className={cn("relative grid place-items-center rounded-2xl bg-brand-gradient shadow-glow-sm", className)}
      style={{ width: size, height: size }}
      animate={animated ? { y: [0, -6, 0] } : undefined}
      transition={animated ? { duration: 5, repeat: Infinity, ease: "easeInOut" } : undefined}
    >
      {animated && (
        <span className="pointer-events-none absolute inset-0 rounded-2xl bg-brand-gradient opacity-60 blur-md animate-pulse" />
      )}
      <svg
        viewBox="0 0 24 24"
        width={size * 0.58}
        height={size * 0.58}
        fill="none"
        className="relative text-white"
        aria-hidden
      >
        {/* paper-plane body */}
        <path
          d="M21 3L3 10.5l6.2 2.3L21 3zM9.2 12.8l2.4 6.2L21 3 9.2 12.8z"
          fill="currentColor"
          fillOpacity="0.95"
        />
        {/* fork tine accent */}
        <path
          d="M9.2 12.8l2.4 6.2 2.1-3.6-4.5-2.6z"
          fill="#fff"
          fillOpacity="0.45"
        />
      </svg>
    </motion.div>
  );
}

export function Wordmark({ className }: { className?: string }) {
  return (
    <span className={cn("font-display font-bold tracking-tight", className)}>
      Food<span className="text-gradient animate-gradient-text">Pilot</span>
    </span>
  );
}

export function Logo({
  size = 36,
  animated = false,
  showWord = true,
  className,
}: {
  size?: number;
  animated?: boolean;
  showWord?: boolean;
  className?: string;
}) {
  return (
    <div className={cn("flex items-center gap-2.5", className)}>
      <LogoMark size={size} animated={animated} />
      {showWord && <Wordmark className="text-lg" />}
    </div>
  );
}
