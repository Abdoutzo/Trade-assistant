// Monthly investing (DCA) projection: an initial amount, then the same amount every month,
// compounded at a constant annual rate. Illustrative only: real markets are never constant.

export type Point = { month: number; invested: number; value: number };

export function project(initial: number, monthly: number, annualRate: number, years: number): Point[] {
  const r = Math.pow(1 + annualRate, 1 / 12) - 1;
  const points: Point[] = [{ month: 0, invested: initial, value: initial }];
  let value = initial;
  let invested = initial;
  for (let m = 1; m <= years * 12; m++) {
    value = value * (1 + r) + monthly;
    invested += monthly;
    points.push({ month: m, invested, value });
  }
  return points;
}

export const euros = (x: number) =>
  x.toLocaleString("fr-FR", { style: "currency", currency: "EUR", maximumFractionDigits: 0 });
