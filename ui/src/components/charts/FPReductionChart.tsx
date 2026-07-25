"use client";

import React, { useEffect, useState } from "react";
import {
  AreaChart,
  Area,
  XAxis,
  YAxis,
  CartesianGrid,
  Tooltip,
  ResponsiveContainer
} from "recharts";

interface FPData {
  stage: string;
  falsePositives: number;
}

interface FPReductionChartProps {
  data: FPData[];
}

export function FPReductionChart({ data }: FPReductionChartProps) {
  const [mounted, setMounted] = useState(false);

  useEffect(() => {
    setMounted(true);
  }, []);

  if (!mounted) return <div className="w-full h-[300px] bg-slate-900/20 animate-pulse rounded-lg" />;

  return (
    <div className="w-full h-[300px] text-sm">
      <ResponsiveContainer width="100%" height="100%">
        <AreaChart
          data={data}
          margin={{ top: 10, right: 30, left: 0, bottom: 0 }}
        >
          <defs>
            <linearGradient id="colorFp" x1="0" y1="0" x2="0" y2="1">
              <stop offset="5%" stopColor="#ef4444" stopOpacity={0.4}/>
              <stop offset="95%" stopColor="#ef4444" stopOpacity={0}/>
            </linearGradient>
          </defs>
          <CartesianGrid strokeDasharray="3 3" stroke="#1e293b" vertical={false} />
          <XAxis 
            dataKey="stage" 
            stroke="#64748b" 
            tick={{ fill: "#94a3b8" }} 
            tickLine={false}
            axisLine={{ stroke: "#334155" }}
          />
          <YAxis 
            stroke="#64748b" 
            tick={{ fill: "#94a3b8" }} 
            tickLine={false}
            axisLine={{ stroke: "#334155" }}
          />
          <Tooltip 
            cursor={{ stroke: "#475569", strokeWidth: 1, strokeDasharray: "3 3" }}
            contentStyle={{ 
              backgroundColor: "rgba(15, 23, 42, 0.8)", 
              backdropFilter: "blur(8px)",
              borderColor: "#334155",
              borderRadius: "0.5rem",
              color: "#f8fafc"
            }}
          />
          <Area 
            type="monotone" 
            dataKey="falsePositives" 
            stroke="#ef4444" 
            strokeWidth={3}
            fillOpacity={1} 
            fill="url(#colorFp)" 
            animationDuration={1500}
            name="False Positives"
          />
        </AreaChart>
      </ResponsiveContainer>
    </div>
  );
}
