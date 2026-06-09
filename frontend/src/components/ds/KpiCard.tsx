import clsx from "clsx";

export function KpiCard({
  label,
  value,
  delta,
  helper,
  tone,
}: {
  label: string;
  value: string | number;
  delta?: string;
  helper?: string;
  tone?: "green" | "amber" | "red";
}) {
  return (
    <div className="rounded-md border border-charcoal-300 bg-white shadow-card px-5 py-4">
      <div className="miq-eyebrow">{label}</div>
      <div className="mt-1 flex items-baseline gap-2">
        <div className="miq-numeric text-[28px] font-semibold text-charcoal-900 leading-none">
          {value}
        </div>
        {delta && (
          <span
            className={clsx(
              "text-[12px] font-medium",
              tone === "green" && "text-status-green",
              tone === "amber" && "text-status-amber",
              tone === "red" && "text-status-red",
              !tone && "text-charcoal-500",
            )}
          >
            {delta}
          </span>
        )}
      </div>
      {helper && <div className="text-[12px] text-charcoal-500 mt-1">{helper}</div>}
    </div>
  );
}
