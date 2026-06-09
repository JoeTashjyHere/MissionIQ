import clsx from "clsx";

export function BriefingSection({
  eyebrow,
  title,
  children,
  className,
}: {
  eyebrow?: string;
  title: string;
  children: React.ReactNode;
  className?: string;
}) {
  return (
    <section className={clsx("border-t border-charcoal-100 px-6 py-5", className)}>
      {eyebrow && <div className="miq-eyebrow mb-1">{eyebrow}</div>}
      <h2 className="text-h3 text-charcoal-900 mb-3">{title}</h2>
      <div className="text-[14px] text-charcoal-900 leading-relaxed">{children}</div>
    </section>
  );
}

export function BulletList({ items }: { items: string[] }) {
  if (!items?.length) {
    return <p className="text-charcoal-500 italic text-[13px]">No items.</p>;
  }
  return (
    <ul className="list-disc pl-5 space-y-1.5 text-[14px]">
      {items.map((it, i) => (
        <li key={i}>{it}</li>
      ))}
    </ul>
  );
}
