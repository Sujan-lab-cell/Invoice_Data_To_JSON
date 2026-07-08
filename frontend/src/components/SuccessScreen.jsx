function SuccessScreen({ onNewInvoice, onViewHistory }) {
  return (
    <div className="min-h-screen bg-[var(--bg)] px-4 py-10 sm:px-6 lg:px-8">
      <div className="mx-auto max-w-xl rounded-[2rem] border border-[var(--border)] bg-[var(--card)] p-10 shadow-[0_24px_70px_rgba(15,23,42,0.08)]">
        <div className="flex h-24 w-24 items-center justify-center rounded-full bg-emerald-100 text-5xl text-emerald-700 shadow-inner shadow-emerald-200">
          ✓
        </div>
        <div className="mt-8 text-center">
          <p className="kicker">Success</p>
          <h1 className="mt-4 text-3xl font-semibold text-[var(--dark-orange)] sm:text-4xl">
            Purchase Invoice Created Successfully
          </h1>
          <p className="mt-4 text-sm leading-7 text-slate-600">
            Your purchase invoice has been generated and saved successfully. You can create another invoice or review past entries.
          </p>
        </div>

        <div className="mt-10 grid gap-4 sm:grid-cols-2">
          <button type="button" onClick={onNewInvoice} className="button-primary">
            New Invoice
          </button>
          <button type="button" onClick={onViewHistory} className="button-secondary">
            View History
          </button>
        </div>
      </div>
    </div>
  )
}

export default SuccessScreen
