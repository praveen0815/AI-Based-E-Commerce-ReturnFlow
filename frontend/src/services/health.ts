import { api, ApiError } from "./api";
import type { SuccessResponse } from "../types/api";
import type { HealthData, ReadinessData } from "../types/health";

function isReadinessData(value: unknown): value is ReadinessData {
  if (!value || typeof value !== "object") {
    return false;
  }
  const record = value as Record<string, unknown>;
  const checks = record.checks;
  if (!checks || typeof checks !== "object") {
    return false;
  }
  const checkRecord = checks as Record<string, unknown>;
  return (
    (record.status === "ready" || record.status === "not_ready") &&
    typeof checkRecord.database === "object" &&
    checkRecord.database !== null &&
    typeof checkRecord.redis === "object" &&
    checkRecord.redis !== null
  );
}

export async function getHealth(signal?: AbortSignal): Promise<HealthData> {
  const response = await api.get<SuccessResponse<HealthData>>("/api/v1/health", { signal });
  return response.data.data;
}

export async function getReadiness(signal?: AbortSignal): Promise<ReadinessData> {
  try {
    const response = await api.get<SuccessResponse<ReadinessData>>("/api/v1/ready", { signal });
    return response.data.data;
  } catch (error) {
    if (error instanceof ApiError && error.code === "not_ready" && isReadinessData(error.details)) {
      return error.details;
    }
    throw error;
  }
}
