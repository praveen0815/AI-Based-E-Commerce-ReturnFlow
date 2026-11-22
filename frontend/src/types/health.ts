export interface HealthData {
  status: "ok";
  service: string;
  environment: string;
  version: string;
}

export interface DependencyCheck {
  status: "up" | "down";
  detail?: string;
}

export interface ReadinessData {
  status: "ready" | "not_ready";
  checks: {
    database: DependencyCheck;
    redis: DependencyCheck;
  };
}
