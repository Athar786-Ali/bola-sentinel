'use client';
import { useEffect, useState } from 'react';
import { motion } from 'framer-motion';
import { Settings, Server, CheckCircle2, XCircle, Info, Moon, Sun } from 'lucide-react';
import { cn } from '@/lib/utils';

const fadeIn = { hidden: { opacity: 0, y: 20 }, visible: { opacity: 1, y: 0 } };
const stagger = { visible: { transition: { staggerChildren: 0.08 } }, hidden: {} };

interface SystemHealth {
  python: { installed: boolean; version: string };
  docker: { installed: boolean; running: boolean };
  ollama: { installed: boolean; running: boolean; model: string };
}

export default function SettingsPage() {
  const [health, setHealth] = useState<SystemHealth | null>(null);
  const [theme, setTheme] = useState('dark');

  useEffect(() => {
    // Simulate fetching /api/system
    setTimeout(() => {
      setHealth({
        python: { installed: true, version: '3.10.12' },
        docker: { installed: true, running: true },
        ollama: { installed: true, running: true, model: 'qwen2.5:7b-instruct' }
      });
    }, 800);
  }, []);

  const StatusItem = ({ label, value, ok, details }: { label: string, value: string, ok: boolean, details?: string }) => (
    <div className="flex items-center justify-between p-4 border border-slate-800 rounded-lg bg-slate-900/30">
      <div>
        <p className="font-medium text-slate-200">{label}</p>
        {details && <p className="text-xs text-slate-500 mt-1">{details}</p>}
      </div>
      <div className="flex items-center gap-3">
        <span className="text-sm font-mono text-slate-400">{value}</span>
        {ok ? <CheckCircle2 className="w-5 h-5 text-emerald-500" /> : <XCircle className="w-5 h-5 text-rose-500" />}
      </div>
    </div>
  );

  return (
    <div className="p-8 max-w-4xl mx-auto space-y-8 min-h-screen">
      <motion.div initial="hidden" animate="visible" variants={stagger} className="space-y-2">
        <motion.h1 variants={fadeIn} className="text-3xl font-bold text-white tracking-tight">Settings & Health</motion.h1>
        <motion.p variants={fadeIn} className="text-slate-400">System configuration and environment status.</motion.p>
      </motion.div>

      {!health ? (
        <div className="space-y-4">
          {[1,2,3].map(i => <div key={i} className="h-20 rounded-xl bg-slate-800/50 animate-pulse border border-slate-800" />)}
        </div>
      ) : (
        <motion.div initial="hidden" animate="visible" variants={stagger} className="space-y-8">
          
          <motion.section variants={fadeIn} className="space-y-4">
            <h2 className="text-xl font-semibold text-white flex items-center gap-2">
              <Server className="w-5 h-5 text-indigo-400" /> System Health
            </h2>
            <div className="grid gap-4">
              <StatusItem label="Python" value={health.python.version} ok={health.python.installed} details="Required for backend scripts" />
              <StatusItem label="Docker Engine" value={health.docker.running ? 'Running' : 'Stopped'} ok={health.docker.installed && health.docker.running} details="Required for dynamic verification containers" />
              <StatusItem label="Ollama Service" value={health.ollama.model} ok={health.ollama.installed && health.ollama.running} details="Local LLM inference engine" />
            </div>
          </motion.section>

          <motion.section variants={fadeIn} className="space-y-4">
             <h2 className="text-xl font-semibold text-white flex items-center gap-2">
              <Settings className="w-5 h-5 text-indigo-400" /> Appearance
            </h2>
            <div className="p-4 border border-slate-800 rounded-lg bg-slate-900/30 flex items-center justify-between">
              <div>
                <p className="font-medium text-slate-200">Theme Preference</p>
                <p className="text-xs text-slate-500 mt-1">Toggle between light and dark mode (Visual Demo)</p>
              </div>
              <button 
                onClick={() => setTheme(theme === 'dark' ? 'light' : 'dark')}
                className="p-2 bg-slate-800 hover:bg-slate-700 rounded-lg transition-colors border border-slate-700"
              >
                {theme === 'dark' ? <Moon className="w-5 h-5 text-indigo-400" /> : <Sun className="w-5 h-5 text-amber-400" />}
              </button>
            </div>
          </motion.section>

          <motion.section variants={fadeIn} className="space-y-4">
            <h2 className="text-xl font-semibold text-white flex items-center gap-2">
              <Info className="w-5 h-5 text-indigo-400" /> About BOLA-Sentinel
            </h2>
            <div className="p-6 border border-slate-800 rounded-lg bg-slate-900/30">
              <p className="text-slate-300">BOLA-Sentinel v1.0.0</p>
              <p className="text-sm text-slate-500 mt-2">Enterprise-grade cybersecurity dashboard for detecting Broken Object Level Authorization vulnerabilities using LLMs.</p>
            </div>
          </motion.section>

        </motion.div>
      )}
    </div>
  );
}
