import clsx from "clsx";

export interface Column<T> {
  key: string;
  header: string;
  render: (row: T) => React.ReactNode;
  width?: string;
  align?: "left" | "right" | "center";
}

export function DataTable<T>({
  columns,
  rows,
  emptyState,
  onRowClick,
  className,
}: {
  columns: Column<T>[];
  rows: T[];
  emptyState?: React.ReactNode;
  onRowClick?: (row: T) => void;
  className?: string;
}) {
  if (rows.length === 0 && emptyState) {
    return <div>{emptyState}</div>;
  }
  return (
    <div className={clsx("overflow-x-auto rounded-md border border-charcoal-300 bg-white", className)}>
      <table className="w-full border-collapse text-[14px]">
        <thead className="bg-charcoal-100 text-charcoal-700">
          <tr>
            {columns.map((c) => (
              <th
                key={c.key}
                scope="col"
                style={{ width: c.width }}
                className={clsx(
                  "px-4 py-2.5 font-semibold border-b border-charcoal-300 text-[12px] uppercase tracking-wide",
                  c.align === "right" && "text-right",
                  c.align === "center" && "text-center",
                  c.align !== "right" && c.align !== "center" && "text-left",
                )}
              >
                {c.header}
              </th>
            ))}
          </tr>
        </thead>
        <tbody>
          {rows.map((row, idx) => (
            <tr
              key={idx}
              onClick={onRowClick ? () => onRowClick(row) : undefined}
              className={clsx(
                "border-b border-charcoal-100 last:border-b-0",
                onRowClick && "cursor-pointer hover:bg-charcoal-100/50",
              )}
            >
              {columns.map((c) => (
                <td
                  key={c.key}
                  className={clsx(
                    "px-4 py-3 align-top",
                    c.align === "right" && "text-right",
                    c.align === "center" && "text-center",
                  )}
                >
                  {c.render(row)}
                </td>
              ))}
            </tr>
          ))}
        </tbody>
      </table>
    </div>
  );
}
