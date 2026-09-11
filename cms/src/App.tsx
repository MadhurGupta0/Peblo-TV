import { Navigate, Route, Routes } from "react-router-dom";

import { Layout } from "./components/Layout";
import { ProtectedRoute } from "./components/ProtectedRoute";
import { EpisodeFormPage } from "./pages/EpisodeFormPage";
import { EpisodesListPage } from "./pages/EpisodesListPage";
import { LoginPage } from "./pages/LoginPage";
import { PublishPage } from "./pages/PublishPage";
import { ShowFormPage } from "./pages/ShowFormPage";
import { ShowsListPage } from "./pages/ShowsListPage";

export function App() {
  return (
    <Routes>
      <Route path="/login" element={<LoginPage />} />
      <Route element={<ProtectedRoute />}>
        <Route element={<Layout />}>
          <Route path="/" element={<Navigate to="/shows" replace />} />
          <Route path="/shows" element={<ShowsListPage />} />
          <Route path="/shows/:id" element={<ShowFormPage />} />
          <Route path="/episodes" element={<EpisodesListPage />} />
          <Route path="/episodes/:id" element={<EpisodeFormPage />} />
          <Route path="/publish" element={<PublishPage />} />
        </Route>
      </Route>
    </Routes>
  );
}
