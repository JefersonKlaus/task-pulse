// What the API answers (backend/core/pulse_core/application.py). Money in integer cents, moments as
// "YYYY-MM-DDTHH:MM" (Brasília), days as "YYYY-MM-DD".

export type Status = "DOING" | "DONE" | "APPROVED" | "REJECTED";
export type Billing = "" | "paid" | "not_paid";

import { N_ } from "./i18n.js";

/** In Portuguese: show them with t(STATUS_LABELS[status]). */
export const STATUS_LABELS: Record<Status, string> = {
  DOING: N_("Fazendo"), DONE: N_("Concluída"), APPROVED: N_("Aprovada"), REJECTED: N_("Rejeitada"),
};

/** `known`: a well-known company, the same for everyone (backend domain/catalog.py); nobody edits it. */
export interface Company {
  id: string; name: string; notes: string; known?: boolean; projects?: number; open_tasks?: number;
}

/** A deadline (a package to deliver): on one day, every week on a weekday (1 = Monday ... 7 = Sunday) or every
 * month on a day (1-31). `next_on`: its next day from today; null for a day that has passed. */
export type DeadlineKind = "date" | "weekly" | "monthly";
export interface Deadline {
  id: string; kind: DeadlineKind; label: string;
  on: string | null; weekday: number | null; month_day: number | null; next_on?: string | null;
}

export interface BonusTier { min_tasks: number; bonus_cents: number }

export interface Rule {
  id: string;
  starts_at: string;
  ends_at: string | null;
  kind: "hourly" | "fixed";
  hourly_cents: number;
  flat_cents: number | null;
  fixed_cents: number;
  paid_only_if_approved: boolean;
  bonus_tiers: BonusTier[];
}

export interface Project {
  id: string;
  company_id: string;
  company_name: string;
  name: string;
  currency: string;
  company_known?: boolean;
  deadlines: Deadline[];
  next_deadline: Deadline | null;
  description: string;
  rules: Rule[];
  current_rule_id: string | null;
  open_tasks?: number;
}

export interface Task {
  id: string;
  project_id: string;
  project_name: string;
  company_id: string;
  currency: string;
  name: string;
  external_id: string;
  repository: string;
  description: string;
  status: Status;
  started_at: string;
  finished_at: string | null;
  minutes: number;
  time_log: { at: string; minutes: number }[];
  billing: Billing;
  payment_id: string | null;
  value_cents: number;
  lost_cents: number;
  rule_id: string | null;
}

export interface TaskList { tasks: Task[]; totals: { tasks: number; minutes: number; value_cents: number } }

export interface Payment {
  id: string;
  project_id: string;
  period_start: string;
  period_end: string;
  received_on: string;
  received_cents: number;
  expected_cents: number;
  bonus_cents: number;
  difference_cents: number;
  not_paid_cents: number;
  paid_tasks: number;
  not_paid_tasks: number;
  notes: string;
  project_name?: string;
  company_name?: string;
  currency?: string;
}

export interface BillingReport {
  project: Omit<Project, "company_name" | "current_rule_id">;
  period: { from: string; to: string };
  tasks: Task[];
  payments: Payment[];
  bonus: { cents: number; paid_cents: number; due_cents: number; approved_tasks: number; rule_id: string | null };
  totals: {
    tasks: number; minutes: number; paid_tasks: number; not_paid_tasks: number; open_tasks: number;
    paid_value_cents: number; not_paid_value_cents: number; open_value_cents: number;
    to_receive_cents: number; expected_cents: number; received_cents: number; difference_cents: number;
  };
}

export interface PaymentList {
  payments: Payment[];
  totals: { expected_cents: number; received_cents: number; difference_cents: number; not_paid_cents: number };
}
