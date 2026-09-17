import { useEffect, useState } from 'react'
import { Edit3, Search, Trash2, X } from 'lucide-react'
import { deletePatient, getAppointments, searchPatients, updatePatient } from '../api'
import Pagination from '../components/Pagination'
import Notice from '../components/Notice'

export default function PatientSearch() {
  const [search, setSearch] = useState('')
  const [data, setData] = useState({ items: [], page: 1, pages: 0, total: 0 })
  const [selected, setSelected] = useState(null)
  const [appointments, setAppointments] = useState([])
  const [editing, setEditing] = useState(false)
  const [form, setForm] = useState({ name: '', phone: '', email: '' })
  const [state, setState] = useState({ loading: false, error: '', notice: null })

  const load = async () => {
    setState(current => ({ ...current, loading: true, error: '' }))
    try { setData(await searchPatients({ search, page: data.page, size: 10 })) }
    catch (err) { setState(current => ({ ...current, error: err.message })) }
    finally { setState(current => ({ ...current, loading: false })) }
  }
  useEffect(() => { const timer = setTimeout(load, 200); return () => clearTimeout(timer) }, [search, data.page])

  const choose = async patient => {
    setSelected(patient)
    setForm({ name: patient.name, phone: patient.phone || '', email: patient.email || '' })
    setEditing(false)
    try { const result = await getAppointments({ patient_id: patient.id, size: 100, sort: 'start_time' }); setAppointments(result.items) }
    catch (err) { setState(current => ({ ...current, error: err.message })) }
  }
  const save = async event => {
    event.preventDefault()
    try {
      const updated = await updatePatient(selected.id, { name: form.name, phone: form.phone || null, email: form.email || null })
      setSelected(updated); setEditing(false); load()
      setState(current => ({ ...current, notice: { type: 'success', message: 'Patient details updated.' } }))
    } catch (err) { setState(current => ({ ...current, error: err.message })) }
  }
  const remove = async () => {
    if (!window.confirm(`Delete ${selected.name}?`)) return
    try {
      await deletePatient(selected.id); setSelected(null); setAppointments([]); load()
      setState(current => ({ ...current, notice: { type: 'success', message: 'Patient deleted.' } }))
    } catch (err) { setState(current => ({ ...current, error: err.message })) }
  }
  const dismiss = () => setState(current => ({ ...current, error: '', notice: null }))

  return <>
    <header className="topbar"><div><p className="eyebrow">PATIENT LOOKUP</p><h1>Find a patient</h1></div></header>
    <Notice notice={state.notice || (state.error ? { type: 'error', message: state.error } : null)} onDismiss={dismiss}/>
    <div className="section-heading"><h2>Search patients</h2><div className="search-box"><Search size={18}/><input autoFocus placeholder="Search by name" value={search} onChange={event => { setSearch(event.target.value); setData(current => ({ ...current, page: 1 })) }}/></div></div>
    {state.loading ? <div className="loading">Searching patients…</div> : <div className="patient-layout"><div className="patient-results">{data.items.length ? data.items.map(patient => <button className={`patient-result ${selected?.id === patient.id ? 'selected' : ''}`} key={patient.id} onClick={() => choose(patient)}><strong>{patient.name}</strong><small>{patient.phone || patient.email || 'No contact details'}</small></button>) : <div className="empty">No patients match this search.</div>}<Pagination page={data.page} pages={data.pages} onPageChange={page => setData(current => ({ ...current, page }))}/></div>{selected ? <div className="patient-detail"><div className="detail-actions"><button className="row-action" onClick={() => setEditing(true)}><Edit3 size={15}/> Edit</button><button className="row-action danger" onClick={remove}><Trash2 size={15}/> Delete</button></div>{editing ? <form onSubmit={save} className="patient-edit-form"><button type="button" className="close-button" onClick={() => setEditing(false)}><X size={15}/></button><label>Name<input required value={form.name} onChange={event => setForm({ ...form, name: event.target.value })}/></label><label>Phone<input value={form.phone} onChange={event => setForm({ ...form, phone: event.target.value })}/></label><label>Email<input type="email" value={form.email} onChange={event => setForm({ ...form, email: event.target.value })}/></label><button className="primary small">Save details</button></form> : <><p className="eyebrow">PATIENT PROFILE</p><h2>{selected.name}</h2><p className="muted">{selected.phone || 'No phone'} · {selected.email || 'No email'}</p><h3>Appointments</h3>{appointments.length ? appointments.map(item => <div className="mini-appointment" key={item.id}><strong>{new Date(item.start_time).toLocaleString([], { dateStyle: 'medium', timeStyle: 'short' })}</strong><span>{item.doctor_name || `Doctor #${item.doctor_id}`} · {item.status}</span></div>) : <div className="empty">No appointments for this patient.</div>}</>}</div> : <div className="empty">Select a patient to see their appointments.</div>}</div>}
  </>
}
