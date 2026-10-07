export type SLAStatus = "overdue" | "at_risk" | "on_track" | "closed_late" | "closed_on_time";

export interface Appeal {
  appeal_id: string;
  submitted_on: string;
  masked_text: string;
  location: string;
  category: string;
  confidence: number;
  needs_review: boolean;
  urgent: boolean;
  deadline: string;
  remaining_business_days: number;
  status: SLAStatus;
  model_version: string;
  reviewed: boolean;
  closed_on: string | null;
}

export interface Summary {
  today: string;
  model_version: string;
  total: number;
  by_status: Record<SLAStatus, number>;
  open_by_category: Record<string, number>;
  needs_review: number;
  urgent_open: number;
}

export interface Metrics {
  accuracy: number;
  macro_f1: number;
  review_rate: number;
  auto_accepted_accuracy: number | null;
  n_test: number;
  n_train?: number;
  seed?: number;
  model_version?: string;
  labels?: string[];
  confusion_matrix?: number[][];
}

export interface AppConfig {
  categories: string[];
  statuses: SLAStatus[];
}

export interface Filters {
  query: string;
  category: string;
  status: SLAStatus | "" | "open";
  reviewOnly: boolean;
  urgentOnly: boolean;
}

export type SortKey = "priority" | "deadline" | "submitted_on" | "confidence" | "category";
export interface Sort {
  key: SortKey;
  dir: "asc" | "desc";
}

export const EMPTY_FILTERS: Filters = {
  query: "",
  category: "",
  status: "",
  reviewOnly: false,
  urgentOnly: false,
};
