"use client";

import { useState } from "react";
import { useRouter } from "next/navigation";
import Link from "next/link";
import { useAuth } from "@/lib/auth-context";
import { Input } from "@/components/ds/Input";
import { Button } from "@/components/ds/Button";
import { ApiError } from "@/lib/api";

export default function SignupPage() {
  const router = useRouter();
  const { signup } = useAuth();
  const [email, setEmail] = useState("");
  const [password, setPassword] = useState("");
  const [fullName, setFullName] = useState("");
  const [error, setError] = useState<string | null>(null);
  const [submitting, setSubmitting] = useState(false);

  const onSubmit = async (e: React.FormEvent) => {
    e.preventDefault();
    setError(null);
    setSubmitting(true);
    try {
      await signup(email, password, fullName);
      router.push("/dashboard");
    } catch (err) {
      setError(err instanceof ApiError ? err.detail : "Sign-up failed.");
    } finally {
      setSubmitting(false);
    }
  };

  return (
    <div>
      <h1 className="text-h1 text-charcoal-900">Create account</h1>
      <p className="text-[14px] text-charcoal-500 mt-1">
        Set up your MissionIQ identity. You can create or join a workspace next.
      </p>
      <form onSubmit={onSubmit} className="mt-6 flex flex-col gap-4">
        <Input
          label="Full name"
          name="full_name"
          required
          value={fullName}
          onChange={(e) => setFullName(e.target.value)}
        />
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
          autoComplete="new-password"
          required
          value={password}
          onChange={(e) => setPassword(e.target.value)}
          helper="Minimum 12 characters."
        />
        {error && (
          <div className="text-[13px] text-status-red bg-status-redBg border border-status-red/30 rounded-md px-3 py-2">
            {error}
          </div>
        )}
        <Button type="submit" loading={submitting} size="lg">
          Create account
        </Button>
      </form>
      <p className="mt-6 text-[13px] text-charcoal-500">
        Already have an account?{" "}
        <Link href="/login" className="font-medium">
          Sign in
        </Link>
        .
      </p>
    </div>
  );
}
