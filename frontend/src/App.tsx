import { useEffect } from 'react';
import { BrowserRouter, Routes, Route } from 'react-router-dom';
import MainLayout from './components/layout/MainLayout';
import Dashboard from './pages/Dashboard';
import SessionPage from './pages/SessionPage';
import HistoryPage from './pages/HistoryPage';
import SessionDetailPage from './pages/SessionDetailPage';
import DocumentsPage from './pages/DocumentsPage';
import SettingsPage from './pages/SettingsPage';
import { applyStoredTheme, subscribeToThemeChanges } from './config/theme';

export default function App() {
  useEffect(() => {
    applyStoredTheme();
    return subscribeToThemeChanges(applyStoredTheme);
  }, []);

  return (
    <BrowserRouter>
      <Routes>
        <Route element={<MainLayout />}>
          <Route path="/" element={<Dashboard />} />
          <Route path="/session" element={<SessionPage />} />
          <Route path="/history" element={<HistoryPage />} />
          <Route path="/history/:id" element={<SessionDetailPage />} />
          <Route path="/documents" element={<DocumentsPage />} />
          <Route path="/settings" element={<SettingsPage />} />
        </Route>
      </Routes>
    </BrowserRouter>
  );
}
