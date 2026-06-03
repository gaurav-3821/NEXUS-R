import { create } from 'zustand';
import { getProjects, createProject, deleteProject, addConversationToProject, removeConversationFromProject } from '../api/projects';
import type { Project } from '../api/projects';

interface ProjectsState {
  projects: Project[];
  isLoading: boolean;
}

interface ProjectsActions {
  loadProjects: () => Promise<void>;
  addProject: (name: string, description?: string) => Promise<Project | null>;
  removeProject: (projectId: string) => Promise<void>;
  addConversation: (projectId: string, conversationId: string) => Promise<void>;
  removeConversation: (projectId: string, conversationId: string) => Promise<void>;
  getProjectForConversation: (conversationId: string) => Project | undefined;
}

export const useProjectsStore = create<ProjectsState & ProjectsActions>((set, get) => ({
  projects: [],
  isLoading: false,

  loadProjects: async () => {
    try {
      const data = await getProjects();
      set({ projects: data.projects || [] });
    } catch (e) {
      console.error('Failed to load projects:', e);
    }
  },

  addProject: async (name: string, description?: string) => {
    try {
      const project = await createProject(name, description);
      set((state) => ({ projects: [...state.projects, project] }));
      return project;
    } catch (e) {
      console.error('Failed to create project:', e);
      return null;
    }
  },

  removeProject: async (projectId: string) => {
    try {
      await deleteProject(projectId);
      set((state) => ({ projects: state.projects.filter(p => p.project_id !== projectId) }));
    } catch (e) {
      console.error('Failed to delete project:', e);
    }
  },

  addConversation: async (projectId: string, conversationId: string) => {
    try {
      await addConversationToProject(projectId, conversationId);
      set((state) => ({
        projects: state.projects.map(p =>
          p.project_id === projectId
            ? { ...p, conversation_ids: [...p.conversation_ids, conversationId] }
            : p
        ),
      }));
    } catch (e) {
      console.error('Failed to add conversation to project:', e);
    }
  },

  removeConversation: async (projectId: string, conversationId: string) => {
    try {
      await removeConversationFromProject(projectId, conversationId);
      set((state) => ({
        projects: state.projects.map(p =>
          p.project_id === projectId
            ? { ...p, conversation_ids: p.conversation_ids.filter(c => c !== conversationId) }
            : p
        ),
      }));
    } catch (e) {
      console.error('Failed to remove conversation from project:', e);
    }
  },

  getProjectForConversation: (conversationId: string) => {
    return get().projects.find(p => p.conversation_ids.includes(conversationId));
  },
}));
