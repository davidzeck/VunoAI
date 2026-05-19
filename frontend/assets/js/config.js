/**
 * Central config — change API_BASE to switch between environments.
 * Dev:  http://localhost:8000
 * Prod: https://your-backend.onrender.com
 */
export const API_BASE = "http://localhost:8000";

export const POLL_INTERVAL_MS = 2000;
export const PROCESSING_STATUSES = ["pending", "in_progress"];
export const TERMINAL_STATUSES   = ["completed", "failed", "rejected"];

export const INTENT_LABELS = {
  send_money:       "Send Money",
  verify_document:  "Verify Document",
  hire_service:     "Hire Service",
  airport_transfer: "Airport Transfer",
  general_inquiry:  "General Inquiry",
};

export const STATUS_LABELS = {
  pending:     "Pending",
  in_progress: "In Progress",
  completed:   "Completed",
  failed:      "Failed",
  rejected:    "Rejected",
};

export const RISK_LABELS = {
  low:    "Low Risk",
  medium: "Medium Risk",
  high:   "High Risk",
};
