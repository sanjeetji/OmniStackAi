/**
 * SMS for one-time sign-in codes. The mock provider logs the code instead of sending it (never in
 * production logs: it prints only while OMNISTACK_PREVIEW=1). Twilio or MSG91 implement the same
 * interface.
 */
export interface SmsProvider {
  readonly name: string;
  send(phone: string, message: string): Promise<void>;
}

export const mockSms: SmsProvider = {
  name: "mock",
  async send(phone, message) {
    if (process.env.OMNISTACK_PREVIEW === "1") {
      console.log(`[sms:mock] to ${phone}: ${message}`);
    }
  },
};
