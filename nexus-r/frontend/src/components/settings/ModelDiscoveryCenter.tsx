import { useState, useEffect, useRef, useMemo } from 'react';
import { useModelsStore } from '../../store/modelsStore';
import { X, Search, Download, Box, HardDrive, CheckCircle2, Pause, Play, Tag, ExternalLink, Trash2, Globe, Server, Zap, RefreshCw, List } from 'lucide-react';
import clsx from 'clsx';

interface ModelDiscoveryCenterProps {
  onClose: () => void;
}

type DiscoverSource = 'huggingface' | 'openrouter';

const TABS = ['Installed', 'Discover', 'Downloads', 'Updates'];
const HF_FILTERS = ['gguf', 'safetensors', 'text-generation', 'embedding', 'vision', 'audio', 'coding', 'reasoning'];

const SOURCE_ICONS: Record<string, typeof Server> = {
  ollama: Server,
  lmstudio: List,
  gguf: HardDrive,
};

const SOURCE_COLORS: Record<string, string> = {
  ollama: 'text-amber-600 dark:text-amber-400 bg-amber-50 dark:bg-amber-900/20',
  lmstudio: 'text-blue-600 dark:text-blue-400 bg-blue-50 dark:bg-blue-900/20',
  gguf: 'text-purple-600 dark:text-purple-400 bg-purple-50 dark:bg-purple-900/20',
};

export function ModelDiscoveryCenter({ onClose }: ModelDiscoveryCenterProps) {
  const {
    downloadJobs, localModels, huggingfaceResults, openrouterModels, isSearching,
    loadDownloadJobs, refreshLocalModels, searchHFModels, listOpenRouter,
    startModelDownload, pauseModelDownload, resumeModelDownload, cancelModelDownload,
    loadModels, deleteLocalModel
  } = useModelsStore();

  const [activeTab, setActiveTab] = useState('Installed');
  const [searchQuery, setSearchQuery] = useState('');
  const [discoverSource, setDiscoverSource] = useState<DiscoverSource>('huggingface');
  const [activeFilter, setActiveFilter] = useState('gguf');
  const [installingModelId, setInstallingModelId] = useState<string | null>(null);
  const searchTimerRef = useRef<ReturnType<typeof setTimeout> | null>(null);

  useEffect(() => {
    const poll = async () => {
      await loadDownloadJobs();
      await refreshLocalModels();
    };
    poll();
    const intervalId = setInterval(poll, 2000);
    return () => clearInterval(intervalId);
  }, []);

  // Live search with debounce
  useEffect(() => {
    if (searchTimerRef.current) clearTimeout(searchTimerRef.current);
    if (discoverSource === 'huggingface') {
      const trimmed = searchQuery.trim();
      if (trimmed) {
        searchTimerRef.current = setTimeout(() => {
          searchHFModels(trimmed, activeFilter);
        }, 300);
      } else {
        searchHFModels('Qwen', activeFilter);
      }
    }
    return () => {
      if (searchTimerRef.current) clearTimeout(searchTimerRef.current);
    };
  }, [searchQuery, discoverSource, activeFilter]);

  const handleSourceChange = (source: DiscoverSource) => {
    setDiscoverSource(source);
    if (source === 'openrouter' && openrouterModels.length === 0) {
      listOpenRouter();
    }
  };

  const handleFilterChange = (filter: string) => {
    const newFilter = activeFilter === filter ? '' : filter;
    setActiveFilter(newFilter);
  };

  const handleDownload = async (modelId: string, filename?: string) => {
    const actualFile = filename || `${modelId.split('/').pop() || modelId}.gguf`;
    const url = `https://huggingface.co/${modelId}/resolve/main/${actualFile}?download=true`;
    setInstallingModelId(modelId);
    const success = await startModelDownload(`hf/${actualFile}`, url);
    if (!success) setInstallingModelId(null);
    setActiveTab('Downloads');
  };

  const checkIsInstalled = (modelId: string, modelName?: string) => {
    return localModels.some(m =>
      m.name === modelId || m.name === `${modelId}:latest` ||
      (modelName && m.name === modelName)
    );
  };

  const getJobForModel = (modelId: string, modelName?: string) => {
    return downloadJobs.find(job =>
      job.model_name === modelId || job.model_name === `${modelId}:latest` ||
      (modelName && job.model_name === modelName)
    );
  };

  const formatBytes = (bytes: number) => {
    if (!bytes || bytes === 0) return '0 B';
    const k = 1024;
    const sizes = ['B', 'KB', 'MB', 'GB', 'TB'];
    const i = Math.floor(Math.log(bytes) / Math.log(k));
    return parseFloat((bytes / Math.pow(k, i)).toFixed(2)) + ' ' + sizes[i];
  };

  return (
    <div className="absolute inset-0 z-50 flex items-center justify-center p-4 bg-slate-900/50 backdrop-blur-sm animate-in fade-in duration-200">
      <div className="bg-white dark:bg-slate-900 border border-gray-200 dark:border-slate-800 rounded-2xl shadow-2xl flex flex-col w-full max-w-6xl h-[85vh] overflow-hidden flex-shrink-0 animate-in zoom-in-95 duration-200">

        {/* Header */}
        <div className="flex flex-col gap-4 p-6 border-b border-gray-100 dark:border-slate-800 shrink-0">
          <div className="flex items-center justify-between">
            <div className="flex items-center gap-3">
              <div className="w-10 h-10 rounded-xl bg-purple-50 dark:bg-purple-900/20 text-purple-600 dark:text-purple-400 flex items-center justify-center">
                <Box size={20} />
              </div>
              <div>
                <h2 className="text-xl font-bold text-gray-900 dark:text-gray-100">Model Discovery Center</h2>
                <p className="text-sm font-medium text-gray-500 dark:text-gray-400 mt-0.5">
                  Discover, install, and manage local models from multiple sources.
                </p>
              </div>
            </div>
            <button
              onClick={() => { loadModels(); onClose(); }}
              className="w-10 h-10 flex items-center justify-center rounded-full hover:bg-gray-100 dark:hover:bg-slate-800 text-gray-500 transition-colors"
            >
              <X size={20} />
            </button>
          </div>

          {/* Tabs */}
          <div className="flex items-center gap-6 border-b border-gray-100 dark:border-slate-800">
            {TABS.map(tab => (
              <button
                key={tab}
                onClick={() => setActiveTab(tab)}
                className={clsx(
                  "pb-3 text-sm font-bold transition-all relative",
                  activeTab === tab
                    ? "text-purple-600 dark:text-purple-400"
                    : "text-gray-500 dark:text-gray-400 hover:text-gray-900 dark:hover:text-gray-200"
                )}
              >
                {tab}
                {tab === 'Downloads' && downloadJobs.filter(j => j.status !== 'completed' && j.status !== 'failed').length > 0 && (
                  <span className="ml-2 inline-flex items-center justify-center bg-purple-100 dark:bg-purple-900/50 text-purple-600 dark:text-purple-300 text-[10px] font-bold px-1.5 py-0.5 rounded-full">
                    {downloadJobs.filter(j => j.status !== 'completed' && j.status !== 'failed').length}
                  </span>
                )}
                {activeTab === tab && (
                  <div className="absolute bottom-0 left-0 right-0 h-0.5 bg-purple-600 dark:bg-purple-400 rounded-t-full"></div>
                )}
              </button>
            ))}
          </div>

          {/* Discover tab header: source selector + search */}
          {activeTab === 'Discover' && (
            <div className="flex flex-col gap-3 mt-2">
              <div className="flex items-center gap-2">
                <button
                  onClick={() => handleSourceChange('huggingface')}
                  className={clsx(
                    "px-3 py-1.5 rounded-lg text-xs font-bold flex items-center gap-1.5 transition-colors border",
                    discoverSource === 'huggingface'
                      ? "bg-purple-100 dark:bg-purple-900/30 text-purple-700 dark:text-purple-300 border-purple-200 dark:border-purple-700/50"
                      : "bg-gray-50 dark:bg-slate-800 text-gray-600 dark:text-gray-400 border-gray-200 dark:border-slate-700 hover:bg-gray-100 dark:hover:bg-slate-700"
                  )}
                >
                  <Search size={14} /> HuggingFace
                </button>
                <button
                  onClick={() => handleSourceChange('openrouter')}
                  className={clsx(
                    "px-3 py-1.5 rounded-lg text-xs font-bold flex items-center gap-1.5 transition-colors border",
                    discoverSource === 'openrouter'
                      ? "bg-purple-100 dark:bg-purple-900/30 text-purple-700 dark:text-purple-300 border-purple-200 dark:border-purple-700/50"
                      : "bg-gray-50 dark:bg-slate-800 text-gray-600 dark:text-gray-400 border-gray-200 dark:border-slate-700 hover:bg-gray-100 dark:hover:bg-slate-700"
                  )}
                >
                  <Globe size={14} /> OpenRouter
                </button>
              </div>

              {discoverSource === 'huggingface' && (
                <div className="relative">
                  <Search size={16} className="absolute left-3 top-1/2 -translate-y-1/2 text-gray-400" />
                  <input
                    type="text"
                    value={searchQuery}
                    onChange={(e) => setSearchQuery(e.target.value)}
                    placeholder="Live search HuggingFace models (e.g., DeepSeek, Llama, Qwen)..."
                    className="w-full pl-9 pr-4 py-2.5 bg-gray-50 dark:bg-[#0f172a] border border-gray-200 dark:border-slate-800 rounded-xl text-sm outline-none focus:border-purple-400 focus:ring-2 focus:ring-purple-100 transition-all dark:text-gray-200 dark:focus:ring-purple-900/20"
                  />
                </div>
              )}

              {discoverSource === 'huggingface' && (
                <div className="flex flex-wrap items-center gap-2">
                  {HF_FILTERS.map(filter => (
                    <button
                      key={filter}
                      onClick={() => handleFilterChange(filter)}
                      className={clsx(
                        "px-3 py-1 rounded-full text-xs font-semibold flex items-center gap-1.5 transition-colors",
                        activeFilter === filter
                          ? "bg-purple-100 dark:bg-purple-900/30 text-purple-700 dark:text-purple-300 border border-purple-200 dark:border-purple-700/50"
                          : "bg-gray-50 dark:bg-slate-800 text-gray-600 dark:text-gray-400 border border-gray-200 dark:border-slate-700 hover:bg-gray-100 dark:hover:bg-slate-700"
                      )}
                    >
                      <Tag size={12} /> {filter}
                    </button>
                  ))}
                </div>
              )}
            </div>
          )}
        </div>

        {/* Body */}
        <div className="flex-1 overflow-y-auto p-6 bg-gray-50 dark:bg-[#0b1120]">

          {/* ===== INSTALLED TAB ===== */}
          {activeTab === 'Installed' && (
            <div className="grid grid-cols-1 lg:grid-cols-2 gap-4">
              {localModels.length === 0 ? (
                <div className="col-span-full py-12 text-center text-gray-500">No models installed locally.</div>
              ) : (
                localModels.map(model => {
                  const SourceIcon = SOURCE_ICONS[model.source || 'ollama'] || Server;
                  const sourceColor = SOURCE_COLORS[model.source || 'ollama'] || 'text-gray-600 dark:text-gray-400 bg-gray-50 dark:bg-slate-800';
                  return (
                    <div key={model.name} className="bg-white dark:bg-slate-900 rounded-xl p-5 border border-gray-200 dark:border-slate-800 shadow-sm flex flex-col">
                      <div className="flex items-start justify-between mb-3">
                        <div className="flex-1 min-w-0 pr-4">
                          <h5 className="font-bold text-gray-900 dark:text-gray-100 text-[15px] truncate" title={model.name}>{model.name}</h5>
                          <p className="text-xs font-medium text-emerald-600 dark:text-emerald-400 mt-1 flex items-center gap-1">
                            <CheckCircle2 size={12} /> Ready to use
                          </p>
                        </div>
                        <div className="flex items-center gap-2 shrink-0">
                          <div className={clsx("text-[10px] font-bold px-2 py-1 rounded flex items-center gap-1", sourceColor)}>
                            <SourceIcon size={10} />
                            {(model.source || 'ollama').toUpperCase()}
                          </div>
                          <button
                            onClick={async () => {
                              if (window.confirm(`Delete ${model.name}?`)) {
                                await deleteLocalModel(model.source === 'gguf' ? `gguf/${model.name}` : model.name);
                              }
                            }}
                            className="w-7 h-7 flex items-center justify-center rounded hover:bg-red-50 hover:text-red-600 text-gray-400 transition-colors"
                            title="Delete Model"
                          >
                            <Trash2 size={14} />
                          </button>
                        </div>
                      </div>
                      <div className="flex flex-wrap gap-2 mt-auto">
                        {model.size && (
                          <span className="text-[11px] font-medium px-2 py-1 bg-gray-50 dark:bg-[#0f172a] text-gray-600 dark:text-gray-400 rounded-md border border-gray-100 dark:border-slate-800 flex items-center gap-1.5">
                            <HardDrive size={12} /> {model.size}
                          </span>
                        )}
                        {model.details?.parameter_size && model.details.parameter_size !== "unknown" && (
                          <span className="text-[11px] font-medium px-2 py-1 bg-gray-50 dark:bg-[#0f172a] text-gray-600 dark:text-gray-400 rounded-md border border-gray-100 dark:border-slate-800">
                            {model.details.parameter_size} Params
                          </span>
                        )}
                        {model.details?.quantization_level && (
                          <span className="text-[11px] font-medium px-2 py-1 bg-gray-50 dark:bg-[#0f172a] text-gray-600 dark:text-gray-400 rounded-md border border-gray-100 dark:border-slate-800">
                            {model.details.quantization_level}
                          </span>
                        )}
                      </div>
                    </div>
                  );
                })
              )}
            </div>
          )}

          {/* ===== DISCOVER TAB ===== */}
          {activeTab === 'Discover' && discoverSource === 'huggingface' && (
            <div>
              {isSearching ? (
                <div className="py-20 flex flex-col items-center justify-center">
                  <div className="w-8 h-8 border-4 border-purple-200 border-t-purple-600 rounded-full animate-spin mb-4"></div>
                  <p className="text-gray-500 font-medium">Searching HuggingFace...</p>
                </div>
              ) : huggingfaceResults.length === 0 ? (
                <div className="py-20 flex flex-col items-center justify-center text-center">
                  <div className="w-16 h-16 rounded-full bg-white dark:bg-slate-800 border border-gray-200 dark:border-slate-700 flex items-center justify-center text-gray-400 mb-4 shadow-sm">
                    <Search size={24} />
                  </div>
                  <h4 className="text-lg font-bold text-gray-900 dark:text-gray-100 mb-2">No models found</h4>
                  <p className="text-sm text-gray-500 dark:text-gray-400">Try a different search term or filter.</p>
                </div>
              ) : (
                <div className="grid grid-cols-1 lg:grid-cols-2 gap-4">
                  {huggingfaceResults.map(model => {
                    const defaultFile = model.gguf_files && model.gguf_files.length > 0 ? model.gguf_files[0] : null;
                    const isInstalled = checkIsInstalled(model.id, defaultFile);
                    const activeJob = getJobForModel(model.id, defaultFile);
                    const isDownloading = !!activeJob && activeJob.status !== 'completed' && activeJob.status !== 'failed';
                    return (
                      <div key={model.id} className={clsx(
                        "bg-white dark:bg-slate-900 rounded-xl p-5 border shadow-sm flex flex-col transition-all h-full",
                        isInstalled ? "border-emerald-200 dark:border-emerald-900/30" : "border-gray-200 dark:border-slate-800 hover:shadow-md"
                      )}>
                        <div className="flex items-start justify-between mb-2">
                          <div className="flex-1 min-w-0 pr-4">
                            <h5 className="font-bold text-gray-900 dark:text-gray-100 text-[15px] truncate" title={model.id}>{model.id}</h5>
                            <p className="text-xs font-medium text-gray-400 dark:text-gray-500 mt-1">by {model.author}</p>
                          </div>
                          {isInstalled ? (
                            <div className="bg-emerald-50 dark:bg-emerald-900/20 text-emerald-600 dark:text-emerald-400 p-1.5 rounded-full shrink-0" title="Installed">
                              <CheckCircle2 size={16} />
                            </div>
                          ) : (
                            <a href={`https://huggingface.co/${model.id}`} target="_blank" rel="noreferrer"
                              className="text-gray-400 hover:text-purple-500 p-1.5 rounded-full shrink-0 transition-colors">
                              <ExternalLink size={16} />
                            </a>
                          )}
                        </div>
                        <div className="flex flex-wrap gap-2 mb-4">
                          <span className="text-[10px] font-bold px-2 py-0.5 bg-gray-100 dark:bg-slate-800 text-gray-600 dark:text-gray-300 rounded-md">
                            {formatBytes(model.downloads)} DLs
                          </span>
                          <span className="text-[10px] font-bold px-2 py-0.5 bg-gray-100 dark:bg-slate-800 text-gray-600 dark:text-gray-300 rounded-md flex items-center gap-1">
                            ❤️ {model.likes}
                          </span>
                          {model.pipeline_tag && (
                            <span className="text-[10px] font-bold px-2 py-0.5 bg-purple-50 dark:bg-purple-900/20 text-purple-600 dark:text-purple-300 rounded-md">
                              {model.pipeline_tag}
                            </span>
                          )}
                        </div>
                        <div className="mt-auto pt-4 flex gap-3">
                          {isInstalled || (activeJob?.status === 'completed') ? (
                            <button disabled className="flex-1 py-2 bg-emerald-50 dark:bg-emerald-900/20 text-emerald-700 dark:text-emerald-400 text-[13px] font-bold rounded-lg flex items-center justify-center gap-2 cursor-default">
                              <CheckCircle2 size={14} /> Installed
                            </button>
                          ) : isDownloading ? (
                            <button onClick={() => setActiveTab('Downloads')}
                              className="flex-1 py-2 bg-purple-50 dark:bg-purple-900/20 text-purple-700 dark:text-purple-400 text-[13px] font-bold rounded-lg flex items-center justify-center gap-2 cursor-pointer hover:bg-purple-100 transition-colors">
                              <Download size={14} className="animate-bounce" /> {activeJob.progress_percent}%
                            </button>
                          ) : installingModelId === model.id ? (
                            <button disabled className="flex-1 py-2 bg-purple-50 dark:bg-purple-900/20 text-purple-700 dark:text-purple-400 text-[13px] font-bold rounded-lg flex items-center justify-center gap-2 cursor-wait">
                              <div className="w-3.5 h-3.5 border-2 border-purple-500 border-t-transparent rounded-full animate-spin" /> Starting...
                            </button>
                          ) : (
                            <button onClick={() => handleDownload(model.id, defaultFile || undefined)}
                              className="flex-1 py-2 bg-gray-900 hover:bg-gray-800 dark:bg-purple-600 dark:hover:bg-purple-700 text-white text-[13px] font-bold rounded-lg flex items-center justify-center gap-2 transition-all">
                              <Download size={14} /> Download
                            </button>
                          )}
                        </div>
                      </div>
                    );
                  })}
                </div>
              )}
            </div>
          )}

          {activeTab === 'Discover' && discoverSource === 'openrouter' && (
            <div>
              {isSearching ? (
                <div className="py-20 flex flex-col items-center justify-center">
                  <div className="w-8 h-8 border-4 border-purple-200 border-t-purple-600 rounded-full animate-spin mb-4"></div>
                  <p className="text-gray-500 font-medium">Loading OpenRouter models...</p>
                </div>
              ) : openrouterModels.length === 0 ? (
                <div className="py-20 flex flex-col items-center justify-center text-center">
                  <div className="w-16 h-16 rounded-full bg-white dark:bg-slate-800 border border-gray-200 dark:border-slate-700 flex items-center justify-center text-gray-400 mb-4 shadow-sm">
                    <Globe size={24} />
                  </div>
                  <h4 className="text-lg font-bold text-gray-900 dark:text-gray-100 mb-2">No models from OpenRouter</h4>
                  <p className="text-sm text-gray-500 dark:text-gray-400">Could not fetch model list from OpenRouter.</p>
                  <button onClick={() => listOpenRouter()}
                    className="mt-4 px-4 py-2 bg-purple-600 hover:bg-purple-700 text-white text-xs font-bold rounded-lg flex items-center gap-2 transition-colors">
                    <RefreshCw size={14} /> Retry
                  </button>
                </div>
              ) : (
                <div className="grid grid-cols-1 lg:grid-cols-2 gap-4">
                  {openrouterModels.map(model => {
                    const pricing = model.pricing || {};
                    const promptPrice = pricing.prompt ? `$${parseFloat(pricing.prompt).toFixed(6)}/tok` : 'N/A';
                    const completionPrice = pricing.completion ? `$${parseFloat(pricing.completion).toFixed(6)}/tok` : 'N/A';
                    return (
                      <div key={model.id} className="bg-white dark:bg-slate-900 rounded-xl p-5 border border-gray-200 dark:border-slate-800 shadow-sm flex flex-col h-full hover:shadow-md transition-all">
                        <div className="flex items-start justify-between mb-2">
                          <div className="flex-1 min-w-0 pr-4">
                            <h5 className="font-bold text-gray-900 dark:text-gray-100 text-[15px] truncate" title={model.id}>{model.id}</h5>
                            <p className="text-xs font-medium text-gray-400 dark:text-gray-500 mt-1">
                              {model.name || model.id.split('/').pop()}
                            </p>
                          </div>
                          <a href={`https://openrouter.ai/models/${model.id}`} target="_blank" rel="noreferrer"
                            className="text-gray-400 hover:text-purple-500 p-1.5 rounded-full shrink-0 transition-colors">
                            <ExternalLink size={16} />
                          </a>
                        </div>
                        {model.description && (
                          <p className="text-xs text-gray-500 dark:text-gray-400 mb-3 line-clamp-2">{model.description}</p>
                        )}
                        <div className="flex flex-wrap gap-2 mb-4">
                          {model.context_length && (
                            <span className="text-[10px] font-bold px-2 py-0.5 bg-gray-100 dark:bg-slate-800 text-gray-600 dark:text-gray-300 rounded-md">
                              {model.context_length.toLocaleString()} ctx
                            </span>
                          )}
                          {model.architecture && (
                            <span className="text-[10px] font-bold px-2 py-0.5 bg-blue-50 dark:bg-blue-900/20 text-blue-600 dark:text-blue-300 rounded-md">
                              {model.architecture}
                            </span>
                          )}
                          <span className="text-[10px] font-bold px-2 py-0.5 bg-gray-100 dark:bg-slate-800 text-gray-600 dark:text-gray-300 rounded-md" title={`Prompt: ${promptPrice}, Completion: ${completionPrice}`}>
                            <Zap size={10} className="inline mr-0.5" />{promptPrice}
                          </span>
                        </div>
                      </div>
                    );
                  })}
                </div>
              )}
            </div>
          )}

          {/* ===== DOWNLOADS TAB ===== */}
          {activeTab === 'Downloads' && (
            <div className="space-y-4 max-w-4xl mx-auto">
              {downloadJobs.filter(j => j.status !== 'completed' && j.status !== 'cancelled').length === 0 ? (
                <div className="py-12 text-center text-gray-500">No active downloads</div>
              ) : (
                downloadJobs.filter(j => j.status !== 'completed' && j.status !== 'cancelled').map(job => (
                  <div key={job.job_id} className="bg-white dark:bg-slate-900 border border-gray-200 dark:border-slate-800 rounded-xl p-5 shadow-sm relative overflow-hidden">
                    <div className={clsx(
                      "absolute top-0 left-0 h-1 transition-all duration-500 ease-in-out",
                      job.status === 'paused' ? "bg-amber-500" : job.status === 'failed' ? "bg-red-500" : "bg-purple-500"
                    )} style={{ width: `${job.progress_percent}%` }}></div>
                    <div className="flex items-center justify-between">
                      <div className="flex items-center gap-4">
                        <div className={clsx(
                          "w-10 h-10 rounded-full flex items-center justify-center",
                          job.status === 'paused' ? "bg-amber-50 text-amber-600 dark:bg-amber-900/20 dark:text-amber-400" :
                          job.status === 'failed' ? "bg-red-50 text-red-600 dark:bg-red-900/20 dark:text-red-400" :
                          "bg-purple-50 text-purple-600 dark:bg-purple-900/20 dark:text-purple-400"
                        )}>
                          <Download size={18} className={job.status === 'downloading' ? "animate-bounce" : ""} />
                        </div>
                        <div>
                          <h5 className="font-bold text-gray-900 dark:text-gray-100">{job.model_name}</h5>
                          <p className="text-sm font-medium text-gray-500 dark:text-gray-400 mt-0.5">
                            {job.status === 'downloading' ? `Downloading... ${formatBytes(job.downloaded_bytes)} / ${formatBytes(job.total_bytes)}` :
                             job.status === 'paused' ? `Paused at ${formatBytes(job.downloaded_bytes)}` :
                             job.status === 'failed' ? `Failed: ${job.error}` : 'Processing...'}
                          </p>
                        </div>
                      </div>
                      <div className="flex items-center gap-6">
                        <div className="text-right">
                          <div className="text-lg font-bold text-gray-900 dark:text-gray-100">{job.progress_percent}%</div>
                          <div className="text-xs font-medium text-gray-500 dark:text-gray-400">
                            {job.speed_mbps > 0 ? `${job.speed_mbps.toFixed(1)} MB/s` : '-- MB/s'}
                          </div>
                        </div>
                        <div className="flex items-center gap-2">
                          {job.status === 'downloading' ? (
                            <button onClick={() => pauseModelDownload(job.job_id)}
                              className="w-8 h-8 rounded-full hover:bg-amber-50 text-gray-400 hover:text-amber-600 flex items-center justify-center transition-colors" title="Pause">
                              <Pause size={16} />
                            </button>
                          ) : job.status === 'paused' || job.status === 'failed' ? (
                            <button onClick={() => resumeModelDownload(job.job_id)}
                              className="w-8 h-8 rounded-full hover:bg-emerald-50 text-gray-400 hover:text-emerald-600 flex items-center justify-center transition-colors" title="Resume">
                              <Play size={16} />
                            </button>
                          ) : null}
                          <button onClick={() => cancelModelDownload(job.job_id)}
                            className="w-8 h-8 rounded-full hover:bg-red-50 dark:hover:bg-red-900/20 text-gray-400 hover:text-red-500 flex items-center justify-center transition-colors" title="Cancel">
                            <X size={16} />
                          </button>
                        </div>
                      </div>
                    </div>
                  </div>
                ))
              )}
              {downloadJobs.filter(j => j.status === 'completed' && j.status !== 'cancelled').length > 0 && (
                <div className="pt-6 border-t border-gray-200 dark:border-slate-800">
                  <h4 className="text-sm font-bold text-gray-700 dark:text-gray-300 mb-3">Completed Downloads</h4>
                  {downloadJobs.filter(j => j.status === 'completed').map(job => (
                    <div key={job.job_id} className="bg-white dark:bg-slate-900 border border-emerald-200 dark:border-emerald-900/30 rounded-xl p-4 shadow-sm flex items-center justify-between">
                      <div className="flex items-center gap-3">
                        <div className="w-8 h-8 rounded-full bg-emerald-50 dark:bg-emerald-900/20 text-emerald-600 dark:text-emerald-400 flex items-center justify-center">
                          <CheckCircle2 size={16} />
                        </div>
                        <div>
                          <h5 className="font-bold text-gray-900 dark:text-gray-100 text-sm">{job.model_name}</h5>
                          <p className="text-xs text-gray-500">Completed {job.completed_at ? new Date(job.completed_at).toLocaleString() : ''}</p>
                        </div>
                      </div>
                    </div>
                  ))}
                </div>
              )}
            </div>
          )}

          {/* ===== UPDATES TAB ===== */}
          {activeTab === 'Updates' && (
            <div className="max-w-4xl mx-auto">
              {localModels.length === 0 ? (
                <div className="py-12 text-center text-gray-500">No installed models to check for updates.</div>
              ) : (
                <div className="space-y-3">
                  {localModels.map(model => {
                    const SourceIcon = SOURCE_ICONS[model.source || 'ollama'] || Server;
                    const sourceColor = SOURCE_COLORS[model.source || 'ollama'] || 'text-gray-600 dark:text-gray-400 bg-gray-50 dark:bg-slate-800';
                    return (
                      <div key={model.name} className="bg-white dark:bg-slate-900 rounded-xl p-5 border border-gray-200 dark:border-slate-800 shadow-sm flex items-center justify-between">
                        <div className="flex items-center gap-4 flex-1 min-w-0">
                          <div className="w-10 h-10 rounded-full bg-gray-50 dark:bg-slate-800 flex items-center justify-center shrink-0">
                            <SourceIcon size={18} className="text-gray-500" />
                          </div>
                          <div className="min-w-0">
                            <h5 className="font-bold text-gray-900 dark:text-gray-100 text-[15px] truncate">{model.name}</h5>
                            <div className="flex items-center gap-2 mt-1">
                              <span className={clsx("text-[10px] font-bold px-1.5 py-0.5 rounded flex items-center gap-1", sourceColor)}>
                                <SourceIcon size={9} />
                                {(model.source || 'ollama').toUpperCase()}
                              </span>
                              <span className="text-xs text-gray-400">Up to date</span>
                            </div>
                          </div>
                        </div>
                        <button
                          onClick={() => refreshLocalModels()}
                          className="shrink-0 px-3 py-1.5 bg-gray-50 dark:bg-slate-800 text-gray-600 dark:text-gray-400 border border-gray-200 dark:border-slate-700 rounded-lg text-xs font-bold hover:bg-gray-100 dark:hover:bg-slate-700 transition-colors flex items-center gap-1.5"
                          title="Check for updates"
                        >
                          <RefreshCw size={12} /> Check
                        </button>
                      </div>
                    );
                  })}
                </div>
              )}
            </div>
          )}

        </div>
      </div>
    </div>
  );
}
