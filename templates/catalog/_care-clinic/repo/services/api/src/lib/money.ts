/** Currency formatting and cancellation fee calculations. */

export function formatINR(paiseOrRupees: number, isRupees = true): string {
  const rupees = isRupees ? paiseOrRupees : paiseOrRupees / 100;
  return new Intl.NumberFormat("en-IN", {
    style: "currency",
    currency: "INR",
    maximumFractionDigits: 0,
  }).format(rupees);
}

export interface CancellationPolicyResult {
  canCancel: boolean;
  refundAmount: number;
  cancellationFee: number;
  refundPercentage: number;
  reasonExplanation: string;
}

/**
 * Healthcare cancellation policy:
 * - > 24 hours before scheduled time: 100% refund, ₹0 cancellation fee
 * - 4 to 24 hours before: 70% refund, 30% cancellation fee
 * - < 4 hours before: 0% refund, 100% fee (late cancellation penalty)
 */
export function calculateCancellationRefund(
  feeAmount: number,
  scheduledDate: string, // YYYY-MM-DD
  startTime: string,     // HH:MM:SS
  now = new Date()
): CancellationPolicyResult {
  const [year, month, day] = scheduledDate.split("-").map(Number);
  const [hours, minutes, seconds = 0] = startTime.split(":").map(Number);
  const scheduledTimeMs = Date.UTC(year, month - 1, day, hours, minutes, seconds);
  const nowMs = now.getTime();
  const diffHours = (scheduledTimeMs - nowMs) / (1000 * 60 * 60);

  if (diffHours < 0) {
    return {
      canCancel: false,
      refundAmount: 0,
      cancellationFee: feeAmount,
      refundPercentage: 0,
      reasonExplanation: "Past appointment cannot be cancelled for a refund.",
    };
  }

  if (diffHours >= 24) {
    return {
      canCancel: true,
      refundAmount: feeAmount,
      cancellationFee: 0,
      refundPercentage: 100,
      reasonExplanation: "Cancelled more than 24 hours in advance: 100% full refund.",
    };
  }

  if (diffHours >= 4) {
    const fee = Math.round(feeAmount * 0.3);
    const refund = feeAmount - fee;
    return {
      canCancel: true,
      refundAmount: refund,
      cancellationFee: fee,
      refundPercentage: 70,
      reasonExplanation: "Cancelled between 4 and 24 hours in advance: 70% refund with 30% clinic processing fee.",
    };
  }

  return {
    canCancel: true,
    refundAmount: 0,
    cancellationFee: feeAmount,
    refundPercentage: 0,
    reasonExplanation: "Cancelled less than 4 hours in advance: late cancellation policy applies, non-refundable.",
  };
}
