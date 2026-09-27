import type { Metadata } from "next";
import Link from "next/link";
import AuthScreen from "@/components/auth-screen";
import { VerifyEmail } from "@/components/account-forms";

export const metadata: Metadata = {
  title: "Confirm your email",
};

export default async function VerifyEmailPage({
  searchParams,
}: Readonly<{ searchParams: Promise<{ token?: string }> }>) {
  const { token } = await searchParams;
  return (
    <AuthScreen
      title="Confirm your email"
      description="Building and publishing start once your address is confirmed."
      footer={
        <Link href="/" className="font-medium text-foreground underline underline-offset-4 hover:text-brand">
          Back to OmniStackAI
        </Link>
      }
    >
      <VerifyEmail token={typeof token === "string" ? token : ""} />
    </AuthScreen>
  );
}
