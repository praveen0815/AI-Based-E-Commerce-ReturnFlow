import type { SuccessResponse } from "../types/api";
import type { AuditEvent, AuthResult, CurrentUser, MemberRecord, MemberRole, StoreSummary } from "../types/auth";
import { api } from "./api";

export async function registerAccount(input: {
  email: string;
  password: string;
  display_name: string;
}): Promise<AuthResult> {
  const response = await api.post<SuccessResponse<AuthResult>>("/api/v1/auth/register", input);
  return response.data.data;
}

export async function loginAccount(input: { email: string; password: string }): Promise<AuthResult> {
  const response = await api.post<SuccessResponse<AuthResult>>("/api/v1/auth/login", input);
  return response.data.data;
}

export async function logoutAccount(): Promise<void> {
  await api.post("/api/v1/auth/logout");
}

export async function currentUser(): Promise<CurrentUser> {
  const response = await api.get<SuccessResponse<CurrentUser>>("/api/v1/auth/me");
  return response.data.data;
}

export async function updateProfile(displayName: string): Promise<CurrentUser["user"]> {
  const response = await api.patch<SuccessResponse<CurrentUser["user"]>>("/api/v1/profile", {
    display_name: displayName,
  });
  return response.data.data;
}

export async function createStore(name: string): Promise<StoreSummary> {
  const response = await api.post<SuccessResponse<StoreSummary>>("/api/v1/stores", { name });
  return response.data.data;
}

export async function listMembers(): Promise<MemberRecord[]> {
  const response = await api.get<SuccessResponse<{ members: MemberRecord[] }>>("/api/v1/stores/current/members");
  return response.data.data.members;
}

export async function addMember(email: string, role: MemberRole): Promise<MemberRecord> {
  const response = await api.post<SuccessResponse<MemberRecord>>("/api/v1/stores/current/members", { email, role });
  return response.data.data;
}

export async function changeMemberRole(membershipId: string, role: MemberRole): Promise<MemberRecord> {
  const response = await api.patch<SuccessResponse<MemberRecord>>(
    `/api/v1/stores/current/members/${membershipId}`,
    { role },
  );
  return response.data.data;
}

export async function removeMember(membershipId: string): Promise<void> {
  await api.delete(`/api/v1/stores/current/members/${membershipId}`);
}

export async function listAudit(): Promise<AuditEvent[]> {
  const response = await api.get<SuccessResponse<{ events: AuditEvent[] }>>("/api/v1/stores/current/audit");
  return response.data.data.events;
}
