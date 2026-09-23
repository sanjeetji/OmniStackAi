/**
 * Human-readable document numbers (APT-2026-00042, INV-2026-00042, …).
 *
 * These were once derived from `COUNT(*) + 1`, which collides as soon as the table has any gap —
 * the demo seed leaves several — and the unique index then rejects the insert. The next number is
 * the highest one already issued plus one, read inside the caller's transaction.
 */

export interface Queryable {
  query(text: string, values?: unknown[]): Promise<{ rows: any[] }>;
}

const TABLES = {
  appointments: { column: "appointment_number", prefix: "APT" },
  invoices: { column: "invoice_number", prefix: "INV" },
  prescriptions: { column: "prescription_number", prefix: "RX" },
  refunds: { column: "refund_number", prefix: "REF" },
  lab_orders: { column: "order_number", prefix: "LAB" },
} as const;

export type NumberedTable = keyof typeof TABLES;

export async function nextDocumentNumber(
  client: Queryable,
  table: NumberedTable,
  year = new Date().getFullYear()
): Promise<string> {
  const { column, prefix } = TABLES[table];
  const series = `${prefix}-${year}-`;

  // The table and column names come from the map above, never from a caller's input.
  const res = await client.query(
    `SELECT COALESCE(MAX(NULLIF(regexp_replace(${column}, '^.*-', ''), '')::bigint), 0) AS highest
       FROM ${table}
      WHERE ${column} LIKE $1`,
    [`${series}%`]
  );

  const next = Number(res.rows[0]?.highest ?? 0) + 1;
  return `${series}${next.toString().padStart(5, "0")}`;
}
