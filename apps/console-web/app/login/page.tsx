import type { Metadata } from "next";
import Link from "next/link";
import { redirect } from "next/navigation";
import { getCurrentUser } from "@/lib/session";
import AuthScreen from "@/components/auth-screen";
import LoginForm from "./login-form";

export const metadata: Metadata = {
  title: "Sign in",
};

export default async function LoginPage() {
  // Someone who is already signed in has no reason to see this page. If the control-plane is
  // unreachable, treat that as "not signed in" so the sign-in page itself still renders.
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
      title="Sign in"
      description="Welcome back. Pick up where you left off."
      footer={
        <>
          No account yet?{" "}
          <Link
            href="/register"
            className="font-medium text-foreground underline underline-offset-4 transition-colors hover:text-brand"
          >
            Create one
          </Link>
          .
        </>
      }
    >
      <LoginForm />
    </AuthScreen>
  );
}
