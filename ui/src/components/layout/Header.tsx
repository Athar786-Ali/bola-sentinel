"use client";

import React from "react";
import { usePathname } from "next/navigation";
import { ChevronRight } from "lucide-react";

export function Header() {
  const pathname = usePathname();
  const pathSegments = pathname.split('/').filter(Boolean);
  
  const pageTitle = pathSegments.length > 0 
    ? pathSegments[0].charAt(0).toUpperCase() + pathSegments[0].slice(1)
    : "Dashboard";

  return (
    <header className="h-16 glass border-b border-slate-800 sticky top-0 z-30 flex items-center justify-between px-6">
      <div className="flex items-center gap-4">
        <h1 className="text-xl font-semibold text-white">{pageTitle}</h1>
        
        <div className="flex items-center text-sm text-slate-400 space-x-2">
          <span>Home</span>
          {pathSegments.map((segment, index) => (
            <React.Fragment key={segment}>
              <ChevronRight size={14} className="text-slate-600" />
              <span className={index === pathSegments.length - 1 ? "text-slate-300" : ""}>
                {segment.charAt(0).toUpperCase() + segment.slice(1)}
              </span>
            </React.Fragment>
          ))}
        </div>
      </div>

      <div className="flex items-center gap-3 bg-slate-900/50 px-3 py-1.5 rounded-full border border-slate-800">
        <div className="relative flex h-2.5 w-2.5">
          <span className="animate-ping absolute inline-flex h-full w-full rounded-full bg-green-400 opacity-75"></span>
          <span className="relative inline-flex rounded-full h-2.5 w-2.5 bg-green-500"></span>
        </div>
        <span className="text-xs font-medium text-slate-300">System Healthy</span>
      </div>
    </header>
  );
}
