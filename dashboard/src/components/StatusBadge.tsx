import type { SLAStatus } from "../types";
import { STATUS_META } from "../utils";

/** Small colour square; never used without the text label next to it. */
export function StatusIcon({ status }: { status: SLAStatus }) {
  return <span className="status-mark" style={{ background: STATUS_META[status].color }} aria-hidden="true" />;
}

export function StatusBadge({ status }: { status: SLAStatus }) {
  return (
    <span className={`status status-${status}`}>
      <StatusIcon status={status} />
      {STATUS_META[status].label}
    </span>
  );
}
