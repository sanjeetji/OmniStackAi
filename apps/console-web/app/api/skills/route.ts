import { NextRequest, NextResponse } from "next/server";
import {
  ControlPlaneError,
  createSkill,
  listSkills,
  type CreateSkillParams,
} from "@/lib/control-plane";
import { getSessionToken } from "@/lib/session";

export async function GET() {
  const token = await getSessionToken();
  if (!token) {
    return NextResponse.json({ error: "not signed in" }, { status: 401 });
  }

  try {
    const skills = await listSkills(token);
    return NextResponse.json({ skills }, { status: 200 });
  } catch (error) {
    if (error instanceof ControlPlaneError) {
      return NextResponse.json({ error: error.message }, { status: error.status });
    }
    return NextResponse.json({ error: "could not reach the control-plane" }, { status: 502 });
  }
}

export async function POST(request: NextRequest) {
  const token = await getSessionToken();
  if (!token) {
    return NextResponse.json({ error: "not signed in" }, { status: 401 });
  }

  let body: CreateSkillParams;
  try {
    body = (await request.json()) as CreateSkillParams;
  } catch {
    return NextResponse.json({ error: "invalid request body" }, { status: 400 });
  }

  try {
    const skill = await createSkill(token, body);
    return NextResponse.json(skill, { status: 201 });
  } catch (error) {
    if (error instanceof ControlPlaneError) {
      return NextResponse.json({ error: error.message }, { status: error.status });
    }
    return NextResponse.json({ error: "could not reach the control-plane" }, { status: 502 });
  }
}
