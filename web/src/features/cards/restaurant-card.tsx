"use client";

import * as React from "react";
import { motion } from "framer-motion";
import Image from "next/image";
import { Heart, MapPin, Clock, Phone, Check } from "lucide-react";
import type { Restaurant } from "@/lib/types";
import { Button } from "@/components/ui/button";
import { Badge } from "@/components/ui/badge";
import { Rating } from "@/components/ui/rating";
import { cn, formatDistance, estimateEta, arabic } from "@/lib/utils";
import { t } from "@/lib/i18n";

interface RestaurantCardProps {
  restaurant: Restaurant;
  index?: number;
  selected?: boolean;
  disabled?: boolean;
  onSelect?: (r: Restaurant) => void;
}

export function RestaurantCard({
  restaurant,
  index = 0,
  selected,
  disabled,
  onSelect,
}: RestaurantCardProps) {
  const [fav, setFav] = React.useState(restaurant.favorite ?? false);
  const score = restaurant.score != null ? Math.round(restaurant.score * 100) : null;
  const tel = (restaurant.phone || "").replace(/[^\d+]/g, "");

  return (
    <motion.article
      layout
      initial={{ opacity: 0, y: 16, scale: 0.98 }}
      animate={{ opacity: 1, y: 0, scale: 1 }}
      transition={{ delay: index * 0.06, type: "spring", stiffness: 260, damping: 24 }}
      whileHover={{ y: -4 }}
      className={cn(
        "group glass rounded-3xl overflow-hidden transition-shadow hover:shadow-soft-lg",
        selected && "ring-2 ring-brand-500 shadow-glow",
        disabled && !selected && "opacity-60"
      )}
    >
      {/* Image */}
      <div className="relative h-40 w-full overflow-hidden">
        {restaurant.image ? (
          <Image
            src={restaurant.image}
            alt={restaurant.name}
            fill
            sizes="(max-width:768px) 100vw, 360px"
            className="object-cover transition-transform duration-500 group-hover:scale-105"
          />
        ) : (
          <div className="grid h-full w-full place-items-center bg-brand-gradient">
            <span className="font-display text-4xl font-bold text-white/90">
              {restaurant.name?.trim().charAt(0) || "🍽️"}
            </span>
          </div>
        )}
        <div className="absolute inset-0 bg-gradient-to-t from-black/55 via-black/0 to-black/10" />

        {/* Top row badges */}
        <div className="absolute inset-x-0 top-0 flex items-start justify-between p-3">
          {score != null && (
            <Badge variant="brand" className="bg-white/90 text-brand-600 backdrop-blur shadow-soft">
              ✦ {arabic(score)}٪ {t.match}
            </Badge>
          )}
          <button
            aria-label={fav ? "إزالة من المفضلة" : "أضف للمفضلة"}
            onClick={() => setFav((v) => !v)}
            className="grid h-8 w-8 place-items-center rounded-full bg-white/85 backdrop-blur shadow-soft transition-transform active:scale-90 focus-ring"
          >
            <Heart className={cn("h-4 w-4", fav ? "fill-red-500 text-red-500" : "text-foreground/70")} />
          </button>
        </div>

        {/* Bottom status */}
        <div className="absolute inset-x-0 bottom-0 flex items-end justify-between p-3 text-white">
          <Rating value={restaurant.rating} className="text-white drop-shadow" />
          {restaurant.open != null && (
            <Badge variant={restaurant.open ? "success" : "danger"} className="bg-black/40 text-white backdrop-blur">
              <span className={cn("h-1.5 w-1.5 rounded-full", restaurant.open ? "bg-leaf-400" : "bg-red-400")} />
              {restaurant.open ? t.openNow : t.closed}
            </Badge>
          )}
        </div>
      </div>

      {/* Body */}
      <div className="space-y-2.5 p-4">
        <div className="flex items-start justify-between gap-2">
          <div className="min-w-0">
            <h3 className="truncate font-display text-base font-semibold">{restaurant.name}</h3>
            <p className="truncate text-xs text-muted-foreground">{restaurant.cuisine}</p>
          </div>
          {restaurant.price_level && (
            <Badge variant="glass" className="shrink-0">
              {restaurant.price_level}
            </Badge>
          )}
        </div>

        <div className="flex flex-wrap items-center gap-x-3 gap-y-1 text-xs text-muted-foreground">
          {restaurant.distance_km != null && (
            <span className="inline-flex items-center gap-1">
              <MapPin className="h-3.5 w-3.5" /> {formatDistance(restaurant.distance_km)}
            </span>
          )}
          <span className="inline-flex items-center gap-1">
            <Clock className="h-3.5 w-3.5" /> {estimateEta(restaurant.distance_km)}
          </span>
          {restaurant.reviews ? <span>{arabic(restaurant.reviews.toLocaleString("ar-EG"))} {t.reviews}</span> : null}
        </div>

        {restaurant.reason && (
          <p className="rounded-xl bg-brand-gradient-soft px-3 py-2 text-xs text-foreground/80">
            {restaurant.reason}
          </p>
        )}

        {/* Actions — keep it simple: select, favorite, call */}
        <div className="flex items-center gap-2 pt-1">
          <Button
            size="sm"
            variant={selected ? "success" : "primary"}
            className="flex-1"
            disabled={disabled}
            onClick={() => onSelect?.(restaurant)}
          >
            {selected ? <Check className="h-4 w-4" /> : null}
            {selected ? t.selected : t.select}
          </Button>
          {tel && (
            <a href={`tel:${tel}`} aria-label={t.phone}>
              <Button size="icon-sm" variant="outline" aria-label={t.phone}>
                <Phone className="h-4 w-4" />
              </Button>
            </a>
          )}
        </div>
      </div>
    </motion.article>
  );
}
