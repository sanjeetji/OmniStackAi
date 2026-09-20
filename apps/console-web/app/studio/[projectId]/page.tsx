import { getCurrentUser } from "@/lib/session";
import StudioChat from "../studio-chat";

export const metadata = {
  title: "Studio",
};

export default async function ProjectStudioPage({
  params,
}: {
  params: Promise<{ projectId: string }>;
}) {
  const { projectId } = await params;
  const user = await getCurrentUser();
  return (
    <StudioChat
      initialCreditBalance={user?.credit_balance ?? 0}
      initialProjectId={projectId}
    />
  );
}
