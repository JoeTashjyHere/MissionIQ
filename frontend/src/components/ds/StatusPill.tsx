import clsx from "clsx";

type Tone = "green" | "amber" | "red" | "info" | "neutral";

export function StatusPill({
  tone = "neutral",
  children,
  className,
}: {
  tone?: Tone;
  children: React.ReactNode;
  className?: string;
}) {
  return (
    <span
      className={clsx(
        "inline-flex items-center gap-1.5 rounded-full px-2.5 py-0.5 text-[12px] font-medium",
        tone === "green" && "bg-status-greenBg text-status-green",
        tone === "amber" && "bg-status-amberBg text-status-amber",
        tone === "red" && "bg-status-redBg text-status-red",
        tone === "info" && "bg-steel-700/10 text-steel-700",
        tone === "neutral" && "bg-charcoal-100 text-charcoal-700",
        className,
      )}
    >
      <span
        className={clsx(
          "h-1.5 w-1.5 rounded-full",
          tone === "green" && "bg-status-green",
          tone === "amber" && "bg-status-amber",
          tone === "red" && "bg-status-red",
          tone === "info" && "bg-steel-700",
          tone === "neutral" && "bg-charcoal-500",
        )}
      />
      {children}
    </span>
  );
}
