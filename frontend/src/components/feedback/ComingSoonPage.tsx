interface ComingSoonPageProps {
  title: string
}

/** Placeholder for routes whose feature lands in a later milestone. */
export function ComingSoonPage({ title }: ComingSoonPageProps) {
  return (
    <div className="flex flex-1 flex-col items-center justify-center gap-2 py-16 text-center">
      <h1 className="text-lg font-semibold">{title}</h1>
      <p className="text-muted-foreground text-sm">This screen is coming in a later milestone.</p>
    </div>
  )
}
