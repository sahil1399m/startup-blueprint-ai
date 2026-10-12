import { Eye, EyeOff, ArrowRight } from 'lucide-react'
import { Spinner } from '../ui'

/**
 * LoginForm — extracted sign-in form component.
 *
 * Props: email, password, showPw, onEmailChange, onPasswordChange,
 *        onTogglePw, onSubmit, loading
 */
export default function LoginForm({
  email,
  password,
  showPw,
  onEmailChange,
  onPasswordChange,
  onTogglePw,
  onSubmit,
  loading,
}) {
  return (
    <form onSubmit={onSubmit} className="space-y-4 animate-fade-in">
      <div>
        <label
          htmlFor="comp-signin-email"
          className="block text-[0.69rem] font-700 text-slate-500 uppercase tracking-wider mb-1.5"
        >
          Email Address
        </label>
        <input
          id="comp-signin-email"
          type="email"
          placeholder="founder@example.com"
          value={email}
          onChange={onEmailChange}
          required
          disabled={loading}
          className="input-base px-4 py-3"
        />
      </div>

      <div>
        <label
          htmlFor="comp-signin-password"
          className="block text-[0.69rem] font-700 text-slate-500 uppercase tracking-wider mb-1.5"
        >
          Password
        </label>
        <div className="relative">
          <input
            id="comp-signin-password"
            type={showPw ? 'text' : 'password'}
            placeholder="••••••••"
            value={password}
            onChange={onPasswordChange}
            required
            disabled={loading}
            className="input-base px-4 py-3 pr-10"
          />
          <button
            type="button"
            onClick={onTogglePw}
            aria-label={showPw ? 'Hide password' : 'Show password'}
            className="absolute right-3 top-1/2 -translate-y-1/2 text-slate-500 hover:text-slate-300 p-1 cursor-pointer"
          >
            {showPw ? <EyeOff size={16} /> : <Eye size={16} />}
          </button>
        </div>
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
