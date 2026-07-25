'use client';

import { useState, useEffect, useRef } from 'react';
import { motion, AnimatePresence } from 'framer-motion';
import { Search, FileTerminal, ArrowDownToLine, RefreshCw, AlertCircle, Loader2 } from 'lucide-react';
import { cn } from '@/lib/utils';

export default function LogsPage() {
  const [categories, setCategories] = useState<Record<string, string[]>>({});
  const [selectedCategory, setSelectedCategory] = useState<string>('');
  const [selectedFile, setSelectedFile] = useState<string>('');
  const [fileContent, setFileContent] = useState<string | null>(null);
  const [isJson, setIsJson] = useState(false);
  const [loading, setLoading] = useState(true);
  const [fetchingFile, setFetchingFile] = useState(false);
  
  const [filter, setFilter] = useState('');
  const [autoScroll, setAutoScroll] = useState(true);
  
  const scrollRef = useRef<HTMLDivElement>(null);

  const fetchCategories = async () => {
    setLoading(true);
    try {
      const res = await fetch('/api/logs');
      if (!res.ok) throw new Error('Failed to fetch logs');
      const data = await res.json();
      setCategories(data.categories || {});
      
      const cats = Object.keys(data.categories || {});
      if (cats.length > 0) {
        const firstCat = cats[0];
        setSelectedCategory(firstCat);
        const files = data.categories[firstCat];
        if (files && files.length > 0) {
          setSelectedFile(files[0]);
        }
      }
    } catch (error) {
      console.error(error);
    } finally {
      setLoading(false);
    }
  };

  useEffect(() => {
    fetchCategories();
  }, []);

  useEffect(() => {
    if (!selectedCategory || !selectedFile) return;
    
    const fetchFileContent = async () => {
      setFetchingFile(true);
      try {
        const res = await fetch(`/api/logs/${selectedCategory}/${selectedFile}`);
        if (!res.ok) throw new Error('Failed to fetch file content');
        const data = await res.json();
        
        if (data.data) {
          setFileContent(JSON.stringify(data.data, null, 2));
          setIsJson(true);
        } else if (data.content) {
          try {
            // Check if string content is actually JSON
            const parsed = JSON.parse(data.content);
            setFileContent(JSON.stringify(parsed, null, 2));
            setIsJson(true);
          } catch {
            setFileContent(data.content);
            setIsJson(selectedFile.endsWith('.json'));
          }
        } else {
          setFileContent('');
          setIsJson(false);
        }
      } catch (error) {
        console.error(error);
        setFileContent('Error loading file content.');
        setIsJson(false);
      } finally {
        setFetchingFile(false);
      }
    };
    
    fetchFileContent();
  }, [selectedCategory, selectedFile]);

  useEffect(() => {
    if (autoScroll && scrollRef.current) {
      scrollRef.current.scrollTop = scrollRef.current.scrollHeight;
    }
  }, [fileContent, autoScroll]);

  const getLogColor = (line: string) => {
    const upper = line.toUpperCase();
    if (upper.includes('[ERROR]') || upper.includes('ERROR')) return 'text-red-400';
    if (upper.includes('[WARN]') || upper.includes('WARN')) return 'text-yellow-400';
    if (upper.includes('[SUCCESS]') || upper.includes('SUCCESS')) return 'text-emerald-400';
    if (upper.includes('[INFO]') || upper.includes('INFO')) return 'text-blue-400';
    return 'text-slate-300';
  };

  const syntaxHighlight = (json: string) => {
    if (!json) return [];
    const lines = json.split('\n');
    return lines.map(line => {
      // Very basic JSON syntax highlighting
      let highlighted = line
        .replace(/("(\\u[a-zA-Z0-9]{4}|\\[^u]|[^\\"])*"(\s*:)?|\b(true|false|null)\b|-?\d+(?:\.\d*)?(?:[eE][+\-]?\d+)?)/g, function (match) {
          let cls = 'text-blue-300'; // number
          if (/^"/.test(match)) {
            if (/:$/.test(match)) {
              cls = 'text-purple-400'; // key
            } else {
              cls = 'text-green-400'; // string
            }
          } else if (/true|false/.test(match)) {
            cls = 'text-amber-400'; // boolean
          } else if (/null/.test(match)) {
            cls = 'text-slate-500'; // null
          }
          return `<span class="${cls}">${match}</span>`;
        });
      return highlighted;
    });
  };

  const renderContent = () => {
    if (fetchingFile) {
      return (
        <div className="flex flex-col items-center justify-center h-full text-slate-400">
          <Loader2 className="w-8 h-8 animate-spin mb-4" />
          <p>Loading file content...</p>
        </div>
      );
    }

    if (!fileContent) {
      return (
        <div className="flex flex-col items-center justify-center h-full text-slate-500">
          <AlertCircle className="w-12 h-12 mb-4 opacity-50" />
          <p>No content available</p>
        </div>
      );
    }

    const lines = isJson ? jsonLines : logLines;
    const filteredLines = lines.filter(line => 
      line.toLowerCase().includes(filter.toLowerCase())
    );

    if (filteredLines.length === 0) {
      return <div className="text-slate-500 text-center mt-10">No matching content found.</div>;
    }

    return filteredLines.map((line, i) => (
      <div key={i} className="flex gap-4 hover:bg-white/[0.02] px-2 py-0.5 rounded">
        <span className="text-slate-600 select-none w-8 text-right shrink-0">{i + 1}</span>
        {isJson ? (
          <span 
            className="break-all whitespace-pre-wrap font-mono text-slate-300" 
            dangerouslySetInnerHTML={{ __html: line }}
          />
        ) : (
          <span className={cn("break-all whitespace-pre-wrap font-mono", getLogColor(line))}>
            {line}
          </span>
        )}
      </div>
    ));
  };

  const logLines = (fileContent || '').split('\n');
  const jsonLines = isJson ? syntaxHighlight(fileContent || '') : [];

  return (
    <motion.div 
      initial={{ opacity: 0, y: 20 }}
      animate={{ opacity: 1, y: 0 }}
      className="p-6 h-[calc(100vh-4rem)] flex flex-col gap-6"
    >
      <div className="flex flex-col sm:flex-row sm:items-center justify-between gap-4 shrink-0">
        <h1 className="text-2xl font-bold text-slate-100">Log Viewer</h1>
        
        <div className="flex items-center gap-3">
          <button onClick={fetchCategories} className="p-2 bg-slate-900 border border-slate-800 rounded-lg text-slate-400 hover:text-slate-200 hover:bg-slate-800 transition-colors">
            <RefreshCw className={cn("w-4 h-4", loading && "animate-spin")} />
          </button>
        </div>
      </div>

      <div className="flex gap-2 overflow-x-auto pb-2 shrink-0">
        {Object.keys(categories).map(cat => (
          <button
            key={cat}
            onClick={() => {
              setSelectedCategory(cat);
              const files = categories[cat];
              if (files && files.length > 0) setSelectedFile(files[0]);
            }}
            className={cn(
              "px-4 py-2 rounded-lg text-sm font-medium transition-colors whitespace-nowrap",
              selectedCategory === cat 
                ? "bg-blue-600 text-white" 
                : "bg-slate-900 border border-slate-800 text-slate-400 hover:bg-slate-800 hover:text-slate-200"
            )}
          >
            {cat.split('_').map(w => w.charAt(0).toUpperCase() + w.slice(1)).join(' ')}
          </button>
        ))}
      </div>

      <div className="flex-1 bg-[#0a0a0a] border border-slate-800 rounded-xl flex flex-col min-h-0 shadow-xl overflow-hidden relative">
        <div className="p-3 border-b border-slate-800 bg-slate-900/80 backdrop-blur flex flex-wrap items-center justify-between gap-4">
          <div className="flex items-center gap-3">
            <FileTerminal className="w-5 h-5 text-slate-400" />
            <select 
              value={selectedFile}
              onChange={(e) => setSelectedFile(e.target.value)}
              className="bg-slate-950 border border-slate-700 rounded-lg px-3 py-1.5 text-sm text-slate-200 focus:outline-none focus:ring-2 focus:ring-blue-500/50 min-w-[200px]"
              disabled={!categories[selectedCategory] || categories[selectedCategory].length === 0}
            >
              {categories[selectedCategory]?.map(file => (
                <option key={file} value={file}>{file}</option>
              ))}
              {(!categories[selectedCategory] || categories[selectedCategory].length === 0) && (
                <option value="">No files</option>
              )}
            </select>
          </div>

          <div className="relative flex-1 max-w-md ml-auto">
            <Search className="absolute left-3 top-1/2 -translate-y-1/2 w-4 h-4 text-slate-500" />
            <input
              type="text"
              placeholder="Filter logs..."
              value={filter}
              onChange={(e) => setFilter(e.target.value)}
              className="w-full pl-9 pr-4 py-1.5 bg-slate-950 border border-slate-700 rounded text-sm text-slate-200 focus:outline-none focus:ring-1 focus:ring-blue-500/50"
            />
          </div>
          
          <div className="flex items-center gap-4">
            <label className="flex items-center gap-2 text-sm text-slate-400 cursor-pointer hover:text-slate-300">
              <input
                type="checkbox"
                checked={autoScroll}
                onChange={(e) => setAutoScroll(e.target.checked)}
                className="rounded border-slate-700 bg-slate-950 text-blue-500 focus:ring-blue-500/50"
              />
              Auto-scroll
            </label>
            <button className="flex items-center gap-1.5 text-sm text-slate-400 hover:text-slate-200 transition-colors">
              <ArrowDownToLine className="w-4 h-4" />
              Download
            </button>
          </div>
        </div>

        <div 
          ref={scrollRef}
          className="flex-1 overflow-y-auto p-4 text-sm leading-relaxed"
        >
          {loading ? (
            <div className="flex flex-col items-center justify-center h-full text-slate-400">
              <Loader2 className="w-8 h-8 animate-spin mb-4" />
              <p>Loading directory...</p>
            </div>
          ) : (
            renderContent()
          )}
        </div>
      </div>
    </motion.div>
  );
}
