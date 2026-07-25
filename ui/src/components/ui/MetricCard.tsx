"use client";

import React, { useEffect, useState } from "react";
import { motion, useAnimation } from "framer-motion";
import { LucideIcon } from "lucide-react";
import { cn } from "@/lib/utils";

interface MetricCardProps {
  title: string;
  value: string | number;
  subtitle?: string;
  icon: LucideIcon;
  trend?: {
    value: number;
    isPositive: boolean;
  };
  color?: "blue" | "green" | "purple" | "red" | "orange";
  className?: string;
}

export function MetricCard({
  title,
  value,
  subtitle,
  icon: Icon,
  trend,
  color = "blue",
  className
}: MetricCardProps) {
  const [displayValue, setDisplayValue] = useState(typeof value === 'number' ? 0 : value);

  useEffect(() => {
    if (typeof value === 'number') {
      let start = 0;
      const end = value;
      const duration = 1000;
      const incrementTime = (duration / end) * 5;
      
      const timer = setInterval(() => {
        start += 1;
        setDisplayValue(start);
        if (start === end) clearInterval(timer);
      }, incrementTime);
      
      return () => clearInterval(timer);
    } else {
      setDisplayValue(value);
    }
  }, [value]);

  const colorStyles = {
    blue: "text-blue-500 bg-blue-500/10 border-blue-500/20",
    green: "text-green-500 bg-green-500/10 border-green-500/20",
    purple: "text-purple-500 bg-purple-500/10 border-purple-500/20",
    red: "text-red-500 bg-red-500/10 border-red-500/20",
    orange: "text-orange-500 bg-orange-500/10 border-orange-500/20",
  };

  const glowStyles = {
    blue: "group-hover:shadow-[0_0_20px_rgba(59,130,246,0.15)]",
    green: "group-hover:shadow-[0_0_20px_rgba(34,197,94,0.15)]",
    purple: "group-hover:shadow-[0_0_20px_rgba(168,85,247,0.15)]",
    red: "group-hover:shadow-[0_0_20px_rgba(239,68,68,0.15)]",
    orange: "group-hover:shadow-[0_0_20px_rgba(249,115,22,0.15)]",
  };

  return (
    <motion.div
      initial={{ opacity: 0, y: 20 }}
      animate={{ opacity: 1, y: 0 }}
      whileHover={{ y: -4 }}
      transition={{ duration: 0.3 }}
      className={cn(
        "glass-card p-6 rounded-xl border border-slate-800 group transition-all duration-300",
        glowStyles[color],
        className
      )}
    >
      <div className="flex justify-between items-start mb-4">
        <div>
          <p className="text-sm font-medium text-slate-400 mb-1">{title}</p>
          <motion.h3 
            className="text-3xl font-bold text-white tracking-tight"
            key={String(value)}
            initial={{ scale: 0.8, opacity: 0 }}
            animate={{ scale: 1, opacity: 1 }}
            transition={{ type: "spring", stiffness: 200, damping: 10 }}
          >
            {displayValue}
          </motion.h3>
        </div>
        <div className={cn("p-3 rounded-lg border", colorStyles[color])}>
          <Icon className="w-5 h-5" />
        </div>
      </div>
      
      {(subtitle || trend) && (
        <div className="flex items-center gap-2 mt-4 text-sm">
          {trend && (
            <span className={cn(
              "font-medium px-2 py-0.5 rounded-full bg-slate-900 border",
              trend.isPositive ? "text-green-400 border-green-500/20" : "text-red-400 border-red-500/20"
            )}>
              {trend.isPositive ? "+" : "-"}{trend.value}%
            </span>
          )}
          {subtitle && <span className="text-slate-500">{subtitle}</span>}
        </div>
      )}
    </motion.div>
  );
}
