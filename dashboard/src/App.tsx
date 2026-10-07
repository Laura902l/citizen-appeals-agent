import { useCallback, useEffect, useMemo, useState } from "react";
import { api } from "./api";
import { AppealDrawer } from "./components/AppealDrawer";
import { Layout } from "./components/Layout";
import { TooltipProvider } from "./components/Tooltip";
import { useHashRoute, type Route } from "./hooks/useHashRoute";
import { AppealsPage, ModelPage, OverviewPage, ReviewPage } from "./pages/Pages";
import type { AppConfig, Appeal, Filters, Metrics, Sort, SortKey, Summary } from "./types";
import { EMPTY_FILTERS } from "./types";
import { filterAppeals, sortAppeals } from "./utils";

interface Data {
  config: AppConfig;
  summary: Summary;
  appeals: Appeal[];
  metrics: Metrics | null;
}

const TITLES: Record<Route, string> = {
  overview: "Overview",
  appeals: "Appeals register",
  review: "Review queue",
  model: "Model quality",
};

export default function App() {
  const [route, navigate] = useHashRoute();
  const [data, setData] = useState<Data | null>(null);
  const [error, setError] = useState<string | null>(null);
  const [filters, setFilters] = useState<Filters>(EMPTY_FILTERS);
  const [sort, setSort] = useState<Sort>({ key: "priority", dir: "asc" });
  const [openId, setOpenId] = useState<string | null>(null);
  const [toast, setToast] = useState<string | null>(null);

  const load = useCallback(async () => {
    try {
      const [config, summary, appeals, metrics] = await Promise.all([
        api.config(),
        api.summary(),
        api.appeals(),
        api.metrics(),
      ]);
      setData({ config, summary, appeals, metrics });
      setError(null);
    } catch (e) {
      setError(e instanceof Error ? e.message : String(e));
    }
  }, []);

  useEffect(() => {
    void load();
  }, [load]);

  const visible = useMemo(
    () => (data ? sortAppeals(filterAppeals(data.appeals, filters), sort) : []),
    [data, filters, sort],
  );

  const drill = (patch: Partial<Filters>) => {
    setFilters({ ...EMPTY_FILTERS, ...patch });
    setSort({ key: "priority", dir: "asc" });
    navigate("appeals");
  };

  const toggleSort = (key: SortKey) =>
    setSort((s) => (s.key === key ? { key, dir: s.dir === "asc" ? "desc" : "asc" } : { key, dir: "asc" }));

  const review = async (id: string, category: string) => {
    try {
      const updated = await api.review(id, category);
      const summary = await api.summary();
      setData((d) =>
        d && { ...d, summary, appeals: d.appeals.map((a) => (a.appeal_id === id ? updated : a)) },
      );
      setToast(`Saved. ${id}: category “${category}”, deadline recalculated.`);
    } catch (e) {
      setToast(`Could not save: ${e instanceof Error ? e.message : e}`);
    }
    window.setTimeout(() => setToast(null), 3500);
  };

  const closeAppeal = async (id: string) => {
    try {
      const updated = await api.close(id);
      const summary = await api.summary();
      setData((d) =>
        d && { ...d, summary, appeals: d.appeals.map((a) => (a.appeal_id === id ? updated : a)) },
      );
      setToast(`Closed. ${id}: ${updated.status === "closed_late" ? "after" : "within"} the deadline.`);
    } catch (e) {
      setToast(`Could not close: ${e instanceof Error ? e.message : e}`);
    }
    window.setTimeout(() => setToast(null), 3500);
  };

  if (error) {
    return (
      <div className="fullscreen">
        <div className="panel error-panel" role="alert">
          <h1>Service unavailable</h1>
          <p>The monitoring service did not respond ({error}).</p>
          <p className="muted">
            Start the backend with <code>appeal-agent serve</code>, then retry.
          </p>
          <button type="button" className="btn btn-primary" onClick={() => void load()}>
            Retry
          </button>
        </div>
      </div>
    );
  }

  if (!data) {
    return (
      <div className="fullscreen" aria-busy="true">
        <p className="muted">Loading…</p>
      </div>
    );
  }

  const { config, summary, metrics, appeals } = data;
  const opened = openId ? appeals.find((a) => a.appeal_id === openId) : undefined;
  return (
    <TooltipProvider>
      <Layout
        route={route}
        onNavigate={navigate}
        reviewCount={summary.needs_review}
        today={summary.today}
        modelVersion={summary.model_version}
        title={TITLES[route]}
        onRefresh={() => void load()}
      >
        {route === "overview" && (
          <OverviewPage
            summary={summary}
            appeals={appeals}
            config={config}
            onDrill={drill}
            onOpen={(a) => setOpenId(a.appeal_id)}
          />
        )}
        {route === "appeals" && (
          <AppealsPage
            appeals={visible}
            total={appeals.length}
            config={config}
            filters={filters}
            sort={sort}
            onFilters={(patch) => setFilters((f) => ({ ...f, ...patch }))}
            onReset={() => setFilters(EMPTY_FILTERS)}
            onSort={toggleSort}
            onOpen={(a) => setOpenId(a.appeal_id)}
            selectedId={openId ?? undefined}
          />
        )}
        {route === "review" && (
          <ReviewPage
            appeals={appeals}
            config={config}
            onReview={review}
            onOpen={(a) => setOpenId(a.appeal_id)}
          />
        )}
        {route === "model" && <ModelPage metrics={metrics} version={summary.model_version} />}
      </Layout>

      {opened && (
        <AppealDrawer
          appeal={opened}
          today={summary.today}
          categories={config.categories}
          onClose={() => setOpenId(null)}
          onReview={review}
          onCloseAppeal={closeAppeal}
        />
      )}
      {toast && (
        <div className="toast" role="status">
          {toast}
        </div>
      )}
    </TooltipProvider>
  );
}
