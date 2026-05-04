import { Outlet } from 'react-router-dom';
import Sidebar from './Sidebar';
import Header from './Header';
import { useStore } from '../../store/useStore';

export default function MainLayout() {
  const { sidebarCollapsed, sidebarWidth } = useStore();
  const effectiveSidebarWidth = sidebarCollapsed ? 64 : sidebarWidth;

  return (
    <div className="flex w-full min-h-screen bg-space-black">
      <Sidebar />
      <div
        className="flex-1 flex flex-col"
        style={{ marginLeft: effectiveSidebarWidth }}
      >
        <Header />
        <main className="flex-1 overflow-auto">
          <Outlet />
        </main>
      </div>
    </div>
  );
}
