import type { Appeal } from "./types";

export function makeAppeal(overrides: Partial<Appeal> = {}): Appeal {
  return {
    appeal_id: "A042-00001",
    submitted_on: "2026-10-01",
    masked_text: "Pothole on the road. My name is [NAME].",
    location: "Abay Avenue 10",
    category: "roads",
    confidence: 0.9,
    needs_review: false,
    urgent: false,
    deadline: "2026-10-22",
    remaining_business_days: 5,
    status: "on_track",
    model_version: "tfidf-logreg-test",
    reviewed: false,
    closed_on: null,
    ...overrides,
  };
}
