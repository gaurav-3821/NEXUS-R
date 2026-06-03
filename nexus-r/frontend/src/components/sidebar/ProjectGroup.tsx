import { useState } from 'react';
import { MessageSquare, Trash2, ChevronDown, ChevronRight, Folder, X, FolderPlus } from 'lucide-react';
import clsx from 'clsx';
import { useNavigate } from 'react-router-dom';
import { useAppStore } from '../../store/useAppStore';
import { useProjectsStore } from '../../store/projectsStore';
import type { Project } from '../../api/projects';

interface ProjectConversation {
  id: string;
  title: string;
}

export function ProjectGroup({ project, conversations }: { project: Project; conversations: ProjectConversation[] }) {
  const [isOpen, setIsOpen] = useState(true);
  const { deleteConversation } = useAppStore();
  const { removeProject } = useProjectsStore();
  const navigate = useNavigate();

  return (
    <div>
      <div className="flex items-center gap-1 px-2 py-1 group">
        <button onClick={() => setIsOpen(!isOpen)} className="text-gray-400 dark:text-gray-500 hover:text-gray-600 dark:hover:text-gray-300">
          {isOpen ? <ChevronDown size={14} /> : <ChevronRight size={14} />}
        </button>
        <Folder size={14} className="text-gray-400 dark:text-gray-500 shrink-0" />
        <span className="text-xs font-semibold text-gray-500 dark:text-gray-400 truncate flex-1">{project.name}</span>
        <button
          onClick={() => { if (confirm('Delete project? Conversations become uncategorized.')) removeProject(project.project_id); }}
          className="opacity-0 group-hover:opacity-100 text-gray-400 hover:text-red-500 transition-opacity"
          title="Delete project"
        >
          <X size={12} />
        </button>
      </div>
      {isOpen && (
        <div className="ml-2 space-y-0.5">
          {conversations.length === 0 ? (
            <div className="text-xs text-gray-400 dark:text-gray-500 italic px-2 py-1">No conversations</div>
          ) : (
            conversations.map(conv => (
              <ConversationRow key={conv.id} conv={conv} projectId={project.project_id} />
            ))
          )}
        </div>
      )}
    </div>
  );
}

export function UncategorizedGroup({ conversations }: { conversations: ProjectConversation[] }) {
  const [isOpen, setIsOpen] = useState(true);

  return (
    <div>
      <div className="flex items-center gap-1 px-2 py-1">
        <button onClick={() => setIsOpen(!isOpen)} className="text-gray-400 dark:text-gray-500 hover:text-gray-600 dark:hover:text-gray-300">
          {isOpen ? <ChevronDown size={14} /> : <ChevronRight size={14} />}
        </button>
        <MessageSquare size={14} className="text-gray-400 dark:text-gray-500 shrink-0" />
        <span className="text-xs font-semibold text-gray-500 dark:text-gray-400 truncate flex-1">Uncategorized</span>
        <span className="text-[10px] text-gray-400">{conversations.length}</span>
      </div>
      {isOpen && (
        <div className="ml-2 space-y-0.5">
          {conversations.map(conv => (
            <ConversationRow key={conv.id} conv={conv} />
          ))}
        </div>
      )}
    </div>
  );
}

function ConversationRow({ conv, projectId }: { conv: ProjectConversation; projectId?: string }) {
  const { currentConversationId, setCurrentConversation, loadConversationMessages, deleteConversation } = useAppStore();
  const { projects, addConversation, removeConversation } = useProjectsStore();
  const navigate = useNavigate();
  const [showProjectPicker, setShowProjectPicker] = useState(false);

  const assignableProjects = projectId
    ? projects.filter(p => p.project_id !== projectId)
    : projects;

  const handleAssign = async (targetProjectId: string) => {
    await addConversation(targetProjectId, conv.id);
    if (projectId) {
      await removeConversation(projectId, conv.id);
    }
    setShowProjectPicker(false);
  };

  return (
    <div className="relative">
      <button
        onClick={() => {
          setCurrentConversation(conv.id);
          loadConversationMessages(conv.id);
          navigate('/');
        }}
        className={clsx(
          "w-full text-left rounded-lg flex items-center gap-2 group transition-colors py-1.5 px-2",
          currentConversationId === conv.id
            ? "bg-accent-50 dark:bg-accent-500/20 text-accent-600 dark:text-accent-400"
            : "text-gray-600 dark:text-gray-100 hover:bg-gray-50 dark:hover:bg-slate-800"
        )}
      >
        <MessageSquare size={13} className="shrink-0 text-gray-400 dark:text-gray-500" />
        <span className="truncate flex-1 text-xs font-medium">{conv.title || "New Conversation"}</span>
        {projects.length > 0 && (
          <FolderPlus
            size={12}
            className="opacity-0 group-hover:opacity-100 text-gray-400 hover:text-accent-500 transition-opacity shrink-0"
            onClick={(e) => {
              e.stopPropagation();
              setShowProjectPicker(!showProjectPicker);
            }}
            title="Move to project"
          />
        )}
        <Trash2
          size={12}
          className="opacity-0 group-hover:opacity-100 hover:text-red-500 transition-opacity shrink-0"
          onClick={(e) => {
            e.stopPropagation();
            if (confirm('Delete this conversation?')) deleteConversation(conv.id);
          }}
        />
      </button>
      {showProjectPicker && (
        <div className="absolute right-0 top-full z-50 mt-1 bg-white dark:bg-slate-800 border border-gray-200 dark:border-slate-700 rounded-lg shadow-lg py-1 min-w-[140px]">
          {assignableProjects.length === 0 ? (
            <div className="text-xs text-gray-400 px-3 py-1">No other projects</div>
          ) : (
            assignableProjects.map(p => (
              <button
                key={p.project_id}
                onClick={() => handleAssign(p.project_id)}
                className="w-full text-left text-xs px-3 py-1.5 hover:bg-gray-100 dark:hover:bg-slate-700 text-gray-700 dark:text-gray-300 flex items-center gap-2"
              >
                <Folder size={12} /> {p.name}
              </button>
            ))
          )}
        </div>
      )}
    </div>
  );
}
