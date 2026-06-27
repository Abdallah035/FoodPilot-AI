/**
 * Egyptian-Arabic UI strings. The whole interface is Arabic + RTL.
 * Centralised here so copy lives in one place and components stay clean.
 */
export const t = {
  // Brand / hero
  appName: "فود بايلوت",
  tagline: "نفسك في أكل إيه النهارده؟",
  heroPlaceholders: [
    'مثال: "عايز برجر"',
    'مثال: "غدا صحي تحت ٤٠٠ سعر حراري"',
    'مثال: "بيتزا قريبة مني"',
    'مثال: "أحسن مأكولات بحرية الليلة"',
    'مثال: "حاجة حرّاقة تحت ٢٥٠ جنيه"',
  ],
  poweredBy: "بيشتغل بـ ٤ وكلاء ذكاء اصطناعي:",

  // Location
  locationLabel: "المكان",
  locationPlaceholder: "اكتب منطقتك… مثال: التحرير، القاهرة",
  searchingNear: (loc: string) => `بندوّر قريب من ${loc}`,

  // Suggestion chips
  chips: {
    pizza: "بيتزا",
    burgers: "برجر",
    healthy: "صحي",
    sushi: "سوشي",
    coffee: "قهوة",
    desserts: "حلويات",
    steak: "ستيك",
    mexican: "مكسيكي",
  },

  // Sidebar
  newChat: "محادثة جديدة",
  searchChats: "ابحث في المحادثات",
  recent: "الأخيرة",
  noMatches: "مفيش نتائج",
  settings: "الإعدادات",

  // Header
  ready: "جاهز",
  agentsWorking: "الوكلاء بيشتغلوا",
  aiConcierge: "مساعد أكل ذكي",

  // Agents
  agents: {
    orchestrator: { name: "المنسّق", role: "بيفهم ويوزّع المهام" },
    scout: { name: "الكشّاف", role: "بيلاقي ويرتّب المطاعم" },
    food: { name: "الأكل", role: "السعرات والمكوّنات" },
    order: { name: "الطلب", role: "بينهي الطلب ويطبّق العروض" },
  },
  agentsCollaborating: "الوكلاء بيتعاونوا",
  agentWorking: (name: string) => `${name} بيشتغل…`,
  multiAgentPipeline: "منظومة متعددة الوكلاء",
  status: {
    idle: "في الانتظار",
    active: "بيشتغل",
    waiting: "مستنّي اختيارك",
    done: "خلص",
    error: "خطأ",
  },

  // Chat / input
  messagePlaceholder: "اكتب رسالتك لفود بايلوت…",
  pickToContinue: "اختار من فوق علشان نكمّل…",
  disclaimer: "ممكن فود بايلوت يغلط. راجع التفاصيل المهمة قبل الطلب.",
  followUps: ["خيارات أرخص", "وجبات أصحّ", "قارن المطاعم", "نباتي بس", "اعرض حلويات", "اطلب دلوقتي"],

  // Cards — restaurant
  openNow: "مفتوح دلوقتي",
  closed: "مقفول",
  match: "تطابق",
  reviews: "تقييم",
  select: "اختار",
  selected: "تم الاختيار",
  details: "تفاصيل",
  directions: "الاتجاهات",

  // Cards — deal
  quantity: "الكمية",
  chooseMeal: "اختار الوجبة دي",
  chosen: "تم اختيارها",
  calories: "سعر حراري",

  // Nutrition
  nutrition: "القيم الغذائية",
  protein: "بروتين",
  carbs: "كارب",
  fat: "دهون",
  fiber: "ألياف",
  healthScore: "مؤشر الصحة",
  ingredients: "المكوّنات",
  source: "المصدر",
  kcal: "سعر",

  // Order summary
  orderSummary: "ملخّص الطلب",
  restaurant: "المطعم",
  meal: "الوجبة",
  promo: "كود الخصم",
  subtotal: "الإجمالي المبدئي",
  discount: "الخصم",
  deliveryFee: "رسوم التوصيل",
  total: "الإجمالي",
  eta: "وقت الوصول",
  saved: "وفّرت",
  phone: "رقم الهاتف",
  callToOrder: "اتصل بالمطعم للطلب",
  confirmOrder: "أكّد الطلب",
  orderConfirmed: "تم تأكيد الطلب",

  // No deals
  noMenuFound: "ملقيناش قائمة طعام للمطعم ده. تحب تعمل إيه؟",

  // Settings
  appearance: "المظهر",
  light: "فاتح",
  dark: "غامق",
  system: "النظام",
  defaultLocation: "المكان الافتراضي",
  dietary: "تفضيلات الأكل",
  diets: ["نباتي", "نباتي صِرف", "حلال", "قليل الكارب", "عالي البروتين", "خالي من الجلوتين"],
  done: "تمام",

  // Thinking lines (fallback if backend doesn't send Arabic)
  thinking: {
    searchingMaps: "بندوّرلك على أقرب المطاعم ليك… 📍",
    ranking: "بنرتّبلك أحسن المطاعم على مقاسك ⭐",
    exploringMenu: "بنفتحلك منيو المطعم… 🍽️",
    checkingPromos: "بندوّرلك على العروض والخصومات ⏳",
    betterDeals: "بنختارلك أحلى الأطباق بأحسن سعر 💛",
    nutrition: "بنشوفلك مكوّنات الوجبة… 🥗",
    calories: "بنحسبلك السعرات الحرارية — ثواني ⏳",
    promo: "بندوّرلك على كوبونات وخصومات شغّالة… 🎟️",
    preparing: "بنجهّزلك الطلب… ✅",
  },
} as const;

/** Convert Western digits to Arabic-Indic for nicer display. */
export function toArabicDigits(value: string | number): string {
  const map = "٠١٢٣٤٥٦٧٨٩";
  return String(value).replace(/[0-9]/g, (d) => map[Number(d)]);
}
