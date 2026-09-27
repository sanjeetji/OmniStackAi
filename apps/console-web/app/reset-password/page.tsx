import type { Metadata } from "next";
import Link from "next/link";
import AuthScreen from "@/components/auth-screen";
import { ResetPasswordForm } from "@/components/account-forms";

export const metadata: Metadata = {
  title: "Choose a new password",
};

export default async function ResetPasswordPage({
  searchParams,
}: Readonly<{ searchParams: Promise<{ token?: string }> }>) {
  const { token } = await searchParams;
  return (
    <AuthScreen
      title="Choose a new password"
      description="Every device signed in to your account is signed out when the password changes."
      footer={
        <>
          Link expired?{" "}
          <Link href="/forgot-password" className="font-medium text-foreground underline underline-offset-4 hover:text-brand">
            Ask for a new one
          </Link>
          .
        </>
      }
    >
      <ResetPasswordForm token={typeof token === "string" ? token : ""} />
    </AuthScreen>
  );
}
