export function ForbiddenPage() {
  return (
    <div className="flex min-h-svh flex-col items-center justify-center gap-2 px-4 text-center">
      <h1 className="text-2xl font-semibold">You don't have access to this page</h1>
      <p className="text-muted-foreground text-sm">Contact your admin if you think this is a mistake.</p>
    </div>
  )
}
