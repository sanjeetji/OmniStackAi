import { Skeleton } from "@/components/ui/skeleton";

/** Studio loading state: the same two-column grid as the real workspace, so the layout does not
 * jump when the page streams in. Renders inside the Studio layout's AppShell. */
export default function StudioLoading() {
  return (
    <div className="studio-grid" role="status" aria-label="Loading the Studio" aria-busy="true">
      <aside className="grid content-start gap-3 border-r border-border/60 bg-card p-4">
        <div className="flex items-center gap-3">
          <div className="grid flex-1 gap-1.5">
            <Skeleton className="h-4 w-1/2" />
            <Skeleton className="h-3 w-2/3" />
          </div>
          <Skeleton className="h-5 w-14 rounded-full" />
        </div>
        <Skeleton className="mt-6 h-10 w-3/5 self-end justify-self-end rounded-2xl" />
        <Skeleton className="h-16 w-4/5 rounded-2xl" />
        <Skeleton className="mt-auto h-12 w-full rounded-xl" />
      </aside>
      <section className="grid content-start gap-4 p-6">
        <Skeleton className="h-7 w-1/3" />
        <Skeleton className="h-4 w-2/3" />
        <div className="flex gap-2">
          <Skeleton className="h-5 w-16 rounded-full" />
          <Skeleton className="h-5 w-20 rounded-full" />
          <Skeleton className="h-5 w-14 rounded-full" />
        </div>
        <Skeleton className="mt-2 h-8 w-80 max-w-full" />
        <Skeleton className="h-72 w-full rounded-xl" />
      </section>
    </div>
  );
}
