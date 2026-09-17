export default function SortableTableHeader({ label, field, sort, onSort }) {
  const active = sort === field || sort === `-${field}`
  return <button className={`sort-header ${active ? 'active' : ''}`} onClick={() => onSort(sort === field ? `-${field}` : field)}>{label}<span>{active ? (sort.startsWith('-') ? '↓' : '↑') : '↕'}</span></button>
}
