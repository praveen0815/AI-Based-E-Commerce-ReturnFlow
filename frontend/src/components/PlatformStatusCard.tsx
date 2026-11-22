import { Button } from "./ui/Button";
import { Alert } from "./ui/Alert";
import { Card } from "./ui/Card";
import { Spinner } from "./ui/Spinner";
import { usePlatformStatus } from "../hooks/usePlatformStatus";

function CheckList({
  database,
  redis,
}: {
  database: { status: string; detail?: string };
  redis: { status: string; detail?: string };
}) {
  return (
    <dl className="mt-3 grid gap-3 sm:grid-cols-2">
      <div>
        <dt className="text-xs uppercase tracking-wide text-ink-faint">PostgreSQL</dt>
        <dd className="mt-1 text-sm font-medium capitalize">
          {database.status}
          {database.detail ? ` (${database.detail})` : ""}
        </dd>
      </div>
      <div>
        <dt className="text-xs uppercase tracking-wide text-ink-faint">Redis</dt>
        <dd className="mt-1 text-sm font-medium capitalize">
          {redis.status}
          {redis.detail ? ` (${redis.detail})` : ""}
        </dd>
      </div>
    </dl>
  );
}

export function PlatformStatusCard({ detailed = false }: { detailed?: boolean }) {
  const { status, reload } = usePlatformStatus();

  return (
    <Card className="p-5" data-testid="platform-status">
      {status.phase === "loading" ? <Spinner label="Checking the API, PostgreSQL, and Redis" /> : null}

      {status.phase === "success" ? (
        <Alert tone="success" title="API, PostgreSQL, and Redis are reachable">
          {status.health.service} {status.health.version} is running in {status.health.environment}.
          {detailed ? (
            <CheckList database={status.readiness.checks.database} redis={status.readiness.checks.redis} />
          ) : null}
        </Alert>
      ) : null}

      {status.phase === "degraded" ? (
        <div className="space-y-4">
          <Alert tone="warning" title="The API is up, and a dependency is not">
            Readiness returned {status.readiness.status}. Connection strings are not shown.
            <CheckList database={status.readiness.checks.database} redis={status.readiness.checks.redis} />
          </Alert>
          <Button variant="secondary" onClick={reload}>
            Check again
          </Button>
        </div>
      ) : null}

      {status.phase === "error" ? (
        <div className="space-y-4">
          <Alert tone="danger" title="Platform status is unavailable">
            {status.message}
            {status.requestId ? ` Request ${status.requestId}.` : ""}
          </Alert>
          <Button variant="secondary" onClick={reload}>
            Try again
          </Button>
        </div>
      ) : null}
    </Card>
  );
}
