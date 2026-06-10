"use client";

import { useState } from "react";
import { useRouter } from "next/navigation";
import Link from "next/link";
import { useAuth } from "@/lib/auth-context";
import { Input } from "@/components/ds/Input";
import { Button } from "@/components/ds/Button";
import { ApiError } from "@/lib/api";

export default function LoginPage() {
  const router = useRouter();
  const { login } = useAuth();
  const [email, setEmail] = useState("sarah.mitchell@apexfederal.demo");
  const [password, setPassword] = useState("MissionIQ!Demo2026");
  const [error, setError] = useState<string | null>(null);
  const [submitting, setSubmitting] = useState(false);

  const onSubmit = async (e: React.FormEvent) => {
    e.preventDefault();
    setError(null);
    setSubmitting(true);
    try {
      await login(email, password);
      router.push("/dashboard");
    } catch (err) {
      setError(err instanceof ApiError ? err.detail : "Sign-in failed.");
    } finally {
      setSubmitting(false);
    }
  };

  return (
    <div>
      <div className="lg:hidden mb-6">
        <div className="text-[20px] font-bold tracking-tight text-charcoal-900">
          MissionIQ
        </div>
        <div className="miq-eyebrow">Operational Intelligence Platform</div>
      </div>
      <h1 className="text-h1 text-charcoal-900">Sign in</h1>
      <p className="text-[14px] text-charcoal-500 mt-1">
        Access your operational intelligence workspace.
      </p>
      <form onSubmit={onSubmit} className="mt-6 flex flex-col gap-4">
        <Input
          label="Email"
          type="email"
          name="email"
          autoComplete="email"
          required
          value={email}
          onChange={(e) => setEmail(e.target.value)}
        />
        <Input
          label="Password"
          type="password"
          name="password"
          autoComplete="current-password"
          required
          value={password}
          onChange={(e) => setPassword(e.target.value)}
        />
        {error && (
          <div className="text-[13px] text-status-red bg-status-redBg border border-status-red/30 rounded-md px-3 py-2">
            {error}
          </div>
        )}
        <Button type="submit" loading={submitting} size="lg">
          Sign in
        </Button>
      </form>
      <p className="mt-4 text-[12.5px] text-charcoal-500 bg-charcoal-50 border border-charcoal-200 rounded-md px-3 py-2.5">
        <span className="font-medium text-charcoal-700">Demo showcase:</span>{" "}
        sarah.mitchell@apexfederal.demo / MissionIQ!Demo2026 — Apex Federal
        Solutions workspace with pursuits, outcomes, and proposal intelligence
        pre-loaded.
      </p>
      <p className="mt-6 text-[13px] text-charcoal-500">
        Need an account?{" "}
        <Link href="/signup" className="font-medium">
          Create one
        </Link>
        .
      </p>
    </div>
  );
}
