"use client";

import { PageHeader } from "@/components/PageHeader";
import { EmptyState } from "@/components/ds/EmptyState";
import { Wand2 } from "lucide-react";

export function ComingSoonModule({
  eyebrow,
  title,
  moduleId,
  description,
}: {
  eyebrow: string;
  title: string;
  moduleId: string;
  description: string;
}) {
  return (
    <div>
      <PageHeader eyebrow={eyebrow} title={title} subtitle={description} />
      <EmptyState
        icon={<Wand2 />}
        title="Module wiring in progress"
        description={`This module (${moduleId}) is part of the MVP roadmap. The platform's module registry, RAG engine, LLM router, and design system pattern are in place — adding a new prompt + module class lands this generator in the same pattern as Opportunity Summary.`}
      />
    </div>
  );
}
