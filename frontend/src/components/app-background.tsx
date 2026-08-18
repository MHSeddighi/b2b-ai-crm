export function AppBackground() {
  return (
    <div className="pointer-events-none absolute inset-0 -z-10 overflow-hidden" aria-hidden="true">
      {/* Soft aurora blobs that slowly drift like flowing water */}
      <div className="animate-drift absolute -left-32 -top-32 h-[34rem] w-[34rem] rounded-full bg-primary/25 blur-3xl" />
      <div
        className="animate-drift absolute -right-24 top-1/4 h-[30rem] w-[30rem] rounded-full bg-violet-500/20 blur-3xl"
        style={{ animationDelay: "-8s", animationDuration: "34s" }}
      />
      <div
        className="animate-drift absolute -bottom-40 left-1/4 h-[32rem] w-[32rem] rounded-full bg-sky-400/20 blur-3xl"
        style={{ animationDelay: "-16s", animationDuration: "30s" }}
      />
      <div
        className="animate-drift absolute bottom-1/4 right-1/4 h-72 w-72 rounded-full bg-emerald-400/15 blur-3xl"
        style={{ animationDelay: "-22s", animationDuration: "40s" }}
      />

      {/* Water ripple rings that fade out toward the edges */}
      <div
        className="absolute -right-40 -top-40 h-[46rem] w-[46rem] rounded-full opacity-60"
        style={{
          background:
            "repeating-radial-gradient(circle at center, transparent 0px, transparent 52px, hsl(var(--primary) / 0.28) 52px, hsl(var(--primary) / 0.28) 53px)",
          maskImage:
            "radial-gradient(circle at center, rgba(0,0,0,0.85) 0%, rgba(0,0,0,0.35) 45%, transparent 72%)",
          WebkitMaskImage:
            "radial-gradient(circle at center, rgba(0,0,0,0.85) 0%, rgba(0,0,0,0.35) 45%, transparent 72%)",
        }}
      />
      <div
        className="absolute -bottom-48 -left-32 h-[38rem] w-[38rem] rounded-full opacity-50"
        style={{
          background:
            "repeating-radial-gradient(circle at center, transparent 0px, transparent 46px, hsl(var(--primary) / 0.22) 46px, hsl(var(--primary) / 0.22) 47px)",
          maskImage:
            "radial-gradient(circle at center, rgba(0,0,0,0.7) 0%, rgba(0,0,0,0.25) 45%, transparent 70%)",
          WebkitMaskImage:
            "radial-gradient(circle at center, rgba(0,0,0,0.7) 0%, rgba(0,0,0,0.25) 45%, transparent 70%)",
        }}
      />
    </div>
  );
}
