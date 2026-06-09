export default function AuthLayout({ children }: { children: React.ReactNode }) {
  return (
    <div className="min-h-screen grid grid-cols-1 lg:grid-cols-2">
      <aside className="hidden lg:flex flex-col justify-between bg-navy-900 text-white p-12">
        <div>
          <div className="text-[20px] font-bold tracking-tight">MissionIQ</div>
          <div className="miq-eyebrow text-steel-300 mt-1">
            Operational Intelligence Platform
          </div>
        </div>
        <div className="max-w-md">
          <h1 className="text-h1 mb-3">
            Intelligence for mission execution.
          </h1>
          <p className="text-[15px] text-charcoal-300 leading-relaxed">
            MissionIQ transforms contracts, documents, processes, and operational
            data into actionable intelligence for the teams that win, deliver, and
            improve mission-critical work.
          </p>
          <ul className="mt-6 space-y-2 text-[13px] text-charcoal-300">
            <li>· Source-cited outputs, never hallucinated</li>
            <li>· Workspace isolation by design</li>
            <li>· No foundation-model training on your data</li>
          </ul>
        </div>
        <div className="text-[11px] text-charcoal-500">
          © MissionIQ. All rights reserved.
        </div>
      </aside>
      <main className="flex items-center justify-center p-8 bg-canvas">
        <div className="w-full max-w-[420px]">{children}</div>
      </main>
    </div>
  );
}
