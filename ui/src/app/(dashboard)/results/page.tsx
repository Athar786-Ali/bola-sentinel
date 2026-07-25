'use client';

import { useState, useEffect } from 'react';
import { motion } from 'framer-motion';
import {
  ResponsiveContainer, BarChart, Bar, XAxis, YAxis, CartesianGrid, Tooltip, Legend,
  AreaChart, Area, RadarChart, PolarGrid, PolarAngleAxis, PolarRadiusAxis, Radar
} from 'recharts';
import { Loader2, AlertCircle } from 'lucide-react';
import { cn } from '@/lib/utils';

export default function ResultsPage() {
  const [data, setData] = useState<any>(null);
  const [loading, setLoading] = useState(true);
  const [error, setError] = useState<string | null>(null);

  useEffect(() => {
    const fetchData = async () => {
      try {
        const res = await fetch('/api/metrics');
        if (!res.ok) throw new Error('Failed to fetch metrics');
        const json = await res.json();
        setData(json);
      } catch (err: any) {
        setError(err.message);
      } finally {
        setLoading(false);
      }
    };
    fetchData();
  }, []);

  if (loading) {
    return (
      <div className="flex items-center justify-center h-[calc(100vh-4rem)]">
        <Loader2 className="w-8 h-8 animate-spin text-blue-500" />
      </div>
    );
  }

  if (error) {
    return (
      <div className="flex items-center justify-center h-[calc(100vh-4rem)]">
        <div className="bg-red-500/10 text-red-500 p-6 rounded-lg flex items-center gap-3">
          <AlertCircle className="w-6 h-6" />
          <p>Error loading results: {error}</p>
        </div>
      </div>
    );
  }

  const pooled = data?.pooled_overall_results || {};
  const perApp = data?.per_application_results || {};
  const appNames = Object.keys(perApp);

  const stageData = [
    { name: 'Stage 1', TP: pooled.stage_1_static_only?.tp || 0, FP: pooled.stage_1_static_only?.fp || 0, FN: pooled.stage_1_static_only?.fn || 0, TN: pooled.stage_1_static_only?.tn || 0 },
    { name: 'Stage 2', TP: pooled.stage_2_static_plus_llm?.tp || 0, FP: pooled.stage_2_static_plus_llm?.fp || 0, FN: pooled.stage_2_static_plus_llm?.fn || 0, TN: pooled.stage_2_static_plus_llm?.tn || 0 },
    { name: 'Stage 3', TP: pooled.stage_3_final_system?.tp || 0, FP: pooled.stage_3_final_system?.fp || 0, FN: pooled.stage_3_final_system?.fn || 0, TN: pooled.stage_3_final_system?.tn || 0 },
  ];

  const metricsFields = [
    { key: 'precision', label: 'Precision' },
    { key: 'recall', label: 'Recall' },
    { key: 'f1', label: 'F1 Score' },
    { key: 'accuracy', label: 'Accuracy' }
  ];

  const radarData = metricsFields.map(m => {
    const row: any = { metric: m.label };
    appNames.forEach(app => {
      row[app] = perApp[app]?.stage_3_final_system?.[m.key] || 0;
    });
    return row;
  });

  const fpReductionData = [
    { name: 'Stage 1', FP: pooled.stage_1_static_only?.fp || 0 },
    { name: 'Stage 2', FP: pooled.stage_2_static_plus_llm?.fp || 0 },
    { name: 'Stage 3', FP: pooled.stage_3_final_system?.fp || 0 },
  ];

  const CustomTooltip = ({ active, payload, label }: any) => {
    if (active && payload && payload.length) {
      return (
        <div className="bg-slate-900/95 border border-slate-700/50 p-3 rounded-md shadow-xl backdrop-blur-sm">
          <p className="text-slate-200 font-medium mb-2">{label}</p>
          {payload.map((entry: any, index: number) => (
            <div key={index} className="flex items-center gap-2 text-sm">
              <div className="w-2 h-2 rounded-full" style={{ backgroundColor: entry.color }} />
              <span className="text-slate-300">{entry.name}:</span>
              <span className="text-slate-100 font-medium">{typeof entry.value === 'number' && entry.value < 1 && entry.value > 0 ? entry.value.toFixed(2) : entry.value}</span>
            </div>
          ))}
        </div>
      );
    }
    return null;
  };

  const colors = ["#8b5cf6", "#3b82f6", "#10b981", "#ef4444", "#f59e0b"];

  return (
    <motion.div 
      initial={{ opacity: 0, y: 20 }}
      animate={{ opacity: 1, y: 0 }}
      className="p-6 space-y-6"
    >
      <div className="flex items-center justify-between">
        <h1 className="text-2xl font-bold text-slate-100">Results & Analytics</h1>
      </div>

      <div className="grid grid-cols-1 lg:grid-cols-2 gap-6">
        <motion.div 
          initial={{ opacity: 0, scale: 0.95 }}
          animate={{ opacity: 1, scale: 1 }}
          transition={{ delay: 0.1 }}
          className="bg-slate-900/50 border border-slate-800 rounded-xl p-6 backdrop-blur-md"
        >
          <h2 className="text-lg font-semibold text-slate-200 mb-6">Detection Stages (TP/FP/FN/TN)</h2>
          <div className="h-[300px]">
            <ResponsiveContainer width="100%" height="100%">
              <BarChart data={stageData} margin={{ top: 10, right: 10, left: -20, bottom: 0 }}>
                <CartesianGrid strokeDasharray="3 3" stroke="#1e293b" vertical={false} />
                <XAxis dataKey="name" stroke="#475569" tick={{ fill: '#94a3b8' }} axisLine={false} tickLine={false} />
                <YAxis stroke="#475569" tick={{ fill: '#94a3b8' }} axisLine={false} tickLine={false} />
                <Tooltip content={<CustomTooltip />} />
                <Legend iconType="circle" wrapperStyle={{ paddingTop: '20px' }} />
                <Bar dataKey="TP" fill="#10b981" radius={[4, 4, 0, 0]} />
                <Bar dataKey="FP" fill="#ef4444" radius={[4, 4, 0, 0]} />
                <Bar dataKey="FN" fill="#f59e0b" radius={[4, 4, 0, 0]} />
                <Bar dataKey="TN" fill="#3b82f6" radius={[4, 4, 0, 0]} />
              </BarChart>
            </ResponsiveContainer>
          </div>
        </motion.div>

        <motion.div 
          initial={{ opacity: 0, scale: 0.95 }}
          animate={{ opacity: 1, scale: 1 }}
          transition={{ delay: 0.2 }}
          className="bg-slate-900/50 border border-slate-800 rounded-xl p-6 backdrop-blur-md"
        >
          <h2 className="text-lg font-semibold text-slate-200 mb-6">False Positive Reduction</h2>
          <div className="h-[300px]">
            <ResponsiveContainer width="100%" height="100%">
              <AreaChart data={fpReductionData} margin={{ top: 10, right: 10, left: -20, bottom: 0 }}>
                <defs>
                  <linearGradient id="colorFp" x1="0" y1="0" x2="0" y2="1">
                    <stop offset="5%" stopColor="#ef4444" stopOpacity={0.3}/>
                    <stop offset="95%" stopColor="#ef4444" stopOpacity={0}/>
                  </linearGradient>
                </defs>
                <CartesianGrid strokeDasharray="3 3" stroke="#1e293b" vertical={false} />
                <XAxis dataKey="name" stroke="#475569" tick={{ fill: '#94a3b8' }} axisLine={false} tickLine={false} />
                <YAxis stroke="#475569" tick={{ fill: '#94a3b8' }} axisLine={false} tickLine={false} />
                <Tooltip content={<CustomTooltip />} />
                <Area type="monotone" dataKey="FP" stroke="#ef4444" strokeWidth={3} fillOpacity={1} fill="url(#colorFp)" />
              </AreaChart>
            </ResponsiveContainer>
          </div>
        </motion.div>

        <motion.div 
          initial={{ opacity: 0, scale: 0.95 }}
          animate={{ opacity: 1, scale: 1 }}
          transition={{ delay: 0.3 }}
          className="bg-slate-900/50 border border-slate-800 rounded-xl p-6 backdrop-blur-md lg:col-span-2"
        >
          <h2 className="text-lg font-semibold text-slate-200 mb-6">App Comparison Metrics (Stage 3)</h2>
          <div className="flex flex-col lg:flex-row items-center justify-between">
            <div className="w-full lg:w-1/2 h-[350px]">
              <ResponsiveContainer width="100%" height="100%">
                <RadarChart cx="50%" cy="50%" outerRadius="70%" data={radarData}>
                  <PolarGrid stroke="#1e293b" />
                  <PolarAngleAxis dataKey="metric" tick={{ fill: '#94a3b8', fontSize: 12 }} />
                  <PolarRadiusAxis angle={30} domain={[0, 1]} tick={{ fill: '#475569' }} />
                  {appNames.map((app, idx) => (
                    <Radar key={app} name={app} dataKey={app} stroke={colors[idx % colors.length]} fill={colors[idx % colors.length]} fillOpacity={0.3} />
                  ))}
                  <Legend iconType="circle" wrapperStyle={{ paddingTop: '20px' }} />
                  <Tooltip content={<CustomTooltip />} />
                </RadarChart>
              </ResponsiveContainer>
            </div>
            <div className="w-full lg:w-1/2 mt-6 lg:mt-0 overflow-x-auto">
              <table className="w-full text-left text-sm text-slate-300">
                <thead className="text-xs uppercase bg-slate-800/50 text-slate-400">
                  <tr>
                    <th className="px-4 py-3 rounded-tl-lg">App Name</th>
                    <th className="px-4 py-3">Precision</th>
                    <th className="px-4 py-3">Recall</th>
                    <th className="px-4 py-3">F1 Score</th>
                    <th className="px-4 py-3 rounded-tr-lg">Accuracy</th>
                  </tr>
                </thead>
                <tbody className="divide-y divide-slate-800/50">
                  {appNames.map(app => (
                    <tr key={app} className="hover:bg-slate-800/30 transition-colors">
                      <td className="px-4 py-3 font-medium text-slate-200">{app}</td>
                      <td className="px-4 py-3 text-emerald-400">{(perApp[app]?.stage_3_final_system?.precision * 100 || 0).toFixed(1)}%</td>
                      <td className="px-4 py-3">{(perApp[app]?.stage_3_final_system?.recall * 100 || 0).toFixed(1)}%</td>
                      <td className="px-4 py-3">{(perApp[app]?.stage_3_final_system?.f1 * 100 || 0).toFixed(1)}%</td>
                      <td className="px-4 py-3">{(perApp[app]?.stage_3_final_system?.accuracy * 100 || 0).toFixed(1)}%</td>
                    </tr>
                  ))}
                  {appNames.length === 0 && (
                     <tr>
                       <td colSpan={5} className="px-4 py-3 text-center text-slate-500">No applications found.</td>
                     </tr>
                  )}
                </tbody>
              </table>
            </div>
          </div>
        </motion.div>
      </div>
    </motion.div>
  );
}
