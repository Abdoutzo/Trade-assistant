export const pct = (x: number | null | undefined, digits = 1) =>
  x == null ? "-" : `${x >= 0 ? "+" : ""}${(x * 100).toFixed(digits).replace(".", ",")} %`;

export const price = (x: number | null | undefined, currency?: string | null) =>
  x == null
    ? "-"
    : x.toLocaleString("fr-FR", { minimumFractionDigits: 2, maximumFractionDigits: 2 }) + (currency ? ` ${currency}` : "");

/** 27 057 800 000 -> "27,06 Md" ; 5.72 -> "5,72". */
export const amount = (x: number) => {
  const abs = Math.abs(x);
  const fmt = (v: number, unit: string) => v.toLocaleString("fr-FR", { maximumFractionDigits: 2 }) + unit;
  if (abs >= 1e9) return fmt(x / 1e9, " Md");
  if (abs >= 1e6) return fmt(x / 1e6, " M");
  return x.toLocaleString("fr-FR", { maximumFractionDigits: 2 });
};

export const changeColor = (x: number | null | undefined) =>
  x == null ? "text-slate-400" : x >= 0 ? "text-emerald-600 dark:text-emerald-400" : "text-red-600 dark:text-red-400";

/** A metric value in its own unit: 0.153 -> "15,3 %", 17.7 -> "17,7x". */
export const metricValue = (x: number | null | undefined, fmt: string) => {
  if (x == null) return "-";
  if (fmt === "pct") return pct(x).replace("+", "");
  const s = x.toLocaleString("fr-FR", { maximumFractionDigits: fmt === "num" ? 2 : 1 });
  return fmt === "x" ? `${s}x` : s;
};

export const scoreColor = (s: number | null | undefined) =>
  s == null
    ? "bg-slate-200 text-slate-600 dark:bg-slate-800 dark:text-slate-400"
    : s >= 70
      ? "bg-emerald-600 text-white"
      : s >= 55
        ? "bg-lime-500 text-white"
        : s >= 40
          ? "bg-amber-500 text-white"
          : "bg-red-500 text-white";

export const barColor = (s: number | null | undefined) =>
  s == null ? "bg-slate-300" : s >= 70 ? "bg-emerald-500" : s >= 55 ? "bg-lime-500" : s >= 40 ? "bg-amber-500" : "bg-red-500";

/** A unit price in euros, with cents: 6.1 -> "6,10 €". */
export const unitEuros = (x: number) =>
  x.toLocaleString("fr-FR", { style: "currency", currency: "EUR", minimumFractionDigits: 2, maximumFractionDigits: 2 });
