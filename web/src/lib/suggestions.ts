import type { SuggestionChip } from "./types";
import { t } from "./i18n";

/** Quick-craving chips shown on the landing hero — Egyptian Arabic. */
export const SUGGESTION_CHIPS: SuggestionChip[] = [
  { emoji: "🍕", label: t.chips.pizza, query: "أحسن بيتزا قريبة مني" },
  { emoji: "🍔", label: t.chips.burgers, query: "عايز برجر تحفة" },
  { emoji: "🥗", label: t.chips.healthy, query: "غدا صحي تحت ٤٠٠ سعر حراري" },
  { emoji: "🍣", label: t.chips.sushi, query: "سوشي طازة الليلة" },
  { emoji: "☕", label: t.chips.coffee, query: "قهوة حلوة ومعجنات قريبة" },
  { emoji: "🍰", label: t.chips.desserts, query: "اعرضلي أحسن الحلويات" },
  { emoji: "🥩", label: t.chips.steak, query: "عشا ستيك فخم" },
  { emoji: "🌮", label: t.chips.mexican, query: "تاكو وأكل مكسيكي" },
];

export const HERO_PLACEHOLDERS = t.heroPlaceholders;

/** Placeholder recent-chats for the sidebar (no persistence layer yet). */
export const SAMPLE_HISTORY = [
  { id: "c1", title: "برجر في المعادي", updatedAt: Date.now() - 1000 * 60 * 12 },
  { id: "c2", title: "غدا صحي تحت ٤٠٠ سعر", updatedAt: Date.now() - 1000 * 60 * 60 * 3 },
  { id: "c3", title: "أحسن سوشي الليلة", updatedAt: Date.now() - 1000 * 60 * 60 * 26 },
];
