import { NextRequest } from "next/server";
import { passThrough } from "@/lib/passthrough";

// PC-011: the billing API, carried under the caller's session (the control plane checks access).
type Params = { params: Promise<{ path: string[] }> };

async function handle(request: NextRequest, { params }: Params) {
  return passThrough(request, "billing", (await params).path);
}

export const GET = handle;
export const POST = handle;
export const PUT = handle;
