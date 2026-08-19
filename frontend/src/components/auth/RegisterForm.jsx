import { ArrowRight } from 'lucide-react'
import { Spinner } from '../ui'

/**
 * RegisterForm — extracted registration form component.
 *
 * Props: name, email, password, confirm, onNameChange, onEmailChange,
 *        onPasswordChange, onConfirmChange, onSubmit, loading
 */
export default function RegisterForm({
  name, email, password, confirm,
  onNameChange, onEmailChange, onPasswordChange, onConfirmChange,
  onSubmit, loading,
}) {
  return (
    <form onSubmit={onSubmit} className="space-y-4 animate-fade-in">
      <div>
        <label className="block text-[0.69rem] font-700 text-slate-500 uppercase tracking-wider mb-1.5">
          Full Name
        </label>
        <input
          placeholder="Priya Sharma"
          value={name}
          onChange={onNameChange}
          required
          className="input-base px-4 py-3"
        />
      </div>

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

      <div>
        <label className="block text-[0.69rem] font-700 text-slate-500 uppercase tracking-wider mb-1.5">
          Password
        </label>
        <input
          type="password"
          placeholder="Minimum 6 characters"
          value={password}
          onChange={onPasswordChange}
          required
          className="input-base px-4 py-3"
        />
      </div>

      <div>
        <label className="block text-[0.69rem] font-700 text-slate-500 uppercase tracking-wider mb-1.5">
          Confirm Password
        </label>
        <input
          type="password"
          placeholder="Re-enter password"
          value={confirm}
          onChange={onConfirmChange}
          required
          className="input-base px-4 py-3"
        />
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
