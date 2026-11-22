import { useState, type FormEvent } from "react";
import { useNavigate } from "react-router-dom";

import { PageHeader } from "../components/PageHeader";
import { Alert } from "../components/ui/Alert";
import { Button } from "../components/ui/Button";
import { Card } from "../components/ui/Card";
import { Input } from "../components/ui/Input";
import { useAuth } from "../hooks/useAuth";
import { ApiError } from "../services/api";
import { createStore } from "../services/auth";
import { validateStoreName } from "../utils/access";

export function OnboardingPage() {
  const { selectStore, refresh } = useAuth();
  const navigate = useNavigate();
  const [name, setName] = useState("");
  const [error, setError] = useState("");
  const [formError, setFormError] = useState("");
  const [pending, setPending] = useState(false);

  async function onSubmit(event: FormEvent<HTMLFormElement>) {
    event.preventDefault();
    const nameError = validateStoreName(name);
    if (nameError) {
      setError(nameError);
      return;
    }
    setPending(true);
    setFormError("");
    try {
      const store = await createStore(name.trim());
      selectStore(store.id);
      await refresh();
      navigate("/");
    } catch (caught) {
      setFormError(caught instanceof ApiError ? caught.message : "The store could not be created.");
    } finally {
      setPending(false);
    }
  }

  return (
    <div className="space-y-6">
      <PageHeader
        eyebrow="Store"
        title="Create your store"
        description="A store is the tenant boundary. You become its owner. Other people can join only after you add their existing account."
      />
      <Card className="max-w-xl p-6">
        <form className="space-y-4" onSubmit={onSubmit} noValidate>
          {formError ? (
            <Alert tone="danger" title="Could not create the store">
              {formError}
            </Alert>
          ) : null}
          <Input
            id="store-name"
            name="name"
            label="Store name"
            value={name}
            error={error}
            hint="2 to 120 characters. The address slug is generated on the server."
            onChange={(event) => {
              setName(event.target.value);
              setError("");
            }}
          />
          <Button type="submit" disabled={pending}>
            {pending ? "Creating store" : "Create store"}
          </Button>
        </form>
      </Card>
    </div>
  );
}
