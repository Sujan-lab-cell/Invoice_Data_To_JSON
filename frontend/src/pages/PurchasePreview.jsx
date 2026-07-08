import { useState } from 'react'
import ConfirmationModal from '../components/ConfirmationModal.jsx'
import SuccessScreen from '../components/SuccessScreen.jsx'

function PurchasePreview() {
  const [showConfirm, setShowConfirm] = useState(false)
  const [showSuccess, setShowSuccess] = useState(false)

  const invoiceDetails = {
    invoiceNumber: 'INV-2026-0112',
    date: '2026-06-30',
    supplier: 'Golden Health Supplies',
    address: '312 Wellness Blvd, Riverside',
    dueDate: '2026-07-07',
    reference: 'PO-0897',
  }

  const medicines = [
    { name: 'Amoxicillin', quantity: 80, unitPrice: '$18.50', batch: 'B1023', expiry: '2027-03-14' },
    { name: 'Paracetamol', quantity: 120, unitPrice: '$6.25', batch: 'P7890', expiry: '2028-01-22' },
    { name: 'Ceftriaxone', quantity: 45, unitPrice: '$32.00', batch: 'C4501', expiry: '2026-11-09' },
  ]

  const totals = {
    grandTotal: '$19,430.00',
    gst: '$1,749.80',
    totalQuantity: 245,
  }

  if (showSuccess) {
    return (
      <SuccessScreen
        onNewInvoice={() => setShowSuccess(false)}
        onViewHistory={() => {
          // TODO: wire navigation to history page
          console.log('View History clicked')
        }}
      />
    )
  }

  return (
    <div className="app-shell min-h-screen">
      <div className="mx-auto max-w-screen-2xl px-4 py-6 sm:px-6 lg:px-8">
        <div className="card card-hover mb-8 p-8">
          <p className="kicker">Purchase preview</p>
          <h1 className="mt-3 text-3xl font-semibold text-[var(--dark-orange)] sm:text-4xl">
            Invoice purchase review
          </h1>
          <p className="mt-4 max-w-2xl text-sm leading-7 text-slate-600">
            Review the invoice details, medicine order summary, and final totals before confirming the purchase.
          </p>
          <div className="mt-6 flex flex-col gap-3 sm:flex-row sm:items-center sm:justify-between">
            <div>
              <p className="text-sm font-medium text-slate-600">Ready to finalize?</p>
              <p className="text-xs text-slate-500">Confirm the purchase invoice when everything looks right.</p>
            </div>
            <button type="button" onClick={() => setShowConfirm(true)} className="button-primary">
              Create Purchase Invoice
            </button>
          </div>
        </div>

        <div className="grid gap-6 xl:grid-cols-[1.2fr_0.8fr]">
          <section className="card card-hover p-8">
            <div className="mb-6 flex flex-col gap-4 sm:flex-row sm:items-center sm:justify-between">
              <div>
                <p className="kicker">Invoice details</p>
                <h2 className="mt-2 text-2xl font-semibold text-[var(--dark-orange)]">Invoice #{invoiceDetails.invoiceNumber}</h2>
              </div>
              <div className="rounded-3xl bg-[#FFF4E4] px-4 py-3 text-sm font-semibold text-[var(--dark-orange)] shadow-sm">
                {invoiceDetails.reference}
              </div>
            </div>
            <dl className="grid gap-6 sm:grid-cols-2">
              <div>
                <dt className="text-xs uppercase tracking-[0.3em] text-slate-400">Supplier</dt>
                <dd className="mt-2 text-sm font-semibold text-[var(--text)]">{invoiceDetails.supplier}</dd>
              </div>
              <div>
                <dt className="text-xs uppercase tracking-[0.3em] text-slate-400">Invoice Date</dt>
                <dd className="mt-2 text-sm font-semibold text-[var(--text)]">{invoiceDetails.date}</dd>
              </div>
              <div className="sm:col-span-2">
                <dt className="text-xs uppercase tracking-[0.3em] text-slate-400">Address</dt>
                <dd className="mt-2 text-sm font-semibold text-[var(--text)]">{invoiceDetails.address}</dd>
              </div>
              <div>
                <dt className="text-xs uppercase tracking-[0.3em] text-slate-400">Due Date</dt>
                <dd className="mt-2 text-sm font-semibold text-[var(--text)]">{invoiceDetails.dueDate}</dd>
              </div>
              <div>
                <dt className="text-xs uppercase tracking-[0.3em] text-slate-400">Status</dt>
                <dd className="mt-2 rounded-3xl bg-[#EFF6FF] px-4 py-2 text-sm font-semibold text-sky-700">Ready to review</dd>
              </div>
            </dl>
          </section>

          <section className="card card-hover p-8">
            <div className="mb-6 flex items-center justify-between gap-4">
              <div>
                <p className="kicker">Medicine summary</p>
                <h2 className="mt-2 text-2xl font-semibold text-[var(--dark-orange)]">Order items</h2>
              </div>
              <span className="rounded-full bg-orange-100 px-3 py-1 text-sm font-semibold text-orange-700">3 items</span>
            </div>
            <div className="overflow-hidden rounded-[1.75rem] border border-[var(--border)] bg-white">
              <table className="min-w-full divide-y divide-slate-200 text-left">
                <thead className="bg-[#FFF6E8]">
                  <tr>
                    {['Medicine', 'Qty', 'Unit Price', 'Batch', 'Expiry'].map((col) => (
                      <th key={col} className="px-4 py-4 text-xs font-semibold uppercase tracking-[0.2em] text-slate-500">
                        {col}
                      </th>
                    ))}
                  </tr>
                </thead>
                <tbody className="divide-y divide-slate-200">
                  {medicines.map((row, index) => (
                    <tr key={row.name} className={index % 2 === 0 ? 'bg-slate-50' : 'bg-white'}>
                      <td className="px-4 py-4 text-sm font-medium text-[var(--text)]">{row.name}</td>
                      <td className="px-4 py-4 text-sm text-slate-600">{row.quantity}</td>
                      <td className="px-4 py-4 text-sm text-slate-600">{row.unitPrice}</td>
                      <td className="px-4 py-4 text-sm text-slate-600">{row.batch}</td>
                      <td className="px-4 py-4 text-sm text-slate-600">{row.expiry}</td>
                    </tr>
                  ))}
                </tbody>
              </table>
            </div>
          </section>
        </div>

        <section className="mt-6 grid gap-6 lg:grid-cols-3">
          <article className="card card-hover p-6">
            <p className="kicker">Grand Total</p>
            <p className="mt-4 text-3xl font-semibold text-[var(--dark-orange)]">{totals.grandTotal}</p>
          </article>
          <article className="card card-hover p-6">
            <p className="kicker">GST</p>
            <p className="mt-4 text-3xl font-semibold text-[var(--dark-orange)]">{totals.gst}</p>
          </article>
          <article className="card card-hover p-6">
            <p className="kicker">Total Quantity</p>
            <p className="mt-4 text-3xl font-semibold text-[var(--dark-orange)]">{totals.totalQuantity}</p>
          </article>
        </section>
      </div>

      <ConfirmationModal
        isOpen={showConfirm}
        onClose={() => setShowConfirm(false)}
        onConfirm={() => {
          setShowConfirm(false)
          setShowSuccess(true)
        }}
      />
    </div>
  )
}

export default PurchasePreview
