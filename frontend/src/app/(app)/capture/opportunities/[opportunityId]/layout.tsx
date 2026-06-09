"use client";

import Link from "next/link";
import { usePathname } from "next/navigation";
import { use } from "react";
import clsx from "clsx";

const TABS = [
  { slug: "", label: "Briefing" },
  { slug: "documents", label: "Documents" },
  { slug: "customer-dna", label: "Customer DNA", emphasis: true },
  { slug: "summary", label: "Summary" },
  { slug: "compliance", label: "Compliance" },
  { slug: "evaluation", label: "Evaluation" },
  { slug: "risks", label: "Risks" },
  { slug: "requirements", label: "Requirements" },
  { slug: "win-themes", label: "Win Themes" },
  { slug: "capabilities", label: "Capabilities" },
  { slug: "staffing", label: "Staffing" },
  { slug: "outline", label: "Outline" },
  { slug: "market-intel", label: "Market Intel" },
  { slug: "assistant", label: "Assistant" },
];

export default function OpportunityLayout({
  children,
  params,
}: {
  children: React.ReactNode;
  params: Promise<{ opportunityId: string }>;
}) {
  const { opportunityId } = use(params);
  const pathname = usePathname();
  const base = `/capture/opportunities/${opportunityId}`;

  return (
    <div>
      <div className="flex gap-1 overflow-x-auto border-b border-charcoal-300 mb-6 -mx-2 px-2">
        {TABS.map((t) => {
          const href = t.slug ? `${base}/${t.slug}` : base;
          const active = t.slug ? pathname.startsWith(href) : pathname === base;
          return (
            <Link
              key={t.slug}
              href={href}
              className={clsx(
                "px-3 py-2.5 text-[13px] font-medium border-b-2 -mb-px whitespace-nowrap",
                active
                  ? "text-charcoal-900 border-steel-700"
                  : t.emphasis
                    ? "text-steel-700 border-transparent hover:text-charcoal-900"
                    : "text-charcoal-500 border-transparent hover:text-charcoal-900",
              )}
            >
              {t.label}
            </Link>
          );
        })}
      </div>
      {children}
    </div>
  );
}
