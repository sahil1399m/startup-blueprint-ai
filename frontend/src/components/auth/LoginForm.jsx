import { Eye, EyeOff, ArrowRight } from 'lucide-react'
import { Spinner } from '../ui'

/**
 * LoginForm — extracted sign-in form component.
 *
 * Props: email, password, showPw, onEmailChange, onPasswordChange,
 *        onTogglePw, onSubmit, loading, error
 */
export default function LoginForm({
  email, password, showPw,
  onEmailChange, onPasswordChange, onTogglePw,
  onSubmit, loading,
}) {
  return (
    <form onSubmit={onSubmit} className="space-y-4 animate-fade-in">
      <div>
        <label className="block text-[0.69rem] font-700 text-slate-500 uppercase tracking-wider mb-1.5">
          Email Address
        </label>
        <input
          type="email"
          placeholder="you@example.com"
          value={email}
          onChange={onEmailChange}
          required
          className="input-base px-4 py-3"
        />
      </div>

      <div className="relative">
        <label className="block text-[0.69rem] font-700 text-slate-500 uppercase tracking-wider mb-1.5">
          Password
        </label>
        <input
          type={showPw ? 'text' : 'password'}
          placeholder="••••••••"
          value={password}
          onChange={onPasswordChange}
          required
          className="input-base px-4 py-3 pr-10"
        />
        <button
          type="button"
          onClick={onTogglePw}
          className="absolute right-3 bottom-3 text-slate-500 hover:text-slate-300"
        >
          {showPw ? <EyeOff size={16} /> : <Eye size={16} />}
        </button>
      </div>

      <button
        type="submit"
        disabled={loading}
        className="btn-primary w-full py-3 flex items-center justify-center gap-2 mt-2"
      >
        {loading ? <Spinner size={18} /> : <><span>Sign In</span><ArrowRight size={16} /></>}
      </button>
    </form>
  )
}
