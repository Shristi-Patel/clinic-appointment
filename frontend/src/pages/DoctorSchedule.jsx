import { useEffect, useState } from 'react'
import { Edit3, Plus, X } from 'lucide-react'
import { createDoctor, getDoctorSchedule, getDoctors, updateDoctor } from '../api'
import Notice from '../components/Notice'

export default function DoctorSchedule() {
  const [doctors, setDoctors] = useState([])
  const [doctor, setDoctor] = useState('')
  const [day, setDay] = useState(new Date().toISOString().slice(0, 10))
  const [items, setItems] = useState([])
  const [editor, setEditor] = useState(null)
  const [form, setForm] = useState({ name: '', specialty: '' })
  const [state, setState] = useState({ loading: true, error: '', notice: null })

  const loadDoctors = async () => {
    try { const data = await getDoctors({ size: 100 }); setDoctors(data.items) }
    catch (err) { setState(current => ({ ...current, error: err.message })) }
    finally { setState(current => ({ ...current, loading: false })) }
  }
  const loadSchedule = async () => {
    if (!doctor) { setItems([]); return }
    setState(current => ({ ...current, loading: true, error: '' }))
    try { setItems(await getDoctorSchedule(doctor, day)) }
    catch (err) { setState(current => ({ ...current, error: err.message })) }
    finally { setState(current => ({ ...current, loading: false })) }
  }
  useEffect(() => { loadDoctors() }, [])
  useEffect(() => { loadSchedule() }, [doctor, day])

  const openCreate = () => { setForm({ name: '', specialty: '' }); setEditor({ type: 'create' }) }
  const openEdit = current => { setForm({ name: current.name, specialty: current.specialty }); setEditor({ type: 'edit', id: current.id }) }
  const saveDoctor = async event => {
    event.preventDefault()
    try {
      const saved = editor.type === 'create' ? await createDoctor(form) : await updateDoctor(editor.id, form)
      setDoctors(current => editor.type === 'create' ? [...current, saved].sort((a, b) => a.name.localeCompare(b.name)) : current.map(item => item.id === saved.id ? saved : item))
      setEditor(null); setState(current => ({ ...current, notice: { type: 'success', message: editor.type === 'create' ? 'Doctor added.' : 'Doctor details updated.' } }))
    } catch (err) { setState(current => ({ ...current, error: err.message })) }
  }
  const dismiss = () => setState(current => ({ ...current, error: '', notice: null }))

  return <><header className="topbar"><div><p className="eyebrow">DAY VIEW</p><h1>Doctor schedule</h1></div><button className="primary small" onClick={openCreate}><Plus size={16}/> Add doctor</button></header><Notice notice={state.error ? { type: 'error', message: state.error } : state.notice} onDismiss={dismiss}/>{editor && <form className="doctor-editor" onSubmit={saveDoctor}><button type="button" className="close-button" onClick={() => setEditor(null)}><X size={15}/></button><p className="eyebrow">{editor.type === 'create' ? 'NEW DOCTOR' : 'EDIT DOCTOR'}</p><label>Name<input required value={form.name} onChange={event => setForm({ ...form, name: event.target.value })}/></label><label>Specialty<input required value={form.specialty} onChange={event => setForm({ ...form, specialty: event.target.value })}/></label><button className="primary small">{editor.type === 'create' ? 'Add doctor' : 'Save details'}</button></form>}<div className="schedule-controls"><select value={doctor} onChange={event => setDoctor(event.target.value)}><option value="">Select a doctor</option>{doctors.map(item => <option key={item.id} value={item.id}>{item.name} · {item.specialty}</option>)}</select>{doctor && <button className="icon-button" title="Edit selected doctor" onClick={() => openEdit(doctors.find(item => String(item.id) === String(doctor)))}><Edit3 size={17}/></button>}<input type="date" value={day} onChange={event => setDay(event.target.value)}/></div>{state.loading ? <div className="loading">Loading schedule…</div> : !doctor ? <div className="empty">Choose a doctor to see their day.</div> : <div className="timeline">{items.length ? items.map(item => <div className="timeline-item" key={item.id}><span>{new Date(item.start_time).toLocaleTimeString([], { hour: 'numeric', minute: '2-digit' })}</span><div className="timeline-card"><b>{item.patient_name || `Patient #${item.patient_id}`}</b><small>{new Date(item.start_time).toLocaleString([], { month: 'short', day: 'numeric' })} · {item.status}</small></div></div>) : <div className="empty">This doctor has a clear schedule for the selected day.</div>}</div>}</>
}
