import { useMemo } from 'react'
import { 
  Bot, ShieldCheck, AlertTriangle, TrendingUp, DollarSign, 
  Sparkles, CheckCircle2, ChevronRight, BookOpen, Wrench, Layers, ExternalLink
} from 'lucide-react'
import { Card, Badge } from '../ui'

const INTENT_BADGES = {
  feasibility: { label: 'Feasibility Assessment', color: 'blue' },
  competitors: { label: 'Competitor Analysis', color: 'red' },
  funding:     { label: 'Funding & Schemes', color: 'green' },
  strategy:    { label: 'Strategic Roadmap', color: 'purple' },
  risk:        { label: 'Risk Analysis', color: 'amber' },
  market:      { label: 'Market Dynamics', color: 'blue' },
  technical:   { label: 'Technical Architecture', color: 'purple' },
  legal:       { label: 'Regulatory & Legal', color: 'amber' },
  growth:      { label: 'Growth Strategy', color: 'green' },
  unknown:     { label: 'AI Strategy Advice', color: 'blue' },
}

/**
 * Parses markdown-like response text into structured visual sections:
 * - Cards for Competitors, Risks, Schemes, Milestones, and Value Props
 * - Formatted Headings, Bullet Lists, and Metrics
 */
export default function StructuredResponse({ message, isGrounded = true }) {
  const { content = '', intent = 'unknown', citations = [], tools_used = [] } = message

  // Parse structured blocks from raw content text
  const parsedSections = useMemo(() => {
    if (!content) return []

    // Split content by major section headers (###, ##, #, or bold titles like **1. Title**)
    const lines = content.split('\n')
    const sections = []
    let currentSection = { title: '', contentLines: [], type: 'text' }

    for (let i = 0; i < lines.length; i++) {
      const line = lines[i]
      const trimmed = line.trim()

      const isHeading = trimmed.startsWith('#') || 
                        /^(\*\*\d+\.|\d+\.\s|\*\*)[^*]+(\*\*|:)/.test(trimmed) ||
                        (trimmed.startsWith('**') && trimmed.endsWith('**') && trimmed.length < 80)

      if (isHeading && currentSection.contentLines.length > 0) {
        sections.push(currentSection)
        currentSection = { title: cleanHeading(trimmed), contentLines: [], type: detectSectionType(trimmed) }
      } else if (isHeading && currentSection.contentLines.length === 0) {
        currentSection.title = cleanHeading(trimmed)
        currentSection.type = detectSectionType(trimmed)
      } else {
        currentSection.contentLines.push(line)
      }
    }

    if (currentSection.contentLines.length > 0 || currentSection.title) {
      sections.push(currentSection)
    }

    return sections
  }, [content])

  const intentBadge = INTENT_BADGES[intent] || INTENT_BADGES.unknown

  return (
    <div className="space-y-4">
      {/* Header bar inside AI response card */}
      <div className="flex items-center justify-between pb-3 border-b border-white/[0.08]">
        <div className="flex items-center gap-2">
          <div className="w-6 h-6 rounded-lg bg-blue-500/20 text-blue-400 flex items-center justify-center">
            <Bot size={14} />
          </div>
          <span className="text-xs font-800 text-slate-200 tracking-wide">AI Startup Advisor</span>
          <Badge variant={intentBadge.color} size="sm">{intentBadge.label}</Badge>
        </div>

        {isGrounded && (
          <div className="flex items-center gap-1.5 text-[0.65rem] font-700 text-emerald-400 bg-emerald-500/10 px-2.5 py-1 rounded-full border border-emerald-500/20">
            <ShieldCheck size={12} />
            <span>CRAG Grounded</span>
          </div>
        )}
      </div>

      {/* Render sections */}
      <div className="space-y-4">
        {parsedSections.map((sec, idx) => (
          <RenderSection key={idx} section={sec} />
        ))}
      </div>

      {/* Citations & Evidence section */}
      {citations?.length > 0 && (
        <div className="mt-4 pt-3 border-t border-white/[0.08]">
          <div className="text-[0.65rem] font-800 text-slate-400 uppercase tracking-wider mb-2 flex items-center gap-1.5">
            <BookOpen size={12} className="text-blue-400" />
            <span>Grounded Sources & Evidence</span>
          </div>
          <div className="flex flex-wrap gap-1.5">
            {citations.map((cite, j) => (
              <a
                key={j}
                href={cite.url || '#'}
                target="_blank"
                rel="noreferrer"
                className="text-[0.67rem] bg-slate-800/80 border border-slate-700/80 px-2.5 py-1 rounded-lg text-slate-300 hover:text-blue-400 hover:border-blue-500/30 transition-colors flex items-center gap-1"
              >
                <span>{cite.title || cite.name || 'Official Source'}</span>
                <ExternalLink size={10} className="opacity-60" />
              </a>
            ))}
          </div>
        </div>
      )}

      {/* Tools Used */}
      {tools_used?.length > 0 && (
        <div className="flex items-center gap-2 pt-2 text-[0.6rem] text-slate-500 font-mono">
          <Wrench size={10} />
          <span>Tools applied: {tools_used.join(', ')}</span>
        </div>
      )}
    </div>
  )
}

// ── Helper parsing functions ──────────────────────────────────────────────────
function cleanHeading(text) {
  return text.replace(/^[#*\d.\s]+/, '').replace(/\*+/g, '').replace(/:$/, '').trim()
}

function detectSectionType(title) {
  const t = title.toLowerCase()
  if (t.includes('competitor') || t.includes('rival')) return 'competitor'
  if (t.includes('risk') || t.includes('threat') || t.includes('warning')) return 'risk'
  if (t.includes('scheme') || t.includes('funding') || t.includes('grant') || t.includes('investor')) return 'funding'
  if (t.includes('roadmap') || t.includes('milestone') || t.includes('timeline')) return 'roadmap'
  if (t.includes('metric') || t.includes('tam') || t.includes('kpi') || t.includes('budget')) return 'metric'
  return 'text'
}

function RenderSection({ section }) {
  const { title, contentLines, type } = section

  // Check if content lines contain list items
  const fullText = contentLines.join('\n').trim()

  return (
    <div className="space-y-2">
      {title && (
        <div className="text-xs font-800 text-blue-400 uppercase tracking-wider flex items-center gap-1.5 pt-1">
          <ChevronRight size={12} className="text-blue-500" />
          <span>{title}</span>
        </div>
      )}

      {type === 'risk' && <RiskBlock text={fullText} />}
      {type === 'competitor' && <CompetitorBlock text={fullText} />}
      {type === 'funding' && <FundingBlock text={fullText} />}
      {type === 'roadmap' && <RoadmapBlock text={fullText} />}
      {type === 'text' && <FormattedTextBlock text={fullText} />}
    </div>
  )
}

function FormattedTextBlock({ text }) {
  if (!text) return null

  const lines = text.split('\n')
  return (
    <div className="space-y-1.5 text-xs text-slate-300 leading-relaxed">
      {lines.map((line, i) => {
        const trimmed = line.trim()
        if (!trimmed) return <div key={i} className="h-1" />

        // Bullet point
        if (/^[-*•✦]\s/.test(trimmed)) {
          const bulletText = trimmed.replace(/^[-*•✦]\s/, '')
          return (
            <div key={i} className="flex items-start gap-2 pl-2">
              <span className="text-blue-400 mt-1 shrink-0 text-[0.6rem]">✦</span>
              <span dangerouslySetInnerHTML={{ __html: formatInlineMarkdown(bulletText) }} />
            </div>
          )
        }

        // Numbered list
        if (/^\d+\.\s/.test(trimmed)) {
          const num = trimmed.match(/^\d+/)[0]
          const listText = trimmed.replace(/^\d+\.\s/, '')
          return (
            <div key={i} className="flex items-start gap-2 pl-2">
              <span className="text-purple-400 font-bold shrink-0 text-[0.7rem]">{num}.</span>
              <span dangerouslySetInnerHTML={{ __html: formatInlineMarkdown(listText) }} />
            </div>
          )
        }

        // Standard paragraph
        return (
          <p key={i} dangerouslySetInnerHTML={{ __html: formatInlineMarkdown(trimmed) }} />
        )
      })}
    </div>
  )
}

function RiskBlock({ text }) {
  const lines = text.split('\n').filter(l => l.trim())
  const isHigh = text.toLowerCase().includes('high') || text.toLowerCase().includes('critical')

  return (
    <div className={`p-3 rounded-xl border ${isHigh ? 'bg-red-500/[0.05] border-red-500/20' : 'bg-amber-500/[0.04] border-amber-500/20'} space-y-2`}>
      <div className="flex items-center justify-between">
        <div className="flex items-center gap-1.5 text-xs font-700 text-slate-200">
          <AlertTriangle size={14} className={isHigh ? 'text-red-400' : 'text-amber-400'} />
          <span>Risk Insights</span>
        </div>
        <span className={`text-[0.6rem] font-800 px-2 py-0.5 rounded border uppercase tracking-wider ${isHigh ? 'bg-red-500/10 text-red-400 border-red-500/20' : 'bg-amber-500/10 text-amber-400 border-amber-500/20'}`}>
          {isHigh ? 'High Severity' : 'Medium Severity'}
        </span>
      </div>
      <FormattedTextBlock text={text} />
    </div>
  )
}

function CompetitorBlock({ text }) {
  return (
    <div className="p-3 rounded-xl bg-blue-500/[0.03] border border-blue-500/20 space-y-2">
      <div className="flex items-center gap-1.5 text-xs font-700 text-blue-300">
        <TrendingUp size={14} />
        <span>Market & Competitive Positioning</span>
      </div>
      <FormattedTextBlock text={text} />
    </div>
  )
}

function FundingBlock({ text }) {
  return (
    <div className="p-3 rounded-xl bg-emerald-500/[0.03] border border-emerald-500/20 space-y-2">
      <div className="flex items-center gap-1.5 text-xs font-700 text-emerald-300">
        <DollarSign size={14} />
        <span>Government Schemes & Funding Pathways</span>
      </div>
      <FormattedTextBlock text={text} />
    </div>
  )
}

function RoadmapBlock({ text }) {
  return (
    <div className="p-3 rounded-xl bg-purple-500/[0.03] border border-purple-500/20 space-y-2">
      <div className="flex items-center gap-1.5 text-xs font-700 text-purple-300">
        <Layers size={14} />
        <span>Execution Roadmap & Milestones</span>
      </div>
      <FormattedTextBlock text={text} />
    </div>
  )
}

function formatInlineMarkdown(text) {
  if (!text) return ''
  return text
    .replace(/\*\*(.*?)\*\*/g, '<strong className="text-slate-100 font-700">$1</strong>')
    .replace(/\*(.*?)\*/g, '<em className="text-slate-300">$1</em>')
    .replace(/`([^`]+)`/g, '<code className="bg-slate-800 text-purple-300 px-1 py-0.5 rounded text-[0.7rem]">$1</code>')
}
