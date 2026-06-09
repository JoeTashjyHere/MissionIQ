"use client";

import Link from "next/link";
import { usePathname } from "next/navigation";
import clsx from "clsx";
import {
  Activity,
  BarChart3,
  GitBranch,
  Globe2,
  LayoutDashboard,
  ShieldAlert,
  Target,
  Users,
  type LucideIcon,
} from "lucide-react";

interface NavItem {
  label: string;
  href?: string;
  icon?: LucideIcon;
  disabled?: boolean;
  children?: NavItem[];
}

const PLATFORM: NavItem[] = [
  { label: "Dashboard", href: "/dashboard", icon: LayoutDashboard },
];

const MODULE_GROUPS: {
  id: string;
  label: string;
  icon: LucideIcon;
  active: boolean;
  href: string;
  children?: NavItem[];
}[] = [
  {
    id: "capture",
    label: "Capture Intelligence",
    icon: Target,
    active: true,
    href: "/capture/opportunities",
    children: [
      { label: "Opportunities", href: "/capture/opportunities" },
      { label: "Market Intelligence", href: "/capture/market-intel/search" },
    ],
  },
  {
    id: "operations",
    label: "Operations Intelligence",
    icon: Activity,
    active: false,
    href: "/operations",
  },
  {
    id: "process",
    label: "Process Intelligence",
    icon: GitBranch,
    active: false,
    href: "/process",
  },
  {
    id: "performance",
    label: "Performance Intelligence",
    icon: BarChart3,
    active: false,
    href: "/performance",
  },
  {
    id: "risk",
    label: "Risk Intelligence",
    icon: ShieldAlert,
    active: false,
    href: "/risk",
  },
  {
    id: "organizational",
    label: "Organizational Intelligence",
    icon: Users,
    active: false,
    href: "/organizational",
  },
  {
    id: "market",
    label: "Market Intelligence",
    icon: Globe2,
    active: false,
    href: "/market",
  },
];

const WORKSPACE: NavItem[] = [
  { label: "Company Profile", href: "/settings/company-profile" },
  { label: "Team", href: "/settings/team" },
  { label: "Settings", href: "/settings" },
];

function NavLink({
  href,
  label,
  Icon,
  active,
  disabled,
}: {
  href: string;
  label: string;
  Icon?: LucideIcon;
  active: boolean;
  disabled?: boolean;
}) {
  const className = clsx(
    "flex items-center gap-2.5 px-3 py-2 rounded-[6px] text-[13px] transition-colors",
    active && "bg-navy-700 text-white",
    !active && !disabled && "text-charcoal-100 hover:bg-navy-700/40",
    disabled && "text-charcoal-300/50 cursor-not-allowed",
  );
  const content = (
    <>
      {Icon && <Icon className="h-4 w-4 shrink-0" strokeWidth={1.75} />}
      <span className="truncate">{label}</span>
      {disabled && (
        <span className="ml-auto text-[10px] uppercase tracking-wider text-charcoal-500">
          soon
        </span>
      )}
    </>
  );
  if (disabled) {
    return <div className={className}>{content}</div>;
  }
  return (
    <Link href={href} className={className}>
      {content}
    </Link>
  );
}

export function LeftNav() {
  const pathname = usePathname();
  return (
    <nav className="w-[248px] bg-navy-800 text-charcoal-100 px-3 py-4 flex flex-col gap-5 shrink-0 min-h-screen">
      <div className="text-white px-3">
        <div className="text-[18px] font-bold tracking-tight">MissionIQ</div>
        <div className="text-[11px] uppercase tracking-wider text-steel-300">
          Operational Intelligence
        </div>
      </div>

      <div className="flex flex-col gap-0.5">
        {PLATFORM.map((item) => (
          <NavLink
            key={item.label}
            href={item.href!}
            label={item.label}
            Icon={item.icon}
            active={!!item.href && pathname.startsWith(item.href)}
          />
        ))}
      </div>

      <div className="flex flex-col gap-3">
        {MODULE_GROUPS.map((g) => (
          <div key={g.id} className="flex flex-col gap-0.5">
            <NavLink
              href={g.href}
              label={g.label}
              Icon={g.icon}
              active={g.active && pathname.startsWith(`/${g.id}`)}
              disabled={!g.active}
            />
            {g.children && g.active && (
              <div className="pl-7 flex flex-col gap-0.5">
                {g.children.map((c) => (
                  <NavLink
                    key={c.label}
                    href={c.href!}
                    label={c.label}
                    active={pathname.startsWith(c.href!)}
                  />
                ))}
              </div>
            )}
          </div>
        ))}
      </div>

      <div className="mt-auto flex flex-col gap-0.5">
        <div className="px-3 mb-1 miq-eyebrow text-charcoal-300">Workspace</div>
        {WORKSPACE.map((item) => (
          <NavLink
            key={item.label}
            href={item.href!}
            label={item.label}
            active={!!item.href && pathname.startsWith(item.href)}
          />
        ))}
      </div>
    </nav>
  );
}
