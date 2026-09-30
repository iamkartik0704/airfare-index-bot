import { Link } from "react-router";
import { Panel } from "@/components/neo";

export default function NotFound() {
  return (
    <Panel kicker="404" title="No such page">
      <p className="text-sm">
        This route does not exist in the dashboard.{" "}
        <Link to="/" className="font-bold underline">
          Back to the index
        </Link>
        .
      </p>
    </Panel>
  );
}
