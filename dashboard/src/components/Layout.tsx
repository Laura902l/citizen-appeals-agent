import type { ReactNode } from "react";
import type { Route } from "../hooks/useHashRoute";
import { fmtInt, formatDate } from "../utils";

const NAV: { route: Route; label: string }[] = [
  { route: "overview", label: "Overview" },
  { route: "appeals", label: "Appeals register" },
  { route: "review", label: "Review queue" },
  { route: "model", label: "Model quality" },
];

interface LayoutProps {
  route: Route;
  onNavigate: (r: Route) => void;
  reviewCount: number;
  today: string;
  modelVersion: string;
  title: string;
  children: ReactNode;
}

export function Layout({
  route,
  onNavigate,
  reviewCount,
  today,
  modelVersion,
  title,
  children,
}: LayoutProps) {
  return (
    <div className="shell">
      <aside className="sidebar">
        <div className="brand">
          <span className="brand-name">Appeals SLA Monitor</span>
        </div>
        <nav aria-label="Main">
          <ul className="nav">
            {NAV.map((item) => (
              <li key={item.route}>
                <a
                  href={`#/${item.route}`}
                  className={`nav-link${route === item.route ? " nav-link-active" : ""}`}
                  aria-current={route === item.route ? "page" : undefined}
                  onClick={(e) => {
                    e.preventDefault();
                    onNavigate(item.route);
                  }}
                >
                  <span>{item.label}</span>
                  {item.route === "review" && reviewCount > 0 && (
                    <span className="nav-count">{fmtInt(reviewCount)}</span>
                  )}
                </a>
              </li>
            ))}
          </ul>
        </nav>
        <dl className="sidebar-meta">
          <div>
            <dt>Data as of</dt>
            <dd>{formatDate(today)}</dd>
          </div>
          <div>
            <dt>Model version</dt>
            <dd className="mono">{modelVersion}</dd>
          </div>
        </dl>
      </aside>
      <div className="main">
        <header className="topbar">
          <h1>{title}</h1>
        </header>
        <main className="content">{children}</main>
      </div>
    </div>
  );
}

export function Panel({
  title,
  aside,
  children,
  className = "",
}: {
  title: string;
  aside?: ReactNode;
  children: ReactNode;
  className?: string;
}) {
  return (
    <section className={`panel ${className}`}>
      <header className="panel-head">
        <h2>{title}</h2>
        {aside}
      </header>
      {children}
    </section>
  );
}
