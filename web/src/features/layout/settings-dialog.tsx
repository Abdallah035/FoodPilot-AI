"use client";

import { AnimatePresence, motion } from "framer-motion";
import { X, Moon, Sun, Monitor, MapPin } from "lucide-react";
import { Button } from "@/components/ui/button";
import { useTheme } from "@/components/theme-provider";
import { cn } from "@/lib/utils";
import { t } from "@/lib/i18n";

export function SettingsDialog({
  open,
  onClose,
  location,
  onLocationChange,
}: {
  open: boolean;
  onClose: () => void;
  location: string;
  onLocationChange: (v: string) => void;
}) {
  const { theme, setTheme } = useTheme();

  return (
    <AnimatePresence>
      {open && (
        <motion.div
          className="fixed inset-0 z-50 grid place-items-center p-4"
          initial={{ opacity: 0 }}
          animate={{ opacity: 1 }}
          exit={{ opacity: 0 }}
        >
          <div className="absolute inset-0 bg-black/40 backdrop-blur-sm" onClick={onClose} />
          <motion.div
            role="dialog"
            aria-modal="true"
            aria-label={t.settings}
            initial={{ opacity: 0, scale: 0.95, y: 10 }}
            animate={{ opacity: 1, scale: 1, y: 0 }}
            exit={{ opacity: 0, scale: 0.95, y: 10 }}
            transition={{ type: "spring", stiffness: 280, damping: 26 }}
            className="glass-strong relative z-10 w-full max-w-md rounded-3xl p-6"
          >
            <div className="mb-5 flex items-center justify-between">
              <h2 className="font-display text-lg font-semibold">{t.settings}</h2>
              <Button size="icon-sm" variant="ghost" aria-label="إغلاق" onClick={onClose}>
                <X className="h-5 w-5" />
              </Button>
            </div>

            <div className="space-y-5">
              <Field label={t.appearance}>
                <div className="grid grid-cols-3 gap-2">
                  {([
                    { key: "light", icon: Sun, label: t.light },
                    { key: "dark", icon: Moon, label: t.dark },
                    { key: "system", icon: Monitor, label: t.system },
                  ] as const).map(({ key, icon: Icon, label }) => {
                    const selected = key === "system" ? false : theme === key;
                    return (
                      <button
                        key={key}
                        onClick={() => key !== "system" && setTheme(key)}
                        className={cn(
                          "glass-subtle flex flex-col items-center gap-1.5 rounded-2xl py-3 text-xs font-medium transition-all focus-ring",
                          selected && "ring-2 ring-brand-500"
                        )}
                      >
                        <Icon className="h-5 w-5" /> {label}
                      </button>
                    );
                  })}
                </div>
              </Field>

              <Field label={t.defaultLocation}>
                <div className="glass-subtle flex items-center gap-2 rounded-full px-3 py-2">
                  <MapPin className="h-4 w-4 text-muted-foreground" />
                  <input
                    value={location}
                    onChange={(e) => onLocationChange(e.target.value)}
                    placeholder={t.locationPlaceholder}
                    className="w-full bg-transparent text-sm outline-none"
                    aria-label={t.defaultLocation}
                  />
                </div>
              </Field>

              <Field label={t.dietary}>
                <div className="flex flex-wrap gap-2">
                  {t.diets.map((d) => (
                    <button
                      key={d}
                      className="glass-subtle rounded-full px-3 py-1.5 text-xs font-medium transition-colors hover:text-brand-600 focus-ring dark:hover:text-brand-300"
                    >
                      {d}
                    </button>
                  ))}
                </div>
              </Field>
            </div>

            <Button className="mt-6 w-full" onClick={onClose}>
              {t.done}
            </Button>
          </motion.div>
        </motion.div>
      )}
    </AnimatePresence>
  );
}

function Field({ label, children }: { label: string; children: React.ReactNode }) {
  return (
    <div>
      <p className="mb-2 text-sm font-medium">{label}</p>
      {children}
    </div>
  );
}
