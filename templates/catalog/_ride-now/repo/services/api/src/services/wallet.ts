import type { Queryable } from "../db.ts";
import { one } from "../db.ts";
import { money, num } from "../lib/money.ts";
import { hub } from "../lib/events.ts";

export type LedgerKind =
  | "topup"
  | "trip_payment"
  | "trip_earning"
  | "commission"
  | "cash_commission"
  | "refund"
  | "payout"
  | "adjustment";

/**
 * Record one money movement and update the wallet balance in the same transaction. `amount` is
 * signed (debits are negative). Returns the new balance. Callers run this inside `tx`.
 */
export async function postLedger(
  client: Queryable,
  userId: string,
  kind: LedgerKind,
  amount: number,
  opts: { tripId?: string | null; reference?: string; note?: string } = {},
): Promise<number> {
  const value = money(amount);
  const wallet = await one<{ balance: string }>(
    `INSERT INTO wallets (user_id, balance) VALUES ($1, $2)
     ON CONFLICT (user_id) DO UPDATE SET balance = wallets.balance + EXCLUDED.balance, updated_at = now()
     RETURNING balance`,
    [userId, value],
    client,
  );
  const balance = num(wallet!.balance);
  await client.query(
    `INSERT INTO wallet_transactions (user_id, trip_id, kind, amount, balance_after, reference, note)
     VALUES ($1, $2, $3, $4, $5, $6, $7)`,
    [userId, opts.tripId ?? null, kind, value, balance, opts.reference ?? "", opts.note ?? ""],
  );
  return balance;
}

export async function balanceOf(userId: string, client?: Queryable): Promise<number> {
  const row = await one<{ balance: string }>("SELECT balance FROM wallets WHERE user_id = $1", [userId], client);
  return row ? num(row.balance) : 0;
}

export function announceWallet(userId: string, balance: number): void {
  hub.publish(`user:${userId}`, "wallet.updated", { balance });
}

let platformUserId: string | null = null;

/** The platform's own account that receives commission (seeded as platform@ridenow.local). */
export async function platformUser(client?: Queryable): Promise<string> {
  if (platformUserId) return platformUserId;
  const row = await one<{ id: string }>("SELECT id FROM users WHERE email = 'platform@ridenow.local'", [], client);
  if (!row) throw new Error("the platform account is missing (run the seed)");
  platformUserId = row.id;
  return platformUserId;
}
