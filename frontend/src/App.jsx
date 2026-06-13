import { BrowserRouter, Routes, Route } from 'react-router-dom'
import Layout from './components/Layout/Layout.jsx'
import Home from './pages/Home.jsx'
import Clubs from './pages/Clubs.jsx'
import ClubDetail from './pages/ClubDetail.jsx'
import Competitions from './pages/Competitions.jsx'
import CompetitionDetail from './pages/CompetitionDetail.jsx'
import GameDetail from './pages/GameDetail.jsx'
import GamePrep from './pages/GamePrep.jsx'
import Stats from './pages/Stats.jsx'
import PlayerDetail from './pages/PlayerDetail.jsx'
import RefZone, { RefZoneProvider } from './pages/RefZone.jsx'
import Notifications from './pages/Notifications.jsx'
import LiveGames from './pages/LiveGames.jsx'


export default function App() {
  return (
    <RefZoneProvider>
      <BrowserRouter>
        <Routes>
          <Route element={<Layout />}>
            <Route path="/" element={<Home />} />
            <Route path="/clubs" element={<Clubs />} />
            <Route path="/clubs/:id" element={<ClubDetail />} />
            <Route path="/competitions" element={<Competitions />} />
            <Route path="/competitions/:id" element={<CompetitionDetail />} />
            <Route path="/games/:id" element={<GameDetail />} />
            <Route path="/games/:id/prep" element={<GamePrep />} />
            <Route path="/stats" element={<Stats />} />
            <Route path="/players/:id" element={<PlayerDetail />} />
            <Route path="/refzone" element={<RefZone />} />
            <Route path="/notifications" element={<Notifications />} />
            <Route path="/live" element={<LiveGames />} />
          </Route>
        </Routes>
      </BrowserRouter>
    </RefZoneProvider>
  )
}
