'use client';

import { useState } from 'react';
import { motion } from 'framer-motion';
import { FileText, Download, ChevronRight } from 'lucide-react';
import { cn } from '@/lib/utils';
// Note: In a real implementation, you'd install and import react-markdown and remark-gfm

const MOCK_REPORTS = [
  { id: '1', name: 'evaluation_juice_shop.md', date: '2026-07-25 14:30' },
  { id: '2', name: 'evaluation_vuln-nodejs-app.md', date: '2026-07-24 09:15' },
];

const MOCK_MD = `
# BOLA Detection Report: juice_shop

## Summary
- **Total Routes Analyzed**: 45
- **BOLA Vulnerabilities Confirmed**: 5
- **False Positives (Filtered by Dynamic Verification)**: 7

## Detailed Findings

| Endpoint | Method | LLM Status | Dynamic Status | Final |
|---|---|---|---|---|
| \`/api/users/:id\` | GET | FLAGGED | CONFIRMED | **BOLA** |
| \`/api/orders/:id\` | GET | FLAGGED | REJECTED | SAFE |

### Explanation for \`/api/users/:id\`
The LLM correctly identified that the endpoint takes a user ID parameter but lacks explicit authorization checks before returning the user profile. Dynamic verification successfully confirmed that user A can access user B's profile.
`;

export default function ReportsPage() {
  const [activeReport, setActiveReport] = useState(MOCK_REPORTS[0].id);

  return (
    <motion.div 
      initial={{ opacity: 0, y: 20 }}
      animate={{ opacity: 1, y: 0 }}
      className="p-6 h-[calc(100vh-4rem)] flex flex-col gap-6"
    >
      <div className="flex items-center justify-between shrink-0">
        <h1 className="text-2xl font-bold text-slate-100">Reports</h1>
      </div>

      <div className="flex flex-col md:flex-row gap-6 flex-1 min-h-0">
        <div className="w-full md:w-64 shrink-0 flex flex-col gap-2">
          {MOCK_REPORTS.map(report => (
            <button
              key={report.id}
              onClick={() => setActiveReport(report.id)}
              className={cn(
                "flex items-center gap-3 p-3 rounded-lg text-left transition-all border",
                activeReport === report.id
                  ? "bg-slate-800 border-slate-700 text-slate-200 shadow-sm"
                  : "bg-slate-900/50 border-transparent text-slate-400 hover:bg-slate-800/50 hover:text-slate-300"
              )}
            >
              <FileText className="w-5 h-5" />
              <div className="flex-1 min-w-0">
                <p className="text-sm font-medium truncate">{report.name}</p>
                <p className="text-xs opacity-60">{report.date}</p>
              </div>
              {activeReport === report.id && <ChevronRight className="w-4 h-4" />}
            </button>
          ))}
        </div>

        <div className="flex-1 bg-slate-900/50 border border-slate-800 rounded-xl backdrop-blur-md flex flex-col min-w-0">
          <div className="p-4 border-b border-slate-800 flex items-center justify-between bg-slate-950/50">
            <h2 className="font-medium text-slate-200 flex items-center gap-2">
              <FileText className="w-4 h-4 text-slate-400" />
              {MOCK_REPORTS.find(r => r.id === activeReport)?.name}
            </h2>
            <button className="p-2 hover:bg-slate-800 rounded-md text-slate-400 hover:text-slate-200 transition-colors">
              <Download className="w-4 h-4" />
            </button>
          </div>
          <div className="p-6 overflow-y-auto flex-1 prose prose-invert prose-slate max-w-none">
            {/* Replace with actual ReactMarkdown implementation */}
            <div dangerouslySetInnerHTML={{ __html: `
              <h1 class="text-2xl font-bold text-white mb-4">BOLA Detection Report: juice_shop</h1>
              <h2 class="text-xl font-semibold text-slate-200 mt-6 mb-3">Summary</h2>
              <ul class="list-disc pl-5 text-slate-300 space-y-1 mb-6">
                <li><strong>Total Routes Analyzed</strong>: 45</li>
                <li><strong>BOLA Vulnerabilities Confirmed</strong>: 5</li>
                <li><strong>False Positives (Filtered by Dynamic Verification)</strong>: 7</li>
              </ul>
              <h2 class="text-xl font-semibold text-slate-200 mt-6 mb-3">Detailed Findings</h2>
              <div class="overflow-x-auto mb-6">
                <table class="w-full border-collapse border border-slate-700 text-sm">
                  <thead class="bg-slate-800">
                    <tr>
                      <th class="border border-slate-700 px-4 py-2 text-left">Endpoint</th>
                      <th class="border border-slate-700 px-4 py-2 text-left">Method</th>
                      <th class="border border-slate-700 px-4 py-2 text-left">LLM Status</th>
                      <th class="border border-slate-700 px-4 py-2 text-left">Dynamic Status</th>
                      <th class="border border-slate-700 px-4 py-2 text-left">Final</th>
                    </tr>
                  </thead>
                  <tbody class="text-slate-300">
                    <tr class="bg-slate-900/50">
                      <td class="border border-slate-700 px-4 py-2 font-mono text-blue-300">/api/users/:id</td>
                      <td class="border border-slate-700 px-4 py-2">GET</td>
                      <td class="border border-slate-700 px-4 py-2 text-amber-400">FLAGGED</td>
                      <td class="border border-slate-700 px-4 py-2 text-red-400">CONFIRMED</td>
                      <td class="border border-slate-700 px-4 py-2 font-bold text-red-400">BOLA</td>
                    </tr>
                    <tr class="bg-slate-900/50">
                      <td class="border border-slate-700 px-4 py-2 font-mono text-blue-300">/api/orders/:id</td>
                      <td class="border border-slate-700 px-4 py-2">GET</td>
                      <td class="border border-slate-700 px-4 py-2 text-amber-400">FLAGGED</td>
                      <td class="border border-slate-700 px-4 py-2 text-emerald-400">REJECTED</td>
                      <td class="border border-slate-700 px-4 py-2 text-emerald-400">SAFE</td>
                    </tr>
                  </tbody>
                </table>
              </div>
              <h3 class="text-lg font-semibold text-slate-200 mt-6 mb-2">Explanation for <code class="bg-slate-800 px-1 py-0.5 rounded text-sm text-blue-300">/api/users/:id</code></h3>
              <p class="text-slate-300">The LLM correctly identified that the endpoint takes a user ID parameter but lacks explicit authorization checks before returning the user profile. Dynamic verification successfully confirmed that user A can access user B's profile.</p>
            `}} />
          </div>
        </div>
      </div>
    </motion.div>
  );
}
