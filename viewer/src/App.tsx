import { Navigate, Route, Routes } from "react-router-dom";

import { ViewerLayout } from "./components/ViewerLayout";
import { HomePage } from "./pages/HomePage";
import { SearchPage } from "./pages/SearchPage";
import { ShowDetailPage } from "./pages/ShowDetailPage";

export function App() {
  return (
    <Routes>
      <Route element={<ViewerLayout />}>
        <Route path="/" element={<HomePage />} />
        <Route path="/search" element={<SearchPage />} />
        <Route path="/shows/:slug" element={<ShowDetailPage />} />
        <Route path="*" element={<Navigate to="/" replace />} />
      </Route>
    </Routes>
  );
}