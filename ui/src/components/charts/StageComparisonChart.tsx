"use client";

import React from "react";
import {
  BarChart,
  Bar,
  XAxis,
  YAxis,
  CartesianGrid,
  Tooltip,
  Legend,
  ResponsiveContainer
} from "recharts";

interface DataPoint {
  stage: string;
  TP: number;
  FP: number;
  FN: number;
  TN: number;
}

interface StageComparisonChartProps {
  data: DataPoint[];
}

export function StageComparisonChart({ data }: StageComparisonChartProps) {
  return (
    <div className="w-full h-80 text-sm">
      <ResponsiveContainer width="100%" height="100%">
        <BarChart
          data={data}
          margin={{ top: 20, right: 30, left: 0, bottom: 5 }}
        >
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
            cursor={{ fill: "rgba(30, 41, 59, 0.4)" }}
            contentStyle={{ 
              backgroundColor: "rgba(15, 23, 42, 0.8)", 
              backdropFilter: "blur(8px)",
              borderColor: "#334155",
              borderRadius: "0.5rem",
              color: "#f8fafc"
            }}
          />
          <Legend wrapperStyle={{ paddingTop: "10px" }} />
          <Bar dataKey="TP" name="True Positives" fill="#22c55e" radius={[4, 4, 0, 0]} />
          <Bar dataKey="FP" name="False Positives" fill="#ef4444" radius={[4, 4, 0, 0]} />
          <Bar dataKey="FN" name="False Negatives" fill="#f97316" radius={[4, 4, 0, 0]} />
          <Bar dataKey="TN" name="True Negatives" fill="#3b82f6" radius={[4, 4, 0, 0]} />
        </BarChart>
      </ResponsiveContainer>
    </div>
  );
}
