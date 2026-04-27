import { NavLink, Outlet, useNavigate } from "react-router-dom";

import { useAuth } from "../context/AuthContext";

function SidebarLink({ to, children, onClick }) {
  return (
    <NavLink
      to={to}
      onClick={onClick}
      className={({ isActive }) =>
        `block rounded px-3 py-2 text-sm ${isActive ? "bg-gray-200 font-semibold" : "text-gray-700 hover:bg-gray-100"}`
      }
    >
      {children}
    </NavLink>
  );
}

export default function DashboardLayout() {
  const { user, logout } = useAuth();
  const navigate = useNavigate();

  const handleLogout = async (event) => {
    event.preventDefault();
    await logout();
    navigate("/login", { replace: true });
  };

  const avatarLabel = user?.first_name?.[0] || user?.email?.[0] || "U";

  return (
    <div className="min-h-screen bg-gray-50">
      <div className="flex min-h-screen">
        <aside className="w-64 border-r bg-white p-4">
          <h2 className="mb-6 text-lg font-bold">SaaS App</h2>
          <nav className="space-y-1">
            <SidebarLink to="/dashboard">Dashboard</SidebarLink>
            <SidebarLink to="/profile">Profile</SidebarLink>
            <SidebarLink to="/settings">Settings</SidebarLink>
            <SidebarLink to="/billing">Billing</SidebarLink>
            <SidebarLink to="/logout" onClick={handleLogout}>
              Logout
            </SidebarLink>
          </nav>
        </aside>

        <div className="flex min-h-screen flex-1 flex-col">
          <header className="flex items-center justify-between border-b bg-white px-6 py-4">
            <h1 className="text-lg font-semibold">Dashboard</h1>
            <div className="flex h-9 w-9 items-center justify-center rounded-full bg-gray-200 text-sm font-semibold text-gray-700">
              {String(avatarLabel).toUpperCase()}
            </div>
          </header>

          <main className="flex-1 p-6">
            <Outlet />
          </main>
        </div>
      </div>
    </div>
  );
}
