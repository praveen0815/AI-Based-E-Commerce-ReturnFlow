import { useState, type FormEvent } from "react";
import { Link, useNavigate } from "react-router-dom";

import { Alert } from "../components/ui/Alert";
import { Button } from "../components/ui/Button";
import { Card } from "../components/ui/Card";
import { Input } from "../components/ui/Input";
import { useAuth } from "../hooks/useAuth";
import { ApiError } from "../services/api";
import { validateDisplayName, validateEmail, validatePassword } from "../utils/access";

export function RegisterPage() {
  const { signUp } = useAuth();
  const navigate = useNavigate();
  const [displayName, setDisplayName] = useState("");
  const [email, setEmail] = useState("");
  const [password, setPassword] = useState("");
  const [errors, setErrors] = useState<{ displayName?: string; email?: string; password?: string }>({});
  const [formError, setFormError] = useState("");
  const [pending, setPending] = useState(false);

  async function onSubmit(event: FormEvent<HTMLFormElement>) {
    event.preventDefault();
    const nextErrors = {
      displayName: validateDisplayName(displayName),
      email: validateEmail(email),
      password: validatePassword(password, email),
    };
    if (nextErrors.displayName || nextErrors.email || nextErrors.password) {
      setErrors(nextErrors);
      setFormError("");
      return;
    }
    setPending(true);
    setFormError("");
    try {
      await signUp(email.trim(), password, displayName.trim());
      navigate("/onboarding");
    } catch (error) {
      const message = error instanceof ApiError ? error.message : "Registration failed.";
      setFormError(message);
    } finally {
      setPending(false);
    }
  }

  return (
    <Card className="p-6">
      <h1 className="text-2xl font-semibold text-white">Create an account</h1>
      <p className="mt-2 text-sm leading-6 text-ink-muted">
        The password is hashed before it is stored. You will create a store next.
      </p>
      <form className="mt-6 space-y-4" onSubmit={onSubmit} noValidate>
        {formError ? (
          <Alert tone="danger" title="Could not create the account">
            {formError}
          </Alert>
        ) : null}
        <Input
          id="register-name"
          name="displayName"
          label="Display name"
          autoComplete="name"
          value={displayName}
          error={errors.displayName}
          onChange={(event) => setDisplayName(event.target.value)}
        />
        <Input
          id="register-email"
          name="email"
          type="email"
          label="Email"
          autoComplete="username"
          value={email}
          error={errors.email}
          onChange={(event) => setEmail(event.target.value)}
        />
        <Input
          id="register-password"
          name="password"
          type="password"
          label="Password"
          autoComplete="new-password"
          hint="12 to 128 characters, and different from the email."
          value={password}
          error={errors.password}
          onChange={(event) => setPassword(event.target.value)}
        />
        <Button type="submit" className="w-full" disabled={pending}>
          {pending ? "Creating account" : "Create account"}
        </Button>
      </form>
      <p className="mt-4 text-sm text-ink-muted">
        Already have an account?{" "}
        <Link to="/login" className="font-semibold text-cyan-300 hover:text-cyan-200">
          Sign in
        </Link>
      </p>
    </Card>
  );
}
