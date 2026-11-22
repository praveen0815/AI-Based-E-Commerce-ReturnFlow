import { useState, type FormEvent } from "react";
import { Link, useNavigate } from "react-router-dom";

import { Alert } from "../components/ui/Alert";
import { Button } from "../components/ui/Button";
import { Card } from "../components/ui/Card";
import { Input } from "../components/ui/Input";
import { useAuth } from "../hooks/useAuth";
import { ApiError } from "../services/api";
import { validateEmail } from "../utils/access";

export function LoginPage() {
  const { signIn, sessionExpired, clearSessionNotice } = useAuth();
  const navigate = useNavigate();
  const [email, setEmail] = useState("");
  const [password, setPassword] = useState("");
  const [errors, setErrors] = useState<{ email?: string; password?: string }>({});
  const [formError, setFormError] = useState("");
  const [pending, setPending] = useState(false);

  async function onSubmit(event: FormEvent<HTMLFormElement>) {
    event.preventDefault();
    const nextErrors: { email?: string; password?: string } = {};
    const emailError = validateEmail(email);
    if (emailError) {
      nextErrors.email = emailError;
    }
    if (!password || password.length > 128) {
      nextErrors.password = "Enter your password.";
    }
    if (nextErrors.email || nextErrors.password) {
      setErrors(nextErrors);
      setFormError("");
      return;
    }
    setPending(true);
    setFormError("");
    try {
      await signIn(email.trim(), password);
      clearSessionNotice();
      navigate("/");
    } catch (error) {
      const message = error instanceof ApiError ? error.message : "Sign-in failed.";
      setFormError(message);
    } finally {
      setPending(false);
    }
  }

  return (
    <Card className="p-6">
      <h1 className="text-2xl font-semibold text-white">Sign in</h1>
      <p className="mt-2 text-sm leading-6 text-ink-muted">Use the email and password for your ReturnFlow account.</p>
      <form className="mt-6 space-y-4" onSubmit={onSubmit} noValidate>
        {sessionExpired ? (
          <Alert tone="warning" title="Your session expired">
            Sign in again to continue. The previous access token is no longer accepted.
          </Alert>
        ) : null}
        {formError ? (
          <Alert tone="danger" title="Could not sign in">
            {formError}
          </Alert>
        ) : null}
        <Input
          id="login-email"
          name="email"
          type="email"
          label="Email"
          autoComplete="username"
          value={email}
          error={errors.email}
          onChange={(event) => {
            setEmail(event.target.value);
            setErrors((current) => ({ ...current, email: undefined }));
          }}
        />
        <Input
          id="login-password"
          name="password"
          type="password"
          label="Password"
          autoComplete="current-password"
          value={password}
          error={errors.password}
          onChange={(event) => {
            setPassword(event.target.value);
            setErrors((current) => ({ ...current, password: undefined }));
          }}
        />
        <Button type="submit" className="w-full" disabled={pending}>
          {pending ? "Signing in" : "Sign in"}
        </Button>
      </form>
      <p className="mt-4 text-sm text-ink-muted">
        New to ReturnFlow?{" "}
        <Link to="/register" className="font-semibold text-cyan-300 hover:text-cyan-200">
          Create an account
        </Link>
      </p>
    </Card>
  );
}
