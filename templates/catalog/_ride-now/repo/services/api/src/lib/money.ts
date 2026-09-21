/** Money is INR with two decimals. Round half away from zero at every step that stores a value. */
export function money(value: number): number {
  // Shift the decimal point in the string form ("1.005e2"), not by multiplying: 1.005 * 100 is
  // 100.49999... in binary floating point and would round down.
  const shifted = Math.round(Number(`${Math.abs(value)}e2`));
  return Math.sign(value) * Number(`${shifted}e-2`) || 0;
}

/** pg returns NUMERIC as a string; convert without losing the two decimals. */
export function num(value: unknown): number {
  if (value === null || value === undefined) return 0;
  const parsed = typeof value === "number" ? value : Number(value);
  if (!Number.isFinite(parsed)) throw new Error(`not a number: ${String(value)}`);
  return parsed;
}
