"use client";

import { useAuth } from "@/lib/auth-context";
import { useRouter } from "next/navigation";
import { useEffect } from "react";
import { LeftNav } from "./LeftNav";
import { TopBar } from "./TopBar";

export function PlatformShell({ children }: { children: React.ReactNode }) {
  const { user, loading } = useAuth();
  const router = useRouter();

  useEffect(() => {
    if (!loading && !user) {
      router.replace("/login");
    }
  }, [loading, user, router]);

  if (loading) {
    return (
      <div className="min-h-screen flex items-center justify-center">
        <div className="text-charcoal-500 text-[13px]">Loading MissionIQ…</div>
      </div>
    );
  }
  if (!user) return null;

  return (
    <div className="min-h-screen flex">
      <LeftNav />
      <div className="flex-1 flex flex-col min-w-0">
        <TopBar />
        <main className="flex-1 p-8 max-w-[1440px] w-full mx-auto">{children}</main>
      </div>
    </div>
  );
}
