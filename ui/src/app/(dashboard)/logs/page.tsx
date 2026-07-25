'use client';

import { useState } from 'react';
import { motion } from 'framer-motion';
import { Search, FileTerminal, ArrowDownToLine, RefreshCw } from 'lucide-react';
import { cn } from '@/lib/utils';

const MOCK_LOGS = `
[2026-07-25 14:30:00] [INFO] Starting BOLA-Sentinel benchmark pipeline...
[2026-07-25 14:30:01] [INFO] Target application: juice_shop
[2026-07-25 14:30:02] [INFO] Running Static Analysis (Semgrep)...
[2026-07-25 14:30:15] [SUCCESS] Static Analysis complete. Found 45 routes, 23 with parameters.
[2026-07-25 14:30:16] [INFO] Running LLM Classification...
[2026-07-25 14:31:40] [WARN] LLM rate limit approached, backing off for 2s...
[2026-07-25 14:32:10] [SUCCESS] LLM Classification complete. Flagged 12 potential vulnerabilities.
[2026-07-25 14:32:11] [INFO] Running Dynamic Verification (Playwright)...
[2026-07-25 14:33:45] [ERROR] Dynamic test failed for route /api/admin/config - Timeout exceeded.
[2026-07-25 14:34:00] [SUCCESS] Dynamic Verification complete. Confirmed 5 BOLA vulnerabilities.
[2026-07-25 14:34:01] [INFO] Generating evaluation reports...
[2026-07-25 14:34:05] [SUCCESS] Pipeline finished successfully.
`.trim().split('\n');

export default function LogsPage() {
  const [filter, setFilter] = useState('');
  const [autoScroll, setAutoScroll] = useState(true);
  const [selectedFile, setSelectedFile] = useState('pipeline.log');

  const filteredLogs = MOCK_LOGS.filter(log => 
    log.toLowerCase().includes(filter.toLowerCase())
  );

  const getLogColor = (line: string) => {
    if (line.includes('[ERROR]')) return 'text-red-400';
    if (line.includes('[WARN]')) return 'text-yellow-400';
    if (line.includes('[SUCCESS]')) return 'text-emerald-400';
    if (line.includes('[INFO]')) return 'text-blue-400';
    return 'text-slate-300';
  };

  return (
    <motion.div 
      initial={{ opacity: 0, y: 20 }}
      animate={{ opacity: 1, y: 0 }}
      className="p-6 h-[calc(100vh-4rem)] flex flex-col gap-6"
    >
      <div className="flex flex-col sm:flex-row sm:items-center justify-between gap-4 shrink-0">
        <h1 className="text-2xl font-bold text-slate-100">Log Viewer</h1>
        
        <div className="flex items-center gap-3">
          <select 
            value={selectedFile}
            onChange={(e) => setSelectedFile(e.target.value)}
            className="bg-slate-900 border border-slate-800 rounded-lg px-3 py-2 text-sm text-slate-200 focus:outline-none focus:ring-2 focus:ring-blue-500/50"
          >
            <option value="pipeline.log">pipeline.log</option>
            <option value="error.log">error.log</option>
            <option value="llm.log">llm.log</option>
          </select>
          <button className="p-2 bg-slate-900 border border-slate-800 rounded-lg text-slate-400 hover:text-slate-200 hover:bg-slate-800 transition-colors">
            <RefreshCw className="w-4 h-4" />
          </button>
        </div>
      </div>

      <div className="flex-1 bg-[#0c0c0c] border border-slate-800 rounded-xl flex flex-col min-h-0 shadow-xl overflow-hidden">
        <div className="p-3 border-b border-slate-800 bg-slate-900/50 flex flex-wrap items-center justify-between gap-4">
          <div className="relative flex-1 max-w-md">
            <Search className="absolute left-3 top-1/2 -translate-y-1/2 w-4 h-4 text-slate-500" />
            <input
              type="text"
              placeholder="Filter logs..."
              value={filter}
              onChange={(e) => setFilter(e.target.value)}
              className="w-full pl-9 pr-4 py-1.5 bg-slate-950 border border-slate-800 rounded text-sm text-slate-200 focus:outline-none focus:ring-1 focus:ring-blue-500/50"
            />
          </div>
          
          <div className="flex items-center gap-4">
            <label className="flex items-center gap-2 text-sm text-slate-400 cursor-pointer">
              <input
                type="checkbox"
                checked={autoScroll}
                onChange={(e) => setAutoScroll(e.target.checked)}
                className="rounded border-slate-800 bg-slate-950 text-blue-500 focus:ring-blue-500/50"
              />
              Auto-scroll
            </label>
            <button className="flex items-center gap-1.5 text-sm text-slate-400 hover:text-slate-200 transition-colors">
              <ArrowDownToLine className="w-4 h-4" />
              Download
            </button>
          </div>
        </div>

        <div className="flex-1 overflow-y-auto p-4 font-mono text-sm leading-relaxed">
          {filteredLogs.length === 0 ? (
            <div className="text-slate-500 text-center mt-10">No logs matching filter.</div>
          ) : (
            filteredLogs.map((line, i) => (
              <div key={i} className="flex gap-4 hover:bg-white/[0.02] px-2 py-0.5 rounded">
                <span className="text-slate-600 select-none w-8 text-right shrink-0">{i + 1}</span>
                <span className={cn("break-all whitespace-pre-wrap", getLogColor(line))}>
                  {line}
                </span>
              </div>
            ))
          )}
        </div>
      </div>
    </motion.div>
  );
}
