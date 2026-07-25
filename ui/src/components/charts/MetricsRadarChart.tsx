"use client";

import React from "react";
import {
  Radar,
  RadarChart,
  PolarGrid,
  PolarAngleAxis,
  PolarRadiusAxis,
  ResponsiveContainer,
  Tooltip,
  Legend
} from "recharts";

interface RadarDataPoint {
  metric: string;
  [key: string]: string | number; // allow app names as keys
}

interface MetricsRadarChartProps {
  data: RadarDataPoint[];
  dataKeys: string[];
  colors?: string[];
}

const DEFAULT_COLORS = ["#3b82f6", "#8b5cf6", "#ec4899", "#10b981", "#f59e0b"];

export function MetricsRadarChart({ data, dataKeys, colors = DEFAULT_COLORS }: MetricsRadarChartProps) {
  return (
    <div className="w-full h-[400px] text-sm">
      <ResponsiveContainer width="100%" height="100%">
        <RadarChart cx="50%" cy="50%" outerRadius="70%" data={data}>
          <PolarGrid stroke="#334155" />
          <PolarAngleAxis dataKey="metric" tick={{ fill: "#94a3b8", fontSize: 12 }} />
          <PolarRadiusAxis angle={30} domain={[0, 100]} tick={{ fill: "#64748b" }} />
          
          <Tooltip
            contentStyle={{ 
              backgroundColor: "rgba(15, 23, 42, 0.8)", 
              backdropFilter: "blur(8px)",
              borderColor: "#334155",
              borderRadius: "0.5rem",
              color: "#f8fafc"
            }}
          />
          <Legend />
          
          {dataKeys.map((key, index) => (
            <Radar
              key={key}
              name={key}
              dataKey={key}
              stroke={colors[index % colors.length]}
              fill={colors[index % colors.length]}
              fillOpacity={0.3}
            />
          ))}
        </RadarChart>
      </ResponsiveContainer>
    </div>
  );
}
