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
import { ROLE_LABELS, validateStoreName } from "../utils/access";

export function StoreSelectPage() {
  const { memberships, selectStore, refresh } = useAuth();
  const navigate = useNavigate();
  const [name, setName] = useState("");
  const [error, setError] = useState("");
  const [formError, setFormError] = useState("");
  const [pending, setPending] = useState(false);

  async function onCreate(event: FormEvent<HTMLFormElement>) {
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
        eyebrow="Stores"
        title="Choose a store"
        description="Requests use the store selected here. A store id typed into the browser is accepted only when your account is a member."
      />
      <div className="grid gap-4 md:grid-cols-2">
        {memberships.map((membership) => (
          <Card key={membership.id} className="p-5">
            <p className="text-lg font-semibold text-white">{membership.store_name}</p>
            <p className="mt-1 text-sm text-ink-muted">{ROLE_LABELS[membership.role]}</p>
            <Button
              className="mt-4"
              onClick={() => {
                selectStore(membership.store_id);
                navigate("/");
              }}
            >
              Open store
            </Button>
          </Card>
        ))}
      </div>
      <Card className="max-w-xl p-6">
        <h2 className="text-base font-semibold text-white">Create another store</h2>
        <form className="mt-4 space-y-4" onSubmit={onCreate} noValidate>
          {formError ? (
            <Alert tone="danger" title="Could not create the store">
              {formError}
            </Alert>
          ) : null}
          <Input
            id="new-store-name"
            name="name"
            label="Store name"
            value={name}
            error={error}
            onChange={(event) => setName(event.target.value)}
          />
          <Button type="submit" disabled={pending}>
            {pending ? "Creating store" : "Create store"}
          </Button>
        </form>
      </Card>
    </div>
  );
}
