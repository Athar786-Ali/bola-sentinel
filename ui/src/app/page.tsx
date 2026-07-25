"use client";

import { motion } from "framer-motion";
import {
  Shield,
  ArrowRight,
  Zap,
  Brain,
  Search,
  BarChart3,
  GitBranch,
  Database,
  CheckCircle2,
  ChevronDown,
} from "lucide-react";
import Link from "next/link";

const fadeIn = {
  hidden: { opacity: 0, y: 20 },
  visible: { opacity: 1, y: 0 },
};

const stagger = {
  visible: { transition: { staggerChildren: 0.1 } },
};

function HeroSection() {
  return (
    <section className="relative min-h-screen flex items-center justify-center overflow-hidden">
      {/* Animated background */}
      <div className="absolute inset-0 animated-gradient" />
      <div className="absolute inset-0 bg-[radial-gradient(ellipse_at_center,rgba(59,130,246,0.08),transparent_70%)]" />

      {/* Grid pattern overlay */}
      <div
        className="absolute inset-0 opacity-[0.03]"
        style={{
          backgroundImage: `linear-gradient(rgba(255,255,255,0.1) 1px, transparent 1px),
                           linear-gradient(90deg, rgba(255,255,255,0.1) 1px, transparent 1px)`,
          backgroundSize: "60px 60px",
        }}
      />

      <motion.div
        className="relative z-10 max-w-5xl mx-auto px-6 text-center"
        initial="hidden"
        animate="visible"
        variants={stagger}
      >
        <motion.div variants={fadeIn} className="mb-6">
          <span className="inline-flex items-center gap-2 px-4 py-1.5 rounded-full glass text-sm text-blue-300 border border-blue-500/20">
            <span className="w-2 h-2 rounded-full bg-emerald-400 animate-pulse-dot" />
            Research-Grade Security Analysis
          </span>
        </motion.div>

        <motion.div variants={fadeIn} className="flex items-center justify-center gap-4 mb-6">
          <Shield className="w-14 h-14 text-blue-400" strokeWidth={1.5} />
          <h1 className="text-6xl md:text-7xl font-bold tracking-tight">
            <span className="gradient-text">BOLA</span>
            <span className="text-slate-300">-Sentinel</span>
          </h1>
        </motion.div>

        <motion.p
          variants={fadeIn}
          className="text-xl md:text-2xl text-slate-400 max-w-3xl mx-auto mb-4 leading-relaxed"
        >
          Automated detection of Broken Object Level Authorization vulnerabilities
          through{" "}
          <span className="text-blue-400">static analysis</span>,{" "}
          <span className="text-violet-400">LLM reasoning</span>, and{" "}
          <span className="text-emerald-400">dynamic verification</span>.
        </motion.p>

        <motion.p
          variants={fadeIn}
          className="text-base text-slate-500 max-w-2xl mx-auto mb-10"
        >
          A multi-stage pipeline that reduces false positives by combining code
          pattern detection with AI-powered contextual analysis and runtime
          behavioral verification.
        </motion.p>

        <motion.div variants={fadeIn} className="flex items-center justify-center gap-4">
          <Link
            href="/dashboard"
            className="inline-flex items-center gap-2 px-8 py-3.5 rounded-xl bg-blue-600 hover:bg-blue-500 text-white font-medium transition-all duration-200 hover:shadow-lg hover:shadow-blue-500/20"
          >
            Open Dashboard
            <ArrowRight className="w-4 h-4" />
          </Link>
          <Link
            href="/benchmark"
            className="inline-flex items-center gap-2 px-8 py-3.5 rounded-xl glass hover:bg-slate-800/50 text-slate-300 font-medium transition-all duration-200"
          >
            Run Benchmark
          </Link>
        </motion.div>

        <motion.div variants={fadeIn} className="mt-16">
          <ChevronDown className="w-6 h-6 text-slate-500 mx-auto animate-bounce" />
        </motion.div>
      </motion.div>
    </section>
  );
}

const pipelineSteps = [
  {
    icon: Search,
    title: "Static Analysis",
    desc: "AST-based route extraction and authorization pattern detection across JavaScript and Python codebases.",
    color: "text-blue-400",
    borderColor: "border-blue-500/30",
    glowColor: "glow-blue",
  },
  {
    icon: Brain,
    title: "LLM Classification",
    desc: "Contextual vulnerability reasoning using large language models to filter false positives with semantic understanding.",
    color: "text-violet-400",
    borderColor: "border-violet-500/30",
    glowColor: "glow-purple",
  },
  {
    icon: Zap,
    title: "Dynamic Verification",
    desc: "Runtime behavioral testing against live application instances to confirm exploitability of flagged endpoints.",
    color: "text-emerald-400",
    borderColor: "border-emerald-500/30",
    glowColor: "glow-green",
  },
  {
    icon: BarChart3,
    title: "Evaluation & Reporting",
    desc: "Confusion matrix computation, stage-wise metrics, and reproducible benchmark reports with full audit trail.",
    color: "text-cyan-400",
    borderColor: "border-cyan-500/30",
    glowColor: "glow-blue",
  },
];

function PipelineSection() {
  return (
    <section className="py-24 px-6 relative">
      <div className="max-w-6xl mx-auto">
        <motion.div
          className="text-center mb-16"
          initial="hidden"
          whileInView="visible"
          viewport={{ once: true }}
          variants={stagger}
        >
          <motion.h2
            variants={fadeIn}
            className="text-3xl md:text-4xl font-bold text-white mb-4"
          >
            Multi-Stage Detection Pipeline
          </motion.h2>
          <motion.p variants={fadeIn} className="text-slate-400 max-w-2xl mx-auto">
            Each stage progressively refines detection accuracy, dramatically
            reducing false positives while maintaining recall.
          </motion.p>
        </motion.div>

        <motion.div
          className="grid md:grid-cols-2 lg:grid-cols-4 gap-6"
          initial="hidden"
          whileInView="visible"
          viewport={{ once: true }}
          variants={stagger}
        >
          {pipelineSteps.map((step, i) => (
            <motion.div
              key={step.title}
              variants={fadeIn}
              whileHover={{ y: -4, transition: { duration: 0.2 } }}
              className={`relative glass-card rounded-2xl p-6 ${step.borderColor} ${step.glowColor}`}
            >
              {i < pipelineSteps.length - 1 && (
                <div className="hidden lg:block absolute top-1/2 -right-3 w-6 h-px bg-slate-600 z-10" />
              )}
              <step.icon className={`w-10 h-10 ${step.color} mb-4`} strokeWidth={1.5} />
              <h3 className="text-lg font-semibold text-white mb-2">{step.title}</h3>
              <p className="text-sm text-slate-400 leading-relaxed">{step.desc}</p>
            </motion.div>
          ))}
        </motion.div>
      </div>
    </section>
  );
}

const features = [
  {
    icon: Database,
    title: "Multi-Application Benchmarking",
    desc: "Test against multiple target applications with a unified evaluation framework. Currently supports vuln-nodejs-app and OWASP Juice Shop.",
  },
  {
    icon: GitBranch,
    title: "Reproducible Research",
    desc: "Every benchmark run is logged with git commits, model versions, dataset versions, and full audit trails for scientific reproducibility.",
  },
  {
    icon: BarChart3,
    title: "Stage-Wise Evaluation",
    desc: "Independent metrics at each pipeline stage reveal exactly how much each component contributes to detection accuracy.",
  },
  {
    icon: CheckCircle2,
    title: "Ground Truth Validation",
    desc: "Expert-reviewed ground truth labels with confidence scores, CWE mappings, and detailed rationale for every classification.",
  },
];

function FeaturesSection() {
  return (
    <section className="py-24 px-6 relative bg-slate-950/50">
      <div className="max-w-6xl mx-auto">
        <motion.div
          className="text-center mb-16"
          initial="hidden"
          whileInView="visible"
          viewport={{ once: true }}
          variants={stagger}
        >
          <motion.h2
            variants={fadeIn}
            className="text-3xl md:text-4xl font-bold text-white mb-4"
          >
            Enterprise Features
          </motion.h2>
          <motion.p variants={fadeIn} className="text-slate-400 max-w-2xl mx-auto">
            Built for research rigor with production-grade engineering.
          </motion.p>
        </motion.div>

        <motion.div
          className="grid md:grid-cols-2 gap-6"
          initial="hidden"
          whileInView="visible"
          viewport={{ once: true }}
          variants={stagger}
        >
          {features.map((feat) => (
            <motion.div
              key={feat.title}
              variants={fadeIn}
              whileHover={{ scale: 1.01, transition: { duration: 0.2 } }}
              className="glass-card rounded-2xl p-6 flex gap-4"
            >
              <div className="flex-shrink-0">
                <div className="w-12 h-12 rounded-xl bg-blue-500/10 flex items-center justify-center">
                  <feat.icon className="w-6 h-6 text-blue-400" />
                </div>
              </div>
              <div>
                <h3 className="text-lg font-semibold text-white mb-1">{feat.title}</h3>
                <p className="text-sm text-slate-400 leading-relaxed">{feat.desc}</p>
              </div>
            </motion.div>
          ))}
        </motion.div>
      </div>
    </section>
  );
}

function StatsSection() {
  const stats = [
    { label: "Routes Analyzed", value: "66", suffix: "+" },
    { label: "FP Reduction", value: "56", suffix: "" },
    { label: "Benchmark Apps", value: "2", suffix: "" },
    { label: "Pipeline Stages", value: "4", suffix: "" },
  ];

  return (
    <section className="py-20 px-6">
      <motion.div
        className="max-w-4xl mx-auto grid grid-cols-2 md:grid-cols-4 gap-8"
        initial="hidden"
        whileInView="visible"
        viewport={{ once: true }}
        variants={stagger}
      >
        {stats.map((stat) => (
          <motion.div key={stat.label} variants={fadeIn} className="text-center">
            <div className="text-4xl md:text-5xl font-bold gradient-text mb-2">
              {stat.value}
              {stat.suffix}
            </div>
            <div className="text-sm text-slate-400">{stat.label}</div>
          </motion.div>
        ))}
      </motion.div>
    </section>
  );
}

function CTASection() {
  return (
    <section className="py-24 px-6">
      <motion.div
        className="max-w-3xl mx-auto text-center"
        initial="hidden"
        whileInView="visible"
        viewport={{ once: true }}
        variants={stagger}
      >
        <motion.h2
          variants={fadeIn}
          className="text-3xl md:text-4xl font-bold text-white mb-4"
        >
          Ready to analyze your APIs?
        </motion.h2>
        <motion.p variants={fadeIn} className="text-slate-400 mb-8">
          Open the dashboard to explore benchmark results, run new analyses, and
          visualize vulnerability findings.
        </motion.p>
        <motion.div variants={fadeIn}>
          <Link
            href="/dashboard"
            className="inline-flex items-center gap-2 px-10 py-4 rounded-xl bg-gradient-to-r from-blue-600 to-violet-600 hover:from-blue-500 hover:to-violet-500 text-white font-semibold text-lg transition-all duration-300 hover:shadow-xl hover:shadow-blue-500/20"
          >
            Open Dashboard
            <ArrowRight className="w-5 h-5" />
          </Link>
        </motion.div>
      </motion.div>
    </section>
  );
}

function Footer() {
  return (
    <footer className="border-t border-slate-800 py-8 px-6">
      <div className="max-w-6xl mx-auto flex flex-col md:flex-row items-center justify-between gap-4">
        <div className="flex items-center gap-2 text-slate-400">
          <Shield className="w-5 h-5 text-blue-400" />
          <span className="font-medium">BOLA-Sentinel</span>
        </div>
        <p className="text-sm text-slate-500">
          Research-grade BOLA/IDOR vulnerability detection engine
        </p>
      </div>
    </footer>
  );
}

export default function LandingPage() {
  return (
    <main className="bg-[#020617] min-h-screen">
      <HeroSection />
      <PipelineSection />
      <StatsSection />
      <FeaturesSection />
      <CTASection />
      <Footer />
    </main>
  );
}
