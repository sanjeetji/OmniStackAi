"use client";

import { useRouter } from "next/navigation";
import { useEffect, useState } from "react";
import { LogOut } from "lucide-react";
import { ApiError, type User } from "@ridenow/shared";
import { AppShell } from "@/components/app-shell";
import { Alert, Avatar, Button, Card, Input, PageHeader } from "@/components/ui";
import { api } from "@/lib/api";
import { useSession } from "@/lib/session";

export default function AccountPage() {
  const { user, setUser, signOut } = useSession();
  const router = useRouter();
  const [profile, setProfile] = useState({ full_name: "", phone: "" });
  const [password, setPassword] = useState("");
  const [status, setStatus] = useState<{ tone: "success" | "danger"; text: string } | null>(null);
  const [busy, setBusy] = useState<"profile" | "password" | null>(null);

  useEffect(() => {
    if (user) setProfile({ full_name: user.full_name, phone: user.phone ?? "" });
  }, [user]);

  async function save(kind: "profile" | "password", body: Record<string, string>) {
    setBusy(kind);
    setStatus(null);
    try {
      const updated = await api.patch<User>("/auth/me", body);
      setUser(updated);
      setStatus({ tone: "success", text: kind === "password" ? "Password changed." : "Profile saved." });
      setPassword("");
    } catch (err) {
      setStatus({ tone: "danger", text: err instanceof ApiError ? err.message : "Couldn't save." });
    } finally {
      setBusy(null);
    }
  }

  return (
    <AppShell>
      <PageHeader title="Account" />
      {user ? (
        <div className="grid gap-5 md:grid-cols-[280px_1fr]">
          <Card className="grid justify-items-center gap-2 p-6 text-center">
            <Avatar name={user.full_name} color={user.avatar_color} size={84} />
            <p className="mt-2 text-lg font-bold">{user.full_name}</p>
            <p className="text-sm text-muted">{user.email ?? user.phone}</p>
            <Button variant="outline" className="mt-4 text-danger" onClick={async () => { await signOut(); router.replace("/login"); }}>
              <LogOut className="size-4" aria-hidden="true" /> Sign out
            </Button>
          </Card>
          <div className="grid gap-5">
            {status ? <Alert tone={status.tone}>{status.text}</Alert> : null}
            <Card className="p-6">
              <form className="grid gap-4" onSubmit={(e) => { e.preventDefault(); void save("profile", { full_name: profile.full_name, ...(profile.phone ? { phone: profile.phone } : {}) }); }}>
                <p className="font-bold">Profile</p>
                <Input label="Full name" value={profile.full_name} onChange={(e) => setProfile({ ...profile, full_name: e.target.value })} autoComplete="name" />
                <Input label="Mobile number" type="tel" value={profile.phone} onChange={(e) => setProfile({ ...profile, phone: e.target.value })} autoComplete="tel" hint="Drivers call this number if they can't find you." />
                <Input label="Email" value={user.email ?? ""} disabled hint="Contact support to change your email." />
                <Button type="submit" busy={busy === "profile"} className="justify-self-start">Save profile</Button>
              </form>
            </Card>
            <Card className="p-6">
              <form className="grid gap-4" onSubmit={(e) => { e.preventDefault(); void save("password", { password }); }}>
                <p className="font-bold">Password</p>
                <Input label="New password" type="password" value={password} onChange={(e) => setPassword(e.target.value)} autoComplete="new-password" hint="At least 8 characters, with letters and numbers." />
                <Button type="submit" variant="dark" busy={busy === "password"} disabled={password.length < 8} className="justify-self-start">Change password</Button>
              </form>
            </Card>
          </div>
        </div>
      ) : null}
    </AppShell>
  );
}
