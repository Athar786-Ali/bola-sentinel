"use client";

import React from "react";
import { motion } from "framer-motion";
import { FileSearch, Bot, ShieldCheck, BarChart4, FileOutput, ArrowRight } from "lucide-react";
import { cn } from "@/lib/utils";

export type PipelineStage = "static_analysis" | "llm_classification" | "dynamic_verification" | "evaluation" | "reports";

interface PipelineVisualizerProps {
  activeStage?: PipelineStage;
  completedStages?: PipelineStage[];
}

const stages = [
  { id: "static_analysis", name: "Static Analysis", icon: FileSearch, desc: "Scanning OpenAPI" },
  { id: "llm_classification", name: "LLM Classification", icon: Bot, desc: "AI Filtering" },
  { id: "dynamic_verification", name: "Dynamic Verification", icon: ShieldCheck, desc: "Active Testing" },
  { id: "evaluation", name: "Evaluation", icon: BarChart4, desc: "Metrics Comp" },
  { id: "reports", name: "Reports", icon: FileOutput, desc: "Result Gen" },
] as const;

export function PipelineVisualizer({ activeStage, completedStages = [] }: PipelineVisualizerProps) {
  return (
    <div className="w-full py-8 overflow-x-auto">
      <div className="min-w-[800px] flex items-center justify-between px-4">
        {stages.map((stage, index) => {
          const Icon = stage.icon;
          const isActive = activeStage === stage.id;
          const isCompleted = completedStages.includes(stage.id as PipelineStage);
          const isPending = !isActive && !isCompleted;

          return (
            <React.Fragment key={stage.id}>
              {/* Node */}
              <div className="relative flex flex-col items-center z-10 w-32">
                <motion.div
                  initial={{ scale: 0.8, opacity: 0 }}
                  animate={{ scale: 1, opacity: 1 }}
                  transition={{ delay: index * 0.1 }}
                  className={cn(
                    "w-14 h-14 rounded-2xl flex items-center justify-center border-2 transition-all duration-500",
                    isActive ? "bg-blue-500/20 border-blue-500 text-blue-400 glow-blue scale-110" :
                    isCompleted ? "bg-green-500/20 border-green-500 text-green-400" :
                    "bg-slate-800 border-slate-700 text-slate-500"
                  )}
                >
                  <Icon className={cn("w-6 h-6", isActive && "animate-pulse")} />
                </motion.div>
                
                <div className="text-center mt-4">
                  <p className={cn(
                    "text-sm font-medium transition-colors duration-300",
                    isActive ? "text-blue-400" :
                    isCompleted ? "text-slate-200" :
                    "text-slate-500"
                  )}>
                    {stage.name}
                  </p>
                  <p className="text-xs text-slate-500 mt-1">{stage.desc}</p>
                </div>

                {/* Status indicator */}
                <div className="absolute -top-2 -right-2">
                  {isCompleted && (
                    <div className="w-5 h-5 rounded-full bg-green-500 border-2 border-slate-950 flex items-center justify-center">
                      <svg className="w-3 h-3 text-white" fill="none" viewBox="0 0 24 24" stroke="currentColor">
                        <path strokeLinecap="round" strokeLinejoin="round" strokeWidth={3} d="M5 13l4 4L19 7" />
                      </svg>
                    </div>
                  )}
                  {isActive && (
                    <span className="flex h-4 w-4 relative">
                      <span className="animate-ping absolute inline-flex h-full w-full rounded-full bg-blue-400 opacity-75"></span>
                      <span className="relative inline-flex rounded-full h-4 w-4 bg-blue-500 border-2 border-slate-950"></span>
                    </span>
                  )}
                </div>
              </div>

              {/* Connecting Line */}
              {index < stages.length - 1 && (
                <div className="flex-1 h-0.5 relative mx-2">
                  <div className="absolute inset-0 bg-slate-800 rounded-full" />
                  <motion.div 
                    className="absolute inset-y-0 left-0 bg-blue-500 rounded-full"
                    initial={{ width: "0%" }}
                    animate={{ width: isCompleted || (isActive && index > 0) ? "100%" : "0%" }}
                    transition={{ duration: 0.8, ease: "easeInOut" }}
                  />
                  {(isCompleted || (isActive && index > 0)) && (
                    <motion.div
                      initial={{ x: 0, opacity: 0 }}
                      animate={{ x: "100%", opacity: [0, 1, 0] }}
                      transition={{ repeat: Infinity, duration: 1.5, ease: "linear" }}
                      className="absolute inset-y-0 -ml-2 -mt-1"
                    >
                      <ArrowRight className="w-4 h-4 text-blue-400" />
                    </motion.div>
                  )}
                </div>
              )}
            </React.Fragment>
          );
        })}
      </div>
    </div>
  );
}
