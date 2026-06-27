"use client";

import * as React from "react";
import { motion } from "framer-motion";
import { ArrowUp, Square } from "lucide-react";
import { Button } from "@/components/ui/button";
import { cn } from "@/lib/utils";
import { t } from "@/lib/i18n";

interface InputBarProps {
  onSend: (text: string) => void;
  disabled?: boolean;
  busy?: boolean;
  onStop?: () => void;
  placeholder?: string;
  autoFocus?: boolean;
  className?: string;
}

/** The main message composer — auto-growing textarea with send/stop. Simple. */
export function InputBar({
  onSend,
  disabled,
  busy,
  onStop,
  placeholder = t.messagePlaceholder,
  autoFocus,
  className,
}: InputBarProps) {
  const [value, setValue] = React.useState("");
  const ref = React.useRef<HTMLTextAreaElement>(null);

  React.useEffect(() => {
    const el = ref.current;
    if (!el) return;
    el.style.height = "auto";
    el.style.height = `${Math.min(el.scrollHeight, 160)}px`;
  }, [value]);

  const submit = () => {
    const text = value.trim();
    if (!text || disabled) return;
    onSend(text);
    setValue("");
  };

  const onKeyDown = (e: React.KeyboardEvent<HTMLTextAreaElement>) => {
    if (e.key === "Enter" && !e.shiftKey) {
      e.preventDefault();
      submit();
    }
  };

  return (
    <motion.div
      initial={{ opacity: 0, y: 12 }}
      animate={{ opacity: 1, y: 0 }}
      className={cn("glass-strong flex items-end gap-2 rounded-[28px] p-2 pr-4 shadow-soft-lg", className)}
    >
      <textarea
        ref={ref}
        value={value}
        rows={1}
        autoFocus={autoFocus}
        onChange={(e) => setValue(e.target.value)}
        onKeyDown={onKeyDown}
        placeholder={placeholder}
        className="max-h-40 flex-1 resize-none bg-transparent py-2.5 pr-2 text-[15px] leading-relaxed outline-none placeholder:text-muted-foreground"
        aria-label={t.messagePlaceholder}
      />

      {busy ? (
        <Button size="icon" variant="secondary" aria-label="إيقاف" onClick={onStop} className="shrink-0">
          <Square className="h-4 w-4 fill-current" />
        </Button>
      ) : (
        <Button size="icon" aria-label="إرسال" onClick={submit} disabled={!value.trim() || disabled} className="shrink-0">
          <ArrowUp className="h-5 w-5" />
        </Button>
      )}
    </motion.div>
  );
}
