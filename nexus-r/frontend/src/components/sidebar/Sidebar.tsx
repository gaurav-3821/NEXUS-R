import { useEffect, useState } from 'react';
import { useAppStore } from '../../store/useAppStore';
import { useAppearanceStore } from '../../store/appearanceStore';
import { useProjectsStore } from '../../store/projectsStore';
import { APP_NAME } from '../../constants';
import { Plus, Search, Settings, Folder, MessageSquare, PanelLeftClose, PanelLeft } from 'lucide-react';
import clsx from 'clsx';
import { UserProfileCard } from './UserProfileCard';
import { useNavigate, useLocation } from 'react-router-dom';
import { ProjectGroup, UncategorizedGroup } from './ProjectGroup';

export default function Sidebar() {
  const { conversations, currentConversationId, setCurrentConversation, loadConversationMessages, startNewChat, deleteConversation, clearAllConversations, toggleSidebar } = useAppStore();
  const { projects, loadProjects, addProject } = useProjectsStore();
  const { sidebarTransparency, compactMode } = useAppearanceStore();
  const navigate = useNavigate();
  const location = useLocation();
  const isSettingsActive = location.pathname.startsWith('/settings');
  const [isCreatingProject, setIsCreatingProject] = useState(false);
  const [newProjectName, setNewProjectName] = useState('');

  useEffect(() => {
    loadProjects();
  }, [loadProjects]);

  // Group conversations by project
  const projectConversationMap: Record<string, typeof conversations> = {};
  const uncategorizedConversations: typeof conversations = [];
  const projectIds = new Set(projects.map(p => p.project_id));

  for (const conv of conversations) {
    let assigned = false;
    for (const project of projects) {
      if (project.conversation_ids.includes(conv.id)) {
        if (!projectConversationMap[project.project_id]) {
          projectConversationMap[project.project_id] = [];
        }
        projectConversationMap[project.project_id].push(conv);
        assigned = true;
        break;
      }
    }
    if (!assigned) {
      uncategorizedConversations.push(conv);
    }
  }

  const handleCreateProject = async () => {
    if (!newProjectName.trim()) return;
    await addProject(newProjectName.trim());
    setNewProjectName('');
    setIsCreatingProject(false);
  };

  return (
    <div className={clsx(
      "flex flex-col h-full text-[#111827] dark:text-slate-100",
      sidebarTransparency ? "bg-white dark:bg-slate-900/70 backdrop-blur-md" : "bg-white dark:bg-slate-900"
    )}>
      {/* Header */}
      <div className={clsx("pb-2", compactMode ? "p-3" : "p-6")}>
        <div className="flex items-center justify-between mb-4">
          <h3 className={clsx("font-bold tracking-[0.2em] uppercase text-gray-900 dark:text-gray-100", compactMode ? "text-lg" : "text-xl")}>
            {APP_NAME}
          </h3>
          <button
            onClick={toggleSidebar}
            className="p-1.5 text-gray-400 hover:text-gray-600 dark:text-gray-500 dark:hover:text-gray-300 rounded-lg hover:bg-gray-100 dark:hover:bg-slate-800 transition-colors"
            title="Collapse sidebar"
          >
            <PanelLeftClose size={18} />
          </button>
        </div>
        <div className={clsx("flex", compactMode ? "gap-1" : "gap-2")}>
          <button 
            className={clsx("flex-1 primary-button rounded-full flex items-center justify-center gap-2", compactMode ? "py-1.5 px-3" : "py-2.5 px-4")}
            onClick={() => {
              startNewChat();
              navigate('/');
            }}
          >
            <Plus size={18} />
            <span>New chat</span>
          </button>
          <button className={clsx("bg-gray-900 dark:bg-slate-700 text-white rounded-full hover:bg-gray-800 dark:hover:bg-slate-600 transition-colors flex items-center justify-center", compactMode ? "w-[36px] h-[36px] p-2" : "w-[42px] h-[42px] p-2.5")}>
            <Search size={18} />
          </button>
        </div>
      </div>

      {/* Conversations List */}
      <div className={clsx("flex-1 overflow-y-auto px-4 mt-4", compactMode ? "space-y-0.5" : "space-y-1")}>
        <div className="flex items-center justify-between px-2 mb-3">
          <span className="text-[11px] font-semibold text-gray-400 dark:text-gray-500 uppercase tracking-wider">Projects</span>
          <button
            onClick={() => setIsCreatingProject(true)}
            className="text-[11px] font-semibold text-accent-500 hover:text-accent-600 transition-colors flex items-center gap-1"
          >
            <Plus size={12} /> New
          </button>
        </div>

        {/* Create project inline */}
        {isCreatingProject && (
          <div className="px-2 mb-2">
            <div className="flex gap-1">
              <input
                autoFocus
                value={newProjectName}
                onChange={(e) => setNewProjectName(e.target.value)}
                onKeyDown={(e) => { if (e.key === 'Enter') handleCreateProject(); if (e.key === 'Escape') { setIsCreatingProject(false); setNewProjectName(''); } }}
                placeholder="Project name..."
                className="flex-1 text-xs px-2 py-1 rounded border border-gray-300 dark:border-slate-700 bg-white dark:bg-slate-800 outline-none focus:border-accent-500 dark:text-gray-200"
              />
              <button onClick={handleCreateProject} className="text-xs px-2 py-1 bg-accent-600 text-white rounded hover:bg-accent-700">
                Add
              </button>
            </div>
          </div>
        )}

        {/* Project groups */}
        {projects.map(project => (
          <ProjectGroup
            key={project.project_id}
            project={project}
            conversations={projectConversationMap[project.project_id] || []}
          />
        ))}

        {/* Uncategorized conversations */}
        {uncategorizedConversations.length > 0 && (
          <UncategorizedGroup conversations={uncategorizedConversations} />
        )}

        {conversations.length === 0 && (
          <div className="text-sm text-gray-500 dark:text-gray-400 text-center py-6">No previous chats</div>
        )}

        {conversations.length > 0 && (
          <div className="px-2 mt-3">
            <button
              onClick={() => { if (confirm('Delete all conversations?')) clearAllConversations(); }}
              className="text-[11px] font-semibold text-red-500 hover:text-red-600 transition-colors"
            >
              Clear All
            </button>
          </div>
        )}
      </div>

      {/* Bottom Profile / Settings */}
      <div className={clsx("pt-2", compactMode ? "p-2" : "p-4")}>
        <button 
          onClick={() => navigate('/settings/general')}
          className={clsx(
            "w-full flex items-center gap-3 text-sm font-medium rounded-full transition-colors",
            compactMode ? "py-1.5 px-3 mb-2" : "py-2.5 px-4 mb-4",
            isSettingsActive ? "bg-accent-50 dark:bg-accent-500/20 text-accent-600 dark:text-accent-400 border border-accent-100 dark:border-accent-500/30" : "text-gray-600 dark:text-gray-400 hover:bg-gray-50 dark:hover:bg-slate-800 border border-transparent"
          )}
        >
          <Settings size={18} className={isSettingsActive ? "text-accent-600 dark:text-accent-400" : "text-gray-400 dark:text-gray-500"} />
          <span>Settings</span>
        </button>
        
        <UserProfileCard />
      </div>
    </div>
  );
}
