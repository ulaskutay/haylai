import { NextResponse } from "next/server";

export async function GET(
  request: Request,
  context: { params: Promise<{ id: string }> },
) {
  const { id } = await context.params;
  const url = new URL(request.url);
  url.pathname = `/api/songs/${id}/stream`;
  url.searchParams.set("download", "1");
  return NextResponse.redirect(url);
}
