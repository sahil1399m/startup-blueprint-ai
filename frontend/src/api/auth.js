import client from './client'

export const authApi = {
  login:            (email, password)                 => client.post('/api/auth/login', { email, password }),
  register:         (name, email, password)           => client.post('/api/auth/register', { name, email, password }),
  getGoogleAuthUrl: (redirectUri)                     => client.get('/api/auth/google/url', { params: { redirect_uri: redirectUri } }),
  googleCallback:   (code, redirectUri, state)        => client.post('/api/auth/google', { code, redirect_uri: redirectUri, state }),
  google:           (code, redirectUri, state)        => client.post('/api/auth/google', { code, redirect_uri: redirectUri, state }),
  me:               ()                                => client.get('/api/auth/me'),
  logout:           ()                                => client.post('/api/auth/logout'),
  getPublicConfig:  ()                                => client.get('/api/config/public'),
}