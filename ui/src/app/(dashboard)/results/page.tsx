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

  // Sample data manipulation based on expected API response or placeholders
  const stageData = [
    { name: 'Stage 1', TP: 45, FP: 120, FN: 5, TN: 200 },
    { name: 'Stage 2', TP: 43, FP: 40, FN: 7, TN: 280 },
    { name: 'Stage 3', TP: 40, FP: 5, FN: 10, TN: 315 },
  ];

  const radarData = [
    { metric: 'Precision', 'Juice Shop': 0.89, 'NodeJS App': 0.85 },
    { metric: 'Recall', 'Juice Shop': 0.8, 'NodeJS App': 0.75 },
    { metric: 'F1 Score', 'Juice Shop': 0.84, 'NodeJS App': 0.79 },
    { metric: 'Accuracy', 'Juice Shop': 0.95, 'NodeJS App': 0.92 },
  ];

  const fpReductionData = [
    { name: 'Stage 1', FP: 120 },
    { name: 'Stage 2', FP: 40 },
    { name: 'Stage 3', FP: 5 },
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
              <span className="text-slate-100 font-medium">{entry.value}</span>
            </div>
          ))}
        </div>
      );
    }
    return null;
  };

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
          <h2 className="text-lg font-semibold text-slate-200 mb-6">App Comparison Metrics</h2>
          <div className="flex flex-col lg:flex-row items-center justify-between">
            <div className="w-full lg:w-1/2 h-[350px]">
              <ResponsiveContainer width="100%" height="100%">
                <RadarChart cx="50%" cy="50%" outerRadius="70%" data={radarData}>
                  <PolarGrid stroke="#1e293b" />
                  <PolarAngleAxis dataKey="metric" tick={{ fill: '#94a3b8', fontSize: 12 }} />
                  <PolarRadiusAxis angle={30} domain={[0, 1]} tick={{ fill: '#475569' }} />
                  <Radar name="Juice Shop" dataKey="Juice Shop" stroke="#8b5cf6" fill="#8b5cf6" fillOpacity={0.3} />
                  <Radar name="NodeJS App" dataKey="NodeJS App" stroke="#3b82f6" fill="#3b82f6" fillOpacity={0.3} />
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
                  <tr className="hover:bg-slate-800/30 transition-colors">
                    <td className="px-4 py-3 font-medium text-slate-200">Juice Shop</td>
                    <td className="px-4 py-3 text-emerald-400">89.0%</td>
                    <td className="px-4 py-3">80.0%</td>
                    <td className="px-4 py-3">84.0%</td>
                    <td className="px-4 py-3">95.0%</td>
                  </tr>
                  <tr className="hover:bg-slate-800/30 transition-colors">
                    <td className="px-4 py-3 font-medium text-slate-200">NodeJS App</td>
                    <td className="px-4 py-3 text-emerald-400">85.0%</td>
                    <td className="px-4 py-3">75.0%</td>
                    <td className="px-4 py-3">79.0%</td>
                    <td className="px-4 py-3">92.0%</td>
                  </tr>
                </tbody>
              </table>
            </div>
          </div>
        </motion.div>
      </div>
    </motion.div>
  );
}
