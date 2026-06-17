export default function HomePage() {
  return (
    <main className="min-h-screen bg-[#0d1016] px-6 py-10 text-[#fffaf0]">
      <div className="mx-auto flex min-h-[calc(100vh-5rem)] max-w-3xl flex-col justify-between">
        <header className="flex items-center justify-between text-[11px] uppercase tracking-[0.18em] text-[#a9b4af]">
          <span>ClipsFlow</span>
          <span>Telegram desk</span>
        </header>

        <section className="py-16">
          <h1 className="max-w-xl text-5xl font-semibold leading-[0.95] md:text-7xl">
            Finished clips only count when delivery lands.
          </h1>
          <p className="mt-6 max-w-lg text-base leading-7 text-[#b9c3bd]">
            Paste the link in the Telegram mini app. The bot keeps the handoff honest: trial exports are watermarked,
            long sources are checked by duration, and delivery status stays in Telegram until the file is sent.
          </p>
          <a
            href="/miniapp"
            className="mt-8 inline-flex rounded-md bg-[#d6ef7d] px-5 py-4 text-sm font-semibold text-[#11160f] transition hover:bg-[#e4ff8a]"
          >
            Open clip desk
          </a>
        </section>

        <footer className="grid gap-3 border-t border-[#222b2c] pt-5 text-[12px] text-[#8d9895] sm:grid-cols-3">
          <span>Watermarked trial runway</span>
          <span>Clean Pro opens after billing setup</span>
          <span>Telegram-confirmed delivery</span>
        </footer>
      </div>
    </main>
  );
}
