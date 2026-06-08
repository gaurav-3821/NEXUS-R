import { describe, it, expect, beforeEach } from 'vitest'
import { useAppearanceStore } from './appearanceStore'
import { act } from '@testing-library/react'

describe('useAppearanceStore', () => {
  beforeEach(() => {
    useAppearanceStore.setState({
      theme: 'system',
      accentColor: 'blue',
      fontSize: 'medium',
    })
  })

  it('should initialize with default appearance settings', () => {
    const state = useAppearanceStore.getState()
    expect(state.theme).toBe('system')
    expect(state.accentColor).toBe('blue')
    expect(state.fontSize).toBe('medium')
  })

  it('should set theme', () => {
    act(() => {
      useAppearanceStore.getState().setTheme('dark')
    })
    expect(useAppearanceStore.getState().theme).toBe('dark')

    act(() => {
      useAppearanceStore.getState().setTheme('light')
    })
    expect(useAppearanceStore.getState().theme).toBe('light')
  })

  it('should set accent color', () => {
    act(() => {
      useAppearanceStore.getState().setAccentColor('purple')
    })
    expect(useAppearanceStore.getState().accentColor).toBe('purple')
  })

  it('should set font size', () => {
    act(() => {
      useAppearanceStore.getState().setFontSize('large')
    })
    expect(useAppearanceStore.getState().fontSize).toBe('large')
  })

  it('should validate theme values', () => {
    const validThemes = ['light', 'dark', 'system']
    validThemes.forEach((theme) => {
      act(() => {
        useAppearanceStore.getState().setTheme(theme as any)
      })
      expect(useAppearanceStore.getState().theme).toBe(theme)
    })
  })
})
