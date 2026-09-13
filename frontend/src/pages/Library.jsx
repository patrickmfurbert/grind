import { useEffect, useState } from "react";
import { useNavigate } from "react-router-dom";
import UploadZone from "../components/BookUpload/UploadZone";
import BookLibrary from "../components/BookUpload/BookLibrary";
import { api } from "../hooks/api";

/** Library page: upload PDFs for RAG indexing and browse previously uploaded books. */
function Library() {
  const navigate = useNavigate();
  const [books, setBooks] = useState([]);

  function refresh() {
    api("/books").then((data) => setBooks(data.books));
  }

  useEffect(refresh, []);

  return (
    <section className="library">
      <button className="back" onClick={() => navigate("/")}>
        ← Map
      </button>
      <h1>Library</h1>
      <UploadZone onUploaded={refresh} />
      <BookLibrary books={books} />
    </section>
  );
}

export default Library;
