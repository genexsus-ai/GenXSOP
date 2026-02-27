import { NavLink } from 'react-router-dom'
import { clsx } from 'clsx'
import {
  LayoutDashboard, TrendingUp, Factory, Package,
  Brain, GitBranch, ClipboardList, BarChart3,
  ShoppingBag, Settings, ChevronLeft, ChevronRight,
  Zap,
} from 'lucide-react'
import { useUIStore } from '@/store/uiStore'
import { useAuthStore } from '@/store/authStore'
import type { AppModule } from '@/auth/permissions'
import { canAccessModule } from '@/auth/permissions'

const navItems: Array<{ to: string; label: string; icon: any; end?: boolean; module: AppModule }> = [
  { to: '/',            label: 'Dashboard',        icon: LayoutDashboard, end: true, module: 'dashboard' },
  { to: '/demand',      label: 'Demand Planning',  icon: TrendingUp, module: 'demand' },
  { to: '/supply',      label: 'Supply Planning',  icon: Factory, module: 'supply' },
  { to: '/inventory',   label: 'Inventory',        icon: Package, module: 'inventory' },
  { to: '/forecasting', label: 'Forecasting',      icon: Brain, module: 'forecasting' },
  { to: '/scenarios',   label: 'Scenarios',        icon: GitBranch, module: 'scenarios' },
  { to: '/sop-cycle',   label: 'S&OP Cycle',       icon: ClipboardList, module: 'sop_cycle' },
  { to: '/kpi',         label: 'KPI Dashboard',    icon: BarChart3, module: 'kpi' },
  { to: '/products',    label: 'Products',         icon: ShoppingBag, module: 'products' },
  { to: '/settings',    label: 'Settings',         icon: Settings, module: 'settings' },
]

export function Sidebar() {
  const { sidebarCollapsed, toggleSidebar } = useUIStore()
  const { user } = useAuthStore()

  const visibleItems = navItems.filter((i) => canAccessModule(user?.role, i.module))

  return (
    <aside
      className={clsx(
        'flex flex-col bg-gray-900 text-white transition-all duration-300 ease-in-out',
        sidebarCollapsed ? 'w-16' : 'w-60',
      )}
    >
      {/* Logo */}
      <div className="flex items-center justify-between px-4 py-5 border-b border-gray-800">
        {!sidebarCollapsed && (
          <div className="flex items-center gap-2">
            <div className="p-1.5 bg-blue-600 rounded-lg">
              <Zap className="h-4 w-4 text-white" />
            </div>
            <span className="font-bold text-sm tracking-tight">GenXSOP</span>
          </div>
        )}
        {sidebarCollapsed && (
          <div className="mx-auto p-1.5 bg-blue-600 rounded-lg">
            <Zap className="h-4 w-4 text-white" />
          </div>
        )}
        {!sidebarCollapsed && (
          <button
            onClick={toggleSidebar}
            className="p-1 rounded text-gray-400 hover:text-white hover:bg-gray-800 transition-colors"
          >
            <ChevronLeft className="h-4 w-4" />
          </button>
        )}
      </div>

      {/* Nav */}
      <nav className="flex-1 py-4 overflow-y-auto scrollbar-thin">
        <ul className="space-y-0.5 px-2">
          {visibleItems.map(({ to, label, icon: Icon, end }) => (
            <li key={to}>
              <NavLink
                to={to}
                end={end}
                className={({ isActive }) =>
                  clsx(
                    'flex items-center gap-3 px-3 py-2.5 rounded-lg text-sm font-medium transition-colors',
                    isActive
                      ? 'bg-blue-600 text-white'
                      : 'text-gray-400 hover:text-white hover:bg-gray-800',
                    sidebarCollapsed && 'justify-center',
                  )
                }
                title={sidebarCollapsed ? label : undefined}
              >
                <Icon className="h-4 w-4 flex-shrink-0" />
                {!sidebarCollapsed && <span>{label}</span>}
              </NavLink>
            </li>
          ))}
        </ul>
      </nav>

      {/* Collapse toggle (when collapsed) */}
      {sidebarCollapsed && (
        <div className="px-2 pb-4">
          <button
            onClick={toggleSidebar}
            className="w-full flex items-center justify-center p-2 rounded-lg text-gray-400 hover:text-white hover:bg-gray-800 transition-colors"
          >
            <ChevronRight className="h-4 w-4" />
          </button>
        </div>
      )}

      {/* Version */}
      {!sidebarCollapsed && (
        <div className="px-4 py-3 border-t border-gray-800">
          <p className="text-xs text-gray-600">GenXSOP v1.0.0</p>
        </div>
      )}
    </aside>
  )
}
