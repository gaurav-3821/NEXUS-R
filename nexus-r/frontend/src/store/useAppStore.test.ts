import { describe, it, expect, vi, beforeEach } from 'vitest'
import { useAppStore } from './useAppStore'
import { act } from '@testing-library/react'

describe('useAppStore', () => {
  beforeEach(() => {
    useAppStore.setState({
      conversations: [],
      currentConversationId: null,
      isSidebarOpen: true,
      totalSessionCost: 0,
      isLoading: false,
    })
  })

  it('should initialize with default state', () => {
    const state = useAppStore.getState()
    expect(state.conversations).toEqual([])
    expect(state.currentConversationId).toBeNull()
    expect(state.isSidebarOpen).toBe(true)
    expect(state.totalSessionCost).toBe(0)
    expect(state.isLoading).toBe(false)
  })

  it('should toggle sidebar', () => {
    act(() => {
      useAppStore.getState().toggleSidebar()
    })
    expect(useAppStore.getState().isSidebarOpen).toBe(false)

    act(() => {
      useAppStore.getState().toggleSidebar()
    })
    expect(useAppStore.getState().isSidebarOpen).toBe(true)
  })

  it('should add a conversation', () => {
    const conversation = {
      id: 'test-1',
      title: 'Test Conversation',
      messages: [],
      createdAt: new Date().toISOString(),
    }
    act(() => {
      useAppStore.getState().addConversation(conversation)
    })
    expect(useAppStore.getState().conversations).toHaveLength(1)
    expect(useAppStore.getState().conversations[0].id).toBe('test-1')
  })

  it('should set loading state', () => {
    act(() => {
      useAppStore.getState().setLoading(true)
    })
    expect(useAppStore.getState().isLoading).toBe(true)

    act(() => {
      useAppStore.getState().setLoading(false)
    })
    expect(useAppStore.getState().isLoading).toBe(false)
  })

  it('should update session cost', () => {
    act(() => {
      useAppStore.getState().setTotalSessionCost(1.5)
    })
    expect(useAppStore.getState().totalSessionCost).toBe(1.5)
  })
})
