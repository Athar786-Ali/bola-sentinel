'use client';

import { useState, useEffect } from 'react';
import { motion } from 'framer-motion';
import { FileText, Download, ChevronRight, Loader2, AlertCircle } from 'lucide-react';
import { cn } from '@/lib/utils';
import ReactMarkdown from 'react-markdown';
import remarkGfm from 'remark-gfm';

interface Report {
  name: string;
  path?: string;
  date?: string;
}

export default function ReportsPage() {
  const [reports, setReports] = useState<Report[]>([]);
  const [activeReport, setActiveReport] = useState<string>('');
  const [content, setContent] = useState<string>('');
  const [loadingList, setLoadingList] = useState(true);
  const [loadingContent, setLoadingContent] = useState(false);

  useEffect(() => {
    const fetchReports = async () => {
      try {
        const res = await fetch('/api/reports');
        if (!res.ok) throw new Error('Failed to fetch reports');
        const data = await res.json();
        const fetchedReports = data.reports || [];
        setReports(fetchedReports);
        
        if (fetchedReports.length > 0) {
          setActiveReport(fetchedReports[0].name);
        }
      } catch (error) {
        console.error(error);
      } finally {
        setLoadingList(false);
      }
    };
    
    fetchReports();
  }, []);

  useEffect(() => {
    if (!activeReport) return;
    
    const fetchReportContent = async () => {
      setLoadingContent(true);
      try {
        const res = await fetch(`/api/reports/${encodeURIComponent(activeReport)}`);
        if (!res.ok) throw new Error('Failed to fetch report content');
        const data = await res.json();
        setContent(data.content || '');
      } catch (error) {
        console.error(error);
        setContent('# Error\nFailed to load report content.');
      } finally {
        setLoadingContent(false);
      }
    };
    
    fetchReportContent();
  }, [activeReport]);

  const handleDownload = () => {
    if (!content || !activeReport) return;
    const blob = new Blob([content], { type: 'text/markdown' });
    const url = URL.createObjectURL(blob);
    const a = document.createElement('a');
    a.href = url;
    a.download = activeReport;
    document.body.appendChild(a);
    a.click();
    document.body.removeChild(a);
    URL.revokeObjectURL(url);
  };

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
        <div className="w-full md:w-64 shrink-0 flex flex-col gap-2 overflow-y-auto pr-2">
          {loadingList ? (
            <div className="flex items-center justify-center py-8 text-slate-400">
              <Loader2 className="w-6 h-6 animate-spin" />
            </div>
          ) : reports.length === 0 ? (
            <div className="text-slate-500 text-sm p-4 text-center border border-dashed border-slate-700 rounded-lg">
              No reports found.
            </div>
          ) : (
            reports.map((report, idx) => (
              <motion.button
                key={report.name}
                initial={{ opacity: 0, x: -10 }}
                animate={{ opacity: 1, x: 0 }}
                transition={{ delay: idx * 0.05 }}
                onClick={() => setActiveReport(report.name)}
                className={cn(
                  "flex items-center gap-3 p-3 rounded-lg text-left transition-all border",
                  activeReport === report.name
                    ? "bg-slate-800 border-slate-700 text-slate-200 shadow-sm"
                    : "bg-slate-900/50 border-transparent text-slate-400 hover:bg-slate-800/50 hover:text-slate-300"
                )}
              >
                <FileText className="w-5 h-5 shrink-0" />
                <div className="flex-1 min-w-0">
                  <p className="text-sm font-medium truncate">{report.name}</p>
                  {report.date && <p className="text-xs opacity-60">{report.date}</p>}
                </div>
                {activeReport === report.name && <ChevronRight className="w-4 h-4 shrink-0" />}
              </motion.button>
            ))
          )}
        </div>

        <div className="flex-1 bg-slate-900/50 border border-slate-800 rounded-xl backdrop-blur-md flex flex-col min-w-0 shadow-lg overflow-hidden">
          <div className="p-4 border-b border-slate-800 flex items-center justify-between bg-slate-950/80">
            <h2 className="font-medium text-slate-200 flex items-center gap-2 truncate">
              <FileText className="w-4 h-4 text-slate-400 shrink-0" />
              <span className="truncate">{activeReport || 'Select a report'}</span>
            </h2>
            <button 
              onClick={handleDownload}
              disabled={!activeReport || !content || loadingContent}
              className="p-2 bg-slate-900 border border-slate-800 hover:bg-slate-800 rounded-md text-slate-400 hover:text-slate-200 transition-colors disabled:opacity-50 disabled:cursor-not-allowed"
              title="Download Report"
            >
              <Download className="w-4 h-4" />
            </button>
          </div>
          
          <div className="p-6 overflow-y-auto flex-1 bg-slate-950/30">
            {loadingContent ? (
              <div className="flex flex-col items-center justify-center h-full text-slate-400">
                <Loader2 className="w-8 h-8 animate-spin mb-4" />
                <p>Loading report content...</p>
              </div>
            ) : !activeReport ? (
              <div className="flex flex-col items-center justify-center h-full text-slate-500">
                <FileText className="w-12 h-12 mb-4 opacity-50" />
                <p>Select a report to view</p>
              </div>
            ) : !content ? (
              <div className="flex flex-col items-center justify-center h-full text-slate-500">
                <AlertCircle className="w-12 h-12 mb-4 opacity-50" />
                <p>Report is empty.</p>
              </div>
            ) : (
              <div className="prose prose-invert prose-slate max-w-none 
                prose-headings:text-white prose-headings:font-bold 
                prose-a:text-blue-400 
                prose-code:bg-slate-900 prose-code:font-mono prose-code:px-1 prose-code:py-0.5 prose-code:rounded 
                prose-pre:bg-slate-900 prose-pre:border prose-pre:border-slate-800
                prose-table:border-collapse prose-table:w-full prose-table:text-sm
                prose-th:border prose-th:border-slate-700 prose-th:bg-slate-800 prose-th:p-2 prose-th:text-left
                prose-td:border prose-td:border-slate-700 prose-td:p-2 prose-td:bg-slate-900/50
                prose-ul:text-slate-300 prose-ol:text-slate-300 prose-p:text-slate-300
              ">
                <ReactMarkdown remarkPlugins={[remarkGfm]}>
                  {content}
                </ReactMarkdown>
              </div>
            )}
          </div>
        </div>
      </div>
    </motion.div>
  );
}
