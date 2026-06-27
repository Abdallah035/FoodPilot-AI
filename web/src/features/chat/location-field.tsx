"use client";

import { MapPin } from "lucide-react";
import { cn } from "@/lib/utils";
import { t } from "@/lib/i18n";

/** Editable search-location input. Sent to the backend with each query. */
export function LocationField({
  value,
  onChange,
  className,
  compact,
}: {
  value: string;
  onChange: (v: string) => void;
  className?: string;
  compact?: boolean;
}) {
  return (
    <label
      className={cn(
        "glass inline-flex items-center gap-2 rounded-full px-3 py-2 text-sm",
        compact && "py-1.5",
        className
      )}
    >
      <MapPin className="h-4 w-4 shrink-0 text-brand-500" />
      {!compact && <span className="shrink-0 text-muted-foreground">{t.locationLabel}:</span>}
      <input
        value={value}
        onChange={(e) => onChange(e.target.value)}
        placeholder={t.locationPlaceholder}
        aria-label={t.locationLabel}
        className="w-full min-w-0 bg-transparent text-foreground outline-none placeholder:text-muted-foreground"
      />
    </label>
  );
}
