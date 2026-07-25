'use client';

import { useState, useEffect } from 'react';
import { motion } from 'framer-motion';
import { Play, CheckCircle2, Circle, Clock, AlertTriangle, Loader2 } from 'lucide-react';
import { cn } from '@/lib/utils';

type Stage = {
  id: string;
  name: string;
  status: 'pending' | 'running' | 'complete' | 'failed';
};

export default function BenchmarkPage() {
  const [apps, setApps] = useState<string[]>([]);
  const [selectedApp, setSelectedApp] = useState<string>('');
  const [force, setForce] = useState(false);
  const [running, setRunning] = useState(false);
  const [logs, setLogs] = useState<string>('');
  const [stages, setStages] = useState<Stage[]>([
    { id: 'static', name: 'Static Analysis', status: 'pending' },
    { id: 'llm', name: 'LLM Classification', status: 'pending' },
    { id: 'dynamic', name: 'Dynamic Verification', status: 'pending' },
    { id: 'eval', name: 'Evaluation', status: 'pending' },
    { id: 'report', name: 'Reports', status: 'pending' },
  ]);

  useEffect(() => {
    // Mock API call to get datasets
    setApps(['juice_shop', 'vuln-nodejs-app']);
    setSelectedApp('juice_shop');
  }, []);

  const runBenchmark = async () => {
    setRunning(true);
    setLogs('Starting benchmark...\n');
    
    const newStages = [...stages].map(s => ({ ...s, status: 'pending' as const }));
    setStages(newStages);

    // Simulated flow
    for (let i = 0; i < newStages.length; i++) {
      setStages(prev => prev.map((s, idx) => idx === i ? { ...s, status: 'running' } : s));
      setLogs(prev => prev + `\n[INFO] Starting ${newStages[i].name}...`);
      
      await new Promise(r => setTimeout(r, 1500));
      
      setStages(prev => prev.map((s, idx) => idx === i ? { ...s, status: 'complete' } : s));
      setLogs(prev => prev + `\n[SUCCESS] Completed ${newStages[i].name}.`);
    }
    
    setLogs(prev => prev + `\n\n[INFO] Benchmark finished successfully.`);
    setRunning(false);
  };

  const getStageIcon = (status: Stage['status']) => {
    switch (status) {
      case 'complete': return <CheckCircle2 className="w-6 h-6 text-emerald-500" />;
      case 'running': return <Loader2 className="w-6 h-6 text-blue-500 animate-spin" />;
      case 'failed': return <AlertTriangle className="w-6 h-6 text-red-500" />;
      default: return <Circle className="w-6 h-6 text-slate-600" />;
    }
  };

  return (
    <motion.div 
      initial={{ opacity: 0, y: 20 }}
      animate={{ opacity: 1, y: 0 }}
      className="p-6 max-w-6xl mx-auto space-y-6"
    >
      <div className="flex items-center justify-between">
        <h1 className="text-2xl font-bold text-slate-100">Benchmark Runner</h1>
      </div>

      <div className="grid grid-cols-1 lg:grid-cols-3 gap-6">
        <div className="lg:col-span-1 space-y-6">
          <motion.div className="bg-slate-900/50 border border-slate-800 rounded-xl p-6 backdrop-blur-md">
            <h2 className="text-lg font-medium text-slate-200 mb-4">Configuration</h2>
            
            <div className="space-y-4">
              <div>
                <label className="block text-sm font-medium text-slate-400 mb-1">Target Application</label>
                <select 
                  value={selectedApp}
                  onChange={(e) => setSelectedApp(e.target.value)}
                  disabled={running}
                  className="w-full bg-slate-950 border border-slate-800 rounded-lg px-3 py-2 text-slate-200 focus:outline-none focus:ring-2 focus:ring-blue-500/50 transition-all"
                >
                  {apps.map(app => (
                    <option key={app} value={app}>{app}</option>
                  ))}
                </select>
              </div>

              <div className="flex items-center gap-2">
                <input 
                  type="checkbox" 
                  id="force" 
                  checked={force}
                  onChange={(e) => setForce(e.target.checked)}
                  disabled={running}
                  className="rounded border-slate-800 bg-slate-950 text-blue-500 focus:ring-blue-500/50"
                />
                <label htmlFor="force" className="text-sm text-slate-400 cursor-pointer">
                  Force run (--force)
                </label>
              </div>

              <button
                onClick={runBenchmark}
                disabled={running}
                className="w-full py-2.5 bg-blue-600 hover:bg-blue-700 disabled:bg-blue-600/50 disabled:cursor-not-allowed text-white rounded-lg font-medium flex items-center justify-center gap-2 transition-colors"
              >
                {running ? <Loader2 className="w-5 h-5 animate-spin" /> : <Play className="w-5 h-5" />}
                {running ? 'Running...' : 'Run Benchmark'}
              </button>
            </div>
          </motion.div>

          <motion.div className="bg-slate-900/50 border border-slate-800 rounded-xl p-6 backdrop-blur-md">
            <h2 className="text-lg font-medium text-slate-200 mb-6">Pipeline Status</h2>
            <div className="space-y-0 relative">
              <div className="absolute left-3 top-3 bottom-3 w-0.5 bg-slate-800" />
              {stages.map((stage, idx) => (
                <div key={stage.id} className="relative flex items-center gap-4 py-4">
                  <div className="relative z-10 bg-slate-900 rounded-full">
                    {getStageIcon(stage.status)}
                  </div>
                  <div>
                    <p className={cn(
                      "font-medium transition-colors",
                      stage.status === 'running' ? "text-blue-400" :
                      stage.status === 'complete' ? "text-slate-200" : "text-slate-500"
                    )}>
                      {stage.name}
                    </p>
                  </div>
                </div>
              ))}
            </div>
          </motion.div>
        </div>

        <div className="lg:col-span-2">
          <motion.div className="bg-slate-900/50 border border-slate-800 rounded-xl p-0 backdrop-blur-md h-full flex flex-col overflow-hidden">
            <div className="border-b border-slate-800 p-4 bg-slate-950/50 flex items-center justify-between">
              <h2 className="font-medium text-slate-200 flex items-center gap-2">
                <Clock className="w-4 h-4 text-slate-400" />
                Execution Logs
              </h2>
              {running && <span className="flex items-center gap-2 text-xs font-medium text-blue-400 bg-blue-400/10 px-2 py-1 rounded-full"><span className="w-2 h-2 rounded-full bg-blue-400 animate-pulse" /> Running</span>}
            </div>
            <div className="p-4 flex-1 bg-[#0c0c0c]">
              <textarea
                readOnly
                value={logs}
                className="w-full h-full min-h-[400px] bg-transparent text-sm font-mono text-slate-300 focus:outline-none resize-none"
                placeholder="Logs will appear here once the benchmark starts..."
              />
            </div>
          </motion.div>
        </div>
      </div>
    </motion.div>
  );
}
