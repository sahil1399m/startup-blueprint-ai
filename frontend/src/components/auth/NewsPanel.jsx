import { useState, useEffect } from 'react'
import { blueprintApi } from '../../api/blueprint'
import { KeywordChip } from '../ui'

const TRENDS = [
  'AI & ML', 'Fintech Unicorns', 'Agritech', 'EV Ecosystem', 'D2C Brands',
  'SaaS for SMBs', 'HealthTech', 'EdTech 2.0', 'Climate Tech', 'Deep Tech',
  'B2B Commerce', 'ONDC', 'Logistics Tech',
]

const STATS = [
  { val: '₹12T',  label: 'Indian Startup Market' },
  { val: '112',   label: 'Unicorns in India' },
  { val: '1.5L+', label: 'DPIIT Startups' },
  { val: '6',     label: 'AI Models' },
]

const CAT_COLORS = {
  Funding:  { text: '#34d399', bg: 'rgba(52,211,153,0.09)', border: 'rgba(52,211,153,0.2)' },
  Unicorns: { text: '#a78bfa', bg: 'rgba(167,139,250,0.09)', border: 'rgba(167,139,250,0.2)' },
  Policy:   { text: '#60a5fa', bg: 'rgba(96,165,250,0.09)', border: 'rgba(96,165,250,0.2)' },
  Info:     { text: '#94a3b8', bg: 'rgba(148,163,184,0.09)', border: 'rgba(148,163,184,0.2)' },
}

/**
 * NewsPanel — left-side panel on the Login page.
 * Shows hero, stats, trending keywords, and live news articles.
 */
export default function NewsPanel() {
  const [news, setNews] = useState([])

  useEffect(() => {
    blueprintApi
      .getNews('India startup funding')
      .then((r) => setNews(r.data?.articles || []))
      .catch(() => {})
  }, [])

  return (
    <div className="hidden md:flex flex-col p-10 border-r border-white/[0.052] overflow-y-auto">
      {/* Hero */}
      <div className="mb-8">
        <div className="inline-flex items-center gap-2 bg-blue-500/[0.09] border border-blue-500/20
          rounded-full px-3 py-1 text-[0.71rem] font-700 text-blue-300 uppercase tracking-wider mb-5">
          🚀 AI-Powered Startup Intelligence
        </div>
        <h1 className="text-5xl font-black tracking-tight leading-[1.05] gradient-text mb-4">
          Build Your Startup<br />Blueprint in Minutes
        </h1>
        <div className="flex flex-wrap gap-1.5 mb-6">
          <span className="badge badge-blue">IBM Granite 4.0</span>
          <span className="badge badge-purple">Groq Llama 3.3</span>
          <span className="badge badge-amber">✨ Gemini Flash</span>
          <span className="badge badge-green">CRAG Self-Correcting</span>
          <span className="badge badge-red">🔴 LIVE Web Search</span>
        </div>

        {/* Stats */}
        <div className="grid grid-cols-4 gap-3 mb-8">
          {STATS.map(({ val, label }) => (
            <div key={label}
              className="rounded-2xl border border-white/[0.07] bg-gradient-to-br from-blue-500/[0.075] to-purple-500/[0.075]
                p-3 text-center backdrop-blur-sm">
              <div className="text-xl font-900 gradient-text-blue">{val}</div>
              <div className="text-[0.62rem] text-slate-500 font-700 uppercase tracking-wider mt-1">{label}</div>
            </div>
          ))}
        </div>

        {/* Trends */}
        <div className="text-[0.67rem] font-700 text-slate-500 uppercase tracking-wider mb-2">
          🔥 Trending in Indian Startup Ecosystem
        </div>
        <div className="mb-6 flex flex-wrap">
          {TRENDS.map((t) => <KeywordChip key={t}>{t}</KeywordChip>)}
        </div>
      </div>

      {/* News */}
      <div className="text-[0.67rem] font-700 text-slate-500 uppercase tracking-wider mb-3">
        📰 Latest Startup News
      </div>
      <div className="space-y-2 flex-1">
        {news.length === 0 && (
          <div className="text-sm text-slate-600 italic">Add NEWS_API_KEY for live news</div>
        )}
        {news.slice(0, 8).map((a, i) => {
          const cat = a._cat || 'Info'
          const c = CAT_COLORS[cat] || CAT_COLORS.Info
          return (
            <div key={i} className="news-card p-3">
              <span className="text-[0.63rem] font-700 rounded-lg px-2 py-0.5"
                style={{ color: c.text, background: c.bg, border: `1px solid ${c.border}` }}>
                {cat}
              </span>
              <div className="text-sm font-600 text-slate-200 mt-1.5 mb-1 leading-snug line-clamp-2">
                {a.title}
              </div>
              <div className="text-[0.72rem] text-slate-500">
                <span style={{ color: c.text, fontWeight: 600 }}>{a.source?.name}</span>
                {' '}· {a.publishedAt?.slice(0, 10)}
                {' '}·{' '}
                <a href={a.url} target="_blank" rel="noreferrer"
                  className="text-blue-400 hover:text-blue-300 font-500">Read →</a>
              </div>
            </div>
          )
        })}
      </div>
    </div>
  )
}
