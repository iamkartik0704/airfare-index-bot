import '@vly-ai/integrations';
import { Toaster } from "@/components/ui/sonner";
import { RequireAuth } from "@/components/RequireAuth";
import { VlyToolbar } from "../vly-toolbar-readonly.tsx";
import { ConvexAuthProvider } from "@convex-dev/auth/react";
import React, { StrictMode, useEffect, lazy, Suspense } from "react";
import { createRoot } from "react-dom/client";
import { BrowserRouter, Route, Routes, useLocation } from "react-router";
import "./index.css";

// Lazy load route components with a retry wrapper for Vite chunk loading failures
const lazyRetry = (componentImport: () => Promise<any>) =>
  lazy(async () => {
    try {
      return await componentImport();
    } catch (error) {
      console.error("Chunk failed to load, forcing reload", error);
      window.location.reload();
      return Promise.reject(error);
    }
  });

const Landing = lazyRetry(() => import("./pages/Landing.tsx"));
const AuthPage = lazyRetry(() => import("./pages/Auth.tsx"));
const AppShell = lazyRetry(() => import("./components/AppShell.tsx"));
const Overview = lazyRetry(() => import("./pages/Overview.tsx"));
const Sectors = lazyRetry(() => import("./pages/Sectors.tsx"));
const LeadTime = lazyRetry(() => import("./pages/LeadTime.tsx"));
const Drivers = lazyRetry(() => import("./pages/Drivers.tsx"));
const Pipeline = lazyRetry(() => import("./pages/Pipeline.tsx"));
const Explorer = lazyRetry(() => import("./pages/Explorer.tsx"));
const Validation = lazyRetry(() => import("./pages/Validation.tsx"));
const Methodology = lazyRetry(() => import("./pages/Methodology.tsx"));
const ApiDocs = lazyRetry(() => import("./pages/ApiDocs.tsx"));
const Deck = lazyRetry(() => import("./pages/Deck.tsx"));
const NotFound = lazyRetry(() => import("./pages/NotFound.tsx"));

// Simple loading fallback for route transitions
function RouteLoading() {
  return (
    <div className="min-h-screen flex items-center justify-center">
      <div className="animate-pulse text-muted-foreground">Loading...</div>
    </div>
  );
}

/** Silent error boundary — if VlyToolbar crashes it renders nothing instead of
 *  crashing the whole app (e.g. hook errors in the browser runtime). */
class ToolbarErrorBoundary extends React.Component<
  { children: React.ReactNode },
  { hasError: boolean }
> {
  state = { hasError: false };
  static getDerivedStateFromError() {
    return { hasError: true };
  }
  componentDidCatch(err: Error) {
    console.warn("[VlyToolbar] Caught error, toolbar disabled:", err.message);
  }
  render() {
    return this.state.hasError ? null : this.props.children;
  }
}

/** Hard guard so runtime errors never leave the preview as a blank page. */
class RootErrorBoundary extends React.Component<
  { children: React.ReactNode },
  { hasError: boolean; message: string; stack: string }
> {
  state = { hasError: false, message: "", stack: "" };
  static getDerivedStateFromError(error: Error) {
    return {
      hasError: true,
      message: error.message || "Unknown runtime error",
      stack: error.stack || "",
    };
  }
  componentDidCatch(err: Error) {
    console.error("[Preview] Root crash:", err);
  }
  render() {
    if (this.state.hasError) {
      return (
        <div className="min-h-screen flex items-center justify-center bg-background text-foreground p-6">
          <div className="max-w-lg text-center">
            <p className="text-sm font-semibold">Preview runtime error</p>
            <p className="mt-2 text-xs text-muted-foreground break-words">
              {this.state.message}
            </p>
            {this.state.stack && (
              <pre className="mt-3 text-left text-[10px] leading-4 text-muted-foreground/80 max-h-40 overflow-auto rounded border border-border/60 p-2">
                {this.state.stack}
              </pre>
            )}
          </div>
        </div>
      );
    }
    return this.props.children;
  }
}

function RouteSyncer() {
  const location = useLocation();
  useEffect(() => {
    window.parent.postMessage(
      { type: "iframe-route-change", path: location.pathname },
      "*",
    );
  }, [location.pathname]);

  useEffect(() => {
    function handleMessage(event: MessageEvent) {
      if (event.data?.type === "navigate") {
        if (event.data.direction === "back") window.history.back();
        if (event.data.direction === "forward") window.history.forward();
      }
    }
    window.addEventListener("message", handleMessage);
    return () => window.removeEventListener("message", handleMessage);
  }, []);

  return null;
}


createRoot(document.getElementById("root")!).render(
  <StrictMode>
    <RootErrorBoundary>
      <ToolbarErrorBoundary>
        <VlyToolbar />
      </ToolbarErrorBoundary>
        <BrowserRouter>
          <RouteSyncer />
          <Suspense fallback={<RouteLoading />}>
            <Routes>
              <Route path="/" element={<Landing />} />
              <Route
                path="/auth"
                element={<AuthPage redirectAfterAuth="/dashboard" />}
              />
              <Route
                path="/dashboard"
                element={
                  <RequireAuth
                    title="Sign in to open the SAFAR console"
                    description="The index, the collector audit trail and the validation results live behind sign-in."
                  >
                    <AppShell />
                  </RequireAuth>
                }
              >
                <Route index element={<Overview />} />
                <Route path="sectors" element={<Sectors />} />
                <Route path="leadtime" element={<LeadTime />} />
                <Route path="drivers" element={<Drivers />} />
                <Route path="pipeline" element={<Pipeline />} />
                <Route path="explorer" element={<Explorer />} />
                <Route path="validation" element={<Validation />} />
                <Route path="methodology" element={<Methodology />} />
                <Route path="api" element={<ApiDocs />} />
                <Route path="deck" element={<Deck />} />
              </Route>
              <Route path="*" element={<NotFound />} />
            </Routes>
          </Suspense>
        </BrowserRouter>
        <Toaster />
    </RootErrorBoundary>
  </StrictMode>,
);
