import { BrowserRouter, Navigate, Route, Routes } from "react-router-dom";
import Layout from "./components/Layout";
import { AuthProvider } from "./context/AuthContext";
import { ThemeProvider } from "./context/ThemeContext";
import Author from "./pages/Author";
import Following from "./pages/Following";
import Home from "./pages/Home";
import Login from "./pages/Login";
import NewsletterConfirm from "./pages/NewsletterConfirm";
import NewsletterUnsubscribe from "./pages/NewsletterUnsubscribe";
import Notifications from "./pages/Notifications";
import PostDetail from "./pages/PostDetail";
import Register from "./pages/Register";
import Search from "./pages/Search";
import SeriesDetail from "./pages/SeriesDetail";
import SeriesList from "./pages/SeriesList";
import Studio from "./pages/Studio";
import Write from "./pages/Write";
import "./styles/ledger.css";

export default function App() {
  return (
    <ThemeProvider>
      <AuthProvider>
        <BrowserRouter>
          <Routes>
            <Route element={<Layout />}>
              <Route index element={<Home />} />
              <Route path="search" element={<Search />} />
              <Route path="post/:slug" element={<PostDetail />} />
              <Route path="author/:username" element={<Author />} />
              <Route path="series" element={<SeriesList />} />
              <Route path="series/:slug" element={<SeriesDetail />} />
              <Route path="following" element={<Following />} />
              <Route path="notifications" element={<Notifications />} />
              <Route path="studio" element={<Studio />} />
              <Route path="write" element={<Write />} />
              <Route path="write/:slug" element={<Write />} />
              <Route path="login" element={<Login />} />
              <Route path="register" element={<Register />} />
              <Route path="newsletter/confirm/:token" element={<NewsletterConfirm />} />
              <Route path="newsletter/unsubscribe/:token" element={<NewsletterUnsubscribe />} />
              <Route path="*" element={<Navigate to="/" replace />} />
            </Route>
          </Routes>
        </BrowserRouter>
      </AuthProvider>
    </ThemeProvider>
  );
}
