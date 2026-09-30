import { createBrowserRouter } from "react-router";
import AppShell from "./components/AppShell";
import ApiDocs from "./pages/ApiDocs";
import Explorer from "./pages/Explorer";
import LeadTime from "./pages/LeadTime";
import Methodology from "./pages/Methodology";
import NotFound from "./pages/NotFound";
import Overview from "./pages/Overview";
import Pipeline from "./pages/Pipeline";
import RouteDetail from "./pages/RouteDetail";
import Sectors from "./pages/Sectors";
import Validation from "./pages/Validation";

export const router = createBrowserRouter([
  {
    path: "/",
    element: <AppShell />,
    children: [
      { index: true, element: <Overview /> },
      { path: "sectors", element: <Sectors /> },
      { path: "routes/:code", element: <RouteDetail /> },
      { path: "lead-time", element: <LeadTime /> },
      { path: "explorer", element: <Explorer /> },
      { path: "pipeline", element: <Pipeline /> },
      { path: "validation", element: <Validation /> },
      { path: "methodology", element: <Methodology /> },
      { path: "api", element: <ApiDocs /> },
      { path: "*", element: <NotFound /> },
    ],
  },
]);
