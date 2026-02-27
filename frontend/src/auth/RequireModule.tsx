import { Navigate, Outlet } from 'react-router-dom'
import { useAuthStore } from '@/store/authStore'
import type { AppModule } from './permissions'
import { canAccessModule } from './permissions'

export function RequireModule({ module }: { module: AppModule }) {
  const { user } = useAuthStore()

  // AppLayout handles authentication. Here we only gate by role/module.
  if (!canAccessModule(user?.role, module)) {
    return <Navigate to="/" replace />
  }

  return <Outlet />
}
