import { NextRequest, NextResponse } from "next/server";
import { controlPlaneUrl } from "@/lib/control-plane";

// PC-011: Stripe and Razorpay call this public address. The raw body and the signature header
// go through unchanged — the control plane verifies the signature over exactly these bytes.
const SIGNATURE_HEADER: Record<string, string> = { stripe: "stripe-signature", razorpay: "x-razorpay-signature" };

export async function POST(request: NextRequest, { params }: { params: Promise<{ provider: string }> }) {
  const { provider } = await params;
  const header = SIGNATURE_HEADER[provider];
  if (!header) return NextResponse.json({ error: "unknown provider" }, { status: 404 });
  const body = await request.arrayBuffer();
  try {
    const upstream = await fetch(`${controlPlaneUrl()}/billing/webhooks/${provider}`, {
      method: "POST",
      headers: { "Content-Type": "application/json", [header]: request.headers.get(header) ?? "" },
      body,
      cache: "no-store",
    });
    return new NextResponse(await upstream.text(), { status: upstream.status,
      headers: { "Content-Type": "application/json" } });
  } catch {
    return NextResponse.json({ error: "unavailable" }, { status: 502 });
  }
}
