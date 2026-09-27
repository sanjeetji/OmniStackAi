import type { Metadata } from "next";
import LegalPage from "@/components/legal-page";
import { termsVersion } from "@/lib/legal";

export const metadata: Metadata = {
  title: "Privacy Policy",
};

export default function PrivacyPage() {
  return (
    <LegalPage title="Privacy Policy" version={termsVersion()}>
      <section>
        <h2>What we collect</h2>
        <ul>
          <li>Your account: name, email address, a one-way hash of your password, your plan and credit balance.</li>
          <li>Your projects: the descriptions you write, the generated code, and the data your previews store.</li>
          <li>Usage: which model answered each request, how many tokens it used, and what it cost.</li>
          <li>Payments: order records from the payment provider. We never see or store card numbers.</li>
        </ul>
      </section>
      <section>
        <h2>How it is used</h2>
        <p>
          Only to run the service for you: to build and preview your apps, charge the right amount, keep
          the service safe, and email you about your account (confirmation and password-reset links).
          We do not sell your data or use it for advertising.
        </p>
      </section>
      <section>
        <h2>Who else sees it</h2>
        <ul>
          <li>The AI model provider that answers a request sees that request&rsquo;s prompt and code context.</li>
          <li>The payment provider sees what it needs to take a payment.</li>
          <li>The email provider sees your address and the message we send you.</li>
          <li>If you bring your own model key, your requests go to that provider under your own agreement with them.</li>
        </ul>
      </section>
      <section>
        <h2>How long it is kept</h2>
        <ul>
          <li>Your account and projects: until you delete them.</li>
          <li>Sign-in sessions: 30 days, or until you sign out or change your password.</li>
          <li>Email confirmation and password-reset links: removed 7 days after they expire.</li>
          <li>Per-request model usage records: 400 days, for billing questions and disputes.</li>
          <li>
            Payment and credit records: until you delete your account. The payment provider keeps its own
            records of your payments as tax law requires.
          </li>
        </ul>
      </section>
      <section>
        <h2>Your choices</h2>
        <ul>
          <li>Export: Settings &rarr; Account downloads everything tied to your account as JSON.</li>
          <li>
            Delete: Settings &rarr; Account deletes your account, projects, previews and published apps,
            and cancels a paid plan first so you are not charged again.
          </li>
          <li>Correction and questions: write to the address on the billing page.</li>
        </ul>
      </section>
    </LegalPage>
  );
}
