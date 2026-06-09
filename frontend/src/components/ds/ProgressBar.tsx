import clsx from "clsx";

type Tone = "steel" | "green" | "amber" | "red";

const TONES: Record<Tone, string> = {
  steel: "bg-steel-700",
  green: "bg-status-green",
  amber: "bg-status-amber",
  red: "bg-status-red",
};

export function ProgressBar({
  value,
  tone = "steel",
  className,
  indeterminate = false,
  ariaLabel,
}: {
  value: number;
  tone?: Tone;
  className?: string;
  indeterminate?: boolean;
  ariaLabel?: string;
}) {
  const clamped = Math.max(0, Math.min(100, Math.round(value)));
  return (
    <div
      role="progressbar"
      aria-label={ariaLabel}
      aria-valuemin={0}
      aria-valuemax={100}
      aria-valuenow={indeterminate ? undefined : clamped}
      className={clsx(
        "h-1.5 w-full overflow-hidden rounded-full bg-charcoal-100",
        className,
      )}
    >
      <div
        className={clsx(
          TONES[tone],
          "h-full rounded-full transition-[width] duration-500 ease-out",
          indeterminate && "animate-pulse",
        )}
        style={{ width: `${indeterminate ? 35 : clamped}%` }}
      />
    </div>
  );
}
