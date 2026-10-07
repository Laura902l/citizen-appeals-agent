import type { Appeal, AppConfig, Filters, Metrics, SLAStatus, Sort, SortKey, Summary } from "../types";
import { capitalize, fmtInt, percent, sortAppeals, STATUS_META } from "../utils";
import { AppealsTable } from "../components/AppealsTable";
import { DeadlineChart, StatusByCategoryChart } from "../components/Charts";
import { KpiStrip } from "../components/KpiStrip";
import { Panel } from "../components/Layout";
import { ReviewControl } from "../components/ReviewControl";
import { StatusBadge } from "../components/StatusBadge";
import { useTooltip } from "../components/Tooltip";

const PRIORITY: Sort = { key: "priority", dir: "asc" };

/* ------------------------------------------------------------------ overview */

export function OverviewPage({
  summary,
  appeals,
  config,
  onDrill,
  onOpen,
}: {
  summary: Summary;
  appeals: Appeal[];
  config: AppConfig;
  onDrill: (patch: Partial<Filters>) => void;
  onOpen: (a: Appeal) => void;
}) {
  const critical = sortAppeals(
    appeals.filter((a) => a.status === "overdue" || a.status === "at_risk"),
    PRIORITY,
  ).slice(0, 8);
  return (
    <div className="stack">
      <KpiStrip
        summary={summary}
        onOpen={(key) =>
          onDrill(key === "review" ? { reviewOnly: true } : { status: key as SLAStatus })
        }
      />
      <div className="grid-2">
        <Panel title="Open appeals by category">
          <StatusByCategoryChart
            appeals={appeals}
            categories={config.categories}
            onSelect={(category, status) => onDrill({ category, status: status ?? "open" })}
          />
        </Panel>
        <Panel title="Deadline calendar">
          <DeadlineChart appeals={appeals} today={summary.today} />
        </Panel>
      </div>
      <Panel
        title="Overdue and at risk"
        className="panel-flush"
        aside={
          <button type="button" className="link" onClick={() => onDrill({ status: "open" })}>
            All open appeals
          </button>
        }
      >
        <AppealsTable appeals={critical} sort={PRIORITY} onSort={() => {}} onOpen={onOpen} sortable={false} />
      </Panel>
    </div>
  );
}

/* ------------------------------------------------------------------ register */

export function AppealsPage({
  appeals,
  total,
  config,
  filters,
  sort,
  onFilters,
  onReset,
  onSort,
  onOpen,
  selectedId,
}: {
  appeals: Appeal[];
  total: number;
  config: AppConfig;
  filters: Filters;
  sort: Sort;
  onFilters: (patch: Partial<Filters>) => void;
  onReset: () => void;
  onSort: (key: SortKey) => void;
  onOpen: (a: Appeal) => void;
  selectedId?: string;
}) {
  const active =
    filters.query || filters.category || filters.status || filters.reviewOnly || filters.urgentOnly;
  return (
    <Panel title="Search" className="panel-flush panel-plain">
      <div className="toolbar" role="search">
        <label className="search">
          <input
            type="search"
            placeholder="No., text or address"
            aria-label="Search appeals"
            value={filters.query}
            onChange={(e) => onFilters({ query: e.target.value })}
          />
        </label>
        <select
          className="input"
          aria-label="Category"
          value={filters.category}
          onChange={(e) => onFilters({ category: e.target.value })}
        >
          <option value="">All categories</option>
          {config.categories.map((c) => (
            <option key={c} value={c}>
              {capitalize(c)}
            </option>
          ))}
        </select>
        <select
          className="input"
          aria-label="SLA status"
          value={filters.status}
          onChange={(e) => onFilters({ status: e.target.value as Filters["status"] })}
        >
          <option value="">All statuses</option>
          <option value="open">Open (not closed)</option>
          {config.statuses.map((s) => (
            <option key={s} value={s}>
              {STATUS_META[s].label}
            </option>
          ))}
        </select>
        <label className="check">
          <input
            type="checkbox"
            checked={filters.reviewOnly}
            onChange={(e) => onFilters({ reviewOnly: e.target.checked })}
          />
          Unconfirmed only
        </label>
        <label className="check">
          <input
            type="checkbox"
            checked={filters.urgentOnly}
            onChange={(e) => onFilters({ urgentOnly: e.target.checked })}
          />
          Urgent only
        </label>
        {active && (
          <button type="button" className="btn btn-quiet" onClick={onReset}>
            Reset
          </button>
        )}
        <span className="toolbar-count" aria-live="polite">
          Found: {fmtInt(appeals.length)} of {fmtInt(total)}
        </span>
      </div>
      <AppealsTable
        appeals={appeals}
        sort={sort}
        onSort={onSort}
        onOpen={onOpen}
        selectedId={selectedId}
      />
    </Panel>
  );
}

/* ------------------------------------------------------------------ review */

export function ReviewPage({
  appeals,
  config,
  onReview,
  onOpen,
}: {
  appeals: Appeal[];
  config: AppConfig;
  onReview: (id: string, category: string) => Promise<void>;
  onOpen: (a: Appeal) => void;
}) {
  const queue = sortAppeals(
    appeals.filter((a) => a.needs_review),
    PRIORITY,
  );
  return (
    <Panel title={`Unconfirmed classifications: ${fmtInt(queue.length)}`} className="panel-flush">
      {queue.length === 0 ? (
        <p className="empty">The review queue is empty.</p>
      ) : (
        <ul className="queue">
          {queue.slice(0, 50).map((a) => (
            <li key={a.appeal_id} className="queue-item">
              <div className="queue-main">
                <div className="queue-meta">
                  <button type="button" className="link mono" onClick={() => onOpen(a)}>
                    {a.appeal_id}
                  </button>
                  <StatusBadge status={a.status} />
                  <span className="muted">
                    Model suggests {capitalize(a.category)}, {(a.confidence * 100).toFixed(0)}%
                  </span>
                  {a.urgent && <span className="text-urgent">Urgent</span>}
                </div>
                <p className="queue-text">{a.masked_text}</p>
              </div>
              <ReviewControl appeal={a} categories={config.categories} onReview={onReview} />
            </li>
          ))}
        </ul>
      )}
      {queue.length > 50 && (
        <p className="cell-sub pad">First 50 of {fmtInt(queue.length)} shown, most urgent first.</p>
      )}
    </Panel>
  );
}

/* ------------------------------------------------------------------ model */

export function ModelPage({
  metrics,
  liveMetrics,
  version,
}: {
  metrics: Metrics | null;
  liveMetrics: Metrics | null;
  version: string;
}) {
  return (
    <div className="stack">
      <h2 className="section-title">Test set (at training)</h2>
      {metrics ? (
        <div className="stack">
          <MetricFigures metrics={metrics} label="Test set metrics" />
          <div className="grid-2">
            <ConfusionMatrix metrics={metrics} />
            <Panel title="Evaluation">
              <dl className="facts facts-1">
                <div>
                  <dt>Model</dt>
                  <dd>TF-IDF (word 1–2-grams) + logistic regression</dd>
                </div>
                <div>
                  <dt>Version</dt>
                  <dd className="mono">{metrics.model_version ?? version}</dd>
                </div>
                <div>
                  <dt>Training / test appeals</dt>
                  <dd>
                    {metrics.n_train !== undefined ? fmtInt(metrics.n_train) : "—"} / {fmtInt(metrics.n_test)}
                  </dd>
                </div>
                <div>
                  <dt>Random seed</dt>
                  <dd>{metrics.seed ?? "—"}</dd>
                </div>
                <div>
                  <dt>Data</dt>
                  <dd>Simulated appeals; results on real appeals are expected to be lower.</dd>
                </div>
              </dl>
            </Panel>
          </div>
        </div>
      ) : (
        <Panel title="Test set">
          <p className="empty">
            No evaluation metrics available. Run <code>appeal-agent train</code> first.
          </p>
        </Panel>
      )}

      <h2 className="section-title">Current data (appeals being served)</h2>
      {liveMetrics ? (
        <div className="stack">
          <MetricFigures metrics={liveMetrics} label="Current data metrics" />
          <div className="grid-2">
            <ConfusionMatrix metrics={liveMetrics} />
            <Panel title="About this check">
              <dl className="facts facts-1">
                <div>
                  <dt>Data file</dt>
                  <dd className="mono">{liveMetrics.source ?? "—"}</dd>
                </div>
                <div>
                  <dt>Appeals with a known category</dt>
                  <dd>{fmtInt(liveMetrics.n_test)}</dd>
                </div>
                <div>
                  <dt>Without a category (not checked)</dt>
                  <dd>{fmtInt(liveMetrics.n_unlabelled ?? 0)}</dd>
                </div>
                <div>
                  <dt>How to read it</dt>
                  <dd>
                    The model's category is compared with the category stored in the data file, once
                    at server start. If this is the training file, most of these appeals were seen
                    during training and the figures are optimistic; serve a file generated with
                    another seed to check the model on unseen appeals.
                  </dd>
                </div>
              </dl>
            </Panel>
          </div>
        </div>
      ) : (
        <Panel title="Current data">
          <p className="empty">
            The served appeals have no known category, so the model cannot be checked against them.
          </p>
        </Panel>
      )}
    </div>
  );
}

function MetricFigures({ metrics, label }: { metrics: Metrics; label: string }) {
  const items = [
    { label: "Accuracy", value: percent(metrics.accuracy) },
    { label: "Macro F1", value: percent(metrics.macro_f1) },
    { label: "Sent to review", value: percent(metrics.review_rate) },
    { label: "Auto-accepted accuracy", value: percent(metrics.auto_accepted_accuracy) },
  ];
  return (
    <section className="kpis kpis-4" aria-label={label}>
      {items.map((i) => (
        <div key={i.label} className="kpi kpi-static">
          <span className="kpi-label">{i.label}</span>
          <span className="kpi-value">{i.value}</span>
        </div>
      ))}
    </section>
  );
}

function ConfusionMatrix({ metrics }: { metrics: Metrics }) {
  const tip = useTooltip();
  const labels = metrics.labels ?? [];
  const cm = metrics.confusion_matrix ?? [];
  const rowMax = Math.max(1, ...cm.flat());
  return (
    <Panel title="Confusion matrix (rows: actual, columns: predicted)">
      <div className="table-wrap">
        <table className="matrix">
          <thead>
            <tr>
              <th />
              {labels.map((l) => (
                <th key={l} scope="col">
                  {capitalize(l)}
                </th>
              ))}
            </tr>
          </thead>
          <tbody>
            {cm.map((row, i) => (
              <tr key={labels[i]}>
                <th scope="row">{capitalize(labels[i])}</th>
                {row.map((v, j) => (
                  <td
                    key={labels[j]}
                    className={i === j ? "diag" : v ? "miss" : undefined}
                    style={{ "--level": v / rowMax } as React.CSSProperties}
                    onMouseMove={(e) =>
                      tip.show(
                        e,
                        <>
                          <strong>
                            {capitalize(labels[i])} → {capitalize(labels[j])}
                          </strong>
                          <span className="tooltip-row">
                            Appeals <b>{v}</b>
                          </span>
                        </>,
                      )
                    }
                    onMouseLeave={tip.hide}
                  >
                    {v}
                  </td>
                ))}
              </tr>
            ))}
          </tbody>
        </table>
      </div>
    </Panel>
  );
}
