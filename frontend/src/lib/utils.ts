import { clsx, type ClassValue } from 'clsx'
import { twMerge } from 'tailwind-merge'

export function cn(...inputs: ClassValue[]) {
  return twMerge(clsx(inputs))
}

export function riskColor(score: number | null): string {
  if (!score) return 'text-gray-400'
  if (score <= 30) return 'text-green-600'
  if (score <= 60) return 'text-yellow-600'
  return 'text-red-600'
}

export function riskBg(score: number | null): string {
  if (!score) return 'bg-gray-100'
  if (score <= 30) return 'bg-green-50'
  if (score <= 60) return 'bg-yellow-50'
  return 'bg-red-50'
}

export function riskLabel(score: number | null): string {
  if (!score) return 'Unknown'
  if (score <= 30) return 'Low Risk'
  if (score <= 60) return 'Medium Risk'
  return 'High Risk'
}

export function formatDate(iso: string): string {
  return new Date(iso).toLocaleDateString('en-US', {
    month: 'short', day: 'numeric', year: 'numeric',
  })
}

export function categoryLabel(cat: string): string {
  return cat.replace(/_/g, ' ').replace(/\b\w/g, c => c.toUpperCase())
}
