import { describe, it, expect } from 'vitest'
import { cn, formatDate, truncateText, debounce } from './cn'

describe('cn() - class name merging', () => {
  it('should merge class names', () => {
    expect(cn('foo', 'bar')).toBe('foo bar')
  })

  it('should handle conditional classes', () => {
    expect(cn('foo', false && 'bar', 'baz')).toBe('foo baz')
    expect(cn('foo', true && 'bar', 'baz')).toBe('foo bar baz')
  })

  it('should handle undefined and null', () => {
    expect(cn('foo', undefined, null, 'bar')).toBe('foo bar')
  })

  it('should merge tailwind classes correctly', () => {
    expect(cn('px-2 py-1', 'px-4')).toBe('py-1 px-4')
  })
})

describe('formatDate()', () => {
  it('should format ISO date string', () => {
    const result = formatDate('2026-01-15T10:30:00Z')
    expect(result).toContain('2026')
    expect(result).toContain('15')
  })

  it('should handle invalid date', () => {
    expect(formatDate('invalid')).toBe('Invalid date')
  })

  it('should handle Date object', () => {
    const date = new Date('2026-06-08')
    const result = formatDate(date)
    expect(result).toContain('2026')
  })
})

describe('truncateText()', () => {
  it('should not truncate short text', () => {
    expect(truncateText('hello', 10)).toBe('hello')
  })

  it('should truncate long text with ellipsis', () => {
    expect(truncateText('hello world this is long', 10)).toBe('hello worl...')
  })

  it('should handle empty string', () => {
    expect(truncateText('', 10)).toBe('')
  })
})

describe('debounce()', () => {
  it('should delay function execution', () => {
    vi.useFakeTimers()
    const fn = vi.fn()
    const debounced = debounce(fn, 100)

    debounced()
    expect(fn).not.toHaveBeenCalled()

    vi.advanceTimersByTime(100)
    expect(fn).toHaveBeenCalledTimes(1)

    vi.useRealTimers()
  })

  it('should reset timer on multiple calls', () => {
    vi.useFakeTimers()
    const fn = vi.fn()
    const debounced = debounce(fn, 100)

    debounced()
    vi.advanceTimersByTime(50)
    debounced()
    vi.advanceTimersByTime(50)
    debounced()
    vi.advanceTimersByTime(100)

    expect(fn).toHaveBeenCalledTimes(1)
    vi.useRealTimers()
  })
})
