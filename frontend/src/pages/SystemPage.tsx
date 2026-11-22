import { PageHeader } from "../components/PageHeader";
import { PlatformStatusCard } from "../components/PlatformStatusCard";
import { apiBaseUrl } from "../services/api";
import { usePlatformStatus } from "../hooks/usePlatformStatus";
import { Card } from "../components/ui/Card";

export function SystemPage() {
  const { status } = usePlatformStatus();
  const version = status.phase === "success" || status.phase === "degraded" ? status.health.version : "Waiting for the API";
  const environment =
    status.phase === "success" || status.phase === "degraded" ? status.health.environment : "Unknown until the API answers";

  return (
    <div className="space-y-6">
      <PageHeader
        eyebrow="System"
        title="Foundation health"
        description="Liveness ignores dependencies. Readiness requires both PostgreSQL and Redis to answer."
      />
      <PlatformStatusCard detailed />
      <Card className="grid gap-4 p-5 sm:grid-cols-3">
        <div>
          <p className="text-xs uppercase tracking-wide text-ink-faint">API base URL</p>
          <p className="mt-1 break-all font-mono text-sm text-white">{apiBaseUrl}</p>
        </div>
        <div>
          <p className="text-xs uppercase tracking-wide text-ink-faint">Reported version</p>
          <p className="mt-1 text-sm text-white">{version}</p>
        </div>
        <div>
          <p className="text-xs uppercase tracking-wide text-ink-faint">Environment</p>
          <p className="mt-1 text-sm text-white">{environment}</p>
        </div>
      </Card>
    </div>
  );
}
