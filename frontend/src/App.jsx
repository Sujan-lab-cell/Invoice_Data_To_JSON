import { useState } from 'react'
import Loading from './components/Loading.jsx'

const menuItems = ['Dashboard', 'Upload Invoice', 'Purchase Preview', 'History', 'Settings']
const statusBadges = [
  { label: 'Found', classes: 'bg-emerald-100 text-emerald-700' },
  { label: 'Not Found', classes: 'bg-orange-100 text-orange-700' },
  { label: 'Matched', classes: 'bg-sky-100 text-sky-700' },
]

const overviewCards = [
  {
    title: 'Invoices Processed',
    value: '8,742',
    subtitle: 'Processed in the last 30 days',
    classes: 'from-[var(--primary)] via-[var(--secondary)] to-[#FED7AA]',
  },
  {
    title: 'Suppliers',
    value: '124',
    subtitle: 'Active supplier profiles',
    classes: 'from-[#FB923C] via-[#F97316] to-[#FED7AA]',
  },
  {
    title: 'Medicines',
    value: '64',
    subtitle: 'Tracked product categories',
    classes: 'from-[#F97316] via-[#FB923C] to-[#FED7AA]',
  },
]

const recentInvoices = [
  { supplier: 'Sunrise Pharma', invoice: 'INV-2026-0071', date: '2026-06-29', total: '$12,480', gst: '18%', venue: 'Downtown Clinic' },
  { supplier: 'MediCare Labs', invoice: 'INV-2026-0084', date: '2026-06-27', total: '$8,190', gst: '12%', venue: 'Eastside Health' },
  { supplier: 'Healthline Co.', invoice: 'INV-2026-0099', date: '2026-06-24', total: '$5,740', gst: '5%', venue: 'North Bay Pharmacy' },
]

const inventoryRows = [
  { medicine: 'Amoxicillin', quantity: 120, price: '$18.50', batch: 'B1023', expiry: '2027-03-14', status: 'In stock' },
  { medicine: 'Ceftriaxone', quantity: 74, price: '$32.00', batch: 'C4501', expiry: '2026-11-09', status: 'Low stock' },
  { medicine: 'Paracetamol', quantity: 220, price: '$6.25', batch: 'P7890', expiry: '2028-01-22', status: 'In stock' },
  { medicine: 'Metformin', quantity: 56, price: '$24.90', batch: 'M1124', expiry: '2026-09-18', status: 'Reorder' },
]

function App() {
  const [sidebarOpen, setSidebarOpen] = useState(false)

  return (
    <div className="app-shell">
      <div className="lg:pl-[260px]">
        <header className="border-b border-[var(--border)]/70 bg-[var(--card)]/90 px-4 py-4 shadow-[0_8px_30px_rgba(249,115,22,0.05)] backdrop-blur sm:px-6 lg:px-8">
          <div className="mx-auto flex max-w-screen-2xl items-center justify-between gap-4">
            <div className="flex items-center gap-3">
              <button
                type="button"
                onClick={() => setSidebarOpen(true)}
                className="inline-flex h-11 w-11 items-center justify-center rounded-3xl border border-[var(--border)] bg-white/90 text-[var(--text)] shadow-[0_8px_24px_rgba(15,23,42,0.04)] transition duration-200 hover:-translate-y-0.5 hover:bg-orange-50 lg:hidden"
              >
                <span className="text-xl">☰</span>
              </button>
              <div className="flex h-12 w-12 items-center justify-center rounded-2xl bg-[var(--primary)] text-white shadow-[0_12px_32px_rgba(249,115,22,0.2)]">
                <span className="text-xl font-bold">AI</span>
              </div>
              <div className="hidden sm:block">
                <p className="kicker">Invoice parser</p>
                <h1 className="text-lg font-semibold tracking-tight text-[var(--dark-orange)] sm:text-xl">
                  AI Invoice Parser
                </h1>
              </div>
            </div>

            <div className="flex items-center gap-4">
              <button className="button-secondary h-11 w-11 rounded-2xl p-0">
                <span className="text-lg">🔔</span>
              </button>
              <div className="flex h-11 w-11 items-center justify-center rounded-2xl bg-[var(--secondary)] text-white shadow-[0_10px_24px_rgba(249,115,22,0.16)]">
                <span className="text-sm font-semibold">JD</span>
              </div>
            </div>
          </div>
        </header>

        <div className="relative">
          <div
            className={`fixed inset-y-0 left-0 z-50 w-72 transform border-r border-[var(--border)]/80 bg-[var(--card)]/95 p-6 shadow-[0_24px_70px_rgba(15,23,42,0.16)] backdrop-blur transition duration-300 lg:static lg:translate-x-0 lg:shadow-none ${
              sidebarOpen ? 'translate-x-0' : '-translate-x-full'
            }`}
          >
            <div className="mb-8 flex items-center justify-between lg:hidden">
              <p className="kicker">Menu</p>
              <button
                type="button"
                onClick={() => setSidebarOpen(false)}
                className="button-secondary rounded-full px-3 py-2"
              >
                Close
              </button>
            </div>
            <div className="mb-8 hidden lg:block">
              <p className="kicker">Menu</p>
            </div>
            <nav className="space-y-2 text-sm font-medium text-[var(--text)]">
              {menuItems.map((item) => {
                const isActive = item === 'Dashboard'
                return (
                  <a
                    key={item}
                    href="#"
                    className={`group block rounded-[1.2rem] border px-5 py-3.5 transition-all duration-200 ${
                      isActive
                        ? 'border-[var(--primary)] bg-[var(--primary)]/10 text-[var(--dark-orange)] shadow-[0_10px_24px_rgba(249,115,22,0.12)]'
                        : 'border-transparent bg-white/80 text-[var(--text)] hover:-translate-y-0.5 hover:border-[var(--border)] hover:bg-orange-50 hover:shadow-[0_10px_24px_rgba(249,115,22,0.06)]'
                    }`}
                  >
                    {item}
                  </a>
                )
              })}
            </nav>
          </div>

          <div
            className={`fixed inset-0 z-40 bg-slate-950/40 transition-opacity lg:hidden ${
              sidebarOpen ? 'pointer-events-auto opacity-100' : 'pointer-events-none opacity-0'
            }`}
            onClick={() => setSidebarOpen(false)}
          />

          <main className="px-4 py-6 sm:px-6 lg:px-8">
            <div className="mx-auto grid max-w-screen-2xl gap-8">
              <section className="card card-hover overflow-hidden p-8">
                <div className="absolute inset-0 bg-[radial-gradient(circle_at_top_left,rgba(249,115,22,0.08),transparent_40%)]" />
                <div className="relative">
                  <p className="kicker">Welcome back</p>
                  <h2 className="mt-3 text-3xl font-semibold text-[var(--dark-orange)] sm:text-4xl">AI Invoice Parser</h2>
                  <p className="mt-4 max-w-2xl text-sm leading-7 text-slate-600">
                    Get a quick overview of your recent invoice activity and supplier data. These cards summarize the latest invoice processing performance for your team.
                  </p>
                </div>
              </section>

              <section className="card card-hover grid gap-4 p-6 sm:grid-cols-[1fr_auto_auto_auto] sm:items-center">
                <div>
                  <p className="kicker">Status summary</p>
                  <h3 className="section-title mt-3">Invoice status</h3>
                </div>
                {statusBadges.map((badge) => (
                  <span key={badge.label} className={`inline-flex items-center rounded-full px-4 py-2 text-sm font-semibold ${badge.classes}`}>
                    {badge.label}
                  </span>
                ))}
              </section>

              <section className="grid gap-6 sm:grid-cols-3">
                {overviewCards.map((card) => (
                  <article key={card.title} className={`card-hover rounded-[2rem] bg-gradient-to-br ${card.classes} p-6 text-white shadow-[0_22px_60px_rgba(249,115,22,0.14)]`}>
                    <p className="text-sm font-semibold uppercase tracking-[0.25em] opacity-90">{card.title}</p>
                    <p className="mt-6 text-4xl font-semibold">{card.value}</p>
                    <p className="mt-3 text-sm opacity-90">{card.subtitle}</p>
                  </article>
                ))}
              </section>

              <section className="grid gap-6">
                {recentInvoices.map((item) => (
                  <article key={item.invoice} className="card card-hover overflow-hidden">
                    <div className="h-2 rounded-t-[1.5rem] bg-[var(--primary)]" />
                    <div className="p-6">
                      <p className="text-xs font-semibold uppercase tracking-[0.35em] text-[var(--secondary)]">Supplier Name</p>
                      <h3 className="mt-3 text-xl font-semibold text-[var(--text)]">{item.supplier}</h3>
                      <div className="mt-6 grid gap-4 sm:grid-cols-2">
                        <div>
                          <p className="text-xs uppercase tracking-[0.3em] text-slate-400">Invoice Number</p>
                          <p className="mt-1 font-medium text-[var(--text)]">{item.invoice}</p>
                        </div>
                        <div>
                          <p className="text-xs uppercase tracking-[0.3em] text-slate-400">Invoice Date</p>
                          <p className="mt-1 font-medium text-[var(--text)]">{item.date}</p>
                        </div>
                        <div>
                          <p className="text-xs uppercase tracking-[0.3em] text-slate-400">Total Amount</p>
                          <p className="mt-1 font-medium text-[var(--text)]">{item.total}</p>
                        </div>
                        <div>
                          <p className="text-xs uppercase tracking-[0.3em] text-slate-400">GST</p>
                          <p className="mt-1 font-medium text-[var(--text)]">{item.gst}</p>
                        </div>
                      </div>
                      <div className="mt-6 rounded-2xl bg-[#FFF5E0] px-4 py-3 text-sm font-medium text-[var(--dark-orange)]">
                        Venue: {item.venue}
                      </div>
                    </div>
                  </article>
                ))}
              </section>

              <section className="card card-hover p-6">
                <div className="mb-6 flex flex-col gap-2 sm:flex-row sm:items-center sm:justify-between">
                  <div>
                    <p className="kicker">Medicine inventory</p>
                    <h3 className="section-title">Medicine details</h3>
                  </div>
                </div>
                <div className="overflow-x-auto">
                  <table className="min-w-full divide-y divide-slate-200 rounded-[1.75rem] border border-[var(--border)] bg-white/80 text-left shadow-sm">
                    <thead className="bg-[#FFF6E8]">
                      <tr>
                        {['Medicine', 'Quantity', 'Unit Price', 'Batch', 'Expiry', 'Status'].map((heading) => (
                          <th key={heading} className="px-5 py-4 text-xs font-semibold uppercase tracking-[0.25em] text-slate-500">
                            {heading}
                          </th>
                        ))}
                      </tr>
                    </thead>
                    <tbody className="divide-y divide-slate-200">
                      {inventoryRows.map((row, index) => (
                        <tr key={row.medicine} className={`transition hover:bg-orange-50 ${index % 2 === 0 ? 'bg-slate-50/70' : 'bg-white'}`}>
                          <td className="px-5 py-4 text-sm font-medium text-[var(--text)]">{row.medicine}</td>
                          <td className="px-5 py-4 text-sm text-slate-600">{row.quantity}</td>
                          <td className="px-5 py-4 text-sm text-slate-600">{row.price}</td>
                          <td className="px-5 py-4 text-sm text-slate-600">{row.batch}</td>
                          <td className="px-5 py-4 text-sm text-slate-600">{row.expiry}</td>
                          <td className="px-5 py-4 text-sm font-semibold text-[var(--dark-orange)]">{row.status}</td>
                        </tr>
                      ))}
                    </tbody>
                  </table>
                </div>
              </section>

              <section className="card card-hover bg-[#FFF4E4] p-6">
                <div className="flex flex-col gap-4 sm:flex-row sm:items-center sm:justify-between">
                  <div>
                    <p className="kicker">Missing medicine</p>
                    <h3 className="mt-2 text-2xl font-semibold text-[var(--dark-orange)]">Medicine not found in master data</h3>
                    <p className="mt-2 max-w-2xl text-sm text-slate-600">
                      This medicine needs to be added to your master list before processing can continue.
                    </p>
                  </div>
                  <button className="button-primary mt-4 sm:mt-0">
                    Add to Master
                  </button>
                </div>
                <div className="mt-4 rounded-3xl bg-[#FFF8EE] px-5 py-4 text-sm text-[var(--text)] shadow-sm">
                  <p className="font-semibold">Medicine Name</p>
                  <p className="mt-1 text-[var(--dark-orange)]">Ibuprofen 400mg</p>
                  <p className="mt-2 text-sm text-slate-500">Reason: Master data entry missing for this medicine.</p>
                </div>
              </section>

              <section className="card card-hover bg-[#FFF5E4] p-6">
                <div className="flex flex-col gap-4 sm:flex-row sm:items-center sm:justify-between">
                  <div className="flex items-center gap-3">
                    <div className="flex h-11 w-11 items-center justify-center rounded-2xl bg-orange-100 text-[var(--dark-orange)]">
                      <span className="text-lg">⚠️</span>
                    </div>
                    <div>
                      <p className="kicker">Supplier missing</p>
                      <h3 className="mt-2 text-2xl font-semibold text-[var(--dark-orange)]">Supplier not found in records</h3>
                    </div>
                  </div>
                  <button className="button-primary mt-2 sm:mt-0">
                    Add Supplier
                  </button>
                </div>
                <div className="mt-4 rounded-3xl bg-[#FFF3DC] px-5 py-4 text-sm text-[var(--text)] shadow-sm">
                  <p className="font-semibold">Supplier Name</p>
                  <p className="mt-1 text-[var(--dark-orange)]">Golden Health Supplies</p>
                  <p className="mt-3 text-sm text-slate-500">Address: 312 Wellness Blvd, Riverside</p>
                </div>
              </section>

              <section className="card card-hover border-dashed border-[var(--primary)] bg-[#FFF6E8] p-8">
                <div className="flex flex-col items-center justify-center gap-6 text-center sm:flex-row sm:items-start sm:text-left">
                  <div className="flex-1">
                    <p className="kicker">Upload invoice</p>
                    <h3 className="mt-3 text-2xl font-semibold text-[var(--dark-orange)]">Drag & drop your files here</h3>
                    <p className="mt-3 text-sm leading-6 text-slate-600">Supported formats: PDF, Image, Excel, CSV. Drag files into the upload area or browse from your device.</p>
                  </div>
                  <button className="button-primary">
                    Browse files
                  </button>
                </div>
                <div className="mt-8 rounded-[1.75rem] border-2 border-dashed border-[var(--primary)] bg-[#FFF4E4] px-6 py-16 text-center text-[var(--text)] shadow-inner shadow-orange-100/50">
                  <p className="text-xl font-semibold">Drop files here</p>
                  <p className="mt-2 text-sm text-slate-500">PDF · Image · Excel · CSV</p>
                </div>
              </section>

              <Loading />
            </div>
          </main>
        </div>
      </div>
    </div>
  )
}

export default App
