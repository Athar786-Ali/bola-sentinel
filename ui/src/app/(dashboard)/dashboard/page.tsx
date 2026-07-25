"use client";

import { useEffect, useState } from "react";
import { motion } from "framer-motion";
import {
  Shield,
  Target,
  AlertTriangle,
  CheckCircle2,
  XCircle,
  TrendingDown,
  Activity,
  Database,
  Crosshair,
  Eye,
} from "lucide-react";
import type { BenchmarkSummary } from "@/lib/types";
import { formatPercent, formatDecimal } from "@/lib/utils";

const fadeIn = {
  hidden: { opacity: 0, y: 20 },
  visible: { opacity: 1, y: 0 },
};

const stagger = {
  visible: { transition: { staggerChildren: 0.06 } },
};

interface MetricCardProps {
  title: string;
  value: string;
  subtitle?: string;
  icon: React.ElementType;
  color: string;
  bgColor: string;
  delay?: number;
}

function MetricCard({ title, value, subtitle, icon: Icon, color, bgColor }: MetricCardProps) {
  return (
    <motion.div
      variants={fadeIn}
      whileHover={{ y: -2, transition: { duration: 0.2 } }}
      className="glass-card rounded-2xl p-5 group cursor-default"
    >
      <div className="flex items-start justify-between mb-3">
        <div className={`w-10 h-10 rounded-xl ${bgColor} flex items-center justify-center`}>
          <Icon className={`w-5 h-5 ${color}`} />
        </div>
      </div>
      <div className={`text-2xl font-bold ${color} mb-0.5`}>{value}</div>
      <div className="text-sm text-slate-400">{title}</div>
      {subtitle && <div className="text-xs text-slate-500 mt-1">{subtitle}</div>}
    </motion.div>
  );
}

function StageTable({ data }: { data: BenchmarkSummary }) {
  const pooled = data.pooled_overall_results;
  const stages = [
    { key: "stage_1_static_only", label: "Stage 1 — Static Analysis", metrics: pooled.stage_1_static_only },
    { key: "stage_2_static_plus_llm", label: "Stage 2 — Static + LLM", metrics: pooled.stage_2_static_plus_llm },
    { key: "stage_3_final_system", label: "Stage 3 — Full Pipeline", metrics: pooled.stage_3_final_system },
  ];

  return (
    <motion.div variants={fadeIn} className="glass-card rounded-2xl p-6">
      <h3 className="text-lg font-semibold text-white mb-4">Stage-wise Metrics (Pooled)</h3>
      <div className="overflow-x-auto">
        <table className="w-full text-sm">
          <thead>
            <tr className="text-slate-400 border-b border-slate-800">
              <th className="text-left py-3 px-3 font-medium">Stage</th>
              <th className="text-center py-3 px-2 font-medium">TP</th>
              <th className="text-center py-3 px-2 font-medium">FP</th>
              <th className="text-center py-3 px-2 font-medium">FN</th>
              <th className="text-center py-3 px-2 font-medium">TN</th>
              <th className="text-center py-3 px-2 font-medium">Precision</th>
              <th className="text-center py-3 px-2 font-medium">Recall</th>
              <th className="text-center py-3 px-2 font-medium">F1</th>
              <th className="text-center py-3 px-2 font-medium">FPR</th>
            </tr>
          </thead>
          <tbody>
            {stages.map((s, i) => (
              <tr key={s.key} className="border-b border-slate-800/50 hover:bg-slate-800/30 transition-colors">
                <td className="py-3 px-3 text-white font-medium">{s.label}</td>
                <td className="text-center py-3 px-2 text-emerald-400">{s.metrics.tp}</td>
                <td className="text-center py-3 px-2 text-red-400">{s.metrics.fp}</td>
                <td className="text-center py-3 px-2 text-amber-400">{s.metrics.fn}</td>
                <td className="text-center py-3 px-2 text-slate-300">{s.metrics.tn}</td>
                <td className="text-center py-3 px-2 text-slate-300">{formatDecimal(s.metrics.precision)}</td>
                <td className="text-center py-3 px-2 text-slate-300">{formatDecimal(s.metrics.recall)}</td>
                <td className="text-center py-3 px-2 text-slate-300">{formatDecimal(s.metrics.f1)}</td>
                <td className="text-center py-3 px-2 text-slate-300">{formatPercent(s.metrics.false_positive_rate)}</td>
              </tr>
            ))}
          </tbody>
        </table>
      </div>
    </motion.div>
  );
}

function AppComparisonCards({ data }: { data: BenchmarkSummary }) {
  return (
    <motion.div variants={fadeIn} className="glass-card rounded-2xl p-6">
      <h3 className="text-lg font-semibold text-white mb-4">Application Comparison</h3>
      <div className="grid md:grid-cols-2 gap-4">
        {Object.entries(data.per_application_results).map(([appName, metrics]) => (
          <div key={appName} className="bg-slate-800/30 rounded-xl p-4 border border-slate-700/30">
            <div className="flex items-center gap-2 mb-3">
              <Database className="w-4 h-4 text-blue-400" />
              <h4 className="text-sm font-semibold text-white">{appName}</h4>
            </div>
            <div className="grid grid-cols-3 gap-3 text-center">
              <div>
                <div className="text-lg font-bold text-blue-400">{formatPercent(metrics.coverage)}</div>
                <div className="text-[10px] text-slate-500">Coverage</div>
              </div>
              <div>
                <div className="text-lg font-bold text-emerald-400">{metrics.ground_truth_size}</div>
                <div className="text-[10px] text-slate-500">GT Routes</div>
              </div>
              <div>
                <div className="text-lg font-bold text-violet-400">{metrics.fp_reduction_stage1_to_stage3_total}</div>
                <div className="text-[10px] text-slate-500">FP Removed</div>
              </div>
            </div>
          </div>
        ))}
      </div>
    </motion.div>
  );
}

export default function DashboardPage() {
  const [data, setData] = useState<BenchmarkSummary | null>(null);
  const [loading, setLoading] = useState(true);

  useEffect(() => {
    fetch("/api/metrics")
      .then((r) => r.json())
      .then((d) => { setData(d); setLoading(false); })
      .catch(() => setLoading(false));
  }, []);

  if (loading) {
    return (
      <div className="space-y-6">
        <div className="h-8 w-48 bg-slate-800 rounded-lg animate-pulse" />
        <div className="grid grid-cols-2 md:grid-cols-3 lg:grid-cols-5 gap-4">
          {Array.from({ length: 10 }).map((_, i) => (
            <div key={i} className="glass-card rounded-2xl p-5 h-32 animate-pulse" />
          ))}
        </div>
      </div>
    );
  }

  if (!data) {
    return (
      <div className="flex items-center justify-center h-[60vh]">
        <div className="text-center">
          <AlertTriangle className="w-12 h-12 text-amber-400 mx-auto mb-4" />
          <h2 className="text-xl font-semibold text-white mb-2">No Benchmark Data</h2>
          <p className="text-slate-400">Run a benchmark first to see results here.</p>
        </div>
      </div>
    );
  }

  const pooled = data.pooled_overall_results;
  const s3 = pooled.stage_3_final_system;
  const totalRoutes = s3.tp + s3.fp + s3.fn + s3.tn;

  return (
    <motion.div
      className="space-y-6"
      initial="hidden"
      animate="visible"
      variants={stagger}
    >
      {/* Page Header */}
      <motion.div variants={fadeIn}>
        <h1 className="text-2xl font-bold text-white mb-1">System Overview</h1>
        <p className="text-sm text-slate-400">
          Last benchmark: {data.run_timestamp} · {data.applications_tested.length} application(s)
        </p>
      </motion.div>

      {/* Metric Cards */}
      <div className="grid grid-cols-2 md:grid-cols-3 lg:grid-cols-5 gap-4">
        <MetricCard
          title="Applications Tested"
          value={String(data.applications_tested.length)}
          subtitle={data.applications_tested.join(", ")}
          icon={Database}
          color="text-blue-400"
          bgColor="bg-blue-500/10"
        />
        <MetricCard
          title="Routes Analyzed"
          value={String(totalRoutes)}
          subtitle={`${s3.evaluated} evaluated`}
          icon={Target}
          color="text-violet-400"
          bgColor="bg-violet-500/10"
        />
        <MetricCard
          title="FP Removed"
          value={String(pooled.fp_reduction_stage1_to_stage3_total)}
          subtitle="Stage 1 → Stage 3"
          icon={TrendingDown}
          color="text-emerald-400"
          bgColor="bg-emerald-500/10"
        />
        <MetricCard
          title="True Positives"
          value={String(s3.tp)}
          subtitle="Confirmed BOLA"
          icon={CheckCircle2}
          color="text-green-400"
          bgColor="bg-green-500/10"
        />
        <MetricCard
          title="False Positives"
          value={String(s3.fp)}
          subtitle="After full pipeline"
          icon={XCircle}
          color="text-red-400"
          bgColor="bg-red-500/10"
        />
        <MetricCard
          title="Precision"
          value={formatDecimal(s3.precision)}
          icon={Crosshair}
          color="text-cyan-400"
          bgColor="bg-cyan-500/10"
        />
        <MetricCard
          title="Recall"
          value={formatDecimal(s3.recall)}
          icon={Eye}
          color="text-amber-400"
          bgColor="bg-amber-500/10"
        />
        <MetricCard
          title="F1 Score"
          value={formatDecimal(s3.f1)}
          icon={Activity}
          color="text-pink-400"
          bgColor="bg-pink-500/10"
        />
        <MetricCard
          title="FPR"
          value={formatPercent(s3.false_positive_rate)}
          subtitle="False Positive Rate"
          icon={AlertTriangle}
          color="text-orange-400"
          bgColor="bg-orange-500/10"
        />
        <MetricCard
          title="Pipeline Status"
          value={data.applications_failed.length === 0 ? "Healthy" : "Issues"}
          subtitle={`${data.applications_successful.length} succeeded`}
          icon={Shield}
          color={data.applications_failed.length === 0 ? "text-emerald-400" : "text-red-400"}
          bgColor={data.applications_failed.length === 0 ? "bg-emerald-500/10" : "bg-red-500/10"}
        />
      </div>

      {/* Stage Table + App Comparison */}
      <div className="grid lg:grid-cols-3 gap-6">
        <div className="lg:col-span-2">
          <StageTable data={data} />
        </div>
        <div>
          <AppComparisonCards data={data} />
        </div>
      </div>

      {/* FP Reduction Summary */}
      <motion.div variants={fadeIn} className="glass-card rounded-2xl p-6">
        <h3 className="text-lg font-semibold text-white mb-4">False-Positive Reduction</h3>
        <div className="grid md:grid-cols-3 gap-4">
          <div className="bg-slate-800/30 rounded-xl p-4 text-center border border-slate-700/30">
            <div className="text-sm text-slate-400 mb-1">Stage 1 → Stage 2</div>
            <div className="text-3xl font-bold text-blue-400">
              -{pooled.fp_reduction_stage1_to_stage2}
            </div>
            <div className="text-xs text-slate-500 mt-1">Adding LLM reasoning</div>
          </div>
          <div className="bg-slate-800/30 rounded-xl p-4 text-center border border-slate-700/30">
            <div className="text-sm text-slate-400 mb-1">Stage 2 → Stage 3</div>
            <div className="text-3xl font-bold text-violet-400">
              -{pooled.fp_reduction_stage2_to_stage3}
            </div>
            <div className="text-xs text-slate-500 mt-1">Adding dynamic verification</div>
          </div>
          <div className="bg-slate-800/30 rounded-xl p-4 text-center border border-emerald-500/20">
            <div className="text-sm text-slate-400 mb-1">Total Reduction</div>
            <div className="text-3xl font-bold text-emerald-400">
              -{pooled.fp_reduction_stage1_to_stage3_total}
            </div>
            <div className="text-xs text-slate-500 mt-1">Full pipeline impact</div>
          </div>
        </div>
      </motion.div>
    </motion.div>
  );
}
