import { useState } from "react";
import type { Appeal } from "../types";
import { formatDate } from "../utils";

interface Props {
  appeal: Appeal;
  today: string;
  onCloseAppeal: (id: string) => Promise<void>;
}

/** Operator closes an open appeal; asks for confirmation because closing cannot be undone. */
export function CloseControl({ appeal, today, onCloseAppeal }: Props) {
  const [confirming, setConfirming] = useState(false);
  const [busy, setBusy] = useState(false);
  if (!confirming) {
    return (
      <button type="button" className="btn btn-primary" onClick={() => setConfirming(true)}>
        Close appeal
      </button>
    );
  }
  return (
    <div className="close-control">
      <p>
        Close appeal <span className="mono">{appeal.appeal_id}</span> as of {formatDate(today)}? This
        cannot be undone.
      </p>
      <div className="review-control">
        <button
          type="button"
          className="btn btn-primary"
          disabled={busy}
          onClick={async () => {
            setBusy(true);
            try {
              await onCloseAppeal(appeal.appeal_id);
            } finally {
              setBusy(false);
              setConfirming(false);
            }
          }}
        >
          Confirm closing
        </button>
        <button type="button" className="btn" disabled={busy} onClick={() => setConfirming(false)}>
          Cancel
        </button>
      </div>
    </div>
  );
}
