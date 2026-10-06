import type { SLAStatus, Summary } from "../types";
import { fmtInt, STATUS_META, STATUS_ORDER } from "../utils";
import { StatusIcon } from "./StatusBadge";
import { useTooltip } from "./Tooltip";

interface Props {
  summary: Summary;
  onOpen: (status: SLAStatus | "review") => void;
}

/** Five status figures over one bar that splits all appeals by SLA status. */
export function KpiStrip({ summary, onOpen }: Props) {
  const tip = useTooltip();
  const s = summary.by_status;
  const pct = (n: number) => (summary.total ? `${((n / summary.total) * 100).toFixed(1)}%` : "—");

  return (
    <section className="summary" aria-label="Key figures">
      <div className="summary-figures">
        {STATUS_ORDER.map((status) => (
          <button
            key={status}
            type="button"
            className={`figure figure-${status}`}
            onClick={() => onOpen(status)}
          >
            <span className="figure-label">
              <StatusIcon status={status} />
              {STATUS_META[status].label}
            </span>
            <span className="figure-value">{fmtInt(s[status])}</span>
            <span className="figure-pct">{pct(s[status])}</span>
          </button>
        ))}
      </div>
      <div className="dist" role="img" aria-label="All appeals by SLA status">
        {STATUS_ORDER.map((status) =>
          s[status] ? (
            <span
              key={status}
              className="dist-seg"
              style={{ flexGrow: s[status], background: STATUS_META[status].color }}
              onMouseMove={(e) =>
                tip.show(
                  e,
                  <>
                    <strong>{STATUS_META[status].label}</strong>
                    <span className="tooltip-row">
                      Appeals <b>{fmtInt(s[status])}</b>
                    </span>
                    <span className="tooltip-row">
                      Share <b>{pct(s[status])}</b>
                    </span>
                  </>,
                )
              }
              onMouseLeave={tip.hide}
              onClick={() => onOpen(status)}
            />
          ) : null,
        )}
      </div>
    </section>
  );
}
