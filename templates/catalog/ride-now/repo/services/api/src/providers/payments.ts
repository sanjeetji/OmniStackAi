/**
 * Card payments for wallet top-ups. The mock provider approves any card except the documented test
 * number 4000 0000 0000 0002, which is declined, so failure paths can be tried. A Stripe or
 * Razorpay provider implements the same interface: create an intent, confirm it with the card
 * token from the provider's client SDK, and verify webhooks in production.
 */
export interface ChargeRequest {
  amount: number;
  currency: string;
  cardNumber: string;
  reference: string;
}

export type ChargeResult = { ok: true; last4: string; providerRef: string } | { ok: false; reason: string; last4: string };

export interface PaymentsProvider {
  readonly name: string;
  charge(request: ChargeRequest): Promise<ChargeResult>;
}

export const DECLINED_TEST_CARD = "4000000000000002";

export const mockPayments: PaymentsProvider = {
  name: "mock",
  async charge({ cardNumber, reference }) {
    const digits = cardNumber.replace(/\D/g, "");
    const last4 = digits.slice(-4);
    if (digits.length < 12 || digits.length > 19) return { ok: false, reason: "Enter a valid card number.", last4 };
    if (digits === DECLINED_TEST_CARD) return { ok: false, reason: "The card was declined.", last4 };
    return { ok: true, last4, providerRef: `mock_${reference}` };
  },
};
