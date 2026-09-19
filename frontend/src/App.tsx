import { Navigate, Route, Routes } from 'react-router-dom'

import Layout from './components/Layout'
import ProtectedRoute from './components/ProtectedRoute'
import LoginPage from './pages/LoginPage'
import PageDetailPage from './pages/PageDetailPage'
import PagesListPage from './pages/PagesListPage'
import UsersPage from './pages/UsersPage'

export default function App() {
  return (
    <Routes>
      <Route path="/login" element={<LoginPage />} />
      <Route element={<ProtectedRoute />}>
        <Route element={<Layout />}>
          <Route path="/" element={<Navigate to="/pages" replace />} />
          <Route path="/pages" element={<PagesListPage />} />
          <Route path="/pages/:pageId" element={<PageDetailPage />} />
          <Route path="/users" element={<UsersPage />} />
        </Route>
      </Route>
      <Route path="*" element={<Navigate to="/pages" replace />} />
    </Routes>
  )
}
