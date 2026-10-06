import { describe, expect, it } from "vitest";
import { makeAppeal } from "./testFixtures";
import { EMPTY_FILTERS } from "./types";
import {
  daysLeftLabel,
  dueByDay,
  filterAppeals,
  formatDate,
  percent,
  workingDaysLeft,
  sortAppeals,
  statusByCategory,
} from "./utils";

const appeals = [
  makeAppeal(),
  makeAppeal({ appeal_id: "A2", category: "water", status: "overdue", urgent: true, remaining_business_days: -2 }),
  makeAppeal({ appeal_id: "A3", category: "waste", needs_review: true, status: "at_risk", remaining_business_days: 1, deadline: "2026-10-06" }),
  makeAppeal({ appeal_id: "A4", status: "closed_on_time", location: "Dostyk Avenue 5" }),
];

describe("filterAppeals", () => {
  it("returns everything with empty filters", () => {
    expect(filterAppeals(appeals, EMPTY_FILTERS)).toHaveLength(4);
  });

  it("filters by category, status and flags", () => {
    const ids = (f: Partial<typeof EMPTY_FILTERS>) =>
      filterAppeals(appeals, { ...EMPTY_FILTERS, ...f }).map((a) => a.appeal_id);
    expect(ids({ category: "water" })).toEqual(["A2"]);
    expect(ids({ status: "overdue" })).toEqual(["A2"]);
    expect(ids({ status: "open" })).toEqual(["A042-00001", "A2", "A3"]);
    expect(ids({ reviewOnly: true })).toEqual(["A3"]);
    expect(ids({ urgentOnly: true })).toEqual(["A2"]);
  });

  it("searches text, location and id case-insensitively", () => {
    const search = (query: string) =>
      filterAppeals(appeals, { ...EMPTY_FILTERS, query }).map((a) => a.appeal_id);
    expect(search("DOSTYK")).toEqual(["A4"]);
    expect(search("a3")).toEqual(["A3"]);
    expect(search("pothole")).toHaveLength(4);
    expect(search("nothing-like-this")).toEqual([]);
  });
});

describe("sorting and aggregation", () => {
  it("orders by priority: overdue, at risk, on track, closed", () => {
    const ids = sortAppeals(appeals, { key: "priority", dir: "asc" }).map((a) => a.appeal_id);
    expect(ids).toEqual(["A2", "A3", "A042-00001", "A4"]);
  });

  it("sorts by deadline in both directions", () => {
    const asc = sortAppeals(appeals, { key: "deadline", dir: "asc" }).map((a) => a.appeal_id);
    const desc = sortAppeals(appeals, { key: "deadline", dir: "desc" }).map((a) => a.appeal_id);
    expect(asc[0]).toBe("A3");
    expect(desc[desc.length - 1]).toBe("A3");
  });

  it("counts statuses per category, busiest category first", () => {
    const rows = statusByCategory(appeals, ["roads", "water", "waste", "lighting"]);
    expect(rows[0]).toMatchObject({ category: "roads", open: 1 });
    expect(rows.find((r) => r.category === "roads")!.counts.closed_on_time).toBe(1);
    expect(rows.find((r) => r.category === "lighting")!.open).toBe(0);
  });

  it("groups open appeals by deadline day, ignoring overdue and closed", () => {
    const days = dueByDay(appeals, "2026-10-05", 3);
    expect(days.map((d) => d.date)).toEqual(["2026-10-05", "2026-10-06", "2026-10-07"]);
    expect(days[1]).toEqual({ date: "2026-10-06", count: 1, atRisk: 1 });
    expect(days.reduce((n, d) => n + d.count, 0)).toBe(1);
  });
});

describe("formatting", () => {
  it("shows working days left as a signed number", () => {
    expect(workingDaysLeft({ status: "on_track", remaining_business_days: 5 })).toBe("5");
    expect(workingDaysLeft({ status: "at_risk", remaining_business_days: 0 })).toBe("0");
    expect(workingDaysLeft({ status: "overdue", remaining_business_days: -3 })).toBe("\u22123");
    // Overdue on a weekend right after the deadline: 0 business days passed, still overdue.
    expect(workingDaysLeft({ status: "overdue", remaining_business_days: 0 })).toBe("\u22121");
    expect(workingDaysLeft({ status: "closed_late", remaining_business_days: -2 })).toBe("—");
  });

  it("describes the remaining time in words for the appeal record", () => {
    expect(daysLeftLabel({ status: "on_track", remaining_business_days: 1 })).toBe("1 working day left");
    expect(daysLeftLabel({ status: "at_risk", remaining_business_days: 0 })).toBe("Due today");
    expect(daysLeftLabel({ status: "overdue", remaining_business_days: -3 })).toBe("3 working days overdue");
    expect(daysLeftLabel({ status: "closed_on_time", remaining_business_days: 2 })).toBe("Closed");
  });

  it("formats dates without timezone shifts and percentages", () => {
    expect(formatDate("2026-10-05")).toBe("05.10.2026");
    expect(percent(0.9592)).toBe("95.9%");
    expect(percent(null)).toBe("—");
  });
});
