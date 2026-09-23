/** Double-entry financial ledger service for Bazaar multi-party accounting. */

import { randomUUID } from "node:crypto";
import type { PoolClient } from "pg";
import { query, withTransaction } from "../db.ts";
import { BadRequestError, NotFoundError } from "../lib/errors.ts";

export interface Account {
  id: string;
  holder_type: "platform" | "vendor" | "shopper";
  holder_id: string | null;
  currency: string;
  balance_cents: number;
}

export interface LedgerEntry {
  id: string;
  journal_id: string;
  debit_account_id: string;
  credit_account_id: string;
  amount_cents: number;
  entry_type:
    | "order_payment"
    | "commission_fee"
    | "vendor_credit"
    | "shopper_refund"
    | "payout_settlement";
  reference_type: "order" | "shipment" | "settlement" | "return";
  reference_id: string;
  description: string;
  created_at: string;
}

export class LedgerService {
  /** Gets an existing account or creates it if not yet present. */
  async getOrCreateAccount(
    holderType: "platform" | "vendor" | "shopper",
    holderId: string | null,
    currency = "INR",
    client?: PoolClient
  ): Promise<Account> {
    const runner = client || { query };

    const sqlSelect = holderId
      ? `SELECT * FROM accounts WHERE holder_type = $1 AND holder_id = $2 AND currency = $3`
      : `SELECT * FROM accounts WHERE holder_type = $1 AND holder_id IS NULL AND currency = $2`;
    const selectParams = holderId ? [holderType, holderId, currency] : [holderType, currency];

    const existing = await runner.query<Account>(sqlSelect, selectParams);
    if (existing.rows.length > 0) {
      return existing.rows[0];
    }

    const sqlInsert = `INSERT INTO accounts (holder_type, holder_id, currency, balance_cents)
                       VALUES ($1, $2, $3, 0)
                       ON CONFLICT ON CONSTRAINT uq_account_holder DO UPDATE SET updated_at = NOW()
                       RETURNING *`;
    const inserted = await runner.query<Account>(sqlInsert, [holderType, holderId, currency]);
    return inserted.rows[0];
  }

  /** Posts a balanced double-entry ledger transaction. */
  async postEntry(
    params: {
      entryType: LedgerEntry["entry_type"];
      debitAccountId: string;
      creditAccountId: string;
      amountCents: number;
      referenceType: LedgerEntry["reference_type"];
      referenceId: string;
      description: string;
    },
    client?: PoolClient
  ): Promise<LedgerEntry> {
    if (params.amountCents <= 0) {
      throw new BadRequestError("Ledger transaction amount must be greater than zero");
    }

    const execute = async (c: PoolClient) => {
      // 1. Update debit account (+ balance)
      await c.query(
        `UPDATE accounts SET balance_cents = balance_cents + $1, updated_at = NOW() WHERE id = $2`,
        [params.amountCents, params.debitAccountId]
      );

      // 2. Update credit account (- balance)
      await c.query(
        `UPDATE accounts SET balance_cents = balance_cents - $1, updated_at = NOW() WHERE id = $2`,
        [params.amountCents, params.creditAccountId]
      );

      // 3. Record journal entry
      const journalId = randomUUID();
      const res = await c.query<LedgerEntry>(
        `INSERT INTO ledger_entries (
           journal_id, debit_account_id, credit_account_id, amount_cents,
           entry_type, reference_type, reference_id, description
         )
         VALUES ($1, $2, $3, $4, $5, $6, $7, $8)
         RETURNING *`,
        [
          journalId,
          params.debitAccountId,
          params.creditAccountId,
          params.amountCents,
          params.entryType,
          params.referenceType,
          params.referenceId,
          params.description,
        ]
      );

      return res.rows[0];
    };

    if (client) {
      return execute(client);
    }
    return withTransaction(execute);
  }

  /** Records order payment received into platform escrow clearing account. */
  async recordOrderPayment(
    orderId: string,
    totalCents: number,
    client?: PoolClient
  ): Promise<void> {
    const platformCash = await this.getOrCreateAccount("platform", null, "INR", client);
    const shopperClearing = await this.getOrCreateAccount("shopper", null, "INR", client);

    await this.postEntry(
      {
        entryType: "order_payment",
        debitAccountId: platformCash.id,
        creditAccountId: shopperClearing.id,
        amountCents: totalCents,
        referenceType: "order",
        referenceId: orderId,
        description: `Customer payment for order ${orderId}`,
      },
      client
    );
  }

  /** Distributes shipment funds: platform takes commission, vendor receives payable. */
  async recordShipmentFulfillment(
    shipmentId: string,
    shopId: string,
    subtotalCents: number,
    commissionCents: number,
    vendorPayoutCents: number,
    client?: PoolClient
  ): Promise<void> {
    const shopperClearing = await this.getOrCreateAccount("shopper", null, "INR", client);
    const platformRevenue = await this.getOrCreateAccount("platform", null, "INR", client);
    const vendorPayable = await this.getOrCreateAccount("vendor", shopId, "INR", client);

    // 1. Commission portion to platform
    if (commissionCents > 0) {
      await this.postEntry(
        {
          entryType: "commission_fee",
          debitAccountId: shopperClearing.id,
          creditAccountId: platformRevenue.id,
          amountCents: commissionCents,
          referenceType: "shipment",
          referenceId: shipmentId,
          description: `Marketplace commission fee for shipment ${shipmentId}`,
        },
        client
      );
    }

    // 2. Net vendor payout credited to vendor payable
    if (vendorPayoutCents > 0) {
      await this.postEntry(
        {
          entryType: "vendor_credit",
          debitAccountId: shopperClearing.id,
          creditAccountId: vendorPayable.id,
          amountCents: vendorPayoutCents,
          referenceType: "shipment",
          referenceId: shipmentId,
          description: `Vendor earnings credit for shipment ${shipmentId}`,
        },
        client
      );
    }
  }

  /** Creates and settles a vendor payout batch. */
  async createSettlementBatch(shopId: string): Promise<any> {
    return withTransaction(async (client) => {
      // Find delivered shipments that have not been settled yet
      const shipRes = await client.query<{
        id: string;
        subtotal_cents: string;
        commission_cents: string;
        vendor_payout_cents: string;
      }>(
        `SELECT id, subtotal_cents, commission_cents, vendor_payout_cents
         FROM shipments
         WHERE shop_id = $1 AND status = 'delivered'
           AND id NOT IN (
             SELECT reference_id FROM ledger_entries WHERE entry_type = 'payout_settlement'
           )`,
        [shopId]
      );

      let grossCents = 0;
      let commCents = 0;
      let netCents = 0;

      for (const s of shipRes.rows) {
        grossCents += parseInt(s.subtotal_cents, 10);
        commCents += parseInt(s.commission_cents, 10);
        netCents += parseInt(s.vendor_payout_cents, 10);
      }

      if (netCents <= 0) {
        throw new BadRequestError("No unsettled earnings available for this vendor");
      }

      const batchNumber = `SET-${Date.now().toString(36).toUpperCase()}-${Math.floor(100 + Math.random() * 900)}`;
      const now = new Date();
      const weekAgo = new Date(now.getTime() - 7 * 24 * 60 * 60 * 1000);

      const batchRes = await client.query(
        `INSERT INTO settlement_batches (
           shop_id, batch_number, status, gross_sales_cents, commission_cents,
           refund_deductions_cents, net_payout_cents, period_start, period_end,
           payout_reference, processed_at
         )
         VALUES ($1, $2, 'processed', $3, $4, 0, $5, $6, $7, $8, NOW())
         RETURNING *`,
        [
          shopId,
          batchNumber,
          grossCents,
          commCents,
          netCents,
          weekAgo.toISOString(),
          now.toISOString(),
          `NEFT-TXN-${Date.now()}`,
        ]
      );

      const batch = batchRes.rows[0];

      // Record ledger payout transaction
      const vendorAccount = await this.getOrCreateAccount("vendor", shopId, "INR", client);
      const platformCash = await this.getOrCreateAccount("platform", null, "INR", client);

      await this.postEntry(
        {
          entryType: "payout_settlement",
          debitAccountId: vendorAccount.id,
          creditAccountId: platformCash.id,
          amountCents: netCents,
          referenceType: "settlement",
          referenceId: batch.id,
          description: `Direct bank transfer payout for batch ${batchNumber}`,
        },
        client
      );

      return batch;
    });
  }

  /** Gets ledger history and current balance for a vendor shop. */
  async getVendorLedger(shopId: string, limit = 50): Promise<{ account: Account; entries: any[] }> {
    const account = await this.getOrCreateAccount("vendor", shopId, "INR");
    const res = await query(
      `SELECT le.*,
              da.holder_type AS debit_holder,
              ca.holder_type AS credit_holder
       FROM ledger_entries le
       JOIN accounts da ON da.id = le.debit_account_id
       JOIN accounts ca ON ca.id = le.credit_account_id
       WHERE le.debit_account_id = $1 OR le.credit_account_id = $1
       ORDER BY le.created_at DESC
       LIMIT $2`,
      [account.id, limit]
    );

    return { account, entries: res.rows };
  }

  /** Aggregates financial overview for platform operators. */
  async getPlatformFinancialSummary(): Promise<{
    platformCashBalanceCents: number;
    platformRevenueCents: number;
    totalVendorPayablesCents: number;
    totalSettlementsPaidCents: number;
  }> {
    const accRes = await query<{
      holder_type: string;
      holder_id: string | null;
      balance_cents: string;
    }>(`SELECT holder_type, holder_id, balance_cents FROM accounts`);

    let platformCash = 0;
    let platformRevenue = 0;
    let vendorPayables = 0;

    for (const a of accRes.rows) {
      const bal = parseInt(a.balance_cents, 10);
      if (a.holder_type === "platform") {
        platformCash += bal;
      } else if (a.holder_type === "vendor") {
        vendorPayables += Math.abs(bal);
      }
    }

    const setRes = await query<{ sum: string }>(
      `SELECT COALESCE(SUM(net_payout_cents), 0)::text as sum FROM settlement_batches WHERE status = 'processed'`
    );
    const settlementsPaid = parseInt(setRes.rows[0]?.sum || "0", 10);

    const commRes = await query<{ sum: string }>(
      `SELECT COALESCE(SUM(amount_cents), 0)::text as sum
       FROM ledger_entries
       WHERE entry_type = 'commission_fee'`
    );
    platformRevenue = parseInt(commRes.rows[0]?.sum || "0", 10);

    return {
      platformCashBalanceCents: platformCash,
      platformRevenueCents: platformRevenue,
      totalVendorPayablesCents: vendorPayables,
      totalSettlementsPaidCents: settlementsPaid,
    };
  }
}

export const ledgerService = new LedgerService();
