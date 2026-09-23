/** Clinic billing, payment reconciliation, and cashier services. */

import { query, withTransaction } from "../db.ts";
import { NotFoundError, BadRequestError } from "../lib/errors.ts";
import { broadcastEvent } from "../routes/stream.ts";

export class BillingService {
  /** Reconcile payment for a consultation or lab order invoice. */
  static async payInvoice(
    invoiceId: string,
    paymentMethod: "card" | "upi" | "cash" | "insurance" | "netbanking",
    transactionRef?: string
  ) {
    return withTransaction(async (client) => {
      const invRes = await client.query(
        `SELECT * FROM invoices WHERE id = $1`,
        [invoiceId]
      );

      if (invRes.rows.length === 0) {
        throw new NotFoundError("Invoice not found");
      }

      const inv = invRes.rows[0];
      if (inv.payment_status === "paid") {
        return inv; // Idempotent
      }

      const txRef =
        transactionRef ||
        `TXN-CC-${Date.now().toString(36).toUpperCase()}-${Math.floor(Math.random() * 1000)}`;

      const updatedInv = await client.query(
        `UPDATE invoices
         SET payment_status = 'paid', payment_method = $1, transaction_ref = $2, paid_at = NOW()
         WHERE id = $3
         RETURNING *`,
        [paymentMethod, txRef, invoiceId]
      );

      // If tied to an appointment, mark appointment as paid
      if (inv.appointment_id) {
        await client.query(
          `UPDATE appointments
           SET is_paid = TRUE, payment_method = $1, updated_at = NOW()
           WHERE id = $2`,
          [paymentMethod, inv.appointment_id]
        );
      }

      // Notify patient
      await client.query(
        `INSERT INTO notifications (user_id, title, message, type, link)
         VALUES ($1, $2, $3, 'payment_received', $4)`,
        [
          inv.patient_id,
          "Payment Receipt",
          `Payment of ₹${inv.net_payable} received for Invoice #${inv.invoice_number}.`,
          `/invoices`,
        ]
      );

      broadcastEvent("payment_received", {
        invoiceId,
        patientId: inv.patient_id,
        netPayable: inv.net_payable,
        paymentMethod,
        transactionRef: txRef,
      });

      return updatedInv.rows[0];
    });
  }
}
