import type { MemberRole } from "../types/auth";

export const ROLE_LABELS: Record<MemberRole, string> = {
  OWNER: "Owner",
  ADMIN: "Admin",
  MANAGER: "Manager",
  SUPPORT_AGENT: "Support agent",
  CUSTOMER: "Customer",
};

export function hasPermission(permissions: string[] | undefined, permission: string): boolean {
  return Boolean(permissions?.includes(permission));
}

export function rolesAssignableBy(actor: MemberRole | undefined): MemberRole[] {
  if (actor === "OWNER") {
    return ["OWNER", "ADMIN", "MANAGER", "SUPPORT_AGENT", "CUSTOMER"];
  }
  if (actor === "ADMIN") {
    return ["ADMIN", "MANAGER", "SUPPORT_AGENT", "CUSTOMER"];
  }
  return [];
}

const emailPattern = /^[^\s@]+@[^\s@]+\.[^\s@]+$/;

export function validateEmail(value: string): string | undefined {
  const email = value.trim();
  if (!emailPattern.test(email)) {
    return "Enter an email address like name@example.com.";
  }
  return undefined;
}

export function validatePassword(value: string, email?: string): string | undefined {
  if (value.length < 12 || value.length > 128) {
    return "Use 12 to 128 characters.";
  }
  if (email && value.toLowerCase() === email.trim().toLowerCase()) {
    return "Use a password that is different from the email.";
  }
  return undefined;
}

export function validateDisplayName(value: string): string | undefined {
  const cleaned = value.trim().replace(/\s+/g, " ");
  if (cleaned.length < 2 || cleaned.length > 80) {
    return "Use 2 to 80 characters.";
  }
  return undefined;
}

export function validateStoreName(value: string): string | undefined {
  const cleaned = value.trim().replace(/\s+/g, " ");
  if (cleaned.length < 2 || cleaned.length > 120) {
    return "Use 2 to 120 characters.";
  }
  return undefined;
}
