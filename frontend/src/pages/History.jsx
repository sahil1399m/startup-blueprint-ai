import { useState, useEffect, useCallback } from 'react'
import { Link, useNavigate } from 'react-router-dom'
import { Search, Eye, MessageSquare, FlaskConical, Lock, Star, Trash2, Clock, X } from 'lucide-react'
import { historyApi } from '../api/history'
import { Spinner } from '../components/ui'

// Simple debounce function
function useDebounce(value, delay) {
  const [debouncedValue, setDebouncedValue] = useState(value);
  useEffect(() => {
    const handler = setTimeout(() => {
      setDebouncedValue(value);
    }, delay);
    return () => clearTimeout(handler);
  }, [value, delay]);
  return debouncedValue;
}

export default function History() {
  const [blueprints, setBlueprints] = useState([])
  const [loading, setLoading] = useState(true)
  const [searchTerm, setSearchTerm] = useState('')
  const debouncedSearchTerm = useDebounce(searchTerm, 500)
  const navigate = useNavigate()

  useEffect(() => {
    fetchHistory(debouncedSearchTerm)
  }, [debouncedSearchTerm])

  const fetchHistory = async (search = '') => {
    try {
      const res = await historyApi.list({ search })
      setBlueprints(res.data.blueprints || [])
    } catch (err) {
      console.error(err)
    } finally {
      setLoading(false)
    }
  }

  const handleDelete = async (e, id) => {
    e.stopPropagation()
    if (!confirm('Are you sure you want to delete this blueprint?')) return
    try {
      await historyApi.delete(id)
      setBlueprints(blueprints.filter((b) => b.id !== id))
    } catch (err) {
      console.error(err)
    }
  }

  const handleClearSearch = () => {
    setSearchTerm('')
  }

  return (
    <div className="max-w-screen-xl mx-auto px-6 py-10">
      <div className="flex items-center gap-4 mb-8">
        <div className="w-10 h-10 rounded-xl bg-gradient-to-br from-blue-500 to-purple-600 flex items-center justify-center shadow-lg shadow-blue-500/20">
          <svg xmlns="http://www.w3.org/2000/svg" width="20" height="20" viewBox="0 0 24 24" fill="none" stroke="currentColor" strokeWidth="2.5" strokeLinecap="round" strokeLinejoin="round" className="text-white"><rect x="2" y="7" width="20" height="14" rx="2" ry="2"></rect><path d="M16 21V5a2 2 0 0 0-2-2h-4a2 2 0 0 0-2 2v16"></path></svg>
        </div>
        <div>
          <h1 className="text-2xl font-900 text-slate-100 tracking-tight flex items-center gap-3">
            Blueprint History
            <span className="text-sm font-500 text-slate-500 mt-1 tracking-normal font-sans">
              Your previously generated blueprints — replayed without any AI calls
            </span>
          </h1>
        </div>
      </div>

      <div className="flex gap-4 mb-6">
        <div className="relative flex-1">
          <Search className="absolute left-4 top-1/2 -translate-y-1/2 text-slate-500" size={18} />
          <input
            type="text"
            placeholder="Search by title or idea..."
            value={searchTerm}
            onChange={(e) => setSearchTerm(e.target.value)}
            className="w-full bg-slate-800/50 border border-slate-700/50 rounded-xl py-3 pl-11 pr-4 text-slate-200 placeholder-slate-500 focus:outline-none focus:border-blue-500/50 focus:ring-1 focus:ring-blue-500/50 transition-all"
          />
        </div>
        <button 
          onClick={handleClearSearch}
          className="px-6 py-3 rounded-xl border border-slate-700/50 text-slate-400 hover:text-slate-200 hover:bg-slate-800/50 transition-all flex items-center gap-2 font-600 text-sm"
        >
          <X size={16} />
          Clear All
        </button>
      </div>

      <div className="text-sm text-slate-500 font-600 mb-6">
        {blueprints.length} blueprints saved
      </div>

      {loading ? (
        <div className="flex justify-center items-center h-64">
          <Spinner size={32} />
        </div>
      ) : blueprints.length === 0 ? (
        <div className="text-center py-20 bg-slate-800/20 border border-slate-800 rounded-2xl">
          <p className="text-slate-500 mb-6 font-600">You haven't generated any blueprints yet, or no results matched your search.</p>
          <Link to="/dashboard" className="bg-blue-600 hover:bg-blue-500 text-white px-8 py-3 rounded-xl font-700 transition-colors shadow-lg shadow-blue-500/20">Generate One Now</Link>
        </div>
      ) : (
        <div className="space-y-6">
          {blueprints.map((bp) => (
            <div key={bp.id} className="bg-slate-900/50 border border-slate-800/80 hover:border-blue-500/30 rounded-2xl p-6 transition-all flex flex-col md:flex-row gap-8">
              {/* Left Column: Details */}
              <div className="flex-1 space-y-4">
                <h3 className="text-xl font-800 text-slate-100 line-clamp-2 leading-tight">
                  {bp.title || bp.idea}
                </h3>
                
                <div className="flex flex-wrap gap-2">
                  <span className="text-xs font-700 bg-blue-500/10 text-blue-400 px-3 py-1 rounded-full border border-blue-500/20">
                    {bp.sector || 'Other'}
                  </span>
                  
                  {bp.confidence && (
                    <span className="text-xs font-700 bg-emerald-500/10 text-emerald-400 px-3 py-1 rounded-full border border-emerald-500/20">
                      CRAG: {bp.confidence}
                    </span>
                  )}
                  
                  <span className="text-xs font-600 bg-white/[0.03] text-slate-400 px-3 py-1 rounded-full border border-white/5">
                    {bp.stage || 'Idea Stage'} {bp.business_model ? `- ${bp.business_model}` : ''} {bp.market ? `- ${bp.market}` : ''}
                  </span>
                </div>

                <div className="flex items-center gap-2 text-xs font-600 text-slate-500 pt-2">
                  <Clock size={14} />
                  {bp.timestamp ? new Date(bp.timestamp).toLocaleString(undefined, {
                    year: 'numeric', month: 'short', day: 'numeric',
                    hour: '2-digit', minute: '2-digit'
                  }) : new Date(bp.created_at).toLocaleString()}
                </div>
              </div>

              {/* Right Column: Actions */}
              <div className="w-full md:w-64 grid grid-cols-2 gap-3 shrink-0">
                <button 
                  onClick={() => navigate(`/history/${bp.id}`)}
                  className="col-span-2 bg-gradient-to-r from-blue-600 to-purple-600 hover:from-blue-500 hover:to-purple-500 text-white rounded-xl py-3 flex items-center justify-center gap-2 font-700 text-sm shadow-lg shadow-blue-500/20 transition-all"
                >
                  <Eye size={16} />
                  View Blueprint
                </button>
                
                <button 
                  onClick={() => navigate(`/mentor/${bp.id}`)}
                  className="col-span-2 bg-slate-800/80 hover:bg-slate-700/80 text-pink-400 border border-slate-700/50 rounded-xl py-3 flex items-center justify-center gap-2 font-700 text-sm transition-all"
                >
                  <MessageSquare size={16} />
                  AI Mentor
                </button>

                <button 
                  onClick={() => navigate(`/deep-research/${bp.id}`)}
                  className="col-span-2 bg-slate-800/80 hover:bg-slate-700/80 text-cyan-400 border border-slate-700/50 rounded-xl py-3 flex items-center justify-center gap-2 font-700 text-sm transition-all"
                >
                  <FlaskConical size={16} />
                  Deep Research
                </button>

                <button 
                  onClick={() => navigate(`/lock-in/${bp.id}`)}
                  className="col-span-2 bg-slate-800/80 hover:bg-slate-700/80 text-amber-400 border border-slate-700/50 rounded-xl py-3 flex items-center justify-center gap-2 font-700 text-sm transition-all"
                >
                  <Lock size={16} />
                  LOCK IN
                </button>

                <button 
                  className="bg-slate-800/80 hover:bg-slate-700/80 text-slate-300 border border-slate-700/50 rounded-xl py-3 flex items-center justify-center gap-2 font-700 text-sm transition-all cursor-not-allowed opacity-70"
                  title="Coming Soon"
                >
                  <Star size={16} />
                  Save
                </button>

                <button 
                  onClick={(e) => handleDelete(e, bp.id)}
                  className="bg-slate-800/80 hover:bg-red-500/20 text-slate-400 hover:text-red-400 border border-slate-700/50 hover:border-red-500/30 rounded-xl py-3 flex items-center justify-center gap-2 font-700 text-sm transition-all"
                >
                  <Trash2 size={16} />
                  Delete
                </button>
              </div>
            </div>
          ))}
        </div>
      )}
    </div>
  )
}
