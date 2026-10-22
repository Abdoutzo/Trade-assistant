export default function PeaBadge({ eligible, reason }: { eligible: boolean | null; reason: string | null }) {
  const [label, style] =
    eligible === true
      ? ["PEA", "bg-emerald-100 text-emerald-800 dark:bg-emerald-950 dark:text-emerald-300"]
      : eligible === false
        ? ["Hors PEA", "bg-red-100 text-red-800 dark:bg-red-950 dark:text-red-300"]
        : ["PEA ?", "bg-amber-100 text-amber-800 dark:bg-amber-950 dark:text-amber-300"];
  return (
    <span title={reason ?? ""} className={`rounded px-1.5 py-0.5 text-xs font-medium ${style}`}>
      {label}
    </span>
  );
}
