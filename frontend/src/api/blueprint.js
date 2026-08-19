import client from './client'

export const blueprintApi = {
  getById: (id) => client.get(`/api/blueprint/${id}`),
  getNews:  (q) => client.get('/api/blueprint/news/feed', { params: { q } }),
}

/**
 * generateBlueprint — SSE streaming blueprint generation.
 *
 * Uses fetch() + ReadableStream because EventSource doesn't support POST.
 * Calls onProgress(event) for each SSE frame, onComplete(blueprint) when done,
 * onError(message) on failure.
 *
 * Returns an AbortController so the caller can cancel mid-stream.
 */
export function generateBlueprint(payload, { onProgress, onComplete, onError }) {
  const token = localStorage.getItem('access_token')
  const baseUrl = import.meta.env.VITE_API_URL || ''
  const ctrl = new AbortController()

  fetch(`${baseUrl}/api/blueprint/generate`, {
    method:  'POST',
    headers: {
      'Content-Type':  'application/json',
      Authorization:   `Bearer ${token}`,
    },
    body:   JSON.stringify(payload),
    signal: ctrl.signal,
  })
    .then(async (res) => {
      if (!res.ok) {
        const err = await res.json().catch(() => ({}))
        onError(err.detail || `Server error ${res.status}`)
        return
      }

      const reader  = res.body.getReader()
      const decoder = new TextDecoder()
      let   buffer  = ''

      while (true) {
        const { done, value } = await reader.read()
        if (done) break

        buffer += decoder.decode(value, { stream: true })
        const lines = buffer.split('\n\n')
        buffer = lines.pop()   // keep incomplete last chunk

        for (const line of lines) {
          const trimmed = line.trim()
          if (!trimmed.startsWith('data: ')) continue
          try {
            const event = JSON.parse(trimmed.slice(6))
            if (event.event === 'progress') {
              onProgress(event)
            } else if (event.event === 'complete') {
              let payload = event.data
              if (typeof payload === 'string') {
                try { payload = JSON.parse(payload) } catch (e) {}
              }
              onComplete(payload)
            } else if (event.event === 'error') {
              onError(event.error || 'Generation failed')
            }
          } catch (e) {
            console.warn('SSE parse error:', e)
          }
        }
      }
    })
    .catch((err) => {
      if (err.name !== 'AbortError') onError(err.message || 'Network error')
    })

  return ctrl   // caller can call ctrl.abort() to cancel
}