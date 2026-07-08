function Loading() {
  const steps = ['Uploading', 'Reading Invoice', 'Extracting Data', 'Validating']

  return (
    <section className="card card-hover p-8">
      <div className="flex flex-col gap-6">
        <div>
          <p className="kicker">Processing status</p>
          <h2 className="mt-3 text-3xl font-semibold text-[var(--dark-orange)] sm:text-4xl">
            Invoice processing in progress
          </h2>
        </div>

        <div className="space-y-6 rounded-[2rem] bg-[#FFF6E8] p-6 shadow-inner">
          <div className="overflow-hidden rounded-full bg-orange-100">
            <div className="h-3 w-[68%] rounded-full bg-gradient-to-r from-[var(--primary)] via-[var(--secondary)] to-[#FED7AA] transition-all duration-500 ease-out" />
          </div>

          <div className="grid gap-4 sm:grid-cols-4">
            {steps.map((step, index) => {
              const active = index <= 2
              return (
                <div key={step} className="flex flex-col items-center gap-3 rounded-[1.25rem] bg-white/80 p-4 text-center shadow-sm">
                  <span className={`flex h-12 w-12 items-center justify-center rounded-full text-lg font-semibold ${
                    active
                      ? 'bg-[var(--primary)] text-white shadow-[0_10px_30px_rgba(249,115,22,0.25)]'
                      : 'bg-orange-100 text-[var(--text)]'
                  }`}>
                    {index + 1}
                  </span>
                  <p className="text-sm font-semibold text-[var(--text)]">{step}</p>
                </div>
              )
            })}
          </div>

          <div className="rounded-[1.25rem] border border-[var(--border)] bg-white p-4 text-sm text-slate-500 shadow-sm">
            <p className="font-semibold text-[var(--text)]">Current step:</p>
            <p className="mt-2">Extracting Data from the invoice and preparing validation checks.</p>
          </div>
        </div>
      </div>
    </section>
  )
}

export default Loading
