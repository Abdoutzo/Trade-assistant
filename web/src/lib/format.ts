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
