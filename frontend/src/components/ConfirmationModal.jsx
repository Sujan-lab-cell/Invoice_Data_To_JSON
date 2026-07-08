function ConfirmationModal({ isOpen, onClose, onConfirm }) {
  if (!isOpen) return null

  return (
    <div className="fixed inset-0 z-50 flex items-center justify-center bg-slate-950/40 px-4 py-6">
      <div className="w-full max-w-md rounded-[2rem] border border-[var(--border)] bg-[var(--card)] p-6 shadow-[0_24px_70px_rgba(15,23,42,0.16)]">
        <div className="mb-6 flex items-start gap-4">
          <div className="flex h-12 w-12 items-center justify-center rounded-3xl bg-orange-100 text-[var(--dark-orange)] shadow-sm">
            <span className="text-xl">⚠️</span>
          </div>
          <div>
            <p className="kicker">Confirmation needed</p>
            <h2 className="mt-3 text-2xl font-semibold text-[var(--dark-orange)]">
              Create Purchase Invoice?
            </h2>
          </div>
        </div>

        <p className="mb-8 text-sm leading-6 text-slate-600">
          Confirm this purchase invoice to finalize the preview and proceed with the invoice creation workflow.
        </p>

        <div className="flex flex-col gap-3 sm:flex-row sm:justify-end">
          <button type="button" onClick={onClose} className="button-secondary w-full sm:w-auto">
            Cancel
          </button>
          <button type="button" onClick={onConfirm} className="button-primary w-full sm:w-auto">
            Create
          </button>
        </div>
      </div>
    </div>
  )
}

export default ConfirmationModal
