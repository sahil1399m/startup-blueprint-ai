import client from './client'

export const authApi = {
  login:    (email, password)     => client.post('/api/auth/login',    { email, password }),
  register: (name, email, password) => client.post('/api/auth/register', { name, email, password }),
  google:   (code)                => client.post('/api/auth/google',   { code }),
  me:       ()                    => client.get('/api/auth/me'),
  logout:   ()                    => client.post('/api/auth/logout'),
}