import { Navigate, Route, Routes } from "react-router-dom";
import AccessPage from "../../pages/AccessPage";
import BookDetailPage from "../../pages/BookDetailPage";
import CategoryPage from "../../pages/CategoryPage";
import CreatedBooksPage from "../../pages/CreatedBooksPage";
import HomePage from "../../pages/HomePage";
import LibraryPage from "../../pages/LibraryPage";
import LoginPage from "../../pages/LoginPage";
import ManualBooksPage from "../../pages/ManualBooksPage";
import NotesPage from "../../pages/NotesPage";
import PasswordLinkPage from "../../pages/PasswordLinkPage";
import PasswordResetPage from "../../pages/PasswordResetPage";
import ProfilePage from "../../pages/ProfilePage";
import ReaderPage from "../../pages/ReaderPage";
import SeriesPage from "../../pages/SeriesPage";
import TwoFactorSetupPage from "../../pages/TwoFactorSetupPage";
import WriterPage from "../../pages/WriterPage";
import ReprocessingPage from "../../pages/ReprocessingPage";
import {
  CatalogProcessingPage,
  CreateProcessingPage,
  EmptyChaptersProcessingPage,
  IncompleteProcessingPage,
  MultiPageTocProcessingPage,
  OnHoldProcessingPage,
} from "../processing/BookProcessingPages";
import ProtectedRoute from "./ProtectedRoute";

const protectedRoutes = [
  { path: "/home", element: <HomePage /> },
  { path: "/catalog", element: <CatalogProcessingPage /> },
  { path: "/create", element: <CreateProcessingPage /> },
  { path: "/on-hold", element: <OnHoldProcessingPage /> },
  { path: "/incomplete", element: <IncompleteProcessingPage /> },
  { path: "/multipage-toc", element: <MultiPageTocProcessingPage /> },
  { path: "/empty-chapters", element: <EmptyChaptersProcessingPage /> },
  { path: "/reprocessing", element: <ReprocessingPage /> },
  { path: "/library", element: <LibraryPage /> },
  { path: "/categories", element: <CategoryPage /> },
  { path: "/series", element: <SeriesPage /> },
  { path: "/writers", element: <WriterPage /> },
  { path: "/translators", element: <WriterPage /> },
  { path: "/editors", element: <WriterPage /> },
  { path: "/publishers", element: <WriterPage /> },
  { path: "/compilers", element: <Navigate to="/editors" replace /> },
  { path: "/manual-books", element: <ManualBooksPage /> },
  { path: "/my-books", element: <CreatedBooksPage /> },
  { path: "/books/:slug", element: <BookDetailPage /> },
  { path: "/access", element: <AccessPage /> },
  { path: "/profile", element: <ProfilePage /> },
  { path: "/notes", element: <NotesPage /> },
  { path: "/two-factor-setup", element: <TwoFactorSetupPage /> },
  { path: "/reader", element: <ReaderPage /> },
];

function renderProtectedRoute({ path, element }) {
  return (
    <Route
      key={path}
      path={path}
      element={<ProtectedRoute>{element}</ProtectedRoute>}
    />
  );
}

export default function AppRoutes() {
  return (
    <Routes>
      <Route
        path="/"
        element={
          <ProtectedRoute>
            <Navigate to="/home" replace />
          </ProtectedRoute>
        }
      />
      <Route path="/login" element={<LoginPage />} />
      <Route
        path="/created-books"
        element={<Navigate to="/my-books" replace />}
      />
      <Route path="/reset-password" element={<PasswordResetPage />} />
      <Route
        path="/reset-password/confirm"
        element={<PasswordLinkPage mode="reset" />}
      />
      <Route
        path="/create-password"
        element={<PasswordLinkPage mode="create" />}
      />
      {protectedRoutes.map(renderProtectedRoute)}
      <Route path="/processing" element={<Navigate to="/catalog" replace />} />
      <Route
        path="/processing-catalog-books"
        element={<Navigate to="/catalog" replace />}
      />
      <Route
        path="/processing-automation"
        element={<Navigate to="/catalog" replace />}
      />
      <Route
        path="/processing-my-requests"
        element={<Navigate to="/create" replace />}
      />
      <Route
        path="/processing-failed-requests"
        element={<Navigate to="/on-hold" replace />}
      />
      <Route
        path="/processing-duplicate-requests"
        element={<Navigate to="/on-hold" replace />}
      />
      <Route
        path="/processing-incomplete-check"
        element={<Navigate to="/incomplete" replace />}
      />
      <Route path="/queue" element={<Navigate to="/create" replace />} />
      <Route path="*" element={<Navigate to="/" replace />} />
    </Routes>
  );
}
