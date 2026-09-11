import { NavLink, Outlet } from "react-router-dom";

export function ViewerLayout() {
  return (
    <div className="viewer-shell">
      <header className="viewer-header">
        <NavLink to="/" className="viewer-brand">
          Peblo TV
        </NavLink>
        <nav className="viewer-nav">
          <NavLink to="/" end>
            Home
          </NavLink>
          <NavLink to="/search">Search</NavLink>
        </nav>
      </header>
      <main className="viewer-main">
        <Outlet />
      </main>
    </div>
  );
}