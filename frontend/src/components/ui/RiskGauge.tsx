import { cn, riskColor, riskLabel } from '@/lib/utils'

interface Props {
  score: number | null
  size?: 'sm' | 'md' | 'lg'
}

export function RiskGauge({ score, size = 'md' }: Props) {
  const s = score ?? 0
  const circumference = 2 * Math.PI * 45
  const offset = circumference - (s / 100) * circumference
  const dims = { sm: 'w-16 h-16', md: 'w-24 h-24', lg: 'w-32 h-32' }
  const textSize = { sm: 'text-sm', md: 'text-xl', lg: 'text-3xl' }

  return (
    <div className={cn('relative', dims[size])}>
      <svg className="w-full h-full -rotate-90" viewBox="0 0 100 100">
        <circle cx="50" cy="50" r="45" fill="none" stroke="#e5e7eb" strokeWidth="8" />
        <circle
          cx="50" cy="50" r="45" fill="none"
          stroke={s <= 30 ? '#22c55e' : s <= 60 ? '#eab308' : '#ef4444'}
          strokeWidth="8" strokeLinecap="round"
          strokeDasharray={circumference}
          strokeDashoffset={offset}
          className="transition-all duration-700"
        />
      </svg>
      <div className="absolute inset-0 flex flex-col items-center justify-center">
        <span className={cn('font-bold', textSize[size], riskColor(score))}>{s}</span>
        {size !== 'sm' && (
          <span className="text-[10px] text-gray-500 font-medium">{riskLabel(score)}</span>
        )}
      </div>
    </div>
  )
}
