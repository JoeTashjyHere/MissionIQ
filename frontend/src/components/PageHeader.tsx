export function PageHeader({
  eyebrow,
  title,
  subtitle,
  actions,
}: {
  eyebrow?: string;
  title: string;
  subtitle?: React.ReactNode;
  actions?: React.ReactNode;
}) {
  return (
    <div className="flex items-start justify-between mb-6 gap-4">
      <div>
        {eyebrow && <div className="miq-eyebrow mb-1.5">{eyebrow}</div>}
        <h1 className="text-h1 text-charcoal-900">{title}</h1>
        {subtitle && (
          <div className="text-[14px] text-charcoal-500 mt-1">{subtitle}</div>
        )}
      </div>
      {actions && <div className="flex items-center gap-2">{actions}</div>}
    </div>
  );
}
