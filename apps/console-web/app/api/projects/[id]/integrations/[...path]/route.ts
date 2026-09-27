import { NextRequest } from "next/server";
import { passThrough } from "@/lib/passthrough";

// PC-013: a project's integration health (last answers, and "test now").
type Params = { params: Promise<{ id: string; path: string[] }> };

async function handle(request: NextRequest, { params }: Params) {
  const { id, path } = await params;
  return passThrough(request, `projects/${encodeURIComponent(id)}/integrations`, path);
}

export const GET = handle;
export const POST = handle;
