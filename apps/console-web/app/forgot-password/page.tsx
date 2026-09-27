import type { Metadata } from "next";
import Link from "next/link";
import AuthScreen from "@/components/auth-screen";
import { ForgotPasswordForm } from "@/components/account-forms";

export const metadata: Metadata = {
  title: "Forgot password",
};

export default function ForgotPasswordPage() {
  return (
    <AuthScreen
      title="Forgot your password?"
      description="Enter the address you signed up with. We will email a link to choose a new password; it works once and for one hour."
      footer={
        <>
          Remembered it?{" "}
          <Link href="/login" className="font-medium text-foreground underline underline-offset-4 hover:text-brand">
            Sign in
          </Link>
          .
        </>
      }
    >
      <ForgotPasswordForm />
    </AuthScreen>
  );
}
