import type { Appeal, Filters, SLAStatus, Sort } from "./types";

export interface StatusMeta {
  label: string;
  /** CSS custom property holding the reserved status colour. */
  color: string;
}

// Status colours are reserved for state and are always shown with an icon and a label.
export const STATUS_META: Record<SLAStatus, StatusMeta> = {
  overdue: { label: "Overdue", color: "var(--status-critical)" },
  at_risk: { label: "At risk", color: "var(--status-warning)" },
  on_track: { label: "On track", color: "var(--status-good)" },
  closed_late: { label: "Closed late", color: "var(--status-serious)" },
  closed_on_time: { label: "Closed on time", color: "var(--status-neutral)" },
};

/** Most urgent first: the order in which an operator should act. */
export const STATUS_ORDER: SLAStatus[] = [
  "overdue",
  "at_risk",
  "on_track",
  "closed_late",
  "closed_on_time",
];

export const OPEN_STATUSES: SLAStatus[] = ["overdue", "at_risk", "on_track"];

export const isOpen = (a: Pick<Appeal, "status">) => OPEN_STATUSES.includes(a.status);

export function filterAppeals(appeals: Appeal[], f: Filters): Appeal[] {
  const needle = f.query.trim().toLowerCase();
  return appeals.filter((a) => {
    if (f.category && a.category !== f.category) return false;
    if (f.status === "open" && !isOpen(a)) return false;
    if (f.status && f.status !== "open" && a.status !== f.status) return false;
    if (f.reviewOnly && !a.needs_review) return false;
    if (f.urgentOnly && !a.urgent) return false;
    if (
      needle &&
      !a.masked_text.toLowerCase().includes(needle) &&
      !a.location.toLowerCase().includes(needle) &&
      !a.appeal_id.toLowerCase().includes(needle)
    ) {
      return false;
    }
    return true;
  });
}

function priorityCompare(a: Appeal, b: Appeal): number {
  return (
    STATUS_ORDER.indexOf(a.status) - STATUS_ORDER.indexOf(b.status) ||
    a.remaining_business_days - b.remaining_business_days ||
    a.appeal_id.localeCompare(b.appeal_id)
  );
}

export function sortAppeals(appeals: Appeal[], sort: Sort): Appeal[] {
  const dir = sort.dir === "asc" ? 1 : -1;
  const compare: Record<Sort["key"], (a: Appeal, b: Appeal) => number> = {
    priority: priorityCompare,
    deadline: (a, b) => a.deadline.localeCompare(b.deadline) || priorityCompare(a, b),
    submitted_on: (a, b) =>
      a.submitted_on.localeCompare(b.submitted_on) || priorityCompare(a, b),
    confidence: (a, b) => a.confidence - b.confidence || priorityCompare(a, b),
    category: (a, b) => a.category.localeCompare(b.category) || priorityCompare(a, b),
  };
  return [...appeals].sort((a, b) => dir * compare[sort.key](a, b));
}

/** Count of appeals per category and status, categories ordered by open workload. */
export function statusByCategory(
  appeals: Appeal[],
  categories: string[],
): { category: string; counts: Record<SLAStatus, number>; open: number }[] {
  const rows = categories.map((category) => {
    const counts = Object.fromEntries(STATUS_ORDER.map((s) => [s, 0])) as Record<
      SLAStatus,
      number
    >;
    for (const a of appeals) if (a.category === category) counts[a.status] += 1;
    return { category, counts, open: counts.overdue + counts.at_risk + counts.on_track };
  });
  return rows.sort((a, b) => b.open - a.open || a.category.localeCompare(b.category));
}

/** Open (not overdue) appeals grouped by deadline date, from `today` for `days` calendar days. */
export function dueByDay(
  appeals: Appeal[],
  today: string,
  days: number,
): { date: string; count: number; atRisk: number }[] {
  const start = parseISO(today);
  const result = Array.from({ length: days }, (_, i) => {
    const d = new Date(start);
    d.setDate(start.getDate() + i);
    return { date: toISO(d), count: 0, atRisk: 0 };
  });
  const index = new Map(result.map((r, i) => [r.date, i]));
  for (const a of appeals) {
    if (a.status !== "on_track" && a.status !== "at_risk") continue;
    const i = index.get(a.deadline);
    if (i === undefined) continue;
    result[i].count += 1;
    if (a.status === "at_risk") result[i].atRisk += 1;
  }
  return result;
}

export function parseISO(iso: string): Date {
  const [y, m, d] = iso.split("-").map(Number);
  return new Date(y, m - 1, d);
}

export function toISO(d: Date): string {
  const pad = (n: number) => String(n).padStart(2, "0");
  return `${d.getFullYear()}-${pad(d.getMonth() + 1)}-${pad(d.getDate())}`;
}

const pad2 = (n: number) => String(n).padStart(2, "0");
const WEEKDAY_FMT = new Intl.DateTimeFormat("en-GB", { weekday: "short" });

/** Local administrative date format: 05.10.2026 */
export const formatDate = (iso: string) => {
  const d = parseISO(iso);
  return `${pad2(d.getDate())}.${pad2(d.getMonth() + 1)}.${d.getFullYear()}`;
};
export const formatShort = (iso: string) => formatDate(iso).slice(0, 5);
export const weekday = (iso: string) => WEEKDAY_FMT.format(parseISO(iso));
export const isWeekend = (iso: string) => [0, 6].includes(parseISO(iso).getDay());

/** Working days left as a signed number; negative when overdue, a dash when closed. */
export function workingDaysLeft(a: Pick<Appeal, "status" | "remaining_business_days">): string {
  if (a.status === "closed_on_time" || a.status === "closed_late") return "—";
  const n = a.status === "overdue" ? Math.min(-1, a.remaining_business_days) : a.remaining_business_days;
  return n < 0 ? `\u2212${-n}` : String(n);
}

/** Sentence form used in the appeal record. */
export function daysLeftLabel(a: Pick<Appeal, "status" | "remaining_business_days">): string {
  const n = a.remaining_business_days;
  if (a.status === "closed_on_time" || a.status === "closed_late") return "Closed";
  if (a.status === "overdue") {
    const d = Math.max(1, -n);
    return `${d} working day${d === 1 ? "" : "s"} overdue`;
  }
  if (n === 0) return "Due today";
  return `${n} working day${n === 1 ? "" : "s"} left`;
}

export function percent(value: number | null | undefined, digits = 1): string {
  return value == null ? "—" : `${(value * 100).toFixed(digits)}%`;
}

export function capitalize(s: string): string {
  return s.charAt(0).toUpperCase() + s.slice(1);
}

export const fmtInt = (n: number) => n.toLocaleString("en-US");
