"use client";

import Link from "next/link";
import { usePathname } from "next/navigation";
import clsx from "clsx";
import {
  BookOpen,
  Brain,
  Globe2,
  LayoutGrid,
  Network,
  Plug,
  Presentation,
  Target,
  type LucideIcon,
} from "lucide-react";

interface NavItem {
  label: string;
  href: string;
  disabled?: boolean;
}

interface NavSection {
  id: string;
  label: string;
  icon: LucideIcon;
  phase?: string; // Win / Deliver / Improve reinforcement
  items: NavItem[];
}

/**
 * Build the platform IA. Capture / Memory / Briefings items are
 * opportunity-scoped, so they deep-link into the currently open opportunity
 * when there is one, and otherwise route to the Opportunities list (the entry
 * point) for the user to pick a pursuit first.
 */
function buildSections(oppBase: string | null): NavSection[] {
  const cap = (slug: string) =>
    oppBase ? `${oppBase}/${slug}` : "/capture/opportunities";

  return [
    {
      id: "capture",
      label: "Capture Intelligence",
      icon: Target,
      phase: "Win",
      items: [
        { label: "Opportunities", href: "/capture/opportunities" },
        { label: "Win Strategy", href: cap("win-strategy") },
        { label: "Customer DNA", href: cap("customer-dna") },
        { label: "Company DNA", href: cap("company-dna") },
        { label: "Capability Match", href: cap("capabilities") },
        { label: "Compliance Intelligence", href: cap("compliance") },
        { label: "Evaluation Intelligence", href: cap("evaluation") },
        { label: "Risk Intelligence", href: cap("risks") },
      ],
    },
    {
      id: "briefings",
      label: "Briefings",
      icon: Presentation,
      phase: "Decide",
      items: [
        { label: "Executive Brief", href: cap("executive-brief") },
        { label: "Gate Review", href: cap("gate-review") },
        { label: "Bid / No-Bid Decision", href: cap("bid-decision") },
      ],
    },
    {
      id: "knowledge",
      label: "Knowledge",
      icon: BookOpen,
      phase: "Improve",
      items: [
        { label: "Proposal Repository", href: "/knowledge" },
        { label: "Past Performance Library", href: "/knowledge/past-performance" },
        { label: "Win Theme Library", href: "/knowledge/win-themes" },
        { label: "Staffing Library", href: "/knowledge/staffing" },
        { label: "Transition Library", href: "/knowledge/transition" },
        { label: "Executive Summary Library", href: "/knowledge/executive-summaries" },
      ],
    },
    {
      id: "memory",
      label: "Memory",
      icon: Brain,
      phase: "Improve",
      items: [
        { label: "Pursuit Memory", href: cap("memory") },
        { label: "Similar Opportunities", href: `${cap("memory")}#similar` },
        { label: "Agency Intelligence", href: `${cap("memory")}#agency` },
        { label: "Knowledge Graph", href: `${cap("memory")}#graph` },
        { label: "Outcome Intelligence", href: "/outcomes" },
        { label: "Win/Loss Analysis", href: "/outcomes#winloss" },
        { label: "Recommendation Performance", href: "/outcomes#recommendations" },
      ],
    },
    {
      id: "market",
      label: "Market Intelligence",
      icon: Globe2,
      items: [
        { label: "Opportunity Search", href: "/capture/market-intel/search" },
        { label: "Linked Records", href: "/capture/market-intel/records" },
        {
          label: "Agency Intelligence",
          href: oppBase ? `${oppBase}/memory#agency` : "/capture/market-intel/search",
        },
      ],
    },
    {
      id: "integrations",
      label: "Integrations",
      icon: Plug,
      items: [
        { label: "Connectors", href: "/integrations/connectors" },
        { label: "Sync History", href: "/integrations/sync-history" },
        { label: "Connector Health", href: "/integrations/health" },
      ],
    },
    {
      id: "platform",
      label: "Platform",
      icon: LayoutGrid,
      items: [
        { label: "Dashboard", href: "/dashboard" },
        { label: "Company Profile", href: "/settings/company-profile" },
        { label: "Team", href: "/settings/team" },
        { label: "Settings", href: "/settings" },
      ],
    },
    {
      id: "future",
      label: "Future Modules",
      icon: Network,
      items: [
        { label: "Operations Intelligence", href: "/operations", disabled: true },
        { label: "Process Intelligence", href: "/process", disabled: true },
        { label: "Performance Intelligence", href: "/performance", disabled: true },
        {
          label: "Organizational Intelligence",
          href: "/organizational",
          disabled: true,
        },
      ],
    },
  ];
}

function NavLink({
  href,
  label,
  active,
  disabled,
}: {
  href: string;
  label: string;
  active: boolean;
  disabled?: boolean;
}) {
  const className = clsx(
    "flex items-center gap-2.5 px-3 py-1.5 rounded-[6px] text-[13px] transition-colors",
    active && "bg-navy-700 text-white",
    !active && !disabled && "text-charcoal-100 hover:bg-navy-700/40",
    disabled && "text-charcoal-300/50 cursor-not-allowed",
  );
  const content = (
    <>
      <span className="truncate">{label}</span>
      {disabled && (
        <span className="ml-auto text-[10px] uppercase tracking-wider text-charcoal-500">
          soon
        </span>
      )}
    </>
  );
  if (disabled) return <div className={className}>{content}</div>;
  return (
    <Link href={href} className={className}>
      {content}
    </Link>
  );
}

export function LeftNav() {
  const pathname = usePathname();

  const oppMatch = pathname.match(
    /\/capture\/opportunities\/([0-9a-fA-F-]{8,})/,
  );
  const oppId =
    oppMatch && oppMatch[1] !== "new" ? oppMatch[1] : null;
  const oppBase = oppId ? `/capture/opportunities/${oppId}` : null;

  const sections = buildSections(oppBase);

  const isActive = (href: string) => {
    const clean = href.split("#")[0];
    // The Opportunities list should not light up on every opportunity subpage.
    if (clean === "/capture/opportunities") {
      return pathname === clean || pathname === "/capture/opportunities/new";
    }
    return pathname === clean || pathname.startsWith(`${clean}/`);
  };

  return (
    <nav className="w-[252px] bg-navy-800 text-charcoal-100 px-3 py-4 flex flex-col gap-4 shrink-0 min-h-screen overflow-y-auto">
      <div className="text-white px-3">
        <div className="text-[18px] font-bold tracking-tight">MissionIQ</div>
        <div className="text-[11px] uppercase tracking-wider text-steel-300">
          Operational Intelligence
        </div>
        <div className="mt-2 flex items-center gap-1.5 text-[10px] font-semibold uppercase tracking-wider text-steel-300/80">
          <span>Win</span>
          <span className="text-charcoal-500">·</span>
          <span>Deliver</span>
          <span className="text-charcoal-500">·</span>
          <span>Improve</span>
        </div>
      </div>

      <div className="flex flex-col gap-4">
        {sections.map((section) => {
          const Icon = section.icon;
          return (
            <div key={section.id} className="flex flex-col gap-1">
              <div className="flex items-center gap-2 px-3">
                <Icon
                  className="h-3.5 w-3.5 shrink-0 text-steel-300"
                  strokeWidth={2}
                />
                <span className="miq-eyebrow text-charcoal-300">
                  {section.label}
                </span>
                {section.phase && (
                  <span className="ml-auto text-[9.5px] font-semibold uppercase tracking-wider text-steel-300/70">
                    {section.phase}
                  </span>
                )}
              </div>
              <div className="flex flex-col gap-0.5 pl-2">
                {section.items.map((item) => (
                  <NavLink
                    key={item.label}
                    href={item.href}
                    label={item.label}
                    active={!item.disabled && isActive(item.href)}
                    disabled={item.disabled}
                  />
                ))}
              </div>
            </div>
          );
        })}
      </div>
    </nav>
  );
}
