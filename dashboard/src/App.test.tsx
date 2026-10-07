import { render, screen, waitFor, within } from "@testing-library/react";
import userEvent from "@testing-library/user-event";
import { afterEach, beforeEach, describe, expect, it, vi } from "vitest";
import App from "./App";
import { makeAppeal } from "./testFixtures";
import type { Appeal, Summary } from "./types";

const appeals: Appeal[] = [
  makeAppeal({ appeal_id: "A1", status: "overdue", remaining_business_days: -2 }),
  makeAppeal({
    appeal_id: "A2",
    category: "waste",
    status: "at_risk",
    needs_review: true,
    confidence: 0.43,
    masked_text: "Trash piled up and also the road was dug up",
  }),
  makeAppeal({ appeal_id: "A3", category: "water", status: "on_track", urgent: true }),
];

const summary: Summary = {
  today: "2026-10-05",
  model_version: "tfidf-logreg-test",
  total: 3,
  by_status: { overdue: 1, at_risk: 1, on_track: 1, closed_late: 0, closed_on_time: 0 },
  open_by_category: { roads: 1, waste: 1, water: 1 },
  needs_review: 1,
  urgent_open: 1,
};

const metrics = {
  accuracy: 0.96,
  macro_f1: 0.959,
  review_rate: 0.1,
  auto_accepted_accuracy: 0.997,
  n_test: 400,
  n_train: 1600,
  seed: 42,
  labels: ["roads", "water"],
  confusion_matrix: [
    [10, 1],
    [0, 12],
  ],
};

function mockFetch() {
  return vi.fn(async (url: string, init?: RequestInit) => {
    const json = (body: unknown, status = 200) =>
      new Response(JSON.stringify(body), {
        status,
        headers: { "Content-Type": "application/json" },
      });
    if (url === "/api/config")
      return json({ categories: ["roads", "waste", "water"], statuses: Object.keys(summary.by_status) });
    if (url === "/api/summary") return json(summary);
    if (url === "/api/appeals") return json(appeals);
    if (url === "/api/metrics") return json(metrics);
    if (url.endsWith("/review") && init?.method === "POST") {
      const { category } = JSON.parse(String(init.body));
      return json({ ...appeals[1], category, needs_review: false, reviewed: true, confidence: 1 });
    }
    if (url.endsWith("/close") && init?.method === "POST") {
      return json({ ...appeals[0], status: "closed_late", closed_on: summary.today });
    }
    return json({ error: "not found" }, 404);
  });
}

describe("App", () => {
  beforeEach(() => {
    window.location.hash = "";
    vi.stubGlobal("fetch", mockFetch());
  });
  afterEach(() => {
    vi.unstubAllGlobals();
  });

  it("shows the overview with key figures and the attention list", async () => {
    render(<App />);
    expect(await screen.findByRole("heading", { level: 1, name: "Overview" })).toBeInTheDocument();
    const kpis = screen.getByRole("region", { name: "Key figures" });
    expect(within(kpis).getByRole("button", { name: /Overdue/ })).toHaveTextContent("1");
    expect(screen.getByRole("link", { name: /Review queue/ })).toHaveTextContent("1");
    expect(screen.getByText("Overdue and at risk")).toBeInTheDocument();
  });

  it("drills down from a KPI into the filtered register", async () => {
    const user = userEvent.setup();
    render(<App />);
    const kpis = await screen.findByRole("region", { name: "Key figures" });
    await user.click(within(kpis).getByRole("button", { name: /On track/ }));
    expect(screen.getByRole("heading", { level: 1, name: "Appeals register" })).toBeInTheDocument();
    expect(screen.getByText("Found: 1 of 3")).toBeInTheDocument();
    expect(window.location.hash).toBe("#/appeals");
  });

  it("opens the appeal record from the register", async () => {
    const user = userEvent.setup();
    window.location.hash = "#/appeals";
    render(<App />);
    await user.click(await screen.findByRole("button", { name: "A3" }));
    const dialog = screen.getByRole("dialog", { name: "Appeal A3" });
    expect(within(dialog).getByText("Appeal text")).toBeInTheDocument();
    await user.keyboard("{Escape}");
    expect(screen.queryByRole("dialog")).not.toBeInTheDocument();
  });

  it("lets an operator correct a label from the review queue", async () => {
    const user = userEvent.setup();
    render(<App />);
    await user.click(await screen.findByRole("link", { name: /Review queue/ }));
    await user.selectOptions(screen.getByLabelText("Category for A2"), "roads");
    await user.click(screen.getByRole("button", { name: "Correct label" }));
    await waitFor(() => expect(screen.getByRole("status")).toHaveTextContent("Saved. A2"));
  });

  it("lets an operator close an open appeal after confirming", async () => {
    const user = userEvent.setup();
    window.location.hash = "#/appeals";
    render(<App />);
    await user.click(await screen.findByRole("button", { name: "A1" }));
    const dialog = screen.getByRole("dialog", { name: "Appeal A1" });
    await user.click(within(dialog).getByRole("button", { name: "Close appeal" }));
    await user.click(within(dialog).getByRole("button", { name: "Confirm closing" }));
    await waitFor(() => expect(screen.getByRole("status")).toHaveTextContent("Closed. A1"));
    expect(within(dialog).getByText("Closed late")).toBeInTheDocument();
    expect(within(dialog).queryByRole("button", { name: "Close appeal" })).not.toBeInTheDocument();
  });

  it("shows model metrics and the confusion matrix", async () => {
    window.location.hash = "#/model";
    render(<App />);
    expect(await screen.findByText(/Confusion matrix/)).toBeInTheDocument();
    expect(screen.getByText("96.0%")).toBeInTheDocument();
    expect(screen.getByText("1,600 / 400")).toBeInTheDocument();
  });

  it("reports when the API is unavailable", async () => {
    vi.stubGlobal("fetch", vi.fn(async () => new Response("{}", { status: 502 })));
    render(<App />);
    expect(await screen.findByRole("alert")).toHaveTextContent("Service unavailable");
  });
});
