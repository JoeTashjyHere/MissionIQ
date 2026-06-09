import clsx from "clsx";

export function EmptyState({
  icon,
  title,
  description,
  action,
  className,
}: {
  icon?: React.ReactNode;
  title: string;
  description?: string;
  action?: React.ReactNode;
  className?: string;
}) {
  return (
    <div
      className={clsx(
        "flex flex-col items-center justify-center text-center py-12 px-6 rounded-md border border-dashed border-charcoal-300 bg-white",
        className,
      )}
    >
      {icon && (
        <div className="text-charcoal-500 mb-3 [&_svg]:h-8 [&_svg]:w-8">{icon}</div>
      )}
      <div className="text-h3 text-charcoal-900">{title}</div>
      {description && (
        <p className="mt-2 max-w-md text-[14px] text-charcoal-500">{description}</p>
      )}
      {action && <div className="mt-4">{action}</div>}
    </div>
  );
}
