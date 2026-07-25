"use client";

import React, { useState } from "react";
import ReactMarkdown from "react-markdown";
import remarkGfm from "remark-gfm";
import { Check, Copy } from "lucide-react";
import { cn } from "@/lib/utils";

interface MarkdownViewerProps {
  content: string;
  className?: string;
}

export function MarkdownViewer({ content, className }: MarkdownViewerProps) {
  const [copiedCode, setCopiedCode] = useState<string | null>(null);

  const handleCopy = (code: string) => {
    navigator.clipboard.writeText(code);
    setCopiedCode(code);
    setTimeout(() => setCopiedCode(null), 2000);
  };

  return (
    <div className={cn("prose prose-invert max-w-none prose-slate", className)}>
      <ReactMarkdown
        remarkPlugins={[remarkGfm]}
        components={{
          h1: ({node, ...props}) => <h1 className="text-2xl font-bold text-white border-b border-slate-800 pb-2 mb-4" {...props} />,
          h2: ({node, ...props}) => <h2 className="text-xl font-semibold text-white mt-8 mb-4" {...props} />,
          h3: ({node, ...props}) => <h3 className="text-lg font-medium text-slate-200 mt-6 mb-3" {...props} />,
          p: ({node, ...props}) => <p className="text-slate-300 leading-relaxed mb-4" {...props} />,
          ul: ({node, ...props}) => <ul className="list-disc list-outside ml-4 mb-4 text-slate-300" {...props} />,
          ol: ({node, ...props}) => <ol className="list-decimal list-outside ml-4 mb-4 text-slate-300" {...props} />,
          li: ({node, ...props}) => <li className="mb-1" {...props} />,
          a: ({node, ...props}) => <a className="text-blue-400 hover:text-blue-300 underline underline-offset-2" {...props} />,
          table: ({node, ...props}) => (
            <div className="overflow-x-auto mb-6 glass rounded-lg border border-slate-800">
              <table className="w-full text-sm text-left" {...props} />
            </div>
          ),
          th: ({node, ...props}) => <th className="px-4 py-3 bg-slate-900/50 font-medium text-slate-300 border-b border-slate-800" {...props} />,
          td: ({node, ...props}) => <td className="px-4 py-3 border-b border-slate-800/50 text-slate-400" {...props} />,
          blockquote: ({node, ...props}) => (
            <blockquote className="border-l-4 border-blue-500 pl-4 py-1 italic bg-blue-500/10 rounded-r-md text-slate-300 mb-4" {...props} />
          ),
          code({node, inline, className, children, ...props}: any) {
            const match = /language-(\w+)/.exec(className || '');
            const codeString = String(children).replace(/\n$/, '');
            
            if (!inline) {
              return (
                <div className="relative group mb-6 rounded-lg overflow-hidden border border-slate-800 bg-[#0d1117]">
                  <div className="flex items-center justify-between px-4 py-2 bg-slate-900/80 border-b border-slate-800">
                    <span className="text-xs font-mono text-slate-400">{match?.[1] || 'text'}</span>
                    <button
                      onClick={() => handleCopy(codeString)}
                      className="text-slate-400 hover:text-white transition-colors"
                      title="Copy code"
                    >
                      {copiedCode === codeString ? <Check size={14} className="text-green-500" /> : <Copy size={14} />}
                    </button>
                  </div>
                  <pre className="p-4 overflow-x-auto text-sm font-mono text-slate-300">
                    <code className={className} {...props}>
                      {children}
                    </code>
                  </pre>
                </div>
              );
            }
            return (
              <code className="bg-slate-800 text-blue-300 px-1.5 py-0.5 rounded text-sm font-mono" {...props}>
                {children}
              </code>
            );
          }
        }}
      >
        {content}
      </ReactMarkdown>
    </div>
  );
}
