import { BrowserRouter as Router, Routes, Route, Navigate } from 'react-router-dom';
import { AuthProvider } from './hooks/useAuth';
import Layout from './components/Layout';
import WelcomePage from './pages/WelcomePage';
import HomePage from './pages/HomePage';
import LoginPage from './pages/LoginPage';
import RegisterPage from './pages/RegisterPage';
import HistoryPage from './pages/HistoryPage';
import AdminPage from './pages/AdminPage';
import GalleryPage from './pages/GalleryPage';
import GalleryDetailPage from './pages/GalleryDetailPage';
import ProtectedRoute from './components/ProtectedRoute';
import WelcomeRoute from './components/WelcomeRoute';

function App() {
  return (
    <AuthProvider>
      <Router>
        <Routes>
          {/* Welcome screen - redirects to /scan if logged in */}
          <Route
            path="/"
            element={
              <WelcomeRoute>
                <WelcomePage />
              </WelcomeRoute>
            }
          />

          {/* Auth routes - use Layout */}
          <Route element={<Layout />}>
            <Route path="/login" element={<LoginPage />} />
            <Route path="/register" element={<RegisterPage />} />
            <Route path="/gallery" element={<GalleryPage />} />
            <Route path="/gallery/:jobId" element={<GalleryDetailPage />} />

            {/* Protected routes - require authentication */}
            <Route
              path="/scan"
              element={
                <ProtectedRoute>
                  <HomePage />
                </ProtectedRoute>
              }
            />
            <Route
              path="/history"
              element={
                <ProtectedRoute>
                  <HistoryPage />
                </ProtectedRoute>
              }
            />
            <Route
              path="/admin"
              element={
                <ProtectedRoute requireAdmin>
                  <AdminPage />
                </ProtectedRoute>
              }
            />
          </Route>

          {/* Catch all - redirect to welcome */}
          <Route path="*" element={<Navigate to="/" replace />} />
        </Routes>
      </Router>
    </AuthProvider>
  );
}

export default App;
