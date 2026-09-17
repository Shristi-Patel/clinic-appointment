import { Navigate, Outlet, Route, Routes } from 'react-router-dom'
import Navbar from './components/Navbar'
import Landing from './pages/Landing'
import Login from './pages/Login'
import Register from './pages/Register'
import Dashboard from './pages/Dashboard'
import BookingForm from './pages/BookingForm'
import DoctorSchedule from './pages/DoctorSchedule'
import PatientSearch from './pages/PatientSearch'

function ProtectedRoute() { return localStorage.getItem('clinicdesk_token') ? <><Navbar/><main className="workspace"><Outlet/></main></> : <Navigate to="/login" replace /> }
export default function App() { return <Routes><Route path="/" element={<Landing/>}/><Route path="/login" element={<Login/>}/><Route path="/register" element={<Register/>}/><Route element={<ProtectedRoute/>}><Route path="/dashboard" element={<Dashboard/>}/><Route path="/book" element={<BookingForm/>}/><Route path="/schedule" element={<DoctorSchedule/>}/><Route path="/patients" element={<PatientSearch/>}/></Route><Route path="*" element={<Navigate to="/" replace/>}/></Routes> }
