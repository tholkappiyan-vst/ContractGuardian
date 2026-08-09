import { Link } from 'react-router-dom'
import { Shield, FileSearch, AlertTriangle, MessageSquare, ArrowRight, CheckCircle } from 'lucide-react'
import { Navbar } from '@/components/layout/Navbar'

const features = [
  { icon: FileSearch, title: 'Instant Analysis', desc: 'Upload any contract and get a complete risk breakdown in under 60 seconds.' },
  { icon: AlertTriangle, title: 'Risk Detection', desc: 'AI identifies unfavorable clauses, missing protections, and hidden penalties.' },
  { icon: MessageSquare, title: 'Ask Questions', desc: 'Chat with your contract in plain language. "Can I terminate early?" "What if I miss a payment?"' },
]

const benefits = [
  'Understand contracts without a lawyer',
  'Spot unfavorable terms before signing',
  'Get negotiation language you can copy-paste',
  'Compare multiple offers side-by-side',
]

export function Landing() {
  return (
    <div className="min-h-screen bg-white">
      <Navbar />

      {/* Hero */}
      <section className="relative overflow-hidden">
        <div className="max-w-7xl mx-auto px-4 sm:px-6 lg:px-8 pt-20 pb-32">
          <div className="text-center max-w-3xl mx-auto">
            <div className="inline-flex items-center gap-2 px-4 py-1.5 bg-brand-50 rounded-full mb-6">
              <Shield className="w-4 h-4 text-brand-600" />
              <span className="text-sm font-medium text-brand-700">AI-Powered Contract Intelligence</span>
            </div>
            <h1 className="text-5xl md:text-6xl font-bold text-gray-900 tracking-tight leading-tight">
              Understand Any Contract
              <span className="text-brand-600"> Before You Sign</span>
            </h1>
            <p className="mt-6 text-xl text-gray-600 leading-relaxed">
              Upload your contract. Get a plain-language risk analysis, clause-by-clause explanations,
              and negotiation suggestions — in seconds, not billable hours.
            </p>
            <div className="mt-10 flex items-center justify-center gap-4">
              <Link to="/register" className="btn-primary text-lg px-8 py-3 flex items-center gap-2">
                Analyze Your Contract <ArrowRight className="w-5 h-5" />
              </Link>
              <Link to="/login" className="btn-secondary text-lg px-8 py-3">
                Log In
              </Link>
            </div>
            <p className="mt-4 text-sm text-gray-500">Free to use. No credit card required.</p>
          </div>
        </div>
        <div className="absolute inset-0 -z-10 bg-gradient-to-b from-brand-50/50 to-white" />
      </section>

      {/* Features */}
      <section className="py-24 bg-gray-50">
        <div className="max-w-7xl mx-auto px-4 sm:px-6 lg:px-8">
          <div className="text-center mb-16">
            <h2 className="text-3xl font-bold text-gray-900">How It Works</h2>
            <p className="mt-4 text-lg text-gray-600">Three steps to contract clarity</p>
          </div>
          <div className="grid md:grid-cols-3 gap-8">
            {features.map(({ icon: Icon, title, desc }) => (
              <div key={title} className="card p-8 text-center hover:shadow-md transition-shadow">
                <div className="w-14 h-14 bg-brand-100 rounded-xl flex items-center justify-center mx-auto mb-5">
                  <Icon className="w-7 h-7 text-brand-600" />
                </div>
                <h3 className="text-lg font-semibold text-gray-900 mb-3">{title}</h3>
                <p className="text-gray-600 leading-relaxed">{desc}</p>
              </div>
            ))}
          </div>
        </div>
      </section>

      {/* Benefits */}
      <section className="py-24">
        <div className="max-w-7xl mx-auto px-4 sm:px-6 lg:px-8">
          <div className="grid md:grid-cols-2 gap-16 items-center">
            <div>
              <h2 className="text-3xl font-bold text-gray-900 mb-6">
                Built for people, not lawyers
              </h2>
              <p className="text-lg text-gray-600 mb-8">
                Every explanation is written at an 8th-grade reading level.
                No legal jargon, no ambiguity — just clear answers about what you're signing.
              </p>
              <ul className="space-y-4">
                {benefits.map(b => (
                  <li key={b} className="flex items-center gap-3">
                    <CheckCircle className="w-5 h-5 text-green-500 flex-shrink-0" />
                    <span className="text-gray-700">{b}</span>
                  </li>
                ))}
              </ul>
            </div>
            <div className="card p-6 bg-gray-900 text-white rounded-2xl">
              <div className="text-sm font-mono space-y-3 opacity-90">
                <p className="text-green-400">// Your employment contract analyzed</p>
                <p><span className="text-yellow-400">Risk Score:</span> 72/100 (High)</p>
                <p><span className="text-yellow-400">Top Risk:</span> Unlimited liability clause</p>
                <p><span className="text-yellow-400">Plain English:</span></p>
                <p className="text-gray-300 pl-4">
                  "If anything goes wrong — even things that aren't your fault — they can
                  sue you for unlimited amounts. Your savings, your house, everything is exposed."
                </p>
                <p className="text-blue-400 mt-4">Suggested fix: Add a liability cap at 12 months of salary.</p>
              </div>
            </div>
          </div>
        </div>
      </section>

      {/* CTA */}
      <section className="py-20 bg-brand-600">
        <div className="max-w-3xl mx-auto text-center px-4">
          <h2 className="text-3xl font-bold text-white mb-4">Stop signing contracts you don't understand</h2>
          <p className="text-brand-100 text-lg mb-8">Join thousands of people who review contracts with confidence.</p>
          <Link to="/register" className="inline-flex items-center gap-2 bg-white text-brand-700 px-8 py-3 rounded-lg font-semibold hover:bg-brand-50 transition-colors">
            Get Started Free <ArrowRight className="w-5 h-5" />
          </Link>
        </div>
      </section>

      {/* Footer */}
      <footer className="bg-gray-900 text-gray-400 py-12">
        <div className="max-w-7xl mx-auto px-4 text-center">
          <div className="flex items-center justify-center gap-2 mb-4">
            <Shield className="w-6 h-6 text-brand-400" />
            <span className="text-white font-bold">ContractAI Guardian</span>
          </div>
          <p className="text-sm">AI-powered contract analysis. Not legal advice.</p>
          <p className="text-xs mt-4">&copy; 2026 ContractAI Guardian. All rights reserved.</p>
        </div>
      </footer>
    </div>
  )
}
