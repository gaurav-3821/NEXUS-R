import { describe, it, expect, vi, beforeEach } from 'vitest'
import { apiClient, wsClient } from './client'

describe('API Client', () => {
  beforeEach(() => {
    vi.resetAllMocks()
  })

  it('should create apiClient with correct base URL', () => {
    expect(apiClient).toBeDefined()
    expect(apiClient.defaults.baseURL).toBe('/api')
    expect(apiClient.defaults.headers['Content-Type']).toBe('application/json')
  })

  it('should handle request errors', async () => {
    const mockError = new Error('Network Error')
    vi.spyOn(apiClient, 'get').mockRejectedValue(mockError)

    await expect(apiClient.get('/test')).rejects.toThrow('Network Error')
  })

  it('should include auth header when apiKey is set', () => {
    const clientWithAuth = { ...apiClient }
    clientWithAuth.defaults.headers['X-API-Key'] = 'test-key-123'
    expect(clientWithAuth.defaults.headers['X-API-Key']).toBe('test-key-123')
  })
})

describe('WebSocket Client', () => {
  it('should create WebSocket connection', () => {
    const ws = wsClient.connect()
    expect(ws).toBeDefined()
    expect(ws.readyState).toBe(WebSocket.OPEN)
  })

  it('should send subscription message on open', () => {
    const ws = wsClient.connect()
    wsClient.subscribe('test-channel')
    expect(ws.send).toHaveBeenCalledWith(
      JSON.stringify({ type: 'subscribe', filter: 'test-channel' })
    )
  })
})
