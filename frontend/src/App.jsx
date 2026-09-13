import { HashRouter, Link, Route, Routes } from "react-router-dom";
import Dashboard from "./pages/Dashboard";
import Study from "./pages/Study";
import Quiz from "./pages/Quiz";
import CodeLab from "./pages/CodeLab";
import Library from "./pages/Library";

/** Top-level shell: bottom nav for mobile plus route switching between the five pages. */
function App() {
  return (
    <HashRouter>
      <main>
        <Routes>
          <Route path="/" element={<Dashboard />} />
          <Route path="/study" element={<Study />} />
          <Route path="/quiz" element={<Quiz />} />
          <Route path="/code" element={<CodeLab />} />
          <Route path="/library" element={<Library />} />
        </Routes>
        <nav className="tab-bar">
          <Link to="/">Map</Link>
          <Link to="/study">Study</Link>
          <Link to="/quiz">Quiz</Link>
          <Link to="/code">Code</Link>
          <Link to="/library">Library</Link>
        </nav>
      </main>
    </HashRouter>
  );
}

export default App;
