/** Lists uploaded books with their processing status and indexed chunk counts. */
function BookLibrary({ books }) {
  if (!books.length) return <p className="empty">No books uploaded yet.</p>;
  return (
    <ul className="book-library">
      {books.map((book) => (
        <li key={book.id}>
          <strong>{book.title}</strong>
          <span className={`status ${book.processing_status}`}>{book.processing_status}</span>
          {book.phase && <small>{book.phase}</small>}
          <small>{book.chunks_indexed} chunks</small>
        </li>
      ))}
    </ul>
  );
}

export default BookLibrary;
