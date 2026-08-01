import { useEffect, useState } from 'react'
import { Link } from 'react-router-dom'
import { Upload, FileText, AlertTriangle, TrendingUp } from 'lucide-react'
import { api } from '@/lib/api'
import { useAuth } from '@/lib/store'
import { RiskBadge } from '@/components/ui/RiskBadge'
import { LoadingSpinner } from '@/components/ui/LoadingSpinner'
import { formatDate } from '@/lib/utils'
import type { Contract } from '@/types'

export function Dashboard() {
  const { user } = useAuth()
  const [contracts, setContracts] = useState<Contract[]>([])
  const [loading, setLoading] = useState(true)

  useEffect(() => {
    api.listContracts().then(r => { setContracts(r.contracts); setLoading(false) })
  }, [])

  const analyzed = contracts.filter(c => c.status === 'analyzed')
  const highRisk = analyzed.filter(c => (c.risk_score ?? 0) > 60)
  const avgRisk = analyzed.length
    ? Math.round(analyzed.reduce((sum, c) => sum + (c.risk_score ?? 0), 0) / analyzed.length)
    : 0

  if (loading) return <LoadingSpinner className="mt-20" />

  return (
    <div className="space-y-8">
      <div className="flex items-center justify-between">
        <div>
          <h1 className="text-2xl font-bold text-gray-900">Welcome back, {user?.full_name?.split(' ')[0]}</h1>
          <p className="text-gray-500 mt-1">{user?.contracts_used}/{user?.contracts_limit} contracts used this month</p>
        </div>
        <Link to="/upload" className="btn-primary flex items-center gap-2">
          <Upload className="w-4 h-4" /> Upload Contract
        </Link>
      </div>

      {/* Stats */}
      <div className="grid grid-cols-1 md:grid-cols-4 gap-4">
        <StatCard icon={FileText} label="Total Contracts" value={contracts.length} />
        <StatCard icon={TrendingUp} label="Analyzed" value={analyzed.length} />
        <StatCard icon={AlertTriangle} label="High Risk" value={highRisk.length} color="text-red-600" />
        <StatCard icon={TrendingUp} label="Avg Risk Score" value={avgRisk} suffix="/100" />
      </div>

      {/* Recent Contracts */}
      <div className="card">
        <div className="px-6 py-4 border-b border-gray-100">
          <h2 className="font-semibold text-gray-900">Recent Contracts</h2>
        </div>
        {contracts.length === 0 ? (
          <div className="p-12 text-center">
            <FileText className="w-12 h-12 text-gray-300 mx-auto mb-4" />
            <p className="text-gray-500 mb-4">No contracts yet</p>
            <Link to="/upload" className="btn-primary">Upload your first contract</Link>
          </div>
        ) : (
          <div className="divide-y divide-gray-100">
            {contracts.slice(0, 10).map(contract => (
              <Link
                key={contract.id}
                to={contract.status === 'analyzed' ? `/analysis/${contract.id}` : `/contracts/${contract.id}`}
                className="flex items-center justify-between px-6 py-4 hover:bg-gray-50 transition-colors"
              >
                <div className="flex items-center gap-4">
                  <div className="w-10 h-10 bg-brand-50 rounded-lg flex items-center justify-center">
                    <FileText className="w-5 h-5 text-brand-600" />
                  </div>
                  <div>
                    <p className="font-medium text-gray-900">{contract.title}</p>
                    <p className="text-sm text-gray-500">
                      {contract.contract_type ?? 'Processing'} &middot; {formatDate(contract.uploaded_at)}
                    </p>
                  </div>
                </div>
                <div className="flex items-center gap-3">
                  <StatusBadge status={contract.status} />
                  {contract.status === 'analyzed' && <RiskBadge score={contract.risk_score} />}
                </div>
              </Link>
            ))}
          </div>
        )}
      </div>
    </div>
  )
}

function StatCard({ icon: Icon, label, value, suffix, color }: {
  icon: React.ElementType; label: string; value: number; suffix?: string; color?: string
}) {
  return (
    <div className="card p-5">
      <div className="flex items-center gap-3">
        <div className="w-10 h-10 bg-gray-100 rounded-lg flex items-center justify-center">
          <Icon className="w-5 h-5 text-gray-600" />
        </div>
        <div>
          <p className="text-sm text-gray-500">{label}</p>
          <p className={`text-2xl font-bold ${color ?? 'text-gray-900'}`}>
            {value}{suffix}
          </p>
        </div>
      </div>
    </div>
  )
}

function StatusBadge({ status }: { status: string }) {
  const styles: Record<string, string> = {
    uploaded: 'bg-gray-100 text-gray-700',
    extracting: 'bg-blue-100 text-blue-700',
    analyzing: 'bg-purple-100 text-purple-700',
    analyzed: 'bg-green-100 text-green-700',
    failed: 'bg-red-100 text-red-700',
  }
  return (
    <span className={`badge ${styles[status] ?? styles.uploaded}`}>
      {status}
    </span>
  )
}
