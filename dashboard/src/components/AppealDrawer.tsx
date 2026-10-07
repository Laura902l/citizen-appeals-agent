import { useEffect } from "react";
import type { Appeal } from "../types";
import { capitalize, daysLeftLabel, formatDate, isOpen, parseISO } from "../utils";
import { CloseControl } from "./CloseControl";
import { ReviewControl } from "./ReviewControl";
import { StatusBadge } from "./StatusBadge";

interface Props {
  appeal: Appeal;
  today: string;
  categories: string[];
  /** Closes the panel (not the appeal). */
  onClose: () => void;
  onReview: (id: string, category: string) => Promise<void>;
  onCloseAppeal: (id: string) => Promise<void>;
}

/** Side panel with the full record of one appeal and its SLA timeline. */
export function AppealDrawer({ appeal: a, today, categories, onClose, onReview, onCloseAppeal }: Props) {
  useEffect(() => {
    const onKey = (e: KeyboardEvent) => e.key === "Escape" && onClose();
    window.addEventListener("keydown", onKey);
    return () => window.removeEventListener("keydown", onKey);
  }, [onClose]);

  return (
    <>
      <div className="drawer-backdrop" onClick={onClose} />
      <aside className="drawer" role="dialog" aria-modal="true" aria-label={`Appeal ${a.appeal_id}`}>
        <header className="drawer-head">
          <div>
            <h2>
              Appeal No. <span className="mono">{a.appeal_id}</span>
            </h2>
          </div>
          <button type="button" className="icon-btn" aria-label="Close" onClick={onClose}>
            ×
          </button>
        </header>

        <div className="drawer-body">
          <div className="drawer-status">
            <StatusBadge status={a.status} />
            <span className="muted">{daysLeftLabel(a)}</span>
            {a.urgent && <span className="text-urgent">Urgent (shortened term)</span>}
          </div>

          <Timeline submitted={a.submitted_on} deadline={a.deadline} today={a.closed_on ?? today} />

          <section>
            <h3>Appeal text</h3>
            <blockquote className="quote">{a.masked_text}</blockquote>
            <p className="cell-sub">Personal data (names, phone numbers, e-mails) masked at intake.</p>
          </section>

          <dl className="facts">
            <div>
              <dt>Location</dt>
              <dd>{a.location || "—"}</dd>
            </div>
            <div>
              <dt>Received</dt>
              <dd>{formatDate(a.submitted_on)}</dd>
            </div>
            <div>
              <dt>Regulatory deadline</dt>
              <dd>{formatDate(a.deadline)}</dd>
            </div>
            {a.closed_on && (
              <div>
                <dt>Closed</dt>
                <dd>{formatDate(a.closed_on)}</dd>
              </div>
            )}
            <div>
              <dt>Remaining</dt>
              <dd>{a.remaining_business_days} business days</dd>
            </div>
            <div>
              <dt>Category</dt>
              <dd>
                {capitalize(a.category)}
                {a.reviewed && <span className="muted">verified by operator</span>}
              </dd>
            </div>
            <div>
              <dt>Model confidence</dt>
              <dd>
                <span className="meter" aria-hidden="true">
                  <span style={{ width: `${a.confidence * 100}%` }} />
                </span>
                {(a.confidence * 100).toFixed(0)}%
              </dd>
            </div>
          </dl>

          {a.needs_review && (
            <section className="callout">
              <h3>Category not confirmed</h3>
              <p>
                Model confidence {(a.confidence * 100).toFixed(0)}% is below the threshold. Check
                the category; the deadline will be recalculated.
              </p>
              <ReviewControl appeal={a} categories={categories} onReview={onReview} />
            </section>
          )}

          {isOpen(a) && (
            <section>
              <h3>Processing</h3>
              <CloseControl appeal={a} today={today} onCloseAppeal={onCloseAppeal} />
            </section>
          )}

          <section>
            <h3>Audit</h3>
            <dl className="facts facts-1">
              <div>
                <dt>Decision source</dt>
                <dd>{a.reviewed ? "Operator (review queue)" : "Automated classifier"}</dd>
              </div>
              <div>
                <dt>Model version</dt>
                <dd className="mono">{a.model_version}</dd>
              </div>
            </dl>
          </section>
        </div>
      </aside>
    </>
  );
}

function Timeline({ submitted, deadline, today }: { submitted: string; deadline: string; today: string }) {
  const t0 = parseISO(submitted).getTime();
  const t1 = parseISO(deadline).getTime();
  const tn = parseISO(today).getTime();
  const end = Math.max(t1, tn);
  const pos = (t: number) => `${((t - t0) / Math.max(1, end - t0)) * 100}%`;
  const overdue = tn > t1;
  return (
    <div className="timeline" aria-label="SLA timeline">
      <div className="timeline-track">
        <span className="timeline-fill" style={{ width: pos(Math.min(tn, t1)) }} />
        {overdue && (
          <span className="timeline-over" style={{ left: pos(t1), width: `calc(${pos(tn)} - ${pos(t1)})` }} />
        )}
        <span className="timeline-dot" style={{ left: "0%" }} />
        <span className="timeline-dot timeline-dot-deadline" style={{ left: pos(t1) }} />
        <span className="timeline-today" style={{ left: pos(tn) }} />
      </div>
      <div className="timeline-labels">
        <span>Received {formatDate(submitted)}</span>
        <span>
          {overdue ? "Deadline passed" : "Deadline"} {formatDate(deadline)}
        </span>
      </div>
    </div>
  );
}
