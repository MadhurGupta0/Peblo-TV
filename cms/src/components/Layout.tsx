import { NavLink, Outlet } from "react-router-dom";

import { useAuth } from "../auth/AuthContext";

export function Layout() {
  const { user, logout } = useAuth();

  return (
    <div className="app-shell">
      <header className="app-header">
        <span className="app-title">Peblo TV — CMS</span>
        <nav>
          <NavLink to="/shows" className={({ isActive }) => (isActive ? "active" : "")}>
            Shows
          </NavLink>
          <NavLink to="/episodes" className={({ isActive }) => (isActive ? "active" : "")}>
            Episodes
          </NavLink>
          <NavLink to="/publish" className={({ isActive }) => (isActive ? "active" : "")}>
            Publish
          </NavLink>
        </nav>
        <div className="app-user">
          {user && (
            <span>
              {user.email} <span className="role-badge">{user.role}</span>
            </span>
          )}
          <button type="button" onClick={logout}>
            Log out
          </button>
        </div>
      </header>
      <main className="app-main">
        <Outlet />
      </main>
    </div>
  );
}
