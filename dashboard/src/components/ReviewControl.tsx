import { useState } from "react";
import type { Appeal } from "../types";
import { capitalize } from "../utils";

interface Props {
  appeal: Appeal;
  categories: string[];
  onReview: (id: string, category: string) => Promise<void>;
}

/** Operator decision for a low-confidence classification (FR7). */
export function ReviewControl({ appeal, categories, onReview }: Props) {
  const [choice, setChoice] = useState(appeal.category);
  const [busy, setBusy] = useState(false);
  const changed = choice !== appeal.category;
  return (
    <div className="review-control">
      <select
        className="input"
        aria-label={`Category for ${appeal.appeal_id}`}
        value={choice}
        onChange={(e) => setChoice(e.target.value)}
      >
        {categories.map((c) => (
          <option key={c} value={c}>
            {capitalize(c)}
            {c === appeal.category ? " (model)" : ""}
          </option>
        ))}
      </select>
      <button
        type="button"
        className="btn btn-primary"
        disabled={busy}
        onClick={async () => {
          setBusy(true);
          try {
            await onReview(appeal.appeal_id, choice);
          } finally {
            setBusy(false);
          }
        }}
      >
        {changed ? "Correct label" : "Confirm"}
      </button>
    </div>
  );
}
