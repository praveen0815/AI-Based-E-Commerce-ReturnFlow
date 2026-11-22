import { Link } from "react-router-dom";

import { EmptyState } from "../components/ui/EmptyState";

export function NotFoundPage() {
  return (
    <EmptyState
      title="That page is not available"
      description="Use the navigation for overview, activity, members, audit, system, or preferences."
      action={
        <Link to="/" className="text-sm font-semibold text-cyan-300 hover:text-cyan-200">
          Back to overview
        </Link>
      }
    />
  );
}
