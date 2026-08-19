// ── Badge ─────────────────────────────────────────────────────────────────────
export function Badge({ children, variant = 'blue', className = '' }) {
  const variants = {
    blue:   'badge-blue',
    purple: 'badge-purple',
    green:  'badge-green',
    amber:  'badge-amber',
    red:    'badge-red',
  }
  return (
    <span className={`badge ${variants[variant] || 'badge-blue'} ${className}`}>
      {children}
    </span>
  )
}

// ── Card ──────────────────────────────────────────────────────────────────────
export function Card({ children, className = '', onClick, hover = true }) {
  return (
    <div
      className={`glass-card p-5 ${hover ? '' : 'hover:transform-none hover:border-white/[0.062] hover:bg-[var(--bg-card)] hover:shadow-none'} ${onClick ? 'cursor-pointer' : ''} ${className}`}
      onClick={onClick}
    >
      {children}
    </div>
  )
}

export function CardBlue({ children, className = '' }) {
  return (
    <div className={`rounded-2xl border border-blue-500/15 bg-gradient-to-br from-blue-500/[0.055] to-indigo-500/[0.035] p-5 ${className}`}>
      {children}
    </div>
  )
}

export function CardGreen({ children, className = '' }) {
  return (
    <div className={`rounded-2xl border border-emerald-500/15 bg-gradient-to-br from-emerald-500/[0.055] to-teal-500/[0.028] p-5 ${className}`}>
      {children}
    </div>
  )
}

export function CardAmber({ children, className = '' }) {
  return (
    <div className={`rounded-2xl border border-amber-500/15 bg-gradient-to-br from-amber-500/[0.055] to-orange-500/[0.028] p-5 ${className}`}>
      {children}
    </div>
  )
}

// ── MetricCard ────────────────────────────────────────────────────────────────
export function MetricCard({ value, label, sub, className = '' }) {
  return (
    <div className={`rounded-2xl border border-white/[0.07] bg-gradient-to-br from-blue-500/[0.075] to-purple-500/[0.075]
      p-5 text-center transition-all duration-200 hover:border-blue-400/25 hover:-translate-y-0.5
      hover:shadow-[0_12px_40px_rgba(15,98,254,0.12)] backdrop-blur-sm h-full ${className}`}>
      <div
        className="text-3xl font-black tracking-tight gradient-text-blue leading-none"
        style={{ fontSize: String(value).length > 6 ? '1.4rem' : undefined }}
      >
        {value}
      </div>
      <div className="text-[0.67rem] text-slate-500 font-700 uppercase tracking-wider mt-2">
        {label}
      </div>
      {sub && <div className="text-[0.67rem] text-emerald-400 font-600 mt-1">{sub}</div>}
    </div>
  )
}

// ── KeywordChip ───────────────────────────────────────────────────────────────
export function KeywordChip({ children }) {
  return (
    <span className="inline-block bg-blue-500/[0.075] border border-blue-500/15 rounded-full
      px-3 py-0.5 text-[0.72rem] text-blue-300 m-0.5 transition-all duration-150
      hover:bg-blue-500/[0.14] hover:border-blue-500/28 hover:-translate-y-px cursor-default">
      {children}
    </span>
  )
}

// ── Spinner ───────────────────────────────────────────────────────────────────
export function Spinner({ size = 20, className = '' }) {
  return (
    <svg
      className={`animate-spin text-blue-400 ${className}`}
      width={size} height={size} viewBox="0 0 24 24" fill="none"
    >
      <circle className="opacity-25" cx="12" cy="12" r="10" stroke="currentColor" strokeWidth="4" />
      <path className="opacity-75" fill="currentColor"
        d="M4 12a8 8 0 018-8V0C5.373 0 0 5.373 0 12h4z" />
    </svg>
  )
}

// ── SectionHeader ─────────────────────────────────────────────────────────────
export function SectionHeader({ children, className = '' }) {
  return (
    <div className={`text-sm font-800 text-slate-200 uppercase tracking-wider mb-4 border-b border-white/[0.06] pb-2 ${className}`}>{children}</div>
  )
}

// ── Divider ───────────────────────────────────────────────────────────────────
export function Divider({ className = '' }) {
  return <hr className={`border-white/[0.06] my-8 ${className}`} />
}

// ── EmptyState ────────────────────────────────────────────────────────────────
export function EmptyState({ icon, title, description, action }) {
  return (
    <div className="flex flex-col items-center justify-center py-20 text-center">
      {icon && <div className="text-5xl mb-4">{icon}</div>}
      <div className="text-lg font-700 text-slate-300 mb-2">{title}</div>
      {description && <div className="text-sm text-slate-500 max-w-sm mb-5">{description}</div>}
      {action}
    </div>
  )
}
