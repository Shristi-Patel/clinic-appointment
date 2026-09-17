import { useEffect, useState } from 'react'
import { Search } from 'lucide-react'
import { getAppointments, searchPatients } from '../api'
import Pagination from '../components/Pagination'
import Notice from '../components/Notice'

export default function PatientSearch() {
  const [search, setSearch] = useState('')
  const [data, setData] = useState({ items: [], page: 1, pages: 0, total: 0 })
  const [selected, setSelected] = useState(null)
  const [appointments, setAppointments] = useState([])
  const [state, setState] = useState({ loading: false, error: '' })
  const load = async () => {
    setState({ loading: true, error: '' })
    try { setData(await searchPatients({ search, page: data.page, size: 10 })) }
    catch (err) { setState({ loading: false, error: err.message }) }
    finally { setState(current => ({ ...current, loading: false })) }
  }
  useEffect(() => { const timer = setTimeout(load, 200); return () => clearTimeout(timer) }, [search, data.page])
  const choose = async patient => {
    setSelected(patient)
    try { const result = await getAppointments({ patient_id: patient.id, size: 100, sort: 'start_time' }); setAppointments(result.items) }
    catch (err) { setState(current => ({ ...current, error: err.message })) }
  }
  return <>
    <header className="topbar"><div><p className="eyebrow">PATIENT LOOKUP</p><h1>Find a patient</h1></div></header>
    {state.error && <Notice notice={{ type: 'error', message: state.error }} onDismiss={() => setState(current => ({ ...current, error: '' }))}/>}<div className="section-heading"><h2>Search patients</h2><div className="search-box"><Search size={18}/><input autoFocus placeholder="Search by name" value={search} onChange={e => { setSearch(e.target.value); setData(current => ({ ...current, page: 1 })) }}/></div></div>
    {state.loading ? <div className="loading">Searching patients…</div> : <div className="patient-layout"><div className="patient-results">{data.items.length ? data.items.map(patient => <button className={`patient-result ${selected?.id === patient.id ? 'selected' : ''}`} key={patient.id} onClick={() => choose(patient)}><strong>{patient.name}</strong><small>{patient.phone || patient.email || 'No contact details'}</small></button>) : <div className="empty">No patients match this search.</div>}<Pagination page={data.page} pages={data.pages} onPageChange={page => setData(current => ({ ...current, page }))}/></div>{selected ? <div className="patient-detail"><p className="eyebrow">PATIENT PROFILE</p><h2>{selected.name}</h2><p className="muted">{selected.phone || 'No phone'} · {selected.email || 'No email'}</p><h3>Appointments</h3>{appointments.length ? appointments.map(item => <div className="mini-appointment" key={item.id}><strong>{new Date(item.start_time).toLocaleString([], { dateStyle: 'medium', timeStyle: 'short' })}</strong><span>{item.doctor_name || `Doctor #${item.doctor_id}`} · {item.status}</span></div>) : <div className="empty">No appointments for this patient.</div>}</div> : <div className="empty">Select a patient to see their appointments.</div>}</div>}
  </>
}
