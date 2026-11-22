import { useState, type FormEvent } from "react";

import { PageHeader } from "../components/PageHeader";
import { Alert } from "../components/ui/Alert";
import { Button } from "../components/ui/Button";
import { Checkbox } from "../components/ui/Checkbox";
import { Input } from "../components/ui/Input";
import { Select } from "../components/ui/Select";
import { type Density, usePreferences } from "../hooks/usePreferences";

interface FieldErrors {
  displayName?: string;
  email?: string;
}

const emailPattern = /^[^\s@]+@[^\s@]+\.[^\s@]+$/;

export function PreferencesPage() {
  const preferences = usePreferences();
  const [displayName, setDisplayName] = useState(preferences.displayName);
  const [email, setEmail] = useState(preferences.email);
  const [density, setDensity] = useState<Density>(preferences.density);
  const [showSampleMetrics, setShowSampleMetrics] = useState(preferences.showSampleMetrics);
  const [errors, setErrors] = useState<FieldErrors>({});
  const [status, setStatus] = useState<"idle" | "error" | "success">("idle");

  function onSubmit(event: FormEvent<HTMLFormElement>) {
    event.preventDefault();
    const nextErrors: FieldErrors = {};
    if (displayName.trim().length < 2) {
      nextErrors.displayName = "Enter at least 2 characters.";
    }
    if (!emailPattern.test(email.trim())) {
      nextErrors.email = "Enter an email address like name@example.com.";
    }
    if (nextErrors.displayName || nextErrors.email) {
      setErrors(nextErrors);
      setStatus("error");
      return;
    }

    preferences.save({
      displayName: displayName.trim(),
      email: email.trim(),
      density,
      showSampleMetrics,
    });
    setErrors({});
    setStatus("success");
  }

  return (
    <div className="space-y-6">
      <PageHeader
        eyebrow="Preferences"
        title="Display preferences"
        description="These settings change this tab only. They are not sent to the API and they disappear on refresh."
      />

      {status === "error" ? (
        <Alert tone="danger" title="Fix the highlighted fields">
          The form was not saved.
        </Alert>
      ) : null}
      {status === "success" ? (
        <Alert tone="success" title="Saved in this browser tab">
          The local display name is now {displayName.trim()}. {email.trim()} was not emailed.
        </Alert>
      ) : null}

      <form className="max-w-xl space-y-5" onSubmit={onSubmit} noValidate>
        <Input
          id="display-name"
          name="displayName"
          label="Display name"
          autoComplete="name"
          value={displayName}
          error={errors.displayName}
          hint="Stored in this tab only. Your account name is on Profile."
          onChange={(event) => {
            setDisplayName(event.target.value);
            setStatus("idle");
          }}
        />
        <Input
          id="email"
          name="email"
          type="email"
          label="Contact email"
          autoComplete="email"
          inputMode="email"
          value={email}
          error={errors.email}
          hint="Checked for shape only. This is not your sign-in email and it is not sent anywhere."
          onChange={(event) => {
            setEmail(event.target.value);
            setStatus("idle");
          }}
        />
        <Select
          id="density"
          name="density"
          label="Overview density"
          value={density}
          hint="Changes the spacing of the sample metric cards."
          options={[
            { value: "comfortable", label: "Comfortable" },
            { value: "compact", label: "Compact" },
          ]}
          onChange={(event) => setDensity(event.target.value as Density)}
        />
        <Checkbox
          id="show-sample-metrics"
          name="showSampleMetrics"
          label="Show sample metrics on the overview"
          hint="Turning this off replaces the figures with an empty state."
          checked={showSampleMetrics}
          onChange={(event) => setShowSampleMetrics(event.target.checked)}
        />
        <Button type="submit">Save preferences</Button>
      </form>
    </div>
  );
}
