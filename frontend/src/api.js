const API = import.meta.env.VITE_API_URL || '/api'

export async function request(path, options = {}) {
  const token = localStorage.getItem('clinicdesk_token')
  const response = await fetch(API + path, {
    ...options,
    headers: { 'Content-Type': 'application/json', ...(token ? { Authorization: `Bearer ${token}` } : {}), ...(options.headers || {}) },
  })
  const body = await response.json().catch(() => ({}))
  if (response.status === 401) {
    localStorage.removeItem('clinicdesk_token')
    window.location.assign('/login')
    throw new Error('Your session expired. Please sign in again.')
  }
  if (!response.ok) throw new Error(body.detail || 'Something went wrong')
  return body
}

const query = params => new URLSearchParams(Object.entries(params).filter(([, value]) => value !== undefined && value !== '')).toString()
export const register = payload => request('/auth/register', { method: 'POST', body: JSON.stringify(payload) })
export const login = payload => request('/auth/login', { method: 'POST', body: JSON.stringify(payload) })
export const getDoctors = params => request(`/doctors?${query(params)}`)
export const createDoctor = payload => request('/doctors', { method: 'POST', body: JSON.stringify(payload) })
export const updateDoctor = (id, payload) => request(`/doctors/${id}`, { method: 'PATCH', body: JSON.stringify(payload) })
export const getAppointments = params => request(`/appointments?${query(params)}`)
export const getAppointment = id => request(`/appointments/${id}`)
export const createAppointment = payload => request('/appointments', { method: 'POST', body: JSON.stringify(payload) })
export const cancelAppointment = id => request(`/appointments/${id}/cancel`, { method: 'PATCH' })
export const completeAppointment = id => request(`/appointments/${id}/complete`, { method: 'PATCH' })
export const rescheduleAppointment = (id, payload) => request(`/appointments/${id}/reschedule`, { method: 'PATCH', body: JSON.stringify(payload) })
export const getDoctorSchedule = (id, date) => request(`/doctors/${id}/schedule?date=${date}`)
export const getClock = () => request('/clock')
export const searchPatients = params => request(`/patients?${query(params)}`)
export const updatePatient = (id, payload) => request(`/patients/${id}`, { method: 'PATCH', body: JSON.stringify(payload) })
export const deletePatient = id => request(`/patients/${id}`, { method: 'DELETE' })
