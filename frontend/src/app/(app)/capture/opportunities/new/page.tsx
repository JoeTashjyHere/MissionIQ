"use client";

import { useState } from "react";
import { useRouter } from "next/navigation";
import { useAuth } from "@/lib/auth-context";
import { apiRequest, ApiError } from "@/lib/api";
import type { Opportunity } from "@/lib/types";
import { PageHeader } from "@/components/PageHeader";
import { Card, CardBody, CardHeader } from "@/components/ds/Card";
import { Input, Textarea } from "@/components/ds/Input";
import { Select } from "@/components/ds/Select";
import { Button } from "@/components/ds/Button";

const STAGES = [
  "identification",
  "qualification",
  "pursue",
  "capture",
  "proposal",
  "submitted",
  "awarded",
  "lost",
  "no-bid",
];

export default function NewOpportunityPage() {
  const router = useRouter();
  const { currentWorkspaceId } = useAuth();
  const [form, setForm] = useState({
    name: "",
    agency: "",
    solicitation_number: "",
    naics_code: "",
    capture_stage: "identification",
    due_date: "",
    estimated_value: "",
    incumbent: "",
    notes: "",
  });
  const [error, setError] = useState<string | null>(null);
  const [submitting, setSubmitting] = useState(false);

  const update = (k: string) => (e: React.ChangeEvent<HTMLInputElement | HTMLTextAreaElement | HTMLSelectElement>) =>
    setForm((f) => ({ ...f, [k]: e.target.value }));

  const onSubmit = async (e: React.FormEvent) => {
    e.preventDefault();
    if (!currentWorkspaceId) return;
    setError(null);
    setSubmitting(true);
    try {
      const cents = form.estimated_value ? Math.round(parseFloat(form.estimated_value) * 100) : null;
      const opp = await apiRequest<Opportunity>(
        `/workspaces/${currentWorkspaceId}/opportunities`,
        {
          method: "POST",
          body: {
            name: form.name,
            agency: form.agency || null,
            solicitation_number: form.solicitation_number || null,
            naics_code: form.naics_code || null,
            capture_stage: form.capture_stage,
            due_date: form.due_date ? new Date(form.due_date).toISOString() : null,
            estimated_value_cents: cents,
            incumbent: form.incumbent || null,
            notes: form.notes || null,
          },
        },
      );
      router.push(`/capture/opportunities/${opp.id}`);
    } catch (err) {
      setError(err instanceof ApiError ? err.detail : "Failed to create opportunity.");
    } finally {
      setSubmitting(false);
    }
  };

  return (
    <div>
      <PageHeader
        eyebrow="Capture Intelligence"
        title="New opportunity"
        subtitle="Capture the essentials. You can refine and upload documents next."
      />
      <Card className="max-w-[760px]">
        <CardHeader title="Opportunity details" />
        <CardBody>
          <form onSubmit={onSubmit} className="grid grid-cols-1 sm:grid-cols-2 gap-4">
            <div className="sm:col-span-2">
              <Input
                label="Opportunity name"
                required
                value={form.name}
                onChange={update("name")}
              />
            </div>
            <Input label="Agency" value={form.agency} onChange={update("agency")} />
            <Input
              label="Solicitation number"
              value={form.solicitation_number}
              onChange={update("solicitation_number")}
            />
            <Input
              label="NAICS code"
              value={form.naics_code}
              onChange={update("naics_code")}
            />
            <Select
              label="Capture stage"
              value={form.capture_stage}
              onChange={update("capture_stage")}
            >
              {STAGES.map((s) => (
                <option key={s} value={s}>
                  {s}
                </option>
              ))}
            </Select>
            <Input
              label="Due date"
              type="date"
              value={form.due_date}
              onChange={update("due_date")}
            />
            <Input
              label="Estimated value (USD)"
              type="number"
              min="0"
              step="1"
              value={form.estimated_value}
              onChange={update("estimated_value")}
            />
            <div className="sm:col-span-2">
              <Input
                label="Incumbent"
                value={form.incumbent}
                onChange={update("incumbent")}
              />
            </div>
            <div className="sm:col-span-2">
              <Textarea label="Notes" value={form.notes} onChange={update("notes")} />
            </div>
            {error && (
              <div className="sm:col-span-2 text-[13px] text-status-red bg-status-redBg border border-status-red/30 rounded-md px-3 py-2">
                {error}
              </div>
            )}
            <div className="sm:col-span-2 flex items-center justify-end gap-2">
              <Button
                type="button"
                variant="secondary"
                onClick={() => router.push("/capture/opportunities")}
              >
                Cancel
              </Button>
              <Button type="submit" loading={submitting}>
                Create
              </Button>
            </div>
          </form>
        </CardBody>
      </Card>
    </div>
  );
}
