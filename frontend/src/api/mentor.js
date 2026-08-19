import client from './client'

export const mentorApi = {
  chat:     (payload)     => client.post('/api/mentor/chat', payload),
  sessions: (blueprintId) => client.get(`/api/mentor/sessions/${blueprintId}`),
  deleteSession: (id)     => client.delete(`/api/mentor/session/${id}`),
}