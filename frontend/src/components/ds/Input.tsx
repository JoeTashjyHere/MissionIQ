"use client";

import clsx from "clsx";
import { type InputHTMLAttributes, type TextareaHTMLAttributes, forwardRef } from "react";

interface InputProps extends InputHTMLAttributes<HTMLInputElement> {
  label?: string;
  helper?: string;
  error?: string;
}

export const Input = forwardRef<HTMLInputElement, InputProps>(function Input(
  { label, helper, error, className, id, ...rest },
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
      <input
        ref={ref}
        id={_id}
        className={clsx(
          "h-10 rounded-[6px] border border-charcoal-300 bg-white px-3 text-[14px] text-charcoal-900",
          "placeholder:text-charcoal-500 focus-visible:border-steel-500",
          error && "border-status-red",
          className,
        )}
        {...rest}
      />
      {(helper || error) && (
        <p
          className={clsx(
            "text-[12px]",
            error ? "text-status-red" : "text-charcoal-500",
          )}
        >
          {error || helper}
        </p>
      )}
    </div>
  );
});

interface TextareaProps extends TextareaHTMLAttributes<HTMLTextAreaElement> {
  label?: string;
  helper?: string;
  error?: string;
}

export const Textarea = forwardRef<HTMLTextAreaElement, TextareaProps>(function Textarea(
  { label, helper, error, className, id, ...rest },
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
      <textarea
        ref={ref}
        id={_id}
        className={clsx(
          "min-h-[80px] rounded-[6px] border border-charcoal-300 bg-white p-3 text-[14px] text-charcoal-900",
          "placeholder:text-charcoal-500 focus-visible:border-steel-500",
          error && "border-status-red",
          className,
        )}
        {...rest}
      />
      {(helper || error) && (
        <p
          className={clsx(
            "text-[12px]",
            error ? "text-status-red" : "text-charcoal-500",
          )}
        >
          {error || helper}
        </p>
      )}
    </div>
  );
});
