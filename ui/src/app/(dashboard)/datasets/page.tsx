'use client';
import { useEffect, useState } from 'react';
import { motion } from 'framer-motion';
import { Database, Folder, Link as LinkIcon, GitCommit, CheckCircle2, XCircle } from 'lucide-react';

const fadeIn = { hidden: { opacity: 0, y: 20 }, visible: { opacity: 1, y: 0 } };
const stagger = { visible: { transition: { staggerChildren: 0.08 } }, hidden: {} };

interface DatasetAPI {
  application_name: string;
  source_path: string;
  base_url: string;
  test_users_file: string;
  ground_truth_file: string;
  git_commit: string;
  dataset_version: string;
}

interface Dataset extends DatasetAPI {
  ground_truth_size?: number;
  coverage?: number;
  validation_status: 'valid' | 'invalid' | 'unknown';
}

export default function DatasetsPage() {
  const [datasets, setDatasets] = useState<Dataset[]>([]);
  const [loading, setLoading] = useState(true);

  useEffect(() => {
    async function fetchData() {
      try {
        const [datasetsRes, metricsRes] = await Promise.all([
          fetch('/api/datasets'),
          fetch('/api/metrics')
        ]);
        
        let datasetsData: DatasetAPI[] = [];
        if (datasetsRes.ok) {
          datasetsData = await datasetsRes.json();
        }

        let metricsData: any = {};
        if (metricsRes.ok) {
          metricsData = await metricsRes.json();
        }

        const perAppMetrics = metricsData.per_application_results || {};

        const combined: Dataset[] = datasetsData.map(ds => {
          const metrics = perAppMetrics[ds.application_name] || {};
          return {
            ...ds,
            ground_truth_size: metrics.ground_truth_size ?? ds.ground_truth_size,
            coverage: metrics.coverage,
            validation_status: 'valid' // Defaulting to valid assuming it's returned by the API if present
          };
        });

        setDatasets(combined);
      } catch (error) {
        console.error("Error fetching datasets:", error);
      } finally {
        setLoading(false);
      }
    }
    fetchData();
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
            <motion.div key={dataset.application_name} variants={fadeIn} className="bg-slate-900/50 backdrop-blur-md border border-slate-800 rounded-xl p-6 hover:border-slate-700 transition-colors group">
              <div className="flex justify-between items-start mb-6">
                <div>
                  <h3 className="text-xl font-semibold text-slate-200 flex items-center gap-2">
                    <Database className="w-5 h-5 text-indigo-400" />
                    {dataset.application_name}
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
                  <p className="text-lg font-semibold text-slate-200">{dataset.coverage != null ? `${(dataset.coverage * 100).toFixed(1)}%` : '-'}</p>
                </div>
              </div>
            </motion.div>
          ))}
        </motion.div>
      )}
    </div>
  );
}
