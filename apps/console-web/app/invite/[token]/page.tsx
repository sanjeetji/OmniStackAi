"use client";

import { useEffect, useState } from "react";
import { useParams, useRouter } from "next/navigation";
import { CheckCircle2, Loader2, Users, XCircle } from "lucide-react";
import { Button } from "@/components/ui/button";
import {
  Card,
  CardContent,
  CardDescription,
  CardFooter,
  CardHeader,
  CardTitle,
} from "@/components/ui/card";
import { setActiveWorkspaceId } from "@/components/workspace-switcher";

export default function InviteAcceptPage() {
  const params = useParams();
  const router = useRouter();
  const token = params?.token as string;

  const [loading, setLoading] = useState(true);
  const [success, setSuccess] = useState(false);
  const [error, setError] = useState<string | null>(null);
  const [result, setResult] = useState<{ workspace_id: string; role: string } | null>(null);

  useEffect(() => {
    if (!token) return;

    const accept = async () => {
      try {
        const res = await fetch(`/api/workspaces/invites/${token}/accept`, {
          method: "POST",
        });
        if (!res.ok) {
          const data = await res.json();
          throw new Error(data.error || "Failed to accept invite");
        }
        const data = await res.json();
        setResult(data);
        setSuccess(true);
        setActiveWorkspaceId(data.workspace_id);
      } catch (err: unknown) {
        setError(err instanceof Error ? err.message : "Invalid or expired invitation");
      } finally {
        setLoading(false);
      }
    };

    void accept();
  }, [token]);

  return (
    <div className="flex min-h-[70vh] items-center justify-center p-4">
      <Card className="w-full max-w-md">
        <CardHeader className="text-center">
          <div className="mx-auto mb-2 flex size-12 items-center justify-center rounded-full bg-primary/10 text-primary">
            <Users className="size-6" />
          </div>
          <CardTitle>Workspace Invitation</CardTitle>
          <CardDescription>
            Joining collaborative workspace on OmniStackAI
          </CardDescription>
        </CardHeader>

        <CardContent className="text-center py-4">
          {loading && (
            <div className="flex flex-col items-center gap-3">
              <Loader2 className="size-8 animate-spin text-primary" />
              <p className="text-sm text-muted-foreground">Accepting your invitation…</p>
            </div>
          )}

          {success && (
            <div className="flex flex-col items-center gap-2">
              <CheckCircle2 className="size-10 text-emerald-500" />
              <h3 className="font-semibold text-foreground">You are in!</h3>
              <p className="text-sm text-muted-foreground">
                You have successfully joined as a <span className="font-medium text-foreground capitalize">{result?.role}</span>.
              </p>
            </div>
          )}

          {error && (
            <div className="flex flex-col items-center gap-2">
              <XCircle className="size-10 text-destructive" />
              <h3 className="font-semibold text-foreground">Invitation Error</h3>
              <p className="text-sm text-destructive">{error}</p>
            </div>
          )}
        </CardContent>

        <CardFooter className="flex justify-center">
          {success ? (
            <Button onClick={() => router.push("/projects")} className="w-full">
              Go to Workspace Projects
            </Button>
          ) : error ? (
            <Button variant="outline" onClick={() => router.push("/projects")} className="w-full">
              Back to Projects
            </Button>
          ) : null}
        </CardFooter>
      </Card>
    </div>
  );
}
