import { clsx, type ClassValue } from "clsx";
import { twMerge } from "tailwind-merge";

export function cn(...inputs: ClassValue[]) {
  return twMerge(clsx(inputs));
}

export function formatPercent(value: number): string {
  return `${(value * 100).toFixed(1)}%`;
}

export function formatDecimal(value: number, digits = 3): string {
  return value.toFixed(digits);
}

export function formatDuration(seconds: number): string {
  if (seconds < 60) return `${seconds.toFixed(1)}s`;
  const mins = Math.floor(seconds / 60);
  const secs = seconds % 60;
  return `${mins}m ${secs.toFixed(0)}s`;
}

export function getStageLabel(stage: string): string {
  const labels: Record<string, string> = {
    stage_1_static_only: "Static Analysis",
    stage_2_static_plus_llm: "Static + LLM",
    stage_3_final_system: "Full Pipeline",
  };
  return labels[stage] || stage;
}

export function getRiskColor(risk: string): string {
  const colors: Record<string, string> = {
    critical: "text-red-400",
    high: "text-orange-400",
    medium: "text-yellow-400",
    low: "text-green-400",
    info: "text-blue-400",
  };
  return colors[risk] || "text-slate-400";
}
