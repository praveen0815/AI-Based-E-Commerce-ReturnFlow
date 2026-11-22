export interface AuthUser {
  id: string;
  email: string;
  display_name: string;
  is_active: boolean;
}

export interface Membership {
  id: string;
  store_id: string;
  store_name: string;
  store_slug: string;
  role: MemberRole;
  permissions: string[];
}

export type MemberRole = "OWNER" | "ADMIN" | "MANAGER" | "SUPPORT_AGENT" | "CUSTOMER";

export interface TokenPayload {
  access_token: string;
  token_type: string;
  expires_in: number;
}

export interface AuthResult {
  token: TokenPayload;
  user: AuthUser;
}

export interface CurrentUser {
  user: AuthUser;
  memberships: Membership[];
}

export interface StoreSummary {
  id: string;
  name: string;
  slug: string;
  role: MemberRole;
}

export interface MemberRecord {
  id: string;
  user_id: string;
  email: string;
  display_name: string;
  role: MemberRole;
}

export interface AuditEvent {
  id: string;
  action: string;
  actor_email?: string;
  target_type?: string;
  target_id?: string;
  details: Record<string, unknown>;
  created_at: string;
}
