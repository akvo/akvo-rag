import DashboardLayout from "@/components/layout/dashboard-layout";
import { Bot, User, Loader2 } from "lucide-react";

export default function ChatLoading() {
  return (
    <DashboardLayout>
      <div className="flex h-[calc(100vh-4.5rem)] overflow-hidden rounded-2xl border bg-background shadow-xs">
        {/* Left Sidebar Skeleton */}
        <div className="w-72 sm:w-80 border-r bg-card p-3.5 flex flex-col gap-3">
          <div className="flex items-center justify-between">
            <div className="h-4 w-28 bg-muted animate-pulse rounded" />
            <div className="h-6 w-6 bg-muted animate-pulse rounded" />
          </div>
          <div className="h-10 w-full bg-muted/60 animate-pulse rounded-xl" />
          <div className="h-8 w-full bg-muted/40 animate-pulse rounded-lg mt-1" />
          <div className="space-y-2 mt-2">
            {[1, 2, 3, 4, 5].map((i) => (
              <div key={i} className="h-12 w-full bg-muted/30 animate-pulse rounded-xl" />
            ))}
          </div>
        </div>

        {/* Central Canvas Skeleton */}
        <div className="flex flex-1 flex-col h-full relative overflow-hidden bg-background">
          {/* Top Bar Skeleton */}
          <div className="flex items-center justify-between border-b px-6 py-3.5 bg-card/60">
            <div className="flex items-center gap-3">
              <div className="h-8 w-8 rounded-lg bg-primary/10 flex items-center justify-center">
                <Loader2 className="h-4 w-4 text-primary animate-spin" />
              </div>
              <div className="space-y-1.5">
                <div className="h-3.5 w-36 bg-muted animate-pulse rounded-md" />
                <div className="h-2.5 w-24 bg-muted/60 animate-pulse rounded-md" />
              </div>
            </div>
            <div className="h-6 w-32 bg-muted/50 rounded-full animate-pulse" />
          </div>

          {/* Messages Skeleton Area */}
          <div className="flex-1 overflow-y-auto px-4 sm:px-8 py-6 space-y-6 max-w-3xl">
            <div className="flex items-start gap-3.5">
              <div className="h-8 w-8 rounded-xl bg-primary/10 border border-primary/20 flex items-center justify-center shrink-0">
                <Bot className="h-4 w-4 text-primary animate-pulse" />
              </div>
              <div className="flex-1 rounded-2xl bg-card border px-5 py-4 space-y-2.5 shadow-xs">
                <div className="h-4 w-3/4 bg-muted/80 rounded-md animate-pulse" />
                <div className="h-4 w-full bg-muted/60 rounded-md animate-pulse" />
                <div className="h-4 w-5/6 bg-muted/50 rounded-md animate-pulse" />
              </div>
            </div>

            <div className="flex items-start justify-end gap-3.5 ml-auto max-w-xl">
              <div className="rounded-2xl bg-primary/20 px-5 py-3.5 space-y-2 w-64 shadow-xs">
                <div className="h-3.5 w-full bg-primary/30 rounded-md animate-pulse" />
                <div className="h-3.5 w-2/3 bg-primary/30 rounded-md animate-pulse" />
              </div>
              <div className="h-8 w-8 rounded-full bg-primary/20 border border-primary/30 flex items-center justify-center shrink-0">
                <User className="h-4 w-4 text-primary" />
              </div>
            </div>

            <div className="flex items-center justify-center gap-2 pt-4 text-xs text-muted-foreground">
              <Loader2 className="h-3.5 w-3.5 animate-spin text-primary" />
              <span>Loading conversation...</span>
            </div>
          </div>

          {/* Composer Placeholder */}
          <div className="border-t bg-card/80 p-4 flex gap-2">
            <div className="flex-1 h-11 rounded-xl border bg-muted/30 animate-pulse" />
            <div className="h-11 w-20 rounded-xl bg-primary/40 animate-pulse" />
          </div>
        </div>
      </div>
    </DashboardLayout>
  );
}
