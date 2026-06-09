"use client";

import clsx from "clsx";
import { type SelectHTMLAttributes, forwardRef } from "react";

interface SelectProps extends SelectHTMLAttributes<HTMLSelectElement> {
  label?: string;
  error?: string;
}

export const Select = forwardRef<HTMLSelectElement, SelectProps>(function Select(
  { label, error, className, children, id, ...rest },
  ref,
) {
  const _id = id ?? rest.name;
  return (
    <div className="flex flex-col gap-1.5">
      {label && (
        <label htmlFor={_id} className="text-[13px] font-medium text-charcoal-700">
          {label}
        </label>
      )}
      <select
        ref={ref}
        id={_id}
        className={clsx(
          "h-10 rounded-[6px] border border-charcoal-300 bg-white px-3 text-[14px] text-charcoal-900",
          "focus-visible:border-steel-500",
          error && "border-status-red",
          className,
        )}
        {...rest}
      >
        {children}
      </select>
      {error && <p className="text-[12px] text-status-red">{error}</p>}
    </div>
  );
});
