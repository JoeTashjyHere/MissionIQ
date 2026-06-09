import clsx from "clsx";

export function Skeleton({ className }: { className?: string }) {
  return (
    <div
      className={clsx(
        "animate-pulse rounded-[6px] bg-charcoal-100",
        className,
      )}
    />
  );
}
