import { useState } from "react";
import { Navigate, useLocation, useNavigate } from "react-router-dom";

import { useLogin } from "../api/auth";
import { isApiError } from "../api/artwork";
import { useAuth } from "../auth/AuthContext";

export function LoginPage() {
  const { isAuthenticated } = useAuth();
  const [email, setEmail] = useState("");
  const [password, setPassword] = useState("");
  const login = useLogin();
  const navigate = useNavigate();
  const location = useLocation();
  const from = (location.state as { from?: string } | null)?.from ?? "/shows";

  if (isAuthenticated) {
    return <Navigate to={from} replace />;
  }

  function handleSubmit(e: React.FormEvent) {
    e.preventDefault();
    login.mutate(
      { email, password },
      {
        onSuccess: () => navigate(from, { replace: true }),
      },
    );
  }

  return (
    <div className="login-page">
      <form onSubmit={handleSubmit} className="login-form">
        <h1>Peblo TV — CMS</h1>
        <label htmlFor="email">Email</label>
        <input id="email" type="email" required autoFocus value={email} onChange={(e) => setEmail(e.target.value)} />

        <label htmlFor="password">Password</label>
        <input
          id="password"
          type="password"
          required
          value={password}
          onChange={(e) => setPassword(e.target.value)}
        />

        <button type="submit" disabled={login.isPending}>
          {login.isPending ? "Signing in…" : "Sign in"}
        </button>

        {login.isError && (
          <p className="field-error" role="alert">
            {isApiError(login.error) ? login.error.message : "Sign in failed."}
          </p>
        )}
      </form>
    </div>
  );
}
