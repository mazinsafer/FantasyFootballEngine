import { useState } from 'react'
import { Navigate, Route, Routes } from 'react-router-dom'
import { Sidebar } from './components/Sidebar'
import { TopBar } from './components/TopBar'
import { HomePage } from './pages/HomePage'
import { RankingsPage } from './pages/RankingsPage'
import { PlayerDetailPage } from './pages/PlayerDetailPage'
import { TeamPage } from './pages/TeamPage'
import { SlatePage } from './pages/SlatePage'
import { ModelPage } from './pages/ModelPage'

export default function App() {
  const [sidebarOpen, setSidebarOpen] = useState(false)

  return (
    <div className="flex min-h-screen">
      <Sidebar open={sidebarOpen} onClose={() => setSidebarOpen(false)} />
      <div className="flex min-w-0 flex-1 flex-col">
        <TopBar onOpenSidebar={() => setSidebarOpen(true)} />
        <main className="flex-1">
          <Routes>
            <Route path="/" element={<HomePage />} />
            <Route path="/rankings" element={<RankingsPage />} />
            <Route path="/players/:playerId" element={<PlayerDetailPage />} />
            <Route path="/teams" element={<Navigate to="/teams/KC" replace />} />
            <Route path="/teams/:abbr" element={<TeamPage />} />
            <Route path="/slate" element={<SlatePage />} />
            <Route path="/model" element={<ModelPage />} />
            <Route path="*" element={<Navigate to="/" replace />} />
          </Routes>
        </main>
      </div>
    </div>
  )
}
