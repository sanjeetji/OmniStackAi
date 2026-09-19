import type { Metadata } from "next";
import Link from "next/link";
import { redirect } from "next/navigation";
import { getCurrentUser } from "@/lib/session";
import AuthScreen from "@/components/auth-screen";
import RegisterForm from "./register-form";

export const metadata: Metadata = {
  title: "Create account",
};

export default async function RegisterPage() {
  let user = null;
  try {
    user = await getCurrentUser();
  } catch {
    user = null;
  }
  if (user) {
    redirect("/");
  }

  return (
    <AuthScreen
      title="Create your account"
      description="The free plan starts with a credit grant, and your own local model always stays free to run. No card required."
      footer={
        <>
          Already have an account?{" "}
          <Link
            href="/login"
            className="font-medium text-foreground underline underline-offset-4 transition-colors hover:text-brand"
          >
            Sign in
          </Link>
          .
        </>
      }
    >
      <RegisterForm />
    </AuthScreen>
  );
}
