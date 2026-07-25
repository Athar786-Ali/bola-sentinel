import { NextResponse } from "next/server";
import fs from "fs";
import path from "path";

const ROOT = path.join(process.cwd(), "..");

export async function GET() {
  try {
    const filePath = path.join(ROOT, "results", "benchmark_summary.json");
    const raw = fs.readFileSync(filePath, "utf-8");
    return NextResponse.json(JSON.parse(raw));
  } catch {
    return NextResponse.json(
      { error: "benchmark_summary.json not found" },
      { status: 404 }
    );
  }
}
