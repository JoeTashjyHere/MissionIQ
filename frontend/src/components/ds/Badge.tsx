import clsx from "clsx";

type Variant = "default" | "info" | "teal" | "neutral";

export function Badge({
  variant = "default",
  children,
  className,
}: {
  variant?: Variant;
  children: React.ReactNode;
  className?: string;
}) {
  return (
    <span
      className={clsx(
        "inline-flex items-center rounded-[6px] px-2 py-0.5 text-[12px] font-medium",
        variant === "default" && "bg-charcoal-100 text-charcoal-700",
        variant === "info" && "bg-steel-700/10 text-steel-700",
        variant === "teal" && "bg-teal-100 text-teal-700",
        variant === "neutral" && "border border-charcoal-300 text-charcoal-700",
        className,
      )}
    >
      {children}
    </span>
  );
}
