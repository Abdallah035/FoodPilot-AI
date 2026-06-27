"use client";

import * as React from "react";

const STORAGE_KEY = "fp-location";
const DEFAULT_LOCATION = "التحرير، القاهرة";

/**
 * The search location, shared across the hero and header and persisted locally.
 * It is sent to the backend with every new query so Apify searches the right area.
 */
export function useLocation(): [string, (loc: string) => void] {
  const [location, setLocationState] = React.useState(DEFAULT_LOCATION);

  React.useEffect(() => {
    const stored = localStorage.getItem(STORAGE_KEY);
    if (stored) setLocationState(stored);
  }, []);

  const setLocation = React.useCallback((loc: string) => {
    const value = loc.trim() || DEFAULT_LOCATION;
    setLocationState(value);
    localStorage.setItem(STORAGE_KEY, value);
  }, []);

  return [location, setLocation];
}

export { DEFAULT_LOCATION };
