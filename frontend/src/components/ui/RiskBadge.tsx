import { cn } from '@/lib/utils'

interface Props {
  score: number | null
  className?: string
}

export function RiskBadge({ score, className }: Props) {
  if (!score) return null

  const variant = score <= 30 ? 'badge-low' : score <= 60 ? 'badge-medium' : 'badge-high'
  const label = score <= 30 ? 'Low' : score <= 60 ? 'Medium' : 'High'

  return (
    <span className={cn('badge', variant, className)}>
      {label} ({score})
    </span>
  )
}
