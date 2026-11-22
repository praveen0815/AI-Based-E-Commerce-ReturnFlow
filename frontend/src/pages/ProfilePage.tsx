import { useState, type FormEvent } from "react";

import { PageHeader } from "../components/PageHeader";
import { Alert } from "../components/ui/Alert";
import { Button } from "../components/ui/Button";
import { Card } from "../components/ui/Card";
import { Input } from "../components/ui/Input";
import { useAuth } from "../hooks/useAuth";
import { ApiError } from "../services/api";
import { updateProfile } from "../services/auth";
import { ROLE_LABELS, validateDisplayName } from "../utils/access";

export function ProfilePage() {
  const { user, activeMembership, refresh } = useAuth();
  const [displayName, setDisplayName] = useState(user?.display_name ?? "");
  const [error, setError] = useState("");
  const [formError, setFormError] = useState("");
  const [saved, setSaved] = useState(false);
  const [pending, setPending] = useState(false);

  async function onSubmit(event: FormEvent<HTMLFormElement>) {
    event.preventDefault();
    const nameError = validateDisplayName(displayName);
    if (nameError) {
      setError(nameError);
      setSaved(false);
      return;
    }
    setPending(true);
    setFormError("");
    setSaved(false);
    try {
      await updateProfile(displayName.trim());
      await refresh();
      setSaved(true);
    } catch (caught) {
      setFormError(caught instanceof ApiError ? caught.message : "The profile could not be saved.");
    } finally {
      setPending(false);
    }
  }

  return (
    <div className="space-y-6">
      <PageHeader
        eyebrow="Account"
        title="Profile"
        description="This name is stored on your account. Display preferences in this tab stay separate and are not sent to the API."
      />
      <Card className="max-w-xl p-6">
        <form className="space-y-4" onSubmit={onSubmit} noValidate>
          {saved ? (
            <Alert tone="success" title="Profile saved">
              The account name is now {displayName.trim()}.
            </Alert>
          ) : null}
          {formError ? (
            <Alert tone="danger" title="Could not save the profile">
              {formError}
            </Alert>
          ) : null}
          <Input id="profile-email" label="Email" value={user?.email ?? ""} readOnly />
          <Input
            id="profile-name"
            name="displayName"
            label="Display name"
            value={displayName}
            error={error}
            onChange={(event) => {
              setDisplayName(event.target.value);
              setSaved(false);
            }}
          />
          {activeMembership ? (
            <p className="text-sm text-ink-muted">
              Current store role: {ROLE_LABELS[activeMembership.role]} at {activeMembership.store_name}.
            </p>
          ) : (
            <p className="text-sm text-ink-muted">You are not inside a store yet.</p>
          )}
          <Button type="submit" disabled={pending}>
            {pending ? "Saving" : "Save profile"}
          </Button>
        </form>
      </Card>
    </div>
  );
}
