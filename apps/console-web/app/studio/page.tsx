import { getCurrentUser } from "@/lib/session";
import StudioChat from "./studio-chat";

export const metadata = {
  title: "Studio",
};

export default async function StudioPage() {
  // The auth gate lives in this route's layout.tsx (it redirects to /login before this ever
  // renders) - the fallback here is purely to satisfy TypeScript's null check, never exercised.
  const user = await getCurrentUser();
  return <StudioChat initialCreditBalance={user?.credit_balance ?? 0} />;
}
