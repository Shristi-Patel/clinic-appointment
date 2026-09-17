import { Check, X } from 'lucide-react'
export default function Notice({ notice, onDismiss, onRetry }) {
  if (!notice) return null
  const retry = onRetry || (() => window.location.reload())
  return <div className={`notice ${notice.type === 'error' ? 'notice-error' : ''}`}><Check size={17}/><span>{notice.message}</span>{notice.type === 'error' && <button className="retry-button" onClick={retry}>Retry</button>}<button onClick={onDismiss}><X size={16}/></button></div>
}
