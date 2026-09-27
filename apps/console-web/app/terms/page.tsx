import type { Metadata } from "next";
import Link from "next/link";
import LegalPage from "@/components/legal-page";
import { termsVersion } from "@/lib/legal";

export const metadata: Metadata = {
  title: "Terms of Service",
};

export default function TermsPage() {
  return (
    <LegalPage title="Terms of Service" version={termsVersion()}>
      <section>
        <h2>1. What OmniStackAI is</h2>
        <p>
          OmniStackAI builds, previews and publishes software from descriptions you write. These terms
          apply to your use of the console, the Studio, previews, published apps and the API.
        </p>
      </section>
      <section>
        <h2>2. Your account</h2>
        <ul>
          <li>You must be at least 16 years old and give a real email address you can confirm.</li>
          <li>Keep your password to yourself. You are responsible for what happens under your account.</li>
          <li>Building and publishing are available once your email address is confirmed.</li>
        </ul>
      </section>
      <section>
        <h2>3. What you build is yours</h2>
        <p>
          The descriptions you write and the code generated for you belong to you. You can download or
          export it at any time. We use your content only to run the service for you, as described in the{" "}
          <Link href="/privacy" className="underline underline-offset-4">Privacy Policy</Link>.
        </p>
      </section>
      <section>
        <h2>4. Acceptable use</h2>
        <ul>
          <li>No malware, phishing, spam, or apps that impersonate a real person or organization.</li>
          <li>No content that is illegal where you or your users are, or that infringes others&rsquo; rights.</li>
          <li>No attempts to break out of previews, reach other users&rsquo; data, or overload the service.</li>
          <li>You are responsible for the apps you publish and for how their users&rsquo; data is handled.</li>
        </ul>
        <p>We may suspend a preview, a published app, or an account that breaks these rules.</p>
      </section>
      <section>
        <h2>5. Credits, plans and payment</h2>
        <p>
          Cloud model calls spend credits. Each build shows an estimate first and never charges beyond the
          budget you see; answers the platform discards are not billed. Paid plans renew until cancelled.
          Prices and plan limits are shown on the billing page before you pay.
        </p>
      </section>
      <section>
        <h2>6. Generated code comes with no warranty</h2>
        <p>
          AI-generated software can contain mistakes. Review it before you rely on it, especially for
          security, payments, or personal data. The service is provided &ldquo;as is&rdquo; during the beta.
        </p>
      </section>
      <section>
        <h2>7. Ending your account</h2>
        <p>
          You can export your data and delete your account from Settings at any time. Deleting removes
          your projects, previews and published apps, and cancels a paid plan.
        </p>
      </section>
      <section>
        <h2>8. Changes</h2>
        <p>
          When these terms change in a way that matters, we will tell you by email and ask you to accept
          the new version.
        </p>
      </section>
    </LegalPage>
  );
}
