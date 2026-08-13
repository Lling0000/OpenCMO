import { motion } from "framer-motion";
import type { ReactNode } from "react";

const SHIMMER = "animate-pulse bg-slate-100";

interface BaseProps {
  className?: string;
  delay?: number;
}

/** Single rounded rectangle. Use as a Lego block for any skeleton. */
export function SkeletonBlock({ className = "", delay = 0 }: BaseProps) {
  return (
    <div
      className={`rounded-md ${SHIMMER} ${className}`}
      style={{ animationDelay: `${delay}ms` }}
    />
  );
}

/** Text line: 1em high, configurable width. Mimics a real line of copy. */
export function SkeletonText({
  width = "100%",
  className = "",
  delay = 0,
}: BaseProps & { width?: string }) {
  return (
    <div
      className={`h-3.5 rounded ${SHIMMER} ${className}`}
      style={{ width, animationDelay: `${delay}ms` }}
    />
  );
}

/** Small chip (KPI badge / tag). */
export function SkeletonChip({ className = "", delay = 0 }: BaseProps) {
  return (
    <div
      className={`h-5 w-16 rounded-full ${SHIMMER} ${className}`}
      style={{ animationDelay: `${delay}ms` }}
    />
  );
}

/** Wrapper that mounts skeletons with a soft fade-in. Reusable shell. */
export function SkeletonFrame({
  children,
  className = "",
}: {
  children: ReactNode;
  className?: string;
}) {
  return (
    <motion.div
      initial={{ opacity: 0 }}
      animate={{ opacity: 1 }}
      transition={{ duration: 0.22, ease: [0.25, 0.46, 0.45, 0.94] as const }}
      className={className}
    >
      {children}
    </motion.div>
  );
}

/** A KPI card skeleton matching `KpiCard`'s real layout. */
export function KpiCardSkeleton({ delay = 0 }: { delay?: number }) {
  return (
    <div className="rounded-2xl border border-slate-200 bg-white p-5 shadow-sm">
      <div className="flex items-start justify-between">
        <div className="space-y-2.5 flex-1">
          <SkeletonText width="40%" delay={delay} />
          <SkeletonBlock className="h-7 w-24" delay={delay + 60} />
          <SkeletonText width="55%" delay={delay + 120} />
        </div>
        <div className={`h-9 w-9 rounded-lg ${SHIMMER}`} style={{ animationDelay: `${delay + 30}ms` }} />
      </div>
    </div>
  );
}

/** A horizontal KPI row: 4 cards by default, responsive. */
export function KpiRowSkeleton({ count = 4 }: { count?: number }) {
  return (
    <div className="grid gap-3 grid-cols-2 md:grid-cols-3 lg:grid-cols-4">
      {Array.from({ length: count }).map((_, i) => (
        <KpiCardSkeleton key={i} delay={i * 60} />
      ))}
    </div>
  );
}

/** A chart card skeleton — title + chart area. Matches `ChartCard` proportions. */
export function ChartCardSkeleton({ height = 280 }: { height?: number }) {
  return (
    <div className="rounded-2xl border border-slate-200 bg-white p-5 shadow-sm">
      <div className="mb-4 flex items-center justify-between">
        <div className="space-y-2 flex-1">
          <SkeletonText width="30%" />
          <SkeletonText width="50%" className="h-2.5" delay={80} />
        </div>
        <SkeletonChip delay={120} />
      </div>
      <div
        className={`rounded-xl ${SHIMMER}`}
        style={{ height, animationDelay: "160ms" }}
      />
    </div>
  );
}

/** A list-row skeleton (for tables, item lists). */
export function ListRowSkeleton({ rows = 5 }: { rows?: number }) {
  return (
    <div className="space-y-2">
      {Array.from({ length: rows }).map((_, i) => (
        <div
          key={i}
          className="flex items-center gap-4 rounded-xl border border-slate-100 bg-white px-4 py-3"
        >
          <div
            className={`h-9 w-9 rounded-lg ${SHIMMER}`}
            style={{ animationDelay: `${i * 80}ms` }}
          />
          <div className="flex-1 space-y-2">
            <SkeletonText width={`${60 + (i * 7) % 30}%`} delay={i * 80 + 40} />
            <SkeletonText width={`${30 + (i * 11) % 30}%`} className="h-2.5" delay={i * 80 + 100} />
          </div>
          <SkeletonChip delay={i * 80 + 60} />
        </div>
      ))}
    </div>
  );
}

/** Project header skeleton — matches `ProjectHeader` (avatar + name + tabs). */
export function ProjectHeaderSkeleton() {
  return (
    <div className="rounded-2xl border border-slate-200 bg-white p-5 shadow-sm">
      <div className="flex items-center gap-4">
        <div className={`h-12 w-12 rounded-xl ${SHIMMER}`} />
        <div className="flex-1 space-y-2">
          <SkeletonText width="38%" className="h-4" delay={60} />
          <SkeletonText width="22%" className="h-2.5" delay={120} />
        </div>
      </div>
    </div>
  );
}

/** Full-page skeleton for project sub-pages (SEO, GEO, SERP, Community).
 *  Header → KPI row → 2 chart cards.
 */
export function ProjectSubpageSkeleton() {
  return (
    <SkeletonFrame className="space-y-5">
      <ProjectHeaderSkeleton />
      <KpiRowSkeleton />
      <div className="grid gap-4 lg:grid-cols-2">
        <ChartCardSkeleton />
        <ChartCardSkeleton />
      </div>
    </SkeletonFrame>
  );
}

/** Dashboard skeleton — hero, KPI row, project grid. */
export function DashboardSkeleton() {
  return (
    <SkeletonFrame className="space-y-6">
      <div className="rounded-3xl border border-slate-200 bg-white p-7 shadow-sm">
        <div className="space-y-3">
          <SkeletonText width="22%" className="h-2.5" />
          <SkeletonText width="46%" className="h-7" delay={80} />
          <SkeletonText width="64%" className="h-3" delay={140} />
        </div>
      </div>
      <KpiRowSkeleton />
      <div className="grid gap-4 sm:grid-cols-2 lg:grid-cols-3">
        {Array.from({ length: 3 }).map((_, i) => (
          <ListItemCardSkeleton key={i} delay={i * 80} />
        ))}
      </div>
    </SkeletonFrame>
  );
}

function ListItemCardSkeleton({ delay = 0 }: { delay?: number }) {
  return (
    <div className="rounded-2xl border border-slate-200 bg-white p-5 shadow-sm space-y-3">
      <div className="flex items-center gap-3">
        <div
          className={`h-10 w-10 rounded-lg ${SHIMMER}`}
          style={{ animationDelay: `${delay}ms` }}
        />
        <div className="flex-1 space-y-2">
          <SkeletonText width="60%" delay={delay + 40} />
          <SkeletonText width="35%" className="h-2.5" delay={delay + 100} />
        </div>
      </div>
      <div className="grid grid-cols-3 gap-2">
        {[0, 1, 2].map((i) => (
          <SkeletonBlock key={i} className="h-10" delay={delay + 140 + i * 50} />
        ))}
      </div>
    </div>
  );
}

/** Chat shell skeleton — sidebar + chat area. */
export function ChatSkeleton() {
  return (
    <SkeletonFrame className="flex h-[calc(100vh-7rem)] gap-4 overflow-hidden">
      <div className="hidden lg:flex w-72 flex-col rounded-2xl border border-slate-200 bg-white p-4 shadow-sm space-y-3">
        <SkeletonText width="40%" />
        <SkeletonBlock className="h-9 w-full" delay={60} />
        <div className="mt-3 space-y-2">
          {Array.from({ length: 5 }).map((_, i) => (
            <SkeletonBlock key={i} className="h-12 w-full" delay={120 + i * 60} />
          ))}
        </div>
      </div>
      <div className="flex flex-1 flex-col min-w-0 space-y-4">
        <div className="rounded-2xl border border-slate-200 bg-white p-4 shadow-sm space-y-2">
          <SkeletonText width="18%" className="h-2.5" />
          <SkeletonText width="34%" className="h-4" delay={50} />
        </div>
        <div className="flex-1 rounded-2xl border border-slate-200 bg-white p-5 shadow-sm space-y-4">
          {Array.from({ length: 4 }).map((_, i) => (
            <div
              key={i}
              className={`flex ${i % 2 === 0 ? "justify-start" : "justify-end"}`}
            >
              <SkeletonBlock
                className={`h-16 ${i % 2 === 0 ? "w-3/4" : "w-2/3"}`}
                delay={i * 100}
              />
            </div>
          ))}
        </div>
      </div>
    </SkeletonFrame>
  );
}

/** Graph page skeleton — toolbar + large 3D area placeholder. */
export function GraphSkeleton() {
  return (
    <SkeletonFrame className="space-y-4">
      <div className="rounded-2xl border border-slate-200 bg-white p-4 shadow-sm flex items-center gap-3">
        <SkeletonChip />
        <SkeletonChip delay={50} />
        <SkeletonChip delay={100} />
        <div className="flex-1" />
        <SkeletonBlock className="h-9 w-32" delay={140} />
      </div>
      <div
        className={`rounded-2xl ${SHIMMER}`}
        style={{ height: "min(640px, calc(100vh - 12rem))" }}
      />
    </SkeletonFrame>
  );
}

/** Approval-queue skeleton — single hero card. */
export function ApprovalSkeleton() {
  return (
    <SkeletonFrame className="flex flex-1 flex-col items-center justify-center pb-20">
      <div className="w-full max-w-3xl rounded-3xl border border-slate-200 bg-white p-7 shadow-sm space-y-5">
        <div className="flex items-center gap-3">
          <SkeletonChip />
          <SkeletonChip delay={50} />
          <div className="flex-1" />
          <SkeletonText width="80px" className="h-2.5" delay={80} />
        </div>
        <div className="space-y-3">
          <SkeletonText width="70%" className="h-5" delay={100} />
          <SkeletonText width="40%" className="h-2.5" delay={140} />
        </div>
        <SkeletonBlock className="h-44" delay={180} />
        <div className="flex justify-end gap-3 pt-2">
          <SkeletonBlock className="h-10 w-24" delay={220} />
          <SkeletonBlock className="h-10 w-36" delay={260} />
        </div>
      </div>
    </SkeletonFrame>
  );
}
