import { useRef, useCallback, useState } from 'react'

/**
 * useSSE — generic SSE hook using fetch() + ReadableStream.
 *
 * Usage:
 *   const { start, cancel, isStreaming } = useSSE(url, payload, {
 *     onProgress, onComplete, onError
 *   })
 *
 * Uses fetch (not EventSource) because POST method is needed.
 */
export function useSSE(url, payload, { onProgress, onComplete, onError } = {}) {
  const [isStreaming, setIsStreaming] = useState(false)
  const ctrlRef = useRef(null)

  const start = useCallback(() => {
    const token = localStorage.getItem('access_token')
    const baseUrl = import.meta.env.VITE_API_URL || ''
    const ctrl = new AbortController()
    ctrlRef.current = ctrl
    setIsStreaming(true)

    fetch(`${baseUrl}${url}`, {
      method: 'POST',
      headers: {
        'Content-Type': 'application/json',
        Authorization: `Bearer ${token}`,
      },
      body: JSON.stringify(payload),
      signal: ctrl.signal,
    })
      .then(async (res) => {
        if (!res.ok) {
          const err = await res.json().catch(() => ({}))
          onError?.(err.detail || `Server error ${res.status}`)
          setIsStreaming(false)
          return
        }

        const reader = res.body.getReader()
        const decoder = new TextDecoder()
        let buffer = ''

        while (true) {
          const { done, value } = await reader.read()
          if (done) break

          buffer += decoder.decode(value, { stream: true })
          const lines = buffer.split('\n\n')
          buffer = lines.pop()

          for (const line of lines) {
            if (!line.startsWith('data: ')) continue
            try {
              const event = JSON.parse(line.slice(6))
              if (event.event === 'progress') {
                onProgress?.(event)
              } else if (event.event === 'complete') {
                onComplete?.(event.data)
              } else if (event.event === 'error') {
                onError?.(event.error || 'Stream failed')
              }
            } catch (e) {
              console.warn('SSE parse error:', e)
            }
          }
        }
        setIsStreaming(false)
      })
      .catch((err) => {
        if (err.name !== 'AbortError') {
          onError?.(err.message || 'Network error')
        }
        setIsStreaming(false)
      })

    return ctrl
  }, [url, payload, onProgress, onComplete, onError])

  const cancel = useCallback(() => {
    ctrlRef.current?.abort()
    setIsStreaming(false)
  }, [])

  return { start, cancel, isStreaming }
}
