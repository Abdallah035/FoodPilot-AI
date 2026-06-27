# Food Pilot Web — build direction & status

The UI reflects the **real backend outputs**, Arabic (Egyptian) + RTL, live-only.

## Status: DONE (typecheck + build pass, dev renders RTL Arabic)

## Confirmed requirements (all implemented)
1. **Live backend only** — no mock. `agentClient` = LiveAgentClient (SSE → FastAPI bridge).
2. **Location field** — `useLocation` store; shown on hero + header + settings; sent with
   every `/chat` query so Apify searches the typed area (default: التحرير، القاهرة).
3. **Full Arabic (Egyptian) + RTL** — `<html lang="ar" dir="rtl">`, Cairo/Tajawal fonts,
   all copy in `src/lib/i18n.ts`, Arabic-Indic digits via `arabic()`/`toArabicDigits()`.
4. **Quantity** flows: deal selection stepper → resume {index, quantity} → finalizer ×qty.
5. **RAG = CALORIES ONLY** — NutritionCard shows calories_per_meal, quantity_grams,
   calories_per_100g, ingredients (from RAG data.json), found/source. NO macros invented.
6. **Promo** from the Order agent (verify_promo) only; shown with required_platform.
7. **Phone to call** — OrderSummary + RestaurantCard + RightPanel show tel: links.
8. **Simplified** — removed Pro upgrade card, voice/attach buttons, compare/details/
   directions, fabricated discount/calories on deal cards, macro rings.
9. Receipt prompt (order_finalizer/nodes.py) rewritten to Egyptian Arabic.
10. Bridge narration + thinking steps in Arabic (server/runner.py).

## Real output shapes (verified by reading source)
- Scout select_restaurant: options[]{index,name,score,reason,address,phone}
- Scout select_deal: options[]{index,item_name,price,currency,deal_description,portion}; resume{index,quantity}
- RAG items[]: {name,quantity,quantity_grams,calories_per_100g,calories_per_meal,found,source:"rag"|"web"|null}
- Finalizer: verified_promo{code,discount_type,value,required_platform}|null, final_price, receipt_summary

## Run
- Bridge:  `uv run uvicorn server.app:app --port 8000 --app-dir .`  (needs .env: APIFY/TAVILY/AZURE)
- Web:     `cd web && npm run dev`  → http://localhost:3100
- No .env present yet → live calls will error in UI (Arabic message) until keys are added.

## Notes / follow-ups
- ProgressRing in components/ui/rating.tsx now unused (harmless).
- Real Apify restaurants have no image → card shows branded gradient + initial.
- Sidebar history is sample data (no persistence layer yet).
