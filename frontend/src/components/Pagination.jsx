export default function Pagination({ page, pages, onPageChange }) {
  if (!pages || pages <= 1) return null
  return <div className="pagination"><button disabled={page <= 1} onClick={() => onPageChange(page - 1)}>Previous</button><span>Page {page} of {pages}</span><button disabled={page >= pages} onClick={() => onPageChange(page + 1)}>Next</button></div>
}
