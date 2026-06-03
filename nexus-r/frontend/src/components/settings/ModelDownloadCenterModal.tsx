import { useState, useEffect, useMemo } from 'react';
import { useModelsStore } from '../../store/modelsStore';
import { X, Search, Download, Box, HardDrive, CheckCircle2 } from 'lucide-react';
import { APP_NAME } from '../../constants';
import clsx from 'clsx';

interface ModelDownloadCenterModalProps {
  onClose: () => void;
}

const POPULAR_MODELS = [
  { id: 'llama3:8b', name: 'Llama 3 (8B)', description: 'Meta\'s latest 8B parameter model. Highly capable for reasoning, coding, and chat.', size: '4.7 GB', memory: '8GB RAM' },
  { id: 'mistral:7b', name: 'Mistral (7B)', description: 'A highly efficient 7B model by Mistral AI. Fast and accurate.', size: '4.1 GB', memory: '8GB RAM' },
  { id: 'gemma:7b', name: 'Gemma (7B)', description: 'Google\'s open model built from the same research and technology as Gemini.', size: '5.0 GB', memory: '8GB RAM' },
  { id: 'gemma:2b', name: 'Gemma (2B)', description: 'A lighter version of Gemma for machines with less RAM.', size: '1.7 GB', memory: '4GB RAM' },
  { id: 'phi3:mini', name: 'Phi-3 Mini', description: 'Microsoft\'s highly capable 3.8B model trained on textbook quality data.', size: '2.4 GB', memory: '4GB RAM' },
  { id: 'qwen2:7b', name: 'Qwen 2 (7B)', description: 'Alibaba\'s latest open model with excellent multilingual capabilities.', size: '4.4 GB', memory: '8GB RAM' },
  { id: 'llava:latest', name: 'LLaVA', description: 'Multimodal model for vision and language tasks.', size: '4.7 GB', memory: '8GB RAM' }
];

export function ModelDownloadCenterModal({ onClose }: ModelDownloadCenterModalProps) {
  const { downloadJobs, localModels, loadDownloadJobs, refreshLocalModels, startModelDownload, cancelModelDownload, loadModels } = useModelsStore();
  const [searchQuery, setSearchQuery] = useState('');
  const [installingModelId, setInstallingModelId] = useState<string | null>(null);

  // Poll for download jobs while the modal is open
  useEffect(() => {
    const poll = async () => {
      await loadDownloadJobs();
      await refreshLocalModels();
    };
    poll();
    const intervalId = setInterval(poll, 2000);
    return () => clearInterval(intervalId);
  }, [loadDownloadJobs, refreshLocalModels]);

  const filteredModels = useMemo(() => {
    if (!searchQuery.trim()) return POPULAR_MODELS;
    const lowerQ = searchQuery.toLowerCase();
    return POPULAR_MODELS.filter(m => 
      m.name.toLowerCase().includes(lowerQ) || 
      m.id.toLowerCase().includes(lowerQ) ||
      m.description.toLowerCase().includes(lowerQ)
    );
  }, [searchQuery]);

  const handleDownload = async (modelId: string) => {
    setInstallingModelId(modelId);
    const success = await startModelDownload(modelId);
    if (!success) {
      setInstallingModelId(null);
    }
  };

  const handleCancel = async (jobId: string) => {
    await cancelModelDownload(jobId);
  };

  const formatBytes = (bytes: number) => {
    if (bytes === 0) return '0 B';
    const k = 1024;
    const sizes = ['B', 'KB', 'MB', 'GB', 'TB'];
    const i = Math.floor(Math.log(bytes) / Math.log(k));
    return parseFloat((bytes / Math.pow(k, i)).toFixed(2)) + ' ' + sizes[i];
  };

  const checkIsInstalled = (modelId: string) => {
    return localModels.some(m => m.name === modelId || m.name === `${modelId}:latest`);
  };

  const getJobForModel = (modelId: string) => {
    // Basic match; the API might return job.model_name exactly as requested
    return downloadJobs.find(job => job.model_name === modelId || job.model_name === `${modelId}:latest`);
  };

  return (
    <div className="absolute inset-0 z-50 flex items-center justify-center p-4 bg-slate-900/50 backdrop-blur-sm animate-in fade-in duration-200">
      <div className="bg-white dark:bg-slate-900 border border-gray-200 dark:border-slate-800 rounded-2xl shadow-2xl flex flex-col w-full max-w-5xl h-[85vh] overflow-hidden flex-shrink-0 animate-in zoom-in-95 duration-200">
        
        {/* Header */}
        <div className="flex flex-col gap-4 p-6 border-b border-gray-100 dark:border-slate-800 shrink-0">
          <div className="flex items-center justify-between">
            <div className="flex items-center gap-3">
              <div className="w-10 h-10 rounded-xl bg-purple-50 dark:bg-purple-900/20 text-purple-600 dark:text-purple-400 flex items-center justify-center">
                <Box size={20} />
              </div>
              <div>
                <h2 className="text-xl font-bold text-gray-900 dark:text-gray-100">Model Download Center</h2>
                <p className="text-sm font-medium text-gray-500 dark:text-gray-400 mt-0.5">
                  Discover and install local models for {APP_NAME}.
                </p>
              </div>
            </div>
            <button 
              onClick={() => {
                loadModels(); // Refresh local models list on close
                onClose();
              }}
              className="w-10 h-10 flex items-center justify-center rounded-full hover:bg-gray-100 dark:hover:bg-slate-800 text-gray-500 transition-colors"
            >
              <X size={20} />
            </button>
          </div>
          
          <div className="relative">
            <Search size={16} className="absolute left-3 top-1/2 -translate-y-1/2 text-gray-400" />
            <input 
              type="text" 
              value={searchQuery}
              onChange={(e) => setSearchQuery(e.target.value)}
              placeholder="Search available models (e.g., Llama 3, Mistral, Gemma)..." 
              className="w-full pl-9 pr-4 py-2.5 bg-gray-50 dark:bg-[#0f172a] border border-gray-200 dark:border-slate-800 rounded-xl text-sm outline-none focus:border-purple-400 focus:ring-2 focus:ring-purple-100 transition-all dark:text-gray-200 dark:focus:ring-purple-900/20"
            />
          </div>
        </div>

        {/* Body */}
        <div className="flex-1 overflow-y-auto p-6 bg-gray-50 dark:bg-[#0b1120]">
          
          {/* Active Downloads Section */}
          {downloadJobs.filter(j => j.status !== 'completed' && j.status !== 'failed' && j.status !== 'cancelled').length > 0 && (
            <div className="mb-8">
              <h4 className="text-[13px] font-bold text-gray-400 uppercase tracking-wider mb-4 px-1">Active Downloads</h4>
              <div className="space-y-3">
                {downloadJobs.filter(j => j.status !== 'completed' && j.status !== 'failed' && j.status !== 'cancelled').map(job => (
                  <div key={job.job_id} className="bg-white dark:bg-slate-900 border border-purple-200 dark:border-purple-900/30 rounded-xl p-4 shadow-sm relative overflow-hidden">
                    <div className="absolute top-0 left-0 h-1 bg-purple-500 transition-all duration-500 ease-in-out" style={{ width: `${job.progress_percent}%` }}></div>
                    <div className="flex items-center justify-between">
                      <div className="flex items-center gap-3">
                        <div className="w-8 h-8 rounded-full bg-purple-50 dark:bg-purple-900/20 flex items-center justify-center text-purple-600 dark:text-purple-400">
                          <Download size={14} className="animate-bounce" />
                        </div>
                        <div>
                          <h5 className="font-bold text-gray-900 dark:text-gray-100">{job.model_name}</h5>
                          <p className="text-xs font-medium text-gray-500 dark:text-gray-400">
                            {job.status === 'downloading' ? `Downloading... ${formatBytes(job.downloaded_bytes)} / ${formatBytes(job.total_bytes)}` : 'Processing...'}
                          </p>
                        </div>
                      </div>
                      <div className="flex items-center gap-4">
                        <div className="text-right">
                          <div className="text-sm font-bold text-gray-900 dark:text-gray-100">{job.progress_percent}%</div>
                          <div className="text-[11px] font-medium text-gray-500 dark:text-gray-400">{job.speed_mbps.toFixed(1)} MB/s</div>
                        </div>
                        <button 
                          onClick={() => handleCancel(job.job_id)}
                          className="w-8 h-8 rounded-full hover:bg-red-50 dark:hover:bg-red-900/20 text-gray-400 hover:text-red-500 flex items-center justify-center transition-colors"
                          title="Cancel Download"
                        >
                          <X size={16} />
                        </button>
                      </div>
                    </div>
                  </div>
                ))}
              </div>
            </div>
          )}

          {/* Model Catalog */}
          <div className="mb-4">
            <h4 className="text-[13px] font-bold text-gray-400 uppercase tracking-wider mb-4 px-1">Curated Models</h4>
            
            {filteredModels.length === 0 ? (
              <div className="py-12 flex flex-col items-center justify-center text-center">
                <div className="w-16 h-16 rounded-full bg-white dark:bg-slate-800 border border-gray-200 dark:border-slate-700 flex items-center justify-center text-gray-400 mb-4 shadow-sm">
                  <Search size={24} />
                </div>
                <h4 className="text-lg font-bold text-gray-900 dark:text-gray-100 mb-2">No models found</h4>
                <p className="text-sm text-gray-500 dark:text-gray-400">Try a different search term.</p>
              </div>
            ) : (
              <div className="grid grid-cols-1 md:grid-cols-2 lg:grid-cols-3 gap-4">
                {filteredModels.map(model => {
                  const isInstalled = checkIsInstalled(model.id);
                  const activeJob = getJobForModel(model.id);
                  const isDownloading = !!activeJob;

                  return (
                    <div 
                      key={model.id} 
                      className={clsx(
                        "bg-white dark:bg-slate-900 rounded-xl p-5 border shadow-sm flex flex-col transition-all",
                        isInstalled ? "border-emerald-200 dark:border-emerald-900/30" : "border-gray-200 dark:border-slate-800 hover:shadow-md"
                      )}
                    >
                      <div className="flex items-start justify-between mb-3">
                        <div>
                          <h5 className="font-bold text-gray-900 dark:text-gray-100 text-[15px]">{model.name}</h5>
                          <p className="text-xs font-medium text-gray-400 dark:text-gray-500 font-mono mt-0.5">{model.id}</p>
                        </div>
                        {isInstalled ? (
                          <div className="bg-emerald-50 dark:bg-emerald-900/20 text-emerald-600 dark:text-emerald-400 p-1.5 rounded-full" title="Installed">
                            <CheckCircle2 size={16} />
                          </div>
                        ) : (
                          <div className="bg-gray-50 dark:bg-slate-800 text-gray-400 p-1.5 rounded-full">
                            <Box size={16} />
                          </div>
                        )}
                      </div>
                      
                      <p className="text-[13px] text-gray-600 dark:text-gray-400 font-medium leading-relaxed mb-5 flex-1">
                        {model.description}
                      </p>
                      
                      <div className="flex items-center gap-3 text-xs font-bold text-gray-500 dark:text-gray-400 mb-4 bg-gray-50 dark:bg-[#0f172a] p-2 rounded-lg">
                        <div className="flex items-center gap-1.5">
                          <HardDrive size={12} /> {model.size}
                        </div>
                        <div className="w-1 h-1 rounded-full bg-gray-300 dark:bg-slate-700"></div>
                        <div className="flex items-center gap-1.5">
                          {model.memory}
                        </div>
                      </div>

                      <div className="mt-auto">
                        {isInstalled || (activeJob?.status === 'completed') ? (
                          <button 
                            disabled
                            className="w-full py-2 bg-emerald-50 dark:bg-emerald-900/20 text-emerald-700 dark:text-emerald-400 text-[13px] font-bold rounded-lg flex items-center justify-center gap-2 cursor-default"
                          >
                            <CheckCircle2 size={14} /> Installed
                          </button>
                        ) : isDownloading ? (
                          <button 
                            disabled
                            className="w-full py-2 bg-purple-50 dark:bg-purple-900/20 text-purple-700 dark:text-purple-400 text-[13px] font-bold rounded-lg flex items-center justify-center gap-2 cursor-wait"
                          >
                            <Download size={14} className="animate-bounce" /> {activeJob.progress_percent}%
                          </button>
                        ) : installingModelId === model.id ? (
                          <button 
                            disabled
                            className="w-full py-2 bg-purple-50 dark:bg-purple-900/20 text-purple-700 dark:text-purple-400 text-[13px] font-bold rounded-lg flex items-center justify-center gap-2 cursor-wait"
                          >
                            <div className="w-3.5 h-3.5 border-2 border-purple-500 border-t-transparent rounded-full animate-spin" /> Installing...
                          </button>
                        ) : (
                          <button 
                            onClick={() => handleDownload(model.id)}
                            className="w-full py-2 bg-purple-600 hover:bg-purple-700 text-white text-[13px] font-bold rounded-lg flex items-center justify-center gap-2 transition-all"
                          >
                            <Download size={14} /> Install
                          </button>
                        )}
                      </div>
                    </div>
                  );
                })}
              </div>
            )}
          </div>
        </div>
      </div>
    </div>
  );
}
