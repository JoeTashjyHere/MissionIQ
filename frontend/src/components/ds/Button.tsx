"use client";

import clsx from "clsx";
import { type ButtonHTMLAttributes, forwardRef } from "react";

type Variant = "primary" | "secondary" | "ghost" | "danger";
type Size = "sm" | "md" | "lg";

interface ButtonProps extends ButtonHTMLAttributes<HTMLButtonElement> {
  variant?: Variant;
  size?: Size;
  loading?: boolean;
}

const variantClass: Record<Variant, string> = {
  primary:
    "bg-steel-700 hover:bg-steel-500 text-white border border-steel-700 disabled:bg-charcoal-300 disabled:border-charcoal-300",
  secondary:
    "bg-white text-charcoal-900 border border-charcoal-300 hover:bg-charcoal-100",
  ghost:
    "bg-transparent text-charcoal-700 border border-transparent hover:bg-charcoal-100",
  danger:
    "bg-status-red text-white border border-status-red hover:opacity-90",
};

const sizeClass: Record<Size, string> = {
  sm: "h-8 text-[13px] px-3 rounded-[6px]",
  md: "h-10 text-[14px] px-4 rounded-[6px]",
  lg: "h-12 text-[15px] px-5 rounded-[8px]",
};

export const Button = forwardRef<HTMLButtonElement, ButtonProps>(function Button(
  { variant = "primary", size = "md", loading, className, children, disabled, ...rest },
  ref,
) {
  return (
    <button
      ref={ref}
      disabled={disabled || loading}
      className={clsx(
        "inline-flex items-center justify-center gap-2 font-medium transition-colors",
        "focus-visible:outline focus-visible:outline-2 focus-visible:outline-steel-300 focus-visible:outline-offset-2",
        "disabled:cursor-not-allowed",
        variantClass[variant],
        sizeClass[size],
        className,
      )}
      {...rest}
    >
      {loading && (
        <span className="inline-block h-3 w-3 rounded-full border-2 border-current border-r-transparent animate-spin" />
      )}
      {children}
    </button>
  );
});
