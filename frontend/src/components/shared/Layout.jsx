import { Outlet, NavLink, useNavigate } from 'react-router-dom'
import { useAuth } from '../../context/AuthContext'
import {
  LayoutDashboard, FileText, FilePlus, ClipboardList, FolderOpen,
  LogOut, ChevronRight, User, Users, Shield, KeyRound, Network, Search
} from 'lucide-react'

const navItems = [
  { to: '/',             label: 'Dashboard',   icon: LayoutDashboard, roles: ['admin','staff','approver'] },
  { to: '/search',       label: 'Search',      icon: Search,          roles: ['admin','staff','approver'] },
  { to: '/templates',    label: 'Templates',   icon: FileText,        roles: ['admin'] },
  { to: '/submissions/new', label: 'New Form', icon: FilePlus,        roles: ['admin','staff'] },
  { to: '/submissions',  label: 'Submissions', icon: ClipboardList,   roles: ['admin','staff','approver'] },
  { to: '/answersets',   label: 'Answersets',  icon: FolderOpen,      roles: ['admin','staff','approver'] },
  { to: '/users',         label: 'Users',       icon: Users,           roles: ['admin'] },
  { to: '/roles',         label: 'Roles',       icon: Shield,          roles: ['admin'] },
  { to: '/workgroups',    label: 'Workgroups',  icon: Network,         roles: ['admin'] },
]

export default function Layout() {
  const { user, logout } = useAuth()
  const navigate = useNavigate()

  const handleLogout = () => { logout(); navigate('/login') }

  const visible = navItems.filter(n => n.roles.includes(user?.role))

  return (
    <div className="flex h-screen bg-brand-50">
      {/* Sidebar */}
      <aside className="w-60 bg-white border-r border-brand-200 flex flex-col">
        {/* Logo */}
        <div className="px-5 py-5 border-b border-brand-100">
          <div className="flex items-center gap-2">
            <img src="/favicon-96x96.png" alt="DocForm" className="w-8 h-8" />
            <span className="font-bold text-brand-900 text-lg">DocForm</span>
          </div>
        </div>

        {/* Nav */}
        <nav className="flex-1 px-3 py-4 space-y-0.5">
          {visible.map(({ to, label, icon: Icon }) => (
            <NavLink
              key={to}
              to={to}
              end={to === '/'}
              className={({ isActive }) =>
                `flex items-center gap-3 px-3 py-2 rounded-lg text-sm font-medium transition-colors group ${
                  isActive
                    ? 'bg-brand-50 text-brand-700'
                    : 'text-brand-600 hover:bg-brand-50 hover:text-brand-900'
                }`
              }
            >
              {({ isActive }) => (
                <>
                  <Icon size={17} className={isActive ? 'text-brand-600' : 'text-brand-400 group-hover:text-brand-600'} />
                  <span className="flex-1">{label}</span>
                  {isActive && <ChevronRight size={14} className="text-brand-400" />}
                </>
              )}
            </NavLink>
          ))}
        </nav>

        {/* User footer */}
        <div className="border-t border-brand-100 px-3 py-3">
          <div className="flex items-center gap-3 px-2 py-2 rounded-lg">
            <div className="w-8 h-8 bg-brand-100 rounded-full flex items-center justify-center">
              <User size={15} className="text-brand-700" />
            </div>
            <div className="flex-1 min-w-0">
              <p className="text-sm font-medium text-brand-900 truncate">{user?.name}</p>
              <p className="text-xs text-brand-400 capitalize">{user?.role}</p>
            </div>
            <NavLink to="/change-password" title="Change password"
              className="text-brand-400 hover:text-brand-600 transition-colors">
              <KeyRound size={16} />
            </NavLink>
            <button onClick={handleLogout} title="Sign out"
              className="text-brand-400 hover:text-red-500 transition-colors">
              <LogOut size={16} />
            </button>
          </div>
        </div>
      </aside>

      {/* Main */}
      <main className="flex-1 overflow-y-auto">
        <div className="max-w-5xl mx-auto px-8 py-8">
          <Outlet />
        </div>
      </main>
    </div>
  )
}
