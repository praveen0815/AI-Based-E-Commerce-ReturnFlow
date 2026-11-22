import { useEffect, useState, type FormEvent } from "react";

import { PageHeader } from "../components/PageHeader";
import { Alert } from "../components/ui/Alert";
import { Button } from "../components/ui/Button";
import { Card } from "../components/ui/Card";
import { Input } from "../components/ui/Input";
import { Select } from "../components/ui/Select";
import { Spinner } from "../components/ui/Spinner";
import { useAuth } from "../hooks/useAuth";
import { ApiError } from "../services/api";
import { addMember, changeMemberRole, listMembers, removeMember } from "../services/auth";
import type { MemberRecord, MemberRole } from "../types/auth";
import { ROLE_LABELS, hasPermission, rolesAssignableBy, validateEmail } from "../utils/access";

export function MembersPage() {
  const { activeMembership, storeId } = useAuth();
  const canManage = hasPermission(activeMembership?.permissions, "membership:manage");
  const assignable = rolesAssignableBy(activeMembership?.role);
  const [members, setMembers] = useState<MemberRecord[]>([]);
  const [email, setEmail] = useState("");
  const [role, setRole] = useState<MemberRole>(assignable[0] ?? "SUPPORT_AGENT");
  const [emailError, setEmailError] = useState("");
  const [formError, setFormError] = useState("");
  const [pageError, setPageError] = useState("");
  const [pending, setPending] = useState(false);
  const [loading, setLoading] = useState(true);
  const [confirmId, setConfirmId] = useState<string | null>(null);

  useEffect(() => {
    let cancelled = false;
    setLoading(true);
    listMembers()
      .then((rows) => {
        if (!cancelled) {
          setMembers(rows);
          setPageError("");
        }
      })
      .catch((error: unknown) => {
        if (!cancelled) {
          setPageError(error instanceof ApiError ? error.message : "Members could not be loaded.");
        }
      })
      .finally(() => {
        if (!cancelled) {
          setLoading(false);
        }
      });
    return () => {
      cancelled = true;
    };
  }, [storeId]);

  async function onAdd(event: FormEvent<HTMLFormElement>) {
    event.preventDefault();
    const nextError = validateEmail(email);
    if (nextError) {
      setEmailError(nextError);
      return;
    }
    setPending(true);
    setFormError("");
    try {
      const created = await addMember(email.trim(), role);
      setMembers((current) => [...current, created]);
      setEmail("");
    } catch (error) {
      setFormError(error instanceof ApiError ? error.message : "The member could not be added.");
    } finally {
      setPending(false);
    }
  }

  async function onRole(member: MemberRecord, nextRole: MemberRole) {
    setPageError("");
    try {
      const updated = await changeMemberRole(member.id, nextRole);
      setMembers((current) => current.map((item) => (item.id === updated.id ? updated : item)));
    } catch (error) {
      setPageError(error instanceof ApiError ? error.message : "The role could not be changed.");
    }
  }

  async function onRemove(memberId: string) {
    setPageError("");
    try {
      await removeMember(memberId);
      setMembers((current) => current.filter((item) => item.id !== memberId));
      setConfirmId(null);
    } catch (error) {
      setPageError(error instanceof ApiError ? error.message : "The member could not be removed.");
    }
  }

  return (
    <div className="space-y-6">
      <PageHeader
        eyebrow="Access"
        title="Members"
        description="People listed here belong to the current store. Adding someone requires an account that already exists."
      />
      {pageError ? (
        <Alert tone="danger" title="Membership change failed">
          {pageError}
        </Alert>
      ) : null}
      {loading ? <Spinner label="Loading members" /> : null}
      <div className="space-y-3">
        {members.map((member) => (
          <Card key={member.id} className="flex flex-col gap-3 p-4 sm:flex-row sm:items-center sm:justify-between">
            <div>
              <p className="font-medium text-white">{member.display_name}</p>
              <p className="text-sm text-ink-muted">{member.email}</p>
            </div>
            <div className="flex flex-wrap items-center gap-2">
              {canManage ? (
                <Select
                  id={`role-${member.id}`}
                  label="Role"
                  value={member.role}
                  options={(member.role === "OWNER" && !assignable.includes("OWNER")
                    ? [member.role]
                    : assignable
                  ).map((value) => ({ value, label: ROLE_LABELS[value] }))}
                  onChange={(event) => onRole(member, event.target.value as MemberRole)}
                />
              ) : (
                <p className="text-sm text-ink">{ROLE_LABELS[member.role]}</p>
              )}
              {canManage ? (
                confirmId === member.id ? (
                  <Button variant="secondary" onClick={() => onRemove(member.id)}>
                    Confirm remove
                  </Button>
                ) : (
                  <Button variant="ghost" onClick={() => setConfirmId(member.id)}>
                    Remove
                  </Button>
                )
              ) : null}
            </div>
          </Card>
        ))}
      </div>
      {canManage ? (
        <Card className="max-w-xl p-6">
          <h2 className="text-base font-semibold text-white">Add a member</h2>
          <form className="mt-4 space-y-4" onSubmit={onAdd} noValidate>
            {formError ? (
              <Alert tone="danger" title="Could not add that account">
                {formError}
              </Alert>
            ) : null}
            <Input
              id="member-email"
              name="email"
              type="email"
              label="Email"
              value={email}
              error={emailError}
              hint="The person must already have a ReturnFlow account."
              onChange={(event) => setEmail(event.target.value)}
            />
            <Select
              id="member-role"
              label="Role"
              value={role}
              options={assignable.map((value) => ({ value, label: ROLE_LABELS[value] }))}
              onChange={(event) => setRole(event.target.value as MemberRole)}
            />
            <Button type="submit" disabled={pending || assignable.length === 0}>
              {pending ? "Adding" : "Add member"}
            </Button>
          </form>
        </Card>
      ) : null}
    </div>
  );
}
