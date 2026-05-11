import { useState } from 'react';
import { NavLink } from 'react-router-dom';
import type { MouseEvent as ReactMouseEvent } from 'react';
import {
  LayoutDashboard,
  Radio,
  Clock,
  FileText,
  Settings,
  ChevronLeft,
  ChevronRight,
  Satellite,
  LineChart,
} from 'lucide-react';
import { useStore } from '../../store/useStore';

const navItems = [
  { to: '/', icon: LayoutDashboard, label: 'Dashboard' },
  { to: '/session', icon: Radio, label: 'Active Session' },
  { to: '/history', icon: Clock, label: 'Structured Notes' },
  { to: '/telemetry-query', icon: LineChart, label: 'Telemetry Query' },
  { to: '/documents', icon: FileText, label: 'Documents' },
  { to: '/settings', icon: Settings, label: 'Settings' },
];

export default function Sidebar() {
  const { sidebarCollapsed, sidebarWidth, setSidebarWidth, toggleSidebar } = useStore();
  const effectiveWidth = sidebarCollapsed ? 64 : sidebarWidth;
  const [isResizing, setIsResizing] = useState(false);

  const startResize = (event: ReactMouseEvent<HTMLDivElement>) => {
    if (sidebarCollapsed) return;
    event.preventDefault();
    setIsResizing(true);
    document.body.style.cursor = 'col-resize';
    document.body.style.userSelect = 'none';

    const handleMove = (moveEvent: MouseEvent) => {
      setSidebarWidth(moveEvent.clientX);
    };

    const stop = () => {
      setIsResizing(false);
      document.body.style.cursor = '';
      document.body.style.userSelect = '';
      window.removeEventListener('mousemove', handleMove);
      window.removeEventListener('mouseup', stop);
    };

    window.addEventListener('mousemove', handleMove);
    window.addEventListener('mouseup', stop);
  };

  return (
    <aside
      className={`fixed left-0 top-0 h-screen bg-space-dark border-r border-space-border flex flex-col z-50 ${
        sidebarCollapsed && !isResizing ? 'transition-[width] duration-200' : ''
      }`}
      style={{ width: effectiveWidth }}
    >
      {/* Logo */}
      <div className="flex items-center gap-3 px-4 h-16 border-b border-space-border shrink-0">
        <div className="w-8 h-8 rounded-lg bg-gradient-to-br from-accent-cyan to-nasa-blue flex items-center justify-center shrink-0">
          <Satellite className="w-4 h-4 text-white" />
        </div>
        {!sidebarCollapsed && (
          <div className="animate-fade-in">
            <h1 className="text-sm font-bold tracking-wider text-text-primary">ASTRA</h1>
            <p className="text-[10px] text-text-muted leading-none">JPL Testbed Assistant</p>
          </div>
        )}
      </div>

      {/* Navigation */}
      <nav className="flex-1 overflow-y-auto py-4 px-2 space-y-1">
        {navItems.map((item) => (
          <NavLink
            key={item.to}
            to={item.to}
            className={({ isActive }) =>
              `flex items-center gap-3 px-3 py-2.5 rounded-lg text-sm font-medium transition-all duration-200 ${
                isActive
                  ? 'bg-accent-cyan/10 text-accent-cyan'
                  : 'text-text-secondary hover:bg-space-hover hover:text-text-primary'
              } ${sidebarCollapsed ? 'justify-center' : ''}`
            }
          >
            <item.icon className="w-5 h-5 shrink-0" />
            {!sidebarCollapsed && <span className="animate-fade-in">{item.label}</span>}
          </NavLink>
        ))}
      </nav>

      {/* System Status - simplified */}
      {!sidebarCollapsed && (
        <div className="px-3 py-4 border-t border-space-border animate-fade-in">
          <div className="flex items-center gap-2 text-xs text-text-muted">
            <div className="w-2 h-2 rounded-full bg-accent-green animate-pulse-glow" />
            System Online
          </div>
        </div>
      )}

      {/* Collapse Toggle */}
      <button
        onClick={toggleSidebar}
        className="flex items-center justify-center h-10 border-t border-space-border text-text-muted hover:text-text-primary hover:bg-space-hover transition-colors"
      >
        {sidebarCollapsed ? <ChevronRight className="w-4 h-4" /> : <ChevronLeft className="w-4 h-4" />}
      </button>

      {!sidebarCollapsed && (
        <div
          onMouseDown={startResize}
          className="absolute right-[-4px] top-0 h-full w-2 cursor-col-resize transition-colors hover:bg-accent-cyan/25"
          title="Drag to resize sidebar"
        />
      )}
    </aside>
  );
}
