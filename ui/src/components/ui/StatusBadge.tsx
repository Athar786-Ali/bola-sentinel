"use client";

import React from "react";
import { cn } from "@/lib/utils";

export type StatusType = "success" | "failed" | "running" | "skipped" | "warning";

interface StatusBadgeProps {
  status: StatusType;
  className?: string;
  text?: string;
}

const statusConfig: Record<StatusType, { bg: string; text: string; dot: string; label: string }> = {
  success: {
    bg: "bg-green-500/10 border-green-500/20",
    text: "text-green-400",
    dot: "bg-green-500",
    label: "Success",
  },
  failed: {
    bg: "bg-red-500/10 border-red-500/20",
    text: "text-red-400",
    dot: "bg-red-500",
    label: "Failed",
  },
  running: {
    bg: "bg-blue-500/10 border-blue-500/20",
    text: "text-blue-400",
    dot: "bg-blue-500",
    label: "Running",
  },
  skipped: {
    bg: "bg-slate-500/10 border-slate-500/20",
    text: "text-slate-400",
    dot: "bg-slate-500",
    label: "Skipped",
  },
  warning: {
    bg: "bg-orange-500/10 border-orange-500/20",
    text: "text-orange-400",
    dot: "bg-orange-500",
    label: "Warning",
  }
};

export function StatusBadge({ status, className, text }: StatusBadgeProps) {
  const config = statusConfig[status];

  return (
    <span
      className={cn(
        "inline-flex items-center gap-1.5 px-2.5 py-1 rounded-md text-xs font-medium border",
        config.bg,
        config.text,
        className
      )}
    >
      <span className="relative flex h-2 w-2">
        {status === "running" && (
          <span className={cn("animate-ping absolute inline-flex h-full w-full rounded-full opacity-75", config.dot)}></span>
        )}
        <span className={cn("relative inline-flex rounded-full h-2 w-2", config.dot)}></span>
      </span>
      {text || config.label}
    </span>
  );
}
