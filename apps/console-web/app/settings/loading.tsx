import { Skeleton } from "@/components/ui/skeleton";

/** Settings loading state: page header, the section nav and three section cards. Renders inside
 * the Settings layout's AppShell. */
export default function SettingsLoading() {
  return (
    <div className="grid gap-8" role="status" aria-label="Loading settings" aria-busy="true">
      <div className="grid gap-2">
        <Skeleton className="h-8 w-40" />
        <Skeleton className="h-4 w-2/3 max-w-md" />
      </div>
      <div className="grid gap-8 lg:grid-cols-[200px_minmax(0,1fr)]">
        <div className="flex gap-2 lg:flex-col">
          <Skeleton className="h-8 w-24" />
          <Skeleton className="h-8 w-28" />
          <Skeleton className="h-8 w-32" />
        </div>
        <div className="grid gap-8">
          {[0, 1, 2].map((index) => (
            <div key={index} className="grid gap-4 rounded-xl bg-card p-4 ring-1 ring-foreground/10">
              <Skeleton className="h-5 w-32" />
              <Skeleton className="h-4 w-3/4" />
              <div className="grid gap-3 sm:grid-cols-2">
                <Skeleton className="h-10 w-full" />
                <Skeleton className="h-10 w-full" />
              </div>
            </div>
          ))}
        </div>
      </div>
    </div>
  );
}
