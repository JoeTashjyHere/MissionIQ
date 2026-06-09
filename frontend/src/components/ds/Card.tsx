import clsx from "clsx";
import { type HTMLAttributes, forwardRef } from "react";

interface CardProps extends HTMLAttributes<HTMLDivElement> {
  variant?: "default" | "subtle" | "outline";
}

export const Card = forwardRef<HTMLDivElement, CardProps>(function Card(
  { variant = "default", className, children, ...rest },
  ref,
) {
  return (
    <div
      ref={ref}
      className={clsx(
        "rounded-md",
        variant === "default" && "bg-white border border-charcoal-300 shadow-card",
        variant === "subtle" && "bg-white",
        variant === "outline" && "bg-transparent border border-charcoal-300",
        className,
      )}
      {...rest}
    >
      {children}
    </div>
  );
});

export function CardHeader({
  eyebrow,
  title,
  subtitle,
  actions,
}: {
  eyebrow?: string;
  title: string;
  subtitle?: string;
  actions?: React.ReactNode;
}) {
  return (
    <div className="flex items-start justify-between border-b border-charcoal-100 px-6 py-4">
      <div>
        {eyebrow && <div className="miq-eyebrow mb-1">{eyebrow}</div>}
        <h3 className="text-h3 text-charcoal-900">{title}</h3>
        {subtitle && (
          <p className="text-[13px] text-charcoal-500 mt-1">{subtitle}</p>
        )}
      </div>
      {actions && <div className="flex items-center gap-2">{actions}</div>}
    </div>
  );
}

export function CardBody({ className, children, ...rest }: HTMLAttributes<HTMLDivElement>) {
  return (
    <div className={clsx("px-6 py-5", className)} {...rest}>
      {children}
    </div>
  );
}
