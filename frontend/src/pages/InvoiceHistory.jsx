import { useMemo, useState } from 'react'

const invoiceData = [
  { id: 'INV-2026-0112', supplier: 'Golden Health Supplies', date: '2026-06-30', status: 'Paid', total: '$19,430.00' },
  { id: 'INV-2026-0107', supplier: 'Sunrise Pharma', date: '2026-06-28', status: 'Pending', total: '$12,480.00' },
  { id: 'INV-2026-0103', supplier: 'MediCare Labs', date: '2026-06-26', status: 'Cancelled', total: '$8,190.00' },
  { id: 'INV-2026-0098', supplier: 'Healthline Co.', date: '2026-06-22', status: 'Paid', total: '$5,740.00' },
  { id: 'INV-2026-0092', supplier: 'Wellness Direct', date: '2026-06-18', status: 'Overdue', total: '$14,025.00' },
  { id: 'INV-2026-0087', supplier: 'PharmaPro Services', date: '2026-06-14', status: 'Paid', total: '$6,520.00' },
  { id: 'INV-2026-0080', supplier: 'CarePlus Solutions', date: '2026-06-09', status: 'Pending', total: '$10,980.00' },
  { id: 'INV-2026-0074', supplier: 'Apex Medical', date: '2026-06-03', status: 'Paid', total: '$7,300.00' },
  { id: 'INV-2026-0069', supplier: 'PharmaSphere', date: '2026-05-29', status: 'Overdue', total: '$11,250.00' },
  { id: 'INV-2026-0062', supplier: 'HealthBridge', date: '2026-05-22', status: 'Cancelled', total: '$9,480.00' },
  { id: 'INV-2026-0058', supplier: 'BioCare Systems', date: '2026-05-17', status: 'Paid', total: '$4,950.00' },
  { id: 'INV-2026-0051', supplier: 'Nexa Pharmaceuticals', date: '2026-05-11', status: 'Pending', total: '$16,720.00' },
]

const statusOptions = ['All', 'Paid', 'Pending', 'Cancelled', 'Overdue']
const dateOptions = ['All', 'Last 7 days', 'Last 30 days', 'This month']

function formatStatusBadge(status) {
  switch (status) {
    case 'Paid':
      return 'bg-emerald-100 text-emerald-700'
    case 'Pending':
      return 'bg-orange-100 text-orange-700'
    case 'Cancelled':
      return 'bg-slate-100 text-slate-700'
    case 'Overdue':
      return 'bg-rose-100 text-rose-700'
    default:
      return 'bg-slate-100 text-slate-700'
  }
}

function InvoiceHistory() {
  const [search, setSearch] = useState('')
  const [statusFilter, setStatusFilter] = useState('All')
  const [dateFilter, setDateFilter] = useState('All')
  const [page, setPage] = useState(1)
  const pageSize = 6

  const filteredInvoices = useMemo(() => {
    const searchLower = search.toLowerCase()
    const today = new Date('2026-07-01')
    const startOfMonth = new Date('2026-06-01')
    const sevenDaysAgo = new Date(today)
    sevenDaysAgo.setDate(today.getDate() - 7)
    const thirtyDaysAgo = new Date(today)
    thirtyDaysAgo.setDate(today.getDate() - 30)

    return invoiceData.filter((invoice) => {
      const matchesSearch =
        invoice.id.toLowerCase().includes(searchLower) ||
        invoice.supplier.toLowerCase().includes(searchLower)

      const matchesStatus = statusFilter === 'All' || invoice.status === statusFilter

      const invoiceDate = new Date(invoice.date)
      let matchesDate = true
      if (dateFilter === 'Last 7 days') {
        matchesDate = invoiceDate >= sevenDaysAgo
      } else if (dateFilter === 'Last 30 days') {
        matchesDate = invoiceDate >= thirtyDaysAgo
      } else if (dateFilter === 'This month') {
        matchesDate = invoiceDate >= startOfMonth
      }

      return matchesSearch && matchesStatus && matchesDate
    })
  }, [search, statusFilter, dateFilter])

  const pageCount = Math.max(1, Math.ceil(filteredInvoices.length / pageSize))
  const paginatedInvoices = filteredInvoices.slice((page - 1) * pageSize, page * pageSize)

  const handlePageChange = (newPage) => {
    setPage(newPage)
    window.scrollTo({ top: 0, behavior: 'smooth' })
  }

  return (
    <div className="app-shell min-h-screen">
      <div className="mx-auto max-w-screen-2xl px-4 py-6 sm:px-6 lg:px-8">
        <div className="card card-hover mb-8 p-8">
          <p className="kicker">Invoice history</p>
          <h1 className="mt-3 text-3xl font-semibold text-[var(--dark-orange)] sm:text-4xl">Purchase invoice archive</h1>
          <p className="mt-4 max-w-2xl text-sm leading-7 text-slate-600">
            Search, filter, and browse recently created invoices with status and date controls. Use pagination to review your full history.
          </p>
        </div>

        <section className="card card-hover grid gap-4 p-6 sm:grid-cols-[1.5fr_auto] sm:items-end">
          <div>
            <label className="block text-sm font-semibold uppercase tracking-[0.25em] text-[var(--secondary)]">
              Search invoices
            </label>
            <input
              type="search"
              value={search}
              onChange={(event) => setSearch(event.target.value)}
              placeholder="Search by invoice number or supplier"
              className="soft-input mt-3 w-full"
            />
          </div>
          <div className="grid gap-4 sm:grid-cols-2">
            <div>
              <label className="block text-sm font-semibold uppercase tracking-[0.25em] text-[var(--secondary)]">Status</label>
              <select
                value={statusFilter}
                onChange={(event) => {
                  setStatusFilter(event.target.value)
                  setPage(1)
                }}
                className="soft-input mt-3 w-full"
              >
                {statusOptions.map((status) => (
                  <option key={status} value={status}>
                    {status}
                  </option>
                ))}
              </select>
            </div>
            <div>
              <label className="block text-sm font-semibold uppercase tracking-[0.25em] text-[var(--secondary)]">Date</label>
              <select
                value={dateFilter}
                onChange={(event) => {
                  setDateFilter(event.target.value)
                  setPage(1)
                }}
                className="soft-input mt-3 w-full"
              >
                {dateOptions.map((option) => (
                  <option key={option} value={option}>
                    {option}
                  </option>
                ))}
              </select>
            </div>
          </div>
        </section>

        <section className="mt-6 overflow-hidden rounded-[2rem] border border-[var(--border)] bg-white shadow-[var(--shadow-soft)]">
          <div className="flex flex-col gap-4 border-b border-slate-200 bg-[#FFF6E8] px-6 py-5 sm:flex-row sm:items-center sm:justify-between">
            <div>
              <p className="kicker">Invoice table</p>
              <p className="mt-1 text-sm text-slate-600">Showing {filteredInvoices.length} invoices across {pageCount} pages.</p>
            </div>
            <div className="flex items-center gap-3 text-sm text-slate-600">
              <span className="pill">Status</span>
              <span className="pill">Date</span>
            </div>
          </div>

          <div className="overflow-x-auto">
            <table className="min-w-full divide-y divide-slate-200 text-left">
              <thead className="bg-white">
                <tr>
                  {['Invoice', 'Supplier', 'Date', 'Status', 'Total'].map((heading) => (
                    <th key={heading} className="px-6 py-4 text-xs font-semibold uppercase tracking-[0.25em] text-slate-500">
                      {heading}
                    </th>
                  ))}
                </tr>
              </thead>
              <tbody className="divide-y divide-slate-200 bg-white">
                {paginatedInvoices.length === 0 ? (
                  <tr>
                    <td colSpan={5} className="px-6 py-10 text-center text-sm text-slate-500">
                      No invoices match your current search and filter settings.
                    </td>
                  </tr>
                ) : (
                  paginatedInvoices.map((invoice, index) => (
                    <tr key={invoice.id} className={`transition hover:bg-orange-50 ${index % 2 === 0 ? 'bg-slate-50/70' : 'bg-white'}`}>
                      <td className="px-6 py-4 text-sm font-semibold text-[var(--text)]">{invoice.id}</td>
                      <td className="px-6 py-4 text-sm text-slate-600">{invoice.supplier}</td>
                      <td className="px-6 py-4 text-sm text-slate-600">{invoice.date}</td>
                      <td className="px-6 py-4">
                        <span className={`inline-flex rounded-full px-3 py-1 text-xs font-semibold ${formatStatusBadge(invoice.status)}`}>
                          {invoice.status}
                        </span>
                      </td>
                      <td className="px-6 py-4 text-sm font-semibold text-[var(--dark-orange)]">{invoice.total}</td>
                    </tr>
                  ))
                )}
              </tbody>
            </table>
          </div>

          <div className="flex flex-col gap-4 border-t border-slate-200 bg-[var(--card)] px-6 py-5 sm:flex-row sm:items-center sm:justify-between">
            <p className="text-sm text-slate-600">
              Page {page} of {pageCount}
            </p>
            <div className="flex flex-wrap items-center gap-2">
              <button
                type="button"
                onClick={() => handlePageChange(Math.max(1, page - 1))}
                disabled={page === 1}
                className="button-secondary px-4 py-2 disabled:cursor-not-allowed disabled:opacity-50"
              >
                Previous
              </button>
              {Array.from({ length: pageCount }, (_, idx) => idx + 1).map((pageNumber) => (
                <button
                  key={pageNumber}
                  type="button"
                  onClick={() => handlePageChange(pageNumber)}
                  className={`inline-flex h-10 min-w-[2.5rem] items-center justify-center rounded-full px-4 text-sm font-semibold transition ${
                    pageNumber === page
                      ? 'bg-[var(--primary)] text-white shadow-sm'
                      : 'bg-white text-[var(--text)] hover:bg-slate-100'
                  }`}
                >
                  {pageNumber}
                </button>
              ))}
              <button
                type="button"
                onClick={() => handlePageChange(Math.min(pageCount, page + 1))}
                disabled={page === pageCount}
                className="button-secondary px-4 py-2 disabled:cursor-not-allowed disabled:opacity-50"
              >
                Next
              </button>
            </div>
          </div>
        </section>
      </div>
    </div>
  )
}

export default InvoiceHistory
