import { useEffect, useState } from "react";
import type { Appeal, Sort, SortKey } from "../types";
import { capitalize, formatDate, workingDaysLeft } from "../utils";
import { StatusBadge } from "./StatusBadge";

interface Props {
  appeals: Appeal[];
  sort: Sort;
  onSort: (key: SortKey) => void;
  onOpen: (appeal: Appeal) => void;
  selectedId?: string;
  pageSize?: number;
  sortable?: boolean;
}

const COLUMNS: { key?: SortKey; label: string; className?: string }[] = [
  { label: "No." },
  { key: "priority", label: "Status" },
  { key: "submitted_on", label: "Received" },
  { key: "category", label: "Category" },
  { label: "Priority" },
  { label: "Subject", className: "col-text" },
  { key: "deadline", label: "Deadline" },
  { label: "Days left", className: "num" },
  { key: "confidence", label: "Conf.", className: "num" },
];

export function AppealsTable({
  appeals,
  sort,
  onSort,
  onOpen,
  selectedId,
  pageSize = 25,
  sortable = true,
}: Props) {
  const [page, setPage] = useState(0);
  const pages = Math.max(1, Math.ceil(appeals.length / pageSize));
  useEffect(() => setPage(0), [appeals.length, sort.key, sort.dir]);
  const rows = appeals.slice(page * pageSize, (page + 1) * pageSize);

  if (appeals.length === 0) {
    return <p className="empty">No appeals found.</p>;
  }

  return (
    <>
      <div className="table-wrap">
        <table className="table">
          <thead>
            <tr>
              {COLUMNS.map((c) => {
                const active = sortable && c.key && sort.key === c.key;
                return (
                  <th
                    key={c.label}
                    className={c.className}
                    aria-sort={active ? (sort.dir === "asc" ? "ascending" : "descending") : undefined}
                  >
                    {sortable && c.key ? (
                      <button type="button" className="th-sort" onClick={() => onSort(c.key!)}>
                        {c.label}
                        <span className="sort-arrow" aria-hidden="true">
                          {active ? (sort.dir === "asc" ? "▲" : "▼") : ""}
                        </span>
                      </button>
                    ) : (
                      c.label
                    )}
                  </th>
                );
              })}
            </tr>
          </thead>
          <tbody>
            {rows.map((a) => (
              <tr
                key={a.appeal_id}
                className={a.appeal_id === selectedId ? "row-selected" : undefined}
                onClick={() => onOpen(a)}
              >
                <td className="nowrap">
                  <button
                    type="button"
                    className="link mono"
                    onClick={(e) => {
                      e.stopPropagation();
                      onOpen(a);
                    }}
                  >
                    {a.appeal_id}
                  </button>
                </td>
                <td>
                  <StatusBadge status={a.status} />
                </td>
                <td className="nowrap">{formatDate(a.submitted_on)}</td>
                <td className="nowrap">
                  {capitalize(a.category)}
                  {a.needs_review && <span className="note-review"> (unconfirmed)</span>}
                </td>
                <td className={a.urgent ? "text-urgent" : "muted"}>{a.urgent ? "Urgent" : "Normal"}</td>
                <td className="col-text">
                  <div className="clamp">{a.masked_text}</div>
                  <div className="cell-sub">{a.location}</div>
                </td>
                <td className="nowrap">{formatDate(a.deadline)}</td>
                <td className="num">
                  <DaysLeft appeal={a} />
                </td>
                <td className="num muted">{a.reviewed ? "verified" : `${(a.confidence * 100).toFixed(0)}%`}</td>
              </tr>
            ))}
          </tbody>
        </table>
      </div>
      {pages > 1 && (
        <nav className="pager" aria-label="Pagination">
          <span className="pager-info">
            Records {page * pageSize + 1}–{Math.min((page + 1) * pageSize, appeals.length)} of{" "}
            {appeals.length.toLocaleString("en-US")}
          </span>
          <button type="button" className="btn" disabled={page === 0} onClick={() => setPage(0)}>
            «
          </button>
          <button type="button" className="btn" disabled={page === 0} onClick={() => setPage((p) => p - 1)}>
            Previous
          </button>
          <span className="pager-info">
            {page + 1} / {pages}
          </span>
          <button
            type="button"
            className="btn"
            disabled={page >= pages - 1}
            onClick={() => setPage((p) => p + 1)}
          >
            Next
          </button>
          <button
            type="button"
            className="btn"
            disabled={page >= pages - 1}
            onClick={() => setPage(pages - 1)}
          >
            »
          </button>
        </nav>
      )}
    </>
  );
}

/** Signed working-days figure with a short bar: red grows with lateness, grey with time left. */
function DaysLeft({ appeal: a }: { appeal: Appeal }) {
  const closed = a.status === "closed_on_time" || a.status === "closed_late";
  const overdue = a.status === "overdue";
  const n = Math.abs(a.remaining_business_days);
  const width = closed ? 0 : Math.min(1, (overdue ? Math.max(1, n) : n) / 25) * 100;
  return (
    <span className={`days${overdue ? " days-over" : ""}`}>
      <span className="days-track" aria-hidden="true">
        {!closed && <span className="days-bar" style={{ width: `${width}%` }} />}
      </span>
      <span className="days-value">{workingDaysLeft(a)}</span>
    </span>
  );
}
