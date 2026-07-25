'use client';

import React, { useState, useEffect } from 'react';
import { motion, AnimatePresence } from 'framer-motion';
import { Search, ShieldAlert, ShieldCheck, ChevronDown, ChevronRight, Check, X, AlertTriangle, Loader2, Eye } from 'lucide-react';
import { cn } from '@/lib/utils';

interface VulnerabilityRow {
  route_id: string;
  http_method: string;
  endpoint: string;
  static_flagged: boolean;
  llm_flagged: boolean;
  llm_confidence: string;
  llm_explanation: string;
  dynamically_verified: boolean;
  verification_status: string;
  final_verdict: string;
  ground_truth: boolean | null;
  is_matched: boolean;
  risk_level: string;
}

const fadeIn = { hidden: { opacity: 0, y: 20 }, visible: { opacity: 1, y: 0 } };
const stagger = { visible: { transition: { staggerChildren: 0.06 } } };

export default function ExplorerPage() {
  const [activeTab, setActiveTab] = useState('juice_shop');
  const [search, setSearch] = useState('');
  const [expandedRow, setExpandedRow] = useState<string | null>(null);
  const [data, setData] = useState<VulnerabilityRow[]>([]);
  const [loading, setLoading] = useState(true);

  useEffect(() => {
    setLoading(true);
    setExpandedRow(null);
    fetch(`/api/vulnerabilities/${activeTab}`)
      .then(r => r.json())
      .then(d => { setData(Array.isArray(d) ? d : []); setLoading(false); })
      .catch(() => { setData([]); setLoading(false); });
  }, [activeTab]);

  // Separate matched (found by analyzer) vs unmatched (GT-only) entries
  const matchedData = data.filter(d => d.is_matched !== false && d.http_method !== 'UNKNOWN');
  const unmatchedGT = data.filter(d => !d.is_matched || d.http_method === 'UNKNOWN');

  const filteredData = matchedData.filter(item =>
    item.endpoint.toLowerCase().includes(search.toLowerCase()) ||
    item.route_id.toLowerCase().includes(search.toLowerCase())
  );

  // Compute stats from REAL data
  const totalRoutes = matchedData.length;
  const llmFlagged = matchedData.filter(d => d.llm_flagged).length;
  const dynamicallyConfirmed = matchedData.filter(d => d.dynamically_verified).length;
  const gtVulnerable = data.filter(d => d.ground_truth === true).length;

  const getMethodColor = (method: string) => {
    switch (method) {
      case 'GET': return 'bg-emerald-500/10 text-emerald-400 border-emerald-500/20';
      case 'POST': return 'bg-blue-500/10 text-blue-400 border-blue-500/20';
      case 'PUT': return 'bg-amber-500/10 text-amber-400 border-amber-500/20';
      case 'DELETE': return 'bg-red-500/10 text-red-400 border-red-500/20';
      case 'PATCH': return 'bg-violet-500/10 text-violet-400 border-violet-500/20';
      default: return 'bg-slate-500/10 text-slate-400 border-slate-500/20';
    }
  };

  const StatusIcon = ({ status }: { status: boolean | null }) => {
    if (status === null) return <span className="text-slate-600 text-xs">—</span>;
    return status ? <Check className="w-4 h-4 text-emerald-500" /> : <X className="w-4 h-4 text-slate-600" />;
  };

  const getVerificationBadge = (status: string) => {
    switch (status) {
      case 'CONFIRMED_VULNERABLE':
        return <span className="px-1.5 py-0.5 rounded text-[10px] font-medium bg-red-500/10 text-red-400">CONFIRMED</span>;
      case 'NOT_VULNERABLE':
        return <span className="px-1.5 py-0.5 rounded text-[10px] font-medium bg-emerald-500/10 text-emerald-400">SAFE</span>;
      case 'INCONCLUSIVE':
        return <span className="px-1.5 py-0.5 rounded text-[10px] font-medium bg-amber-500/10 text-amber-400">INCONCLUSIVE</span>;
      default:
        return <span className="px-1.5 py-0.5 rounded text-[10px] font-medium bg-slate-500/10 text-slate-500">NOT TESTED</span>;
    }
  };

  return (
    <motion.div initial="hidden" animate="visible" variants={stagger} className="space-y-6">
      <motion.div variants={fadeIn} className="flex flex-col sm:flex-row sm:items-center justify-between gap-4">
        <div>
          <h1 className="text-2xl font-bold text-white">Vulnerability Explorer</h1>
          <p className="text-sm text-slate-400 mt-1">Inspect individual endpoint analysis across the pipeline</p>
        </div>
        <div className="flex bg-slate-900/50 p-1 rounded-lg border border-slate-800 backdrop-blur-md">
          {['juice_shop', 'vuln-nodejs-app'].map(tab => (
            <button
              key={tab}
              onClick={() => setActiveTab(tab)}
              className={cn(
                "px-4 py-2 rounded-md text-sm font-medium transition-all",
                activeTab === tab
                  ? "bg-slate-800 text-slate-100 shadow-sm"
                  : "text-slate-400 hover:text-slate-200"
              )}
            >
              {tab === 'juice_shop' ? 'Juice Shop' : 'NodeJS App'}
            </button>
          ))}
        </div>
      </motion.div>

      <motion.div variants={fadeIn} className="grid grid-cols-1 md:grid-cols-4 gap-4">
        {[
          { label: 'Analyzed Routes', value: String(totalRoutes), icon: Eye, color: 'text-blue-400', bg: 'bg-blue-400/10' },
          { label: 'LLM Flagged', value: String(llmFlagged), icon: AlertTriangle, color: 'text-amber-400', bg: 'bg-amber-400/10' },
          { label: 'Dynamically Confirmed', value: String(dynamicallyConfirmed), icon: ShieldAlert, color: 'text-red-400', bg: 'bg-red-400/10' },
          { label: 'Ground Truth Vulnerable', value: String(gtVulnerable), icon: ShieldCheck, color: 'text-violet-400', bg: 'bg-violet-400/10' },
        ].map((stat, i) => (
          <div
            key={i}
            className="bg-slate-900/50 border border-slate-800 rounded-xl p-5 backdrop-blur-md flex items-center gap-4"
          >
            <div className={cn("p-3 rounded-lg", stat.bg)}>
              <stat.icon className={cn("w-6 h-6", stat.color)} />
            </div>
            <div>
              <p className="text-sm text-slate-400">{stat.label}</p>
              <p className="text-2xl font-bold text-slate-100">{loading ? '—' : stat.value}</p>
            </div>
          </div>
        ))}
      </motion.div>

      {/* Unmatched ground truth warning */}
      {!loading && unmatchedGT.length > 0 && (
        <motion.div variants={fadeIn} className="bg-amber-500/5 border border-amber-500/20 rounded-xl p-4 flex items-start gap-3">
          <AlertTriangle className="w-5 h-5 text-amber-400 mt-0.5 shrink-0" />
          <div>
            <p className="text-sm font-medium text-amber-300">
              {unmatchedGT.length} unmatched ground truth {unmatchedGT.length === 1 ? 'entry' : 'entries'}
            </p>
            <p className="text-xs text-slate-400 mt-1">
              These ground truth routes were not found by the static analyzer (coverage gap).
              Route IDs: {unmatchedGT.map(u => u.route_id).join(', ')}
            </p>
          </div>
        </motion.div>
      )}

      <motion.div variants={fadeIn} className="glass-card rounded-2xl overflow-hidden">
        <div className="p-4 border-b border-slate-800 flex items-center gap-4">
          <div className="relative flex-1 max-w-md">
            <Search className="absolute left-3 top-1/2 -translate-y-1/2 w-4 h-4 text-slate-400" />
            <input
              type="text"
              placeholder="Search endpoints..."
              value={search}
              onChange={(e) => setSearch(e.target.value)}
              className="w-full pl-9 pr-4 py-2 bg-slate-950 border border-slate-800 rounded-lg text-sm text-slate-200 focus:outline-none focus:ring-2 focus:ring-blue-500/50 transition-all"
            />
          </div>
          <span className="text-xs text-slate-500">{filteredData.length} result{filteredData.length !== 1 ? 's' : ''}</span>
        </div>

        {loading ? (
          <div className="flex items-center justify-center py-20">
            <Loader2 className="w-8 h-8 text-blue-400 animate-spin" />
          </div>
        ) : (
          <div className="overflow-x-auto">
            <table className="w-full text-left text-sm text-slate-300">
              <thead className="text-xs uppercase bg-slate-800/50 text-slate-400">
                <tr>
                  <th className="px-4 py-3 w-8"></th>
                  <th className="px-4 py-3">Endpoint</th>
                  <th className="px-4 py-3">Method</th>
                  <th className="px-4 py-3 text-center">Static</th>
                  <th className="px-4 py-3 text-center">LLM</th>
                  <th className="px-4 py-3 text-center">Verification</th>
                  <th className="px-4 py-3 text-center">Ground Truth</th>
                  <th className="px-4 py-3">Risk</th>
                </tr>
              </thead>
              <tbody className="divide-y divide-slate-800/50">
                {filteredData.map((row) => (
                  <React.Fragment key={row.route_id}>
                    <tr className="hover:bg-slate-800/30 transition-colors group">
                      <td className="px-4 py-3">
                        <button
                          onClick={() => setExpandedRow(expandedRow === row.route_id ? null : row.route_id)}
                          className="p-1 hover:bg-slate-700 rounded transition-colors text-slate-400"
                        >
                          {expandedRow === row.route_id ? <ChevronDown className="w-4 h-4" /> : <ChevronRight className="w-4 h-4" />}
                        </button>
                      </td>
                      <td className="px-4 py-3 font-mono text-slate-200 text-xs">{row.endpoint}</td>
                      <td className="px-4 py-3">
                        <span className={cn("px-2 py-1 rounded text-xs font-medium border", getMethodColor(row.http_method))}>
                          {row.http_method}
                        </span>
                      </td>
                      <td className="px-4 py-3 text-center"><div className="flex justify-center"><StatusIcon status={row.static_flagged} /></div></td>
                      <td className="px-4 py-3 text-center"><div className="flex justify-center"><StatusIcon status={row.llm_flagged} /></div></td>
                      <td className="px-4 py-3 text-center"><div className="flex justify-center">{getVerificationBadge(row.verification_status)}</div></td>
                      <td className="px-4 py-3 text-center"><div className="flex justify-center"><StatusIcon status={row.ground_truth} /></div></td>
                      <td className="px-4 py-3">
                        <span className={cn(
                          "px-2 py-1 rounded-full text-xs font-medium",
                          row.risk_level === 'high' ? "bg-red-500/10 text-red-400" :
                            row.risk_level === 'medium' ? "bg-amber-500/10 text-amber-400" :
                              "bg-emerald-500/10 text-emerald-400"
                        )}>
                          {row.risk_level}
                        </span>
                      </td>
                    </tr>
                    <AnimatePresence>
                      {expandedRow === row.route_id && (
                        <motion.tr
                          initial={{ opacity: 0, height: 0 }}
                          animate={{ opacity: 1, height: 'auto' }}
                          exit={{ opacity: 0, height: 0 }}
                        >
                          <td colSpan={8} className="px-12 py-4 bg-slate-900/30 border-b border-slate-800/50">
                            <div className="p-4 bg-slate-950 rounded-lg border border-slate-800 text-sm space-y-3">
                              <div className="flex flex-wrap items-center gap-4 text-xs text-slate-500">
                                <span>Route ID: <code className="text-slate-300">{row.route_id}</code></span>
                                <span>LLM Confidence: <code className="text-slate-300">{row.llm_confidence}</code></span>
                                <span>Verification: <code className="text-slate-300">{row.verification_status}</code></span>
                                <span>Final Verdict: <code className="text-slate-300">{row.final_verdict}</code></span>
                              </div>
                              <div>
                                <h4 className="font-semibold text-slate-300 mb-1">LLM Explanation</h4>
                                <p className="text-slate-400 text-xs leading-relaxed">{row.llm_explanation || 'No explanation available (route was not flagged by LLM).'}</p>
                              </div>
                            </div>
                          </td>
                        </motion.tr>
                      )}
                    </AnimatePresence>
                  </React.Fragment>
                ))}
              </tbody>
            </table>
          </div>
        )}
      </motion.div>
    </motion.div>
  );
}
