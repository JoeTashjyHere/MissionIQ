import { PlatformShell } from "@/components/shell/PlatformShell";

export default function AppLayout({ children }: { children: React.ReactNode }) {
  return <PlatformShell>{children}</PlatformShell>;
}
