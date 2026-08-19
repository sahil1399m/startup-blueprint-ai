import client from './client'

export const historyApi = {
  list:      (params)  => client.get('/api/history', { params }),
  getById:   (id)      => client.get(`/api/history/${id}`),
  delete:    (id)      => client.delete(`/api/history/${id}`),
  deleteAll: ()        => client.delete('/api/history'),
  export:    (id)      => client.get(`/api/history/${id}/export`),
}

export const mentorApi = {
  chat:     (payload)     => client.post('/api/mentor/chat', payload),
  sessions: (blueprintId) => client.get(`/api/mentor/sessions/${blueprintId}`),
  deleteSession: (id)     => client.delete(`/api/mentor/session/${id}`),
}