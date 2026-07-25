"use client";

import React, { useState, useEffect, useRef } from "react";
import { Search, Download, Trash2, Maximize2 } from "lucide-react";
import { cn } from "@/lib/utils";

interface LogLine {
  id: string;
  timestamp: string;
  level: "INFO" | "WARN" | "ERROR" | "DEBUG";
  message: string;
}

interface TerminalViewerProps {
  logs: LogLine[];
  onClear?: () => void;
  className?: string;
}

export function TerminalViewer({ logs, onClear, className }: TerminalViewerProps) {
  const [searchTerm, setSearchTerm] = useState("");
  const [autoScroll, setAutoScroll] = useState(true);
  const scrollRef = useRef<HTMLDivElement>(null);

  useEffect(() => {
    if (autoScroll && scrollRef.current) {
      scrollRef.current.scrollTop = scrollRef.current.scrollHeight;
    }
  }, [logs, autoScroll]);

  const filteredLogs = logs.filter(log => 
    log.message.toLowerCase().includes(searchTerm.toLowerCase()) ||
    log.level.toLowerCase().includes(searchTerm.toLowerCase())
  );

  const getLevelColor = (level: string) => {
    switch (level) {
      case "ERROR": return "text-red-400";
      case "WARN": return "text-yellow-400";
      case "INFO": return "text-blue-400";
      case "DEBUG": return "text-slate-500";
      default: return "text-slate-300";
    }
  };

  const handleScroll = (e: React.UIEvent<HTMLDivElement>) => {
    const { scrollTop, scrollHeight, clientHeight } = e.currentTarget;
    const isAtBottom = Math.abs(scrollHeight - clientHeight - scrollTop) < 10;
    setAutoScroll(isAtBottom);
  };

  return (
    <div className={cn("flex flex-col bg-[#0d1117] rounded-xl border border-slate-800 overflow-hidden font-mono shadow-2xl", className)}>
      {/* Terminal Header */}
      <div className="flex items-center justify-between px-4 py-2 bg-slate-900 border-b border-slate-800">
        <div className="flex items-center gap-2">
          <div className="flex gap-1.5">
            <div className="w-3 h-3 rounded-full bg-red-500/80 border border-red-500"></div>
            <div className="w-3 h-3 rounded-full bg-yellow-500/80 border border-yellow-500"></div>
            <div className="w-3 h-3 rounded-full bg-green-500/80 border border-green-500"></div>
          </div>
          <span className="ml-2 text-xs text-slate-500 flex items-center gap-2">
            <Terminal size={12} /> BOLA-Sentinel Logs
          </span>
        </div>
        
        <div className="flex items-center gap-3">
          <div className="relative">
            <Search className="absolute left-2 top-1/2 -translate-y-1/2 w-3 h-3 text-slate-500" />
            <input
              type="text"
              placeholder="Filter..."
              value={searchTerm}
              onChange={(e) => setSearchTerm(e.target.value)}
              className="bg-slate-950 border border-slate-700 rounded text-xs pl-7 pr-2 py-1 text-slate-300 focus:outline-none focus:border-blue-500 w-32 focus:w-48 transition-all"
            />
          </div>
          {onClear && (
            <button onClick={onClear} className="text-slate-500 hover:text-slate-300" title="Clear logs">
              <Trash2 size={14} />
            </button>
          )}
        </div>
      </div>

      {/* Terminal Body */}
      <div 
        ref={scrollRef}
        onScroll={handleScroll}
        className="flex-1 overflow-y-auto p-4 text-[13px] leading-relaxed custom-scrollbar"
        style={{ height: '500px' }}
      >
        {filteredLogs.length === 0 ? (
          <div className="text-slate-500 italic">No logs found.</div>
        ) : (
          filteredLogs.map((log, i) => (
            <div key={log.id} className="flex hover:bg-white/5 py-0.5 rounded px-1 transition-colors group">
              <span className="text-slate-600 w-10 shrink-0 select-none text-right pr-3 border-r border-slate-800 mr-3">
                {i + 1}
              </span>
              <span className="text-slate-500 shrink-0 mr-3">[{log.timestamp}]</span>
              <span className={cn("shrink-0 w-14 font-semibold", getLevelColor(log.level))}>
                {log.level}
              </span>
              <span className="text-slate-300 whitespace-pre-wrap word-break flex-1">
                {searchTerm && log.message.toLowerCase().includes(searchTerm.toLowerCase()) ? (
                  // Highlight search term logic could be added here, simplified for now
                  <span>{log.message}</span>
                ) : (
                  log.message
                )}
              </span>
            </div>
          ))
        )}
      </div>
    </div>
  );
}

// Need to import Terminal icon for header
import { Terminal } from "lucide-react";
