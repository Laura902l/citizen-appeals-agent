import { useEffect, useState } from "react";

export type Route = "overview" | "appeals" | "review" | "model";
const ROUTES: Route[] = ["overview", "appeals", "review", "model"];

function current(): Route {
  const value = window.location.hash.replace(/^#\/?/, "") as Route;
  return ROUTES.includes(value) ? value : "overview";
}

/** Tiny hash router: pages are linkable (#/appeals) without a routing dependency. */
export function useHashRoute(): [Route, (r: Route) => void] {
  const [route, setRoute] = useState<Route>(current);
  useEffect(() => {
    const onChange = () => setRoute(current());
    window.addEventListener("hashchange", onChange);
    return () => window.removeEventListener("hashchange", onChange);
  }, []);
  const navigate = (r: Route) => {
    window.location.hash = `/${r}`;
    setRoute(r);
  };
  return [route, navigate];
}
