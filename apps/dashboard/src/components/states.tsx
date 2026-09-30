import type { UseQueryResult } from "@tanstack/react-query";
import { AlertTriangle, Inbox } from "lucide-react";
import type { ReactNode } from "react";
import { ApiError } from "@/api/client";
import { cn } from "@/lib/format";

export function Loading({ label = "Loading", className }: { label?: string; className?: string }) {
  return (
    <div role="status" aria-live="polite" className={cn("neo-2 flex items-center gap-3 bg-white p-4", className)}>
      <span className="neo-live text-xl" aria-hidden="true">
        ■
      </span>
      <span className="neo-mono text-xs font-bold uppercase tracking-[0.2em]">{label}…</span>
    </div>
  );
}

export function Empty({ label, children }: { label: string; children?: ReactNode }) {
  return (
    <div className="flex flex-col items-center justify-center gap-2 border-[3px] border-dashed border-ink/40 p-6 text-center">
      <Inbox className="h-5 w-5 opacity-60" aria-hidden="true" />
      <span className="neo-mono text-[11px] font-bold uppercase tracking-[0.16em] text-muted-foreground">{label}</span>
      {children && <div className="neo-mono max-w-prose text-[11px] leading-5 text-muted-foreground">{children}</div>}
    </div>
  );
}

/** Shows the API's error envelope verbatim: message, code, HTTP status and request_id. */
export function ErrorBox({ error, className }: { error: unknown; className?: string }) {
  const api = error instanceof ApiError ? error : null;
  const message = error instanceof Error ? error.message : String(error);
  return (
    <div role="alert" className={cn("neo-2 bg-red/10 p-3", className)}>
      <p className="flex items-center gap-2 text-sm font-extrabold uppercase">
        <AlertTriangle className="h-4 w-4 shrink-0 text-red" aria-hidden="true" />
        {api ? `API error · ${api.code}` : "Error"}
      </p>
      <p className="mt-1 text-sm leading-5 break-words">{message}</p>
      {api && (
        <p className="neo-mono mt-1 text-[10px] text-muted-foreground break-all">
          HTTP {api.status || "—"} · {api.path}
          {api.requestId ? ` · request_id ${api.requestId}` : ""}
        </p>
      )}
    </div>
  );
}

/**
 * Renders loading / error / empty for a query and hands the data to `children`.
 * A 404 is treated as an empty state (e.g. "no index has been computed yet"),
 * still quoting the API's own message and request id.
 */
export function QueryState<T>({
  query,
  children,
  loadingLabel,
  emptyLabel = "Nothing to show yet",
  isEmpty,
}: {
  query: UseQueryResult<T>;
  children: (data: T) => ReactNode;
  loadingLabel?: string;
  emptyLabel?: string;
  isEmpty?: (data: T) => boolean;
}) {
  if (query.isPending) return <Loading label={loadingLabel} />;
  if (query.isError) {
    const err = query.error;
    if (err instanceof ApiError && err.isNotFound) {
      return (
        <Empty label={emptyLabel}>
          {err.message}
          {err.requestId ? <span className="block opacity-70">request_id {err.requestId}</span> : null}
        </Empty>
      );
    }
    return <ErrorBox error={err} />;
  }
  const data = query.data as T;
  if (isEmpty?.(data)) return <Empty label={emptyLabel} />;
  return (
    <div className={cn("min-w-0", query.isFetching && query.isPlaceholderData && "opacity-60 transition-opacity")}>
      {children(data)}
    </div>
  );
}
