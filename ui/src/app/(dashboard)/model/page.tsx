'use client';
import { useEffect, useState } from 'react';
import { motion } from 'framer-motion';
import { Cpu, Activity, ShieldAlert, ShieldCheck, Zap } from 'lucide-react';
import { cn } from '@/lib/utils';

const fadeIn = { hidden: { opacity: 0, y: 20 }, visible: { opacity: 1, y: 0 } };
const stagger = { visible: { transition: { staggerChildren: 0.08 } }, hidden: {} };

interface LogEntry {
  id: string;
  endpoint: string;
  confidence: number;
  verdict: 'VULNERABLE' | 'SAFE';
  time: string;
}

export default function ModelMonitorPage() {
  const [logs, setLogs] = useState<LogEntry[]>([]);
  const [loading, setLoading] = useState(true);

  useEffect(() => {
    // Simulate fetching /api/logs
    setTimeout(() => {
      setLogs([
        { id: '1', endpoint: 'GET /api/users/{id}', confidence: 0.92, verdict: 'VULNERABLE', time: '10:45:12 AM' },
        { id: '2', endpoint: 'POST /api/profile', confidence: 0.85, verdict: 'SAFE', time: '10:45:15 AM' },
        { id: '3', endpoint: 'GET /api/documents/{doc_id}', confidence: 0.78, verdict: 'VULNERABLE', time: '10:46:01 AM' },
        { id: '4', endpoint: 'PUT /api/settings', confidence: 0.95, verdict: 'SAFE', time: '10:46:22 AM' }
      ]);
      setLoading(false);
    }, 1000);
  }, []);

  const totalInferences = logs.length;
  const avgConfidence = totalInferences ? (logs.reduce((acc, log) => acc + log.confidence, 0) / totalInferences).toFixed(2) : '0';
  const vulnerableCount = logs.filter(l => l.verdict === 'VULNERABLE').length;

  return (
    <div className="p-8 max-w-6xl mx-auto space-y-8 min-h-screen">
      <motion.div initial="hidden" animate="visible" variants={stagger} className="space-y-2">
        <motion.h1 variants={fadeIn} className="text-3xl font-bold text-white tracking-tight flex items-center gap-3">
          <Cpu className="w-8 h-8 text-purple-400" /> Model Monitor
        </motion.h1>
        <motion.p variants={fadeIn} className="text-slate-400">Real-time LLM inference statistics and classifications.</motion.p>
      </motion.div>

      {loading ? (
         <div className="grid grid-cols-1 md:grid-cols-3 gap-6 mb-8">
           {[1,2,3].map(i => <div key={i} className="h-24 rounded-xl bg-slate-800/50 animate-pulse border border-slate-800" />)}
         </div>
      ) : (
        <motion.div initial="hidden" animate="visible" variants={stagger} className="space-y-8">
          
          <div className="grid grid-cols-1 md:grid-cols-3 gap-6">
            <motion.div variants={fadeIn} className="bg-slate-900/50 border border-slate-800 p-6 rounded-xl relative overflow-hidden">
              <Activity className="absolute right-[-10%] top-[-10%] w-32 h-32 text-slate-800/50" />
              <p className="text-sm text-slate-400 mb-1">Total Inferences</p>
              <p className="text-4xl font-bold text-white">{totalInferences}</p>
            </motion.div>
            <motion.div variants={fadeIn} className="bg-slate-900/50 border border-slate-800 p-6 rounded-xl relative overflow-hidden">
              <Zap className="absolute right-[-10%] top-[-10%] w-32 h-32 text-slate-800/50" />
              <p className="text-sm text-slate-400 mb-1">Avg Confidence</p>
              <p className="text-4xl font-bold text-white">{avgConfidence}</p>
            </motion.div>
            <motion.div variants={fadeIn} className="bg-slate-900/50 border border-slate-800 p-6 rounded-xl relative overflow-hidden">
              <ShieldAlert className="absolute right-[-10%] top-[-10%] w-32 h-32 text-slate-800/50" />
              <p className="text-sm text-slate-400 mb-1">Detected Vulnerabilities</p>
              <p className="text-4xl font-bold text-rose-400">{vulnerableCount}</p>
            </motion.div>
          </div>

          <motion.div variants={fadeIn} className="bg-slate-900/50 border border-slate-800 rounded-xl overflow-hidden">
            <div className="p-4 border-b border-slate-800 bg-slate-900/80">
              <h2 className="font-semibold text-white">Recent Classifications</h2>
            </div>
            <div className="overflow-x-auto">
              <table className="w-full text-left border-collapse">
                <thead>
                  <tr className="bg-slate-900/40 border-b border-slate-800 text-xs uppercase tracking-wider text-slate-500">
                    <th className="p-4 font-medium">Time</th>
                    <th className="p-4 font-medium">Endpoint</th>
                    <th className="p-4 font-medium">Confidence</th>
                    <th className="p-4 font-medium">Verdict</th>
                  </tr>
                </thead>
                <tbody className="divide-y divide-slate-800/50">
                  {logs.map(log => (
                    <tr key={log.id} className="hover:bg-slate-800/20 transition-colors">
                      <td className="p-4 text-sm text-slate-400 whitespace-nowrap">{log.time}</td>
                      <td className="p-4 text-sm font-mono text-slate-300">{log.endpoint}</td>
                      <td className="p-4">
                        <div className="flex items-center gap-2">
                          <div className="w-16 h-2 bg-slate-800 rounded-full overflow-hidden">
                            <div className="h-full bg-indigo-500" style={{ width: `${log.confidence * 100}%` }} />
                          </div>
                          <span className="text-xs text-slate-400">{Math.round(log.confidence * 100)}%</span>
                        </div>
                      </td>
                      <td className="p-4">
                        {log.verdict === 'VULNERABLE' ? (
                          <span className="inline-flex items-center gap-1.5 px-2.5 py-1 rounded-full text-xs font-medium bg-rose-500/10 text-rose-400 border border-rose-500/20">
                            <ShieldAlert className="w-3.5 h-3.5" /> Vulnerable
                          </span>
                        ) : (
                           <span className="inline-flex items-center gap-1.5 px-2.5 py-1 rounded-full text-xs font-medium bg-emerald-500/10 text-emerald-400 border border-emerald-500/20">
                            <ShieldCheck className="w-3.5 h-3.5" /> Safe
                          </span>
                        )}
                      </td>
                    </tr>
                  ))}
                </tbody>
              </table>
            </div>
          </motion.div>

        </motion.div>
      )}
    </div>
  );
}
