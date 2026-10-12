import { useState } from 'react'
import { Eye, EyeOff, ArrowRight } from 'lucide-react'
import { Spinner } from '../ui'

/**
 * RegisterForm — extracted registration form component.
 *
 * Props: name, email, password, confirm, onNameChange, onEmailChange,
 *        onPasswordChange, onConfirmChange, onSubmit, loading
 */
export default function RegisterForm({
  name,
  email,
  password,
  confirm,
  onNameChange,
  onEmailChange,
  onPasswordChange,
  onConfirmChange,
  onSubmit,
  loading,
}) {
  const [showPw, setShowPw] = useState(false)
  const [showConfirmPw, setShowConfirmPw] = useState(false)

  return (
    <form onSubmit={onSubmit} className="space-y-4 animate-fade-in">
      <div>
        <label
          htmlFor="comp-reg-name"
          className="block text-[0.69rem] font-700 text-slate-500 uppercase tracking-wider mb-1.5"
        >
          Full Name
        </label>
        <input
          id="comp-reg-name"
          placeholder="Priya Sharma"
          value={name}
          onChange={onNameChange}
          required
          disabled={loading}
          className="input-base px-4 py-3"
        />
      </div>

      <div>
        <label
          htmlFor="comp-reg-email"
          className="block text-[0.69rem] font-700 text-slate-500 uppercase tracking-wider mb-1.5"
        >
          Email Address
        </label>
        <input
          id="comp-reg-email"
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
          htmlFor="comp-reg-password"
          className="block text-[0.69rem] font-700 text-slate-500 uppercase tracking-wider mb-1.5"
        >
          Password
        </label>
        <div className="relative">
          <input
            id="comp-reg-password"
            type={showPw ? 'text' : 'password'}
            placeholder="Minimum 6 characters"
            value={password}
            onChange={onPasswordChange}
            required
            minLength={6}
            disabled={loading}
            className="input-base px-4 py-3 pr-10"
          />
          <button
            type="button"
            onClick={() => setShowPw(!showPw)}
            aria-label={showPw ? 'Hide password' : 'Show password'}
            className="absolute right-3 top-1/2 -translate-y-1/2 text-slate-500 hover:text-slate-300 p-1 cursor-pointer"
          >
            {showPw ? <EyeOff size={16} /> : <Eye size={16} />}
          </button>
        </div>
      </div>

      <div>
        <label
          htmlFor="comp-reg-confirm"
          className="block text-[0.69rem] font-700 text-slate-500 uppercase tracking-wider mb-1.5"
        >
          Confirm Password
        </label>
        <div className="relative">
          <input
            id="comp-reg-confirm"
            type={showConfirmPw ? 'text' : 'password'}
            placeholder="Re-enter password"
            value={confirm}
            onChange={onConfirmChange}
            required
            minLength={6}
            disabled={loading}
            className="input-base px-4 py-3 pr-10"
          />
          <button
            type="button"
            onClick={() => setShowConfirmPw(!showConfirmPw)}
            aria-label={showConfirmPw ? 'Hide password' : 'Show password'}
            className="absolute right-3 top-1/2 -translate-y-1/2 text-slate-500 hover:text-slate-300 p-1 cursor-pointer"
          >
            {showConfirmPw ? <EyeOff size={16} /> : <Eye size={16} />}
          </button>
        </div>
      </div>

      <button
        type="submit"
        disabled={loading}
        className="btn-primary w-full py-3 flex items-center justify-center gap-2 mt-2"
      >
        {loading ? <Spinner size={18} /> : <><span>Create Account</span><ArrowRight size={16} /></>}
      </button>
    </form>
  )
}
