"use client";

import React from "react";
import { cn } from "@/lib/utils";

interface GlassPanelProps {
  children: React.ReactNode;
  className?: string;
  title?: string;
  subtitle?: string;
  headerRight?: React.ReactNode;
}

export function GlassPanel({ children, className, title, subtitle, headerRight }: GlassPanelProps) {
  return (
    <div className={cn("glass-card rounded-xl border border-slate-800 overflow-hidden flex flex-col", className)}>
      {(title || subtitle || headerRight) && (
        <div className="px-6 py-4 border-b border-slate-800/60 flex justify-between items-center bg-slate-900/30">
          <div>
            {title && <h3 className="text-lg font-medium text-slate-100">{title}</h3>}
            {subtitle && <p className="text-sm text-slate-400 mt-1">{subtitle}</p>}
          </div>
          {headerRight && <div>{headerRight}</div>}
        </div>
      )}
      <div className="p-6 flex-1">
        {children}
      </div>
    </div>
  );
}
