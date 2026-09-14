import { HashRouter, NavLink, Route, Routes } from "react-router-dom";
import Dashboard from "./pages/Dashboard";
import Study from "./pages/Study";
import Quiz from "./pages/Quiz";
import CodeLab from "./pages/CodeLab";
import Library from "./pages/Library";

/** Top-level shell: header nav (highlights the current section) plus route switching
 * between the five pages. */
function App() {
  return (
    <HashRouter>
      <header className="top-nav">
        <NavLink to="/" end>
          Map
        </NavLink>
        <NavLink to="/study">Study</NavLink>
        <NavLink to="/quiz">Quiz</NavLink>
        <NavLink to="/code">Code</NavLink>
        <NavLink to="/library">Library</NavLink>
      </header>
      <main>
        <Routes>
          <Route path="/" element={<Dashboard />} />
          <Route path="/study" element={<Study />} />
          <Route path="/quiz" element={<Quiz />} />
          <Route path="/code" element={<CodeLab />} />
          <Route path="/library" element={<Library />} />
        </Routes>
      </main>
    </HashRouter>
  );
}

export default App;

