import { useEffect, useState } from 'react'
import { Check, Edit3, Search, X } from 'lucide-react'
import { cancelAppointment, completeAppointment, getAppointments, rescheduleAppointment } from '../api'
import Pagination from '../components/Pagination'
import SortableTableHeader from '../components/SortableTableHeader'
import Notice from '../components/Notice'

const fmt = value => new Date(value).toLocaleString([], { month: 'short', day: 'numeric', hour: 'numeric', minute: '2-digit' })

export default function Dashboard() {
  const [data, setData] = useState({ items: [], page: 1, pages: 0, total: 0 })
  const [page, setPage] = useState(1)
  const [query, setQuery] = useState('')
  const [sort, setSort] = useState('start_time')
  const [state, setState] = useState({ loading: true, error: '', notice: null })
  const [editing, setEditing] = useState(null)

  const load = async () => {
    setState(current => ({ ...current, loading: true, error: '' }))
    try { setData(await getAppointments({ page, size: 10, patient_name: query, sort })) }
    catch (err) { setState(current => ({ ...current, error: err.message })) }
    finally { setState(current => ({ ...current, loading: false })) }
  }
  useEffect(() => { const timer = setTimeout(load, 200); return () => clearTimeout(timer) }, [page, query, sort])

  const runAction = async (action, message) => {
    try { const result = await action(); setState(current => ({ ...current, notice: { type: 'success', message: message(result) } })); load() }
    catch (err) { setState(current => ({ ...current, error: err.message })) }
  }
  const cancel = id => runAction(() => cancelAppointment(id), result => result.late_fee_charged ? `Cancelled. Late fee: $${result.late_fee_amount}` : 'Cancelled with no fee.')
  const complete = id => runAction(() => completeAppointment(id), () => 'Appointment marked completed.')
  const saveReschedule = async (id, start, end) => {
    await runAction(() => rescheduleAppointment(id, { start_time: new Date(start).toISOString(), end_time: new Date(end).toISOString() }), () => 'Appointment rescheduled.')
    setEditing(null)
  }

  return <>
    <header className="topbar"><div><p className="eyebrow">APPOINTMENT FINDER</p><h1>Good morning, front desk.</h1></div></header>
    <Notice notice={state.notice || (state.error ? { type: 'error', message: state.error } : null)} onDismiss={() => setState(current => ({ ...current, notice: null, error: '' }))}/>
    <div className="section-heading"><div><p className="eyebrow">{data.total} RESULTS</p><h2>Appointments</h2></div><div className="search-box"><Search size={18}/><input placeholder="Search by patient name" value={query} onChange={event => { setPage(1); setQuery(event.target.value) }}/></div></div>
    {state.loading ? <div className="loading">Loading appointments…</div> : state.error && !data.items.length ? <Retry onRetry={load}/> : <><div className="table-wrap"><div className="table-head"><SortableTableHeader label="Patient" field="patient_name" sort={sort} onSort={setSort}/><SortableTableHeader label="Doctor" field="doctor_name" sort={sort} onSort={setSort}/><SortableTableHeader label="When" field="start_time" sort={sort} onSort={setSort}/><SortableTableHeader label="Status" field="status" sort={sort} onSort={setSort}/><span></span></div>{data.items.length ? data.items.map(item => <div className="table-row" key={item.id}><span><strong>{item.patient_name || `Patient #${item.patient_id}`}</strong><small>Appointment #{item.id}</small></span><span>{item.doctor_name || `Doctor #${item.doctor_id}`}</span><span>{fmt(item.start_time)}<small>{new Date(item.start_time).toLocaleTimeString([], { hour: 'numeric', minute: '2-digit' })} – {new Date(item.end_time).toLocaleTimeString([], { hour: 'numeric', minute: '2-digit' })}</small></span><span><b className={`status ${item.status}`}>{item.status}</b></span><span className="row-actions"><button className="row-action" disabled={item.status !== 'booked'} onClick={() => complete(item.id)} title="Mark completed"><Check size={14}/></button><button className="row-action" disabled={item.status !== 'booked'} onClick={() => cancel(item.id)}>Cancel</button><button className="row-action" disabled={item.status !== 'booked'} onClick={() => setEditing(item)} title="Reschedule"><Edit3 size={14}/></button></span>{editing?.id === item.id && <RescheduleEditor item={item} onSave={saveReschedule} onClose={() => setEditing(null)}/>}</div>) : <div className="empty">No appointments match this search.</div>}</div><Pagination page={data.page} pages={data.pages} onPageChange={setPage}/></>}
  </>
}

function RescheduleEditor({ item, onSave, onClose }) {
  const [start, setStart] = useState(item.start_time.slice(0, 16))
  const [end, setEnd] = useState(item.end_time.slice(0, 16))
  return <div className="reschedule-editor"><button className="close-button" onClick={onClose}><X size={15}/></button><label>Starts<input type="datetime-local" value={start} onChange={event => setStart(event.target.value)}/></label><label>Ends<input type="datetime-local" value={end} onChange={event => setEnd(event.target.value)}/></label><button className="primary small" onClick={() => onSave(item.id, start, end)}>Save new time</button></div>
}
function Retry({ onRetry }) { return <div className="empty">Could not load appointments. <button className="link-button" onClick={onRetry}>Retry</button></div> }
