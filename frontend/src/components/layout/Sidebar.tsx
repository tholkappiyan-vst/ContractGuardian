import { Link, useLocation } from 'react-router-dom'
import { cn } from '@/lib/utils'
import {
  LayoutDashboard, Upload, FileText, AlertTriangle,
  GitCompare, Scale, Shield,
} from 'lucide-react'

const links = [
  { to: '/dashboard', icon: LayoutDashboard, label: 'Dashboard' },
  { to: '/upload', icon: Upload, label: 'Upload' },
  { to: '/contracts', icon: FileText, label: 'Contracts' },
  { to: '/risks', icon: AlertTriangle, label: 'Risk Overview' },
  { to: '/compare', icon: GitCompare, label: 'Compare' },
  { to: '/negotiate', icon: Scale, label: 'Negotiate' },
]

export function Sidebar() {
  const { pathname } = useLocation()

  return (
    <aside className="w-64 bg-white border-r border-gray-200 min-h-[calc(100vh-4rem)] p-4">
      <nav className="space-y-1">
        {links.map(({ to, icon: Icon, label }) => (
          <Link
            key={to}
            to={to}
            className={cn(
              'flex items-center gap-3 px-3 py-2.5 rounded-lg text-sm font-medium transition-colors',
              pathname.startsWith(to)
                ? 'bg-brand-50 text-brand-700'
                : 'text-gray-600 hover:bg-gray-50 hover:text-gray-900'
            )}
          >
            <Icon className="w-5 h-5" />
            {label}
          </Link>
        ))}
      </nav>

      <div className="mt-8 p-4 bg-brand-50 rounded-xl">
        <div className="flex items-center gap-2 mb-2">
          <Shield className="w-5 h-5 text-brand-600" />
          <span className="text-sm font-semibold text-brand-900">Pro Tip</span>
        </div>
        <p className="text-xs text-brand-700 leading-relaxed">
          Upload your contract and ask questions in plain language. Our AI explains everything without legal jargon.
        </p>
      </div>
    </aside>
  )
}
