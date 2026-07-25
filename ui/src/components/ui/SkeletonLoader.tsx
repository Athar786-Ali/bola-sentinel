"use client";

import React from "react";
import { cn } from "@/lib/utils";

interface SkeletonLoaderProps {
  variant: "card" | "table" | "text" | "chart";
  count?: number;
  className?: string;
}

export function SkeletonLoader({ variant, count = 1, className }: SkeletonLoaderProps) {
  const renderSkeleton = (key: number) => {
    switch (variant) {
      case "card":
        return (
          <div key={key} className={cn("glass-card p-6 rounded-xl border border-slate-800 animate-pulse", className)}>
            <div className="flex justify-between items-start mb-6">
              <div className="space-y-2">
                <div className="h-4 w-24 bg-slate-800 rounded"></div>
                <div className="h-8 w-16 bg-slate-800 rounded"></div>
              </div>
              <div className="h-10 w-10 bg-slate-800 rounded-lg"></div>
            </div>
            <div className="h-4 w-32 bg-slate-800 rounded"></div>
          </div>
        );
      case "table":
        return (
          <div key={key} className={cn("space-y-4", className)}>
            <div className="h-10 w-full bg-slate-800/50 rounded-lg animate-pulse"></div>
            {[...Array(5)].map((_, i) => (
              <div key={i} className="h-16 w-full glass rounded-lg animate-pulse"></div>
            ))}
          </div>
        );
      case "text":
        return (
          <div key={key} className={cn("space-y-3", className)}>
            <div className="h-4 w-3/4 bg-slate-800 rounded animate-pulse"></div>
            <div className="h-4 w-1/2 bg-slate-800 rounded animate-pulse"></div>
            <div className="h-4 w-5/6 bg-slate-800 rounded animate-pulse"></div>
          </div>
        );
      case "chart":
        return (
          <div key={key} className={cn("glass-card p-6 rounded-xl border border-slate-800 h-80 flex flex-col justify-end gap-2 animate-pulse", className)}>
             <div className="flex items-end justify-between h-full gap-2 px-4">
                {[...Array(7)].map((_, i) => (
                  <div key={i} className="w-full bg-slate-800/80 rounded-t" style={{ height: `${Math.random() * 60 + 20}%` }}></div>
                ))}
             </div>
          </div>
        );
      default:
        return null;
    }
  };

  return (
    <>
      {[...Array(count)].map((_, i) => renderSkeleton(i))}
    </>
  );
}
