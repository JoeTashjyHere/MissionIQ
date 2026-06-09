"use client";

import { useAuth } from "@/lib/auth-context";
import { useState } from "react";
import clsx from "clsx";
import { ChevronDown, LogOut } from "lucide-react";

export function TopBar() {
  const { user, memberships, currentWorkspaceId, setCurrentWorkspaceId, logout } = useAuth();
  const [wsOpen, setWsOpen] = useState(false);
  const [userOpen, setUserOpen] = useState(false);
  const current = memberships.find((m) => m.workspace_id === currentWorkspaceId);

  return (
    <header className="h-14 bg-navy-900 text-white flex items-center px-5 gap-4 sticky top-0 z-30">
      <div className="text-[15px] font-semibold tracking-tight">MissionIQ</div>
      <div className="text-charcoal-300 mx-2">|</div>
      <div className="relative">
        <button
          onClick={() => setWsOpen((v) => !v)}
          className="flex items-center gap-2 px-3 py-1.5 rounded-[6px] hover:bg-navy-700 text-[13px]"
        >
          <span className="miq-eyebrow text-steel-300">Workspace</span>
          <span className="font-medium">{current?.workspace_name ?? "—"}</span>
          <ChevronDown className="h-3.5 w-3.5" />
        </button>
        {wsOpen && memberships.length > 0 && (
          <div className="absolute left-0 top-full mt-1 w-[280px] rounded-md bg-white text-charcoal-900 shadow-elevated border border-charcoal-300 py-1 z-40">
            {memberships.map((m) => (
              <button
                key={m.workspace_id}
                onClick={() => {
                  setCurrentWorkspaceId(m.workspace_id);
                  setWsOpen(false);
                }}
                className={clsx(
                  "w-full text-left px-3 py-2 text-[13px] hover:bg-charcoal-100",
                  m.workspace_id === currentWorkspaceId && "bg-charcoal-100",
                )}
              >
                <div className="font-medium">{m.workspace_name}</div>
                <div className="text-[11px] text-charcoal-500">
                  {m.workspace_slug} · {m.role}
                </div>
              </button>
            ))}
          </div>
        )}
      </div>

      <div className="ml-auto flex items-center gap-3">
        <div className="hidden md:block text-[12px] text-charcoal-300">
          <span className="font-mono">⌘K</span> Search
        </div>
        <div className="relative">
          <button
            onClick={() => setUserOpen((v) => !v)}
            className="flex items-center gap-2 px-2 py-1 rounded-[6px] hover:bg-navy-700"
          >
            <div className="h-7 w-7 rounded-full bg-steel-500 flex items-center justify-center text-[12px] font-semibold">
              {(user?.full_name ?? "U").slice(0, 1)}
            </div>
            <div className="hidden md:block text-[13px]">{user?.full_name ?? "—"}</div>
            <ChevronDown className="h-3.5 w-3.5" />
          </button>
          {userOpen && (
            <div className="absolute right-0 top-full mt-1 w-[200px] rounded-md bg-white text-charcoal-900 shadow-elevated border border-charcoal-300 py-1 z-40">
              <div className="px-3 py-2 border-b border-charcoal-100">
                <div className="text-[13px] font-medium">{user?.full_name}</div>
                <div className="text-[11px] text-charcoal-500">{user?.email}</div>
              </div>
              <button
                onClick={() => {
                  setUserOpen(false);
                  logout();
                }}
                className="w-full text-left px-3 py-2 text-[13px] hover:bg-charcoal-100 flex items-center gap-2"
              >
                <LogOut className="h-3.5 w-3.5" />
                Sign out
              </button>
            </div>
          )}
        </div>
      </div>
    </header>
  );
}
