import { CalendarDays, Clock3, LogOut, Search, Sparkles, Stethoscope } from 'lucide-react'
import { NavLink, useNavigate } from 'react-router-dom'
export default function Navbar() {
  const navigate = useNavigate()
  const signOut = () => { localStorage.removeItem('clinicdesk_token'); navigate('/login') }
  return <aside className="sidebar"><div className="brand"><span className="brand-mark"><Stethoscope size={18}/></span> ClinicDesk</div><div className="side-label">WORKSPACE</div><NavLink className="nav-item" to="/dashboard"><CalendarDays size={18}/> Overview</NavLink><NavLink className="nav-item" to="/book"><Sparkles size={18}/> Book appointment</NavLink><NavLink className="nav-item" to="/schedule"><Clock3 size={18}/> Doctor schedule</NavLink><NavLink className="nav-item" to="/patients"><Search size={18}/> Patient search</NavLink><div className="side-bottom"><button className="nav-item" onClick={signOut}><LogOut size={18}/> Sign out</button></div></aside>
}
