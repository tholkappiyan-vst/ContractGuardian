import { Link } from 'react-router-dom'
import { Shield, LogOut, User } from 'lucide-react'
import { useAuth } from '@/lib/store'

export function Navbar() {
  const { user, logout } = useAuth()

  return (
    <header className="bg-white border-b border-gray-200 sticky top-0 z-50">
      <div className="max-w-7xl mx-auto px-4 sm:px-6 lg:px-8">
        <div className="flex items-center justify-between h-16">
          <Link to="/" className="flex items-center gap-2">
            <Shield className="w-8 h-8 text-brand-600" />
            <span className="text-xl font-bold text-gray-900">ContractAI</span>
          </Link>

          <nav className="hidden md:flex items-center gap-6">
            {user ? (
              <>
                <Link to="/dashboard" className="text-sm font-medium text-gray-700 hover:text-brand-600">Dashboard</Link>
                <Link to="/upload" className="text-sm font-medium text-gray-700 hover:text-brand-600">Upload</Link>
                <Link to="/compare" className="text-sm font-medium text-gray-700 hover:text-brand-600">Compare</Link>
                <div className="flex items-center gap-3 ml-4 pl-4 border-l">
                  <div className="flex items-center gap-2">
                    <User className="w-4 h-4 text-gray-400" />
                    <span className="text-sm text-gray-600">{user.full_name}</span>
                  </div>
                  <button onClick={logout} className="btn-ghost p-1.5">
                    <LogOut className="w-4 h-4" />
                  </button>
                </div>
              </>
            ) : (
              <>
                <Link to="/login" className="text-sm font-medium text-gray-700 hover:text-brand-600">Log In</Link>
                <Link to="/register" className="btn-primary text-sm">Get Started Free</Link>
              </>
            )}
          </nav>
        </div>
      </div>
    </header>
  )
}
