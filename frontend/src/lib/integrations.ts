import type {
  AutomationStatus,
  ConnectorStatus,
  SyncJobStatus,
} from "@/lib/types";

type Tone = "green" | "amber" | "red" | "info" | "neutral";

export const CONNECTOR_STATUS_LABEL: Record<ConnectorStatus, string> = {
  connected: "Connected",
  disconnected: "Disconnected",
  syncing: "Syncing",
  failed: "Failed",
  disabled: "Disabled",
};

export function connectorStatusTone(s: ConnectorStatus): Tone {
  if (s === "connected") return "green";
  if (s === "syncing") return "amber";
  if (s === "failed") return "red";
  if (s === "disabled") return "neutral";
  return "info";
}

export const SYNC_STATUS_LABEL: Record<SyncJobStatus, string> = {
  queued: "Queued",
  connecting: "Connecting",
  discovering: "Discovering",
  ingesting: "Ingesting",
  succeeded: "Succeeded",
  partial: "Partial",
  failed: "Failed",
};

export const SYNC_IN_FLIGHT: SyncJobStatus[] = [
  "queued",
  "connecting",
  "discovering",
  "ingesting",
];

export function syncStatusTone(s: SyncJobStatus): Tone {
  if (s === "succeeded") return "green";
  if (s === "failed") return "red";
  if (s === "partial") return "amber";
  return "amber";
}

export function syncProgressTone(s: SyncJobStatus): "steel" | "green" | "amber" | "red" {
  if (s === "succeeded") return "green";
  if (s === "failed") return "red";
  if (s === "partial") return "amber";
  return "steel";
}

export const AUTOMATION_STATUS_LABEL: Record<AutomationStatus, string> = {
  queued: "Queued",
  running: "Running",
  succeeded: "Succeeded",
  partial: "Partial",
  failed: "Failed",
};

export function automationStatusTone(s: AutomationStatus): Tone {
  if (s === "succeeded") return "green";
  if (s === "failed") return "red";
  if (s === "partial") return "amber";
  return "amber";
}

export function syncStatsSummary(stats: Record<string, number>): string {
  const parts: string[] = [];
  if (stats.opportunities_created) parts.push(`${stats.opportunities_created} pursuit(s) created`);
  if (stats.opportunities_updated) parts.push(`${stats.opportunities_updated} updated`);
  if (stats.documents_ingested) parts.push(`${stats.documents_ingested} doc(s) ingested`);
  if (stats.items_skipped) parts.push(`${stats.items_skipped} skipped`);
  if (stats.items_failed) parts.push(`${stats.items_failed} failed`);
  if (parts.length === 0 && stats.items_discovered !== undefined) {
    parts.push(`${stats.items_discovered} item(s) discovered`);
  }
  return parts.join(" · ") || "—";
}
