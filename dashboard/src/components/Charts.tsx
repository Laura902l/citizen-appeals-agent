import type { Appeal, SLAStatus } from "../types";
import {
  capitalize,
  dueByDay,
  fmtInt,
  formatDate,
  isWeekend,
  OPEN_STATUSES,
  parseISO,
  STATUS_META,
  statusByCategory,
  toISO,
  weekday,
} from "../utils";
import { StatusIcon } from "./StatusBadge";
import { useTooltip } from "./Tooltip";

function Legend({ statuses }: { statuses: SLAStatus[] }) {
  return (
    <ul className="legend">
      {statuses.map((s) => (
        <li key={s}>
          <StatusIcon status={s} />
          {STATUS_META[s].label}
        </li>
      ))}
    </ul>
  );
}

/** Horizontal stacked bars: open appeals per category split by SLA status. */
export function StatusByCategoryChart({
  appeals,
  categories,
  onSelect,
}: {
  appeals: Appeal[];
  categories: string[];
  onSelect: (category: string, status?: SLAStatus) => void;
}) {
  const tip = useTooltip();
  const rows = statusByCategory(appeals, categories);
  const max = Math.max(1, ...rows.map((r) => r.open));
  return (
    <div className="chart">
      <Legend statuses={OPEN_STATUSES} />
      <div className="hbars" role="list">
        <div className="hbar-row hbar-head" aria-hidden="true">
          <span />
          <span />
          <span>Open</span>
          <span>Overdue</span>
        </div>
        {rows.map((row) => (
          <div key={row.category} className="hbar-row" role="listitem">
            <button type="button" className="hbar-label" onClick={() => onSelect(row.category)}>
              {capitalize(row.category)}
            </button>
            <div className="hbar-track">
              {OPEN_STATUSES.map((s) =>
                row.counts[s] ? (
                  <button
                    key={s}
                    type="button"
                    className="hbar-seg"
                    style={{ width: `${(row.counts[s] / max) * 100}%`, background: STATUS_META[s].color }}
                    aria-label={`${capitalize(row.category)}, ${STATUS_META[s].label}: ${row.counts[s]}`}
                    onMouseMove={(e) =>
                      tip.show(
                        e,
                        <>
                          <strong>{capitalize(row.category)}</strong>
                          <span className="tooltip-row">
                            <StatusIcon status={s} /> {STATUS_META[s].label}
                            <b>{fmtInt(row.counts[s])}</b>
                          </span>
                          <span className="tooltip-muted">
                            {((row.counts[s] / row.open) * 100).toFixed(0)}% of open in category
                          </span>
                        </>,
                      )
                    }
                    onMouseLeave={tip.hide}
                    onClick={() => onSelect(row.category, s)}
                  />
                ) : null,
              )}
            </div>
            <span className="hbar-total">{fmtInt(row.open)}</span>
            <span className="hbar-share">
              {row.open ? `${Math.round((row.counts.overdue / row.open) * 100)}%` : "—"}
            </span>
          </div>
        ))}
      </div>
    </div>
  );
}

const WEEKDAYS = ["Mon", "Tue", "Wed", "Thu", "Fri", "Sat", "Sun"];

/**
 * Three-week calendar of regulatory deadlines for open appeals.
 * Shade (one hue, light to dark) encodes how many appeals fall due on the day.
 */
export function DeadlineChart({ appeals, today }: { appeals: Appeal[]; today: string }) {
  const tip = useTooltip();
  const t = parseISO(today);
  const monday = new Date(t);
  monday.setDate(t.getDate() - ((t.getDay() + 6) % 7));
  const days = dueByDay(appeals, toISO(monday), 21);
  const upcoming = days.filter((d) => d.date >= today);
  const max = Math.max(1, ...upcoming.map((d) => d.count));

  return (
    <div className="chart">
      <div className="cal" role="grid" aria-label="Deadlines calendar">
        <div className="cal-row cal-weekdays" role="row">
          {WEEKDAYS.map((w) => (
            <span key={w} role="columnheader">
              {w}
            </span>
          ))}
        </div>
        {[0, 1, 2].map((week) => (
          <div key={week} className="cal-row" role="row">
            {days.slice(week * 7, week * 7 + 7).map((d) => {
              const past = d.date < today;
              const level = d.count / max;
              const cls = [
                "cal-cell",
                past && "cal-past",
                d.date === today && "cal-today",
                isWeekend(d.date) && "cal-weekend",
                !past && level > 0.5 && "cal-dark",
              ]
                .filter(Boolean)
                .join(" ");
              return (
                <div
                  key={d.date}
                  role="gridcell"
                  tabIndex={past ? -1 : 0}
                  className={cls}
                  style={
                    !past && d.count
                      ? {
                          background: `color-mix(in srgb, var(--series-1) ${Math.round(6 + level * 74)}%, var(--surface))`,
                        }
                      : undefined
                  }
                  aria-label={`${formatDate(d.date)}: ${d.count} due, ${d.atRisk} at risk`}
                  onMouseMove={(e) => {
                    if (past) return;
                    tip.show(
                      e,
                      <>
                        <strong>
                          {weekday(d.date)} {formatDate(d.date)}
                        </strong>
                        <span className="tooltip-row">
                          Fall due <b>{fmtInt(d.count)}</b>
                        </span>
                        <span className="tooltip-row">
                          <StatusIcon status="at_risk" /> At risk <b>{fmtInt(d.atRisk)}</b>
                        </span>
                        {isWeekend(d.date) && <span className="tooltip-muted">Non-working day</span>}
                      </>,
                    );
                  }}
                  onMouseLeave={tip.hide}
                >
                  <span className="cal-date">{parseISO(d.date).getDate()}</span>
                  {!past && d.count > 0 && <span className="cal-count">{d.count}</span>}
                  {!past && d.atRisk > 0 && <span className="cal-risk">{d.atRisk} at risk</span>}
                </div>
              );
            })}
          </div>
        ))}
      </div>

    </div>
  );
}
