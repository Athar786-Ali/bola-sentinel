'use client';
import { useEffect, useState } from 'react';
import { motion } from 'framer-motion';
import { Database, Folder, Link as LinkIcon, GitCommit, CheckCircle2, XCircle, AlertCircle } from 'lucide-react';
import { cn } from '@/lib/utils';

const fadeIn = { hidden: { opacity: 0, y: 20 }, visible: { opacity: 1, y: 0 } };
const stagger = { visible: { transition: { staggerChildren: 0.08 } }, hidden: {} };

interface Dataset {
  app_name: string;
  source_path: string;
  base_url: string;
  git_commit: string;
  dataset_version: string;
  ground_truth_size?: number;
  coverage?: number;
  validation_status: 'valid' | 'invalid' | 'unknown';
}

export default function DatasetsPage() {
  const [datasets, setDatasets] = useState<Dataset[]>([]);
  const [loading, setLoading] = useState(true);

  useEffect(() => {
    // Simulate fetching /api/datasets
    setTimeout(() => {
      setDatasets([
        { app_name: 'vAmPI', source_path: '/apps/vAmPI', base_url: 'http://localhost:5000', git_commit: 'a1b2c3d', dataset_version: '1.0', ground_truth_size: 42, coverage: 85, validation_status: 'valid' },
        { app_name: 'crAPI', source_path: '/apps/crAPI', base_url: 'http://localhost:8888', git_commit: 'f4e5d6c', dataset_version: '2.1', ground_truth_size: 156, coverage: 92, validation_status: 'valid' }
      ]);
      setLoading(false);
    }, 1000);
  }, []);

  return (
    <div className="p-8 max-w-6xl mx-auto space-y-8 min-h-screen">
      <motion.div initial="hidden" animate="visible" variants={stagger} className="space-y-2">
        <motion.h1 variants={fadeIn} className="text-3xl font-bold text-white tracking-tight">Datasets</motion.h1>
        <motion.p variants={fadeIn} className="text-slate-400">Manage registered target applications and ground truth data.</motion.p>
      </motion.div>

      {loading ? (
        <div className="grid grid-cols-1 md:grid-cols-2 gap-6">
          {[1, 2].map(i => (
            <div key={i} className="h-64 rounded-xl bg-slate-800/50 animate-pulse border border-slate-800" />
          ))}
        </div>
      ) : datasets.length === 0 ? (
        <div className="flex flex-col items-center justify-center py-20 text-slate-400 border border-slate-800 rounded-xl bg-slate-900/50 border-dashed">
          <Database className="w-12 h-12 mb-4 text-slate-500" />
          <p>No datasets found.</p>
        </div>
      ) : (
        <motion.div initial="hidden" animate="visible" variants={stagger} className="grid grid-cols-1 md:grid-cols-2 gap-6">
          {datasets.map((dataset) => (
            <motion.div key={dataset.app_name} variants={fadeIn} className="bg-slate-900/50 backdrop-blur-md border border-slate-800 rounded-xl p-6 hover:border-slate-700 transition-colors group">
              <div className="flex justify-between items-start mb-6">
                <div>
                  <h3 className="text-xl font-semibold text-slate-200 flex items-center gap-2">
                    <Database className="w-5 h-5 text-indigo-400" />
                    {dataset.app_name}
                  </h3>
                  <span className="inline-flex items-center gap-1 mt-2 text-xs font-medium px-2 py-1 rounded-md bg-slate-800 text-slate-300">
                    v{dataset.dataset_version}
                  </span>
                </div>
                {dataset.validation_status === 'valid' ? (
                  <span className="flex items-center gap-1 text-xs font-medium px-2.5 py-1 rounded-full bg-emerald-400/10 text-emerald-400 border border-emerald-400/20">
                    <CheckCircle2 className="w-3.5 h-3.5" /> Valid
                  </span>
                ) : (
                  <span className="flex items-center gap-1 text-xs font-medium px-2.5 py-1 rounded-full bg-rose-400/10 text-rose-400 border border-rose-400/20">
                    <XCircle className="w-3.5 h-3.5" /> Invalid
                  </span>
                )}
              </div>
              
              <div className="space-y-3 mb-6">
                <div className="flex items-center gap-3 text-sm text-slate-400">
                  <Folder className="w-4 h-4 text-slate-500" />
                  <span className="truncate" title={dataset.source_path}>{dataset.source_path}</span>
                </div>
                <div className="flex items-center gap-3 text-sm text-slate-400">
                  <LinkIcon className="w-4 h-4 text-slate-500" />
                  <span className="truncate">{dataset.base_url}</span>
                </div>
                <div className="flex items-center gap-3 text-sm text-slate-400">
                  <GitCommit className="w-4 h-4 text-slate-500" />
                  <span className="font-mono">{dataset.git_commit}</span>
                </div>
              </div>

              <div className="grid grid-cols-2 gap-4 pt-4 border-t border-slate-800">
                <div>
                  <p className="text-xs text-slate-500 mb-1">Ground Truth Size</p>
                  <p className="text-lg font-semibold text-slate-200">{dataset.ground_truth_size ?? '-'}</p>
                </div>
                <div>
                  <p className="text-xs text-slate-500 mb-1">Coverage</p>
                  <p className="text-lg font-semibold text-slate-200">{dataset.coverage ? `${dataset.coverage}%` : '-'}</p>
                </div>
              </div>
            </motion.div>
          ))}
        </motion.div>
      )}
    </div>
  );
}
