import { ControlPlaneError, getProjectTemplate, getTemplate } from "@/lib/control-plane";
import { getCurrentUser, getSessionToken } from "@/lib/session";
import StudioChat from "../studio-chat";

export const metadata = {
  title: "Studio",
};

/** Which template this project came from, if any (R-523). A lookup failure only hides the notice. */
async function templateOrigin(projectId: string): Promise<{ name: string; version: string } | undefined> {
  const token = await getSessionToken();
  if (!token) return undefined;
  try {
    const provenance = await getProjectTemplate(token, projectId);
    const name = await getTemplate(provenance.slug)
      .then((template) => template.name)
      .catch(() => provenance.slug);
    return { name, version: provenance.version };
  } catch (error) {
    if (!(error instanceof ControlPlaneError)) {
      console.error("template provenance lookup failed", error);
    }
    return undefined;
  }
}

export default async function ProjectStudioPage({
  params,
}: {
  params: Promise<{ projectId: string }>;
}) {
  const { projectId } = await params;
  const [user, startedFromTemplate] = await Promise.all([getCurrentUser(), templateOrigin(projectId)]);
  return (
    <StudioChat
      initialCreditBalance={user?.credit_balance ?? 0}
      initialProjectId={projectId}
      startedFromTemplate={startedFromTemplate}
    />
  );
}
