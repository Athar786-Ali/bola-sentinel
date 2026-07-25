'use client';
import { useState } from 'react';
import { motion, AnimatePresence } from 'framer-motion';
import { Database, Search, Cpu, Activity, CheckCircle, FileText, ChevronRight, X } from 'lucide-react';
import { cn } from '@/lib/utils';

const fadeIn = { hidden: { opacity: 0, y: 20 }, visible: { opacity: 1, y: 0 } };
const stagger = { visible: { transition: { staggerChildren: 0.08 } }, hidden: {} };

const stages = [
  { id: 'repo', title: 'Repository', description: 'Ingest OpenAPI specs and source code.', icon: Database, color: 'text-blue-400', bg: 'bg-blue-400/10' },
  { id: 'static', title: 'Static Analyzer', description: 'Parse code to extract AST and endpoint graphs.', icon: Search, color: 'text-indigo-400', bg: 'bg-indigo-400/10' },
  { id: 'llm', title: 'LLM Agent', description: 'Generate intelligent test cases for BOLA.', icon: Cpu, color: 'text-purple-400', bg: 'bg-purple-400/10' },
  { id: 'dynamic', title: 'Dynamic Verification', description: 'Execute tests against live instances.', icon: Activity, color: 'text-pink-400', bg: 'bg-pink-400/10' },
  { id: 'eval', title: 'Evaluation', description: 'Compare findings against ground truth.', icon: CheckCircle, color: 'text-emerald-400', bg: 'bg-emerald-400/10' },
  { id: 'report', title: 'Reports', description: 'Generate comprehensive security metrics.', icon: FileText, color: 'text-amber-400', bg: 'bg-amber-400/10' }
];

export default function ArchitecturePage() {
  const [selectedNode, setSelectedNode] = useState<string | null>(null);
  
  const selectedStage = stages.find(s => s.id === selectedNode);

  return (
    <div className="p-8 max-w-6xl mx-auto space-y-8 min-h-screen">
      <motion.div initial="hidden" animate="visible" variants={stagger} className="space-y-2">
        <motion.h1 variants={fadeIn} className="text-3xl font-bold text-white tracking-tight">System Architecture</motion.h1>
        <motion.p variants={fadeIn} className="text-slate-400">Interactive pipeline diagram for BOLA-Sentinel.</motion.p>
      </motion.div>

      <div className="relative">
        <motion.div initial="hidden" animate="visible" variants={stagger} className="grid grid-cols-1 md:grid-cols-2 lg:grid-cols-3 gap-8">
          {stages.map((stage, idx) => (
            <motion.div 
              key={stage.id}
              variants={fadeIn}
              onClick={() => setSelectedNode(stage.id)}
              className={cn(
                "relative group cursor-pointer p-6 rounded-xl border border-slate-800 bg-slate-900/50 backdrop-blur-md transition-all duration-300",
                "hover:border-slate-700 hover:shadow-lg hover:shadow-slate-900/50 hover:scale-[1.02]",
                selectedNode === stage.id ? "ring-2 ring-slate-600" : ""
              )}
            >
              <div className="flex items-start justify-between">
                <div className={cn("p-3 rounded-lg", stage.bg)}>
                  <stage.icon className={cn("w-6 h-6", stage.color)} />
                </div>
                <div className="text-4xl font-black text-slate-800/50 group-hover:text-slate-800 transition-colors">0{idx + 1}</div>
              </div>
              <h3 className="mt-4 text-xl font-semibold text-slate-200">{stage.title}</h3>
              <p className="mt-2 text-sm text-slate-400">{stage.description}</p>
              
              {/* Connector Lines for Desktop */}
              {idx < stages.length - 1 && (
                <div className="hidden lg:block absolute top-1/2 -right-4 w-8 h-[2px] bg-slate-800 group-hover:bg-slate-600 transition-colors z-0">
                  <div className="absolute right-0 top-1/2 -translate-y-1/2 translate-x-1/2 w-2 h-2 rounded-full bg-slate-700" />
                </div>
              )}
            </motion.div>
          ))}
        </motion.div>
      </div>

      <AnimatePresence>
        {selectedStage && (
          <motion.div 
            initial={{ opacity: 0, y: 20 }}
            animate={{ opacity: 1, y: 0 }}
            exit={{ opacity: 0, y: 20 }}
            className="fixed bottom-8 left-1/2 -translate-x-1/2 w-full max-w-2xl bg-slate-900/95 border border-slate-700 p-6 rounded-2xl shadow-2xl backdrop-blur-xl z-50"
          >
            <div className="flex justify-between items-start mb-4">
              <div className="flex items-center gap-4">
                <div className={cn("p-3 rounded-lg", selectedStage.bg)}>
                  <selectedStage.icon className={cn("w-6 h-6", selectedStage.color)} />
                </div>
                <div>
                  <h3 className="text-xl font-bold text-white">{selectedStage.title}</h3>
                  <p className="text-slate-400">Pipeline Stage Details</p>
                </div>
              </div>
              <button onClick={() => setSelectedNode(null)} className="p-2 hover:bg-slate-800 rounded-full transition-colors text-slate-400 hover:text-white">
                <X className="w-5 h-5" />
              </button>
            </div>
            <div className="space-y-4">
              <div className="bg-slate-950 p-4 rounded-lg border border-slate-800">
                <p className="text-slate-300 leading-relaxed">
                  {selectedStage.description} This stage represents a critical component in the BOLA-Sentinel architecture, ensuring robust API security testing.
                </p>
              </div>
            </div>
          </motion.div>
        )}
      </AnimatePresence>
    </div>
  );
}
