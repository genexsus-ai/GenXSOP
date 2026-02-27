import api from './api'
import type { LoginRequest, LoginResponse, RegisterRequest, User } from '@/types'

export const authService = {
  async login(data: LoginRequest): Promise<LoginResponse> {
    // Backend expects JSON with email + password
    const res = await api.post<LoginResponse>('/auth/login', {
      email: data.username,
      password: data.password,
    })
    return res.data
  },

  async register(data: RegisterRequest): Promise<User> {
    const res = await api.post<User>('/auth/register', data)
    return res.data
  },

  async getMe(): Promise<User> {
    const res = await api.get<User>('/auth/me')
    return res.data
  },

  async updateMe(data: Partial<User>): Promise<User> {
    const res = await api.put<User>('/auth/me', data)
    return res.data
  },

  async changePassword(currentPassword: string, newPassword: string): Promise<void> {
    await api.post('/auth/change-password', {
      current_password: currentPassword,
      new_password: newPassword,
    })
  },

  async listUsers(): Promise<User[]> {
    const res = await api.get<User[]>('/auth/users')
    return res.data
  },
}
