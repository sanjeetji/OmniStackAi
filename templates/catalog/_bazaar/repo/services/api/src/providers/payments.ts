/** Mock Payment Gateway provider for Bazaar (Card, UPI, COD). */

import { randomUUID } from "node:crypto";

export interface PaymentIntent {
  id: string;
  orderNumber: string;
  amountCents: number;
  currency: string;
  method: "mock_card" | "mock_upi" | "cod";
  status: "pending" | "paid" | "failed";
  reference: string;
  createdAt: string;
}

export interface RefundResult {
  refundId: string;
  paymentReference: string;
  amountCents: number;
  status: "processed" | "failed";
  processedAt: string;
}

export class MockPaymentProvider {
  /** Initiates a payment transaction. */
  async initiatePayment(params: {
    orderNumber: string;
    amountCents: number;
    currency?: string;
    method: "mock_card" | "mock_upi" | "cod";
  }): Promise<PaymentIntent> {
    const isCod = params.method === "cod";
    const ref = isCod
      ? `COD-${Date.now().toString(36).toUpperCase()}-${Math.floor(1000 + Math.random() * 9000)}`
      : `PAY-${Date.now().toString(36).toUpperCase()}-${Math.floor(1000 + Math.random() * 9000)}`;

    return {
      id: randomUUID(),
      orderNumber: params.orderNumber,
      amountCents: params.amountCents,
      currency: params.currency || "INR",
      method: params.method,
      status: isCod ? "pending" : "paid", // Cards/UPI in mock mode resolve immediately as paid
      reference: ref,
      createdAt: new Date().toISOString(),
    };
  }

  /** Simulates a refund. */
  async processRefund(params: {
    paymentReference: string;
    amountCents: number;
    reason?: string;
  }): Promise<RefundResult> {
    return {
      refundId: `REF-${Date.now().toString(36).toUpperCase()}-${Math.floor(1000 + Math.random() * 9000)}`,
      paymentReference: params.paymentReference,
      amountCents: params.amountCents,
      status: "processed",
      processedAt: new Date().toISOString(),
    };
  }
}

export const paymentProvider = new MockPaymentProvider();
