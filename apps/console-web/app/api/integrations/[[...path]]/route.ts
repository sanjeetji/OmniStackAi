import { NextRequest } from "next/server";
import { passThrough } from "@/lib/passthrough";

// PC-013: the verified integrations catalog.
type Params = { params: Promise<{ path?: string[] }> };

export async function GET(request: NextRequest, { params }: Params) {
  return passThrough(request, "integrations", (await params).path ?? []);
}
