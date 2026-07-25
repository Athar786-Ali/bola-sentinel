'use client';
import { useEffect, useState } from 'react';
import { motion } from 'framer-motion';
import { Clock, CheckCircle, XCircle, AlertCircle, ChevronDown, Calendar, Timer } from 'lucide-react';
import { cn } from '@/lib/utils';

const fadeIn = { hidden: { opacity: 0, y: 20 }, visible: { opacity: 1, y: 0 } };
const stagger = { visible: { transition: { staggerChildren: 0.08 } }, hidden: {} };

interface Run {
  id: string;
  app_name: string;
  timestamp: string;
  status: 'SUCCESS' | 'FAILED' | 'SKIPPED';
  duration: string;
  phases_completed: number;
  model: string;
  error?: string;
}

export default function HistoryPage() {
  const [runs, setRuns] = useState<Run[]>([]);
  const [loading, setLoading] = useState(true);
  const [expandedId, setExpandedId] = useState<string | null>(null);
  const [filterApp, setFilterApp] = useState('All');

  useEffect(() => {
    // Simulate fetching /api/history
    setTimeout(() => {
      setRuns([
        { id: '1', app_name: 'vAmPI', timestamp: '2026-07-25T14:30:00Z', status: 'SUCCESS', duration: '45s', phases_completed: 5, model: 'qwen2.5:7b-instruct' },
        { id: '2', app_name: 'crAPI', timestamp: '2026-07-25T12:15:00Z', status: 'FAILED', duration: '12s', phases_completed: 2, model: 'qwen2.5:7b-instruct', error: 'Docker connection timeout.' },
        { id: '3', app_name: 'vAmPI', timestamp: '2026-07-24T09:00:00Z', status: 'SUCCESS', duration: '42s', phases_completed: 5, model: 'llama3:8b' }
      ]);
      setLoading(false);
    }, 1000);
  }, []);

  const filteredRuns = runs.filter(r => filterApp === 'All' || r.app_name === filterApp);
  const successCount = runs.filter(r => r.status === 'SUCCESS').length;

  return (
    <div className="p-8 max-w-6xl mx-auto space-y-8 min-h-screen">
      <motion.div initial="hidden" animate="visible" variants={stagger} className="space-y-4">
        <motion.h1 variants={fadeIn} className="text-3xl font-bold text-white tracking-tight">Benchmark History</motion.h1>
        
        <motion.div variants={fadeIn} className="grid grid-cols-1 md:grid-cols-3 gap-4">
          <div className="bg-slate-900/50 border border-slate-800 p-4 rounded-xl flex items-center justify-between">
            <div>
              <p className="text-sm text-slate-400">Total Runs</p>
              <p className="text-2xl font-bold text-white">{runs.length}</p>
            </div>
            <Clock className="w-8 h-8 text-slate-700" />
          </div>
          <div className="bg-slate-900/50 border border-slate-800 p-4 rounded-xl flex items-center justify-between">
            <div>
              <p className="text-sm text-slate-400">Success Rate</p>
              <p className="text-2xl font-bold text-white">
                {runs.length > 0 ? Math.round((successCount / runs.length) * 100) : 0}%
              </p>
            </div>
            <CheckCircle className="w-8 h-8 text-emerald-900" />
          </div>
          <div className="bg-slate-900/50 border border-slate-800 p-4 rounded-xl flex items-center gap-2">
             <select 
              value={filterApp} 
              onChange={e => setFilterApp(e.target.value)}
              className="w-full bg-slate-950 border border-slate-800 text-slate-200 rounded-lg p-2 focus:ring-2 focus:ring-indigo-500 outline-none"
             >
               <option value="All">All Applications</option>
               <option value="vAmPI">vAmPI</option>
               <option value="crAPI">crAPI</option>
             </select>
          </div>
        </motion.div>
      </motion.div>

      {loading ? (
        <div className="space-y-4">
          {[1,2,3].map(i => <div key={i} className="h-20 rounded-xl bg-slate-800/50 animate-pulse border border-slate-800" />)}
        </div>
      ) : filteredRuns.length === 0 ? (
        <div className="flex flex-col items-center justify-center py-20 text-slate-400 border border-slate-800 rounded-xl bg-slate-900/50 border-dashed">
          <Clock className="w-12 h-12 mb-4 text-slate-500" />
          <p>No history found.</p>
        </div>
      ) : (
        <motion.div initial="hidden" animate="visible" variants={stagger} className="space-y-4">
          {filteredRuns.map((run) => (
            <motion.div key={run.id} variants={fadeIn} className="bg-slate-900/50 backdrop-blur-md border border-slate-800 rounded-xl overflow-hidden transition-colors hover:border-slate-700">
              <div 
                className="p-4 flex flex-col md:flex-row md:items-center justify-between gap-4 cursor-pointer"
                onClick={() => run.error && setExpandedId(expandedId === run.id ? null : run.id)}
              >
                <div className="flex items-center gap-4">
                  {run.status === 'SUCCESS' && <CheckCircle className="w-6 h-6 text-emerald-500" />}
                  {run.status === 'FAILED' && <XCircle className="w-6 h-6 text-rose-500" />}
                  {run.status === 'SKIPPED' && <AlertCircle className="w-6 h-6 text-slate-500" />}
                  
                  <div>
                    <h4 className="font-semibold text-slate-200">{run.app_name}</h4>
                    <div className="flex items-center gap-3 text-xs text-slate-500 mt-1">
                      <span className="flex items-center gap-1"><Calendar className="w-3 h-3"/> {new Date(run.timestamp).toLocaleString()}</span>
                      <span className="flex items-center gap-1"><Timer className="w-3 h-3"/> {run.duration}</span>
                    </div>
                  </div>
                </div>

                <div className="flex items-center gap-6">
                  <div className="text-right">
                    <p className="text-xs text-slate-400">Model</p>
                    <p className="text-sm font-mono text-slate-300">{run.model}</p>
                  </div>
                  <div className="text-right hidden sm:block">
                    <p className="text-xs text-slate-400">Phases</p>
                    <p className="text-sm text-slate-300">{run.phases_completed}/5</p>
                  </div>
                  {run.error && (
                    <ChevronDown className={cn("w-5 h-5 text-slate-500 transition-transform", expandedId === run.id ? "rotate-180" : "")} />
                  )}
                </div>
              </div>
              
              {run.error && expandedId === run.id && (
                <div className="p-4 bg-slate-950 border-t border-slate-800 text-sm font-mono text-rose-400">
                  {run.error}
                </div>
              )}
            </motion.div>
          ))}
        </motion.div>
      )}
    </div>
  );
}
