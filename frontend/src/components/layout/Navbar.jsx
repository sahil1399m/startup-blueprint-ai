import { useNavigate, useLocation } from 'react-router-dom'
import { useAuthStore } from '../../store/authStore'
import { authApi } from '../../api/auth'
import { Rocket, LayoutDashboard, History, Brain, LogOut } from 'lucide-react'

const NAV = [
  { path: '/dashboard', label: 'Blueprint',  icon: LayoutDashboard },
  { path: '/history',   label: 'History',    icon: History },
  { path: '/mentor',    label: 'AI Mentor',  icon: Brain },
]

export default function Navbar() {
  const navigate = useNavigate()
  const location = useLocation()
  const { user, logout } = useAuthStore()

  const handleLogout = async () => {
    try { await authApi.logout() } catch {}
    logout()
    navigate('/login')
  }

  return (
    <nav className="sticky top-0 z-50 border-b border-white/[0.062] bg-[#04040f]/80 backdrop-blur-xl">
      <div className="max-w-screen-xl mx-auto px-6 h-14 flex items-center justify-between gap-4">

        {/* Logo */}
        <button
          onClick={() => navigate('/dashboard')}
          className="flex items-center gap-2 font-extrabold text-base tracking-tight gradient-text-blue hover:opacity-90 transition-opacity"
        >
          <Rocket size={18} className="text-blue-400 flex-shrink-0" />
          Startup Blueprint
        </button>

        {/* Nav links */}
        <div className="hidden md:flex items-center gap-1">
          {NAV.map(({ path, label, icon: Icon }) => {
            const active = location.pathname.startsWith(path)
            return (
              <button
                key={path}
                onClick={() => navigate(path)}
                className={`flex items-center gap-1.5 px-3 py-1.5 rounded-lg text-xs font-600 transition-all duration-150
                  ${active
                    ? 'bg-blue-500/10 text-blue-400 border border-blue-500/20'
                    : 'text-slate-500 hover:text-slate-300 hover:bg-white/[0.038]'
                  }`}
              >
                <Icon size={13} />
                {label}
              </button>
            )
          })}
        </div>

        {/* Badges + user */}
        <div className="flex items-center gap-2">
          <span className="hidden sm:block badge badge-blue">IBM Granite</span>
          <span className="hidden sm:block badge badge-purple">Groq</span>
          <span className="hidden lg:block badge badge-green">CRAG</span>

          <div className="flex items-center gap-2 ml-2 pl-2 border-l border-white/[0.062]">
            <span className="hidden md:block text-xs text-slate-500 font-500">
              {user?.name?.split(' ')[0] || user?.email?.split('@')[0] || 'User'}
            </span>
            <button
              onClick={handleLogout}
              className="flex items-center gap-1.5 px-2.5 py-1.5 rounded-lg text-xs font-600 text-slate-500
                         hover:text-red-400 hover:bg-red-500/[0.08] border border-transparent
                         hover:border-red-500/20 transition-all duration-150"
              title="Sign out"
            >
              <LogOut size={13} />
              <span className="hidden sm:block">Sign out</span>
            </button>
          </div>
        </div>
      </div>
    </nav>
  )
}