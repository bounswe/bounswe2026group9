"use client";

import Link from "next/link";
import { useMemo, useState } from "react";
import { useSearchParams } from "next/navigation";
import {
  CalendarDays,
  Check,
  Circle,
  Eye,
  EyeOff,
  LockKeyhole,
  Mail,
  UserRound,
} from "lucide-react";

import { AuthShell } from "@/components/auth/auth-shell";
import { GuestOnlyRoute } from "@/components/auth/guest-only-route";
import { Button } from "@/components/ui/button";
import { Card, CardContent, CardDescription, CardHeader, CardTitle } from "@/components/ui/card";
import { Checkbox } from "@/components/ui/checkbox";
import { Input } from "@/components/ui/input";
import { Label } from "@/components/ui/label";
import { Separator } from "@/components/ui/separator";
import { useAuth } from "@/hooks/use-auth";
import { getErrorMessage, getGoogleLoginUrl } from "@/lib/api";
import { cn } from "@/lib/utils";

interface RegisterFormState {
  confirmPassword: string;
  dateOfBirth: string;
  email: string;
  password: string;
  username: string;
}

interface RegisterErrors {
  confirmPassword?: string;
  dateOfBirth?: string;
  email?: string;
  password?: string;
  terms?: string;
  username?: string;
}

const initialFormState: RegisterFormState = {
  confirmPassword: "",
  dateOfBirth: "",
  email: "",
  password: "",
  username: "",
};

function GoogleIcon() {
  return (
    <svg aria-hidden="true" viewBox="0 0 48 48" className="size-[1.125rem]">
      <path
        fill="#EA4335"
        d="M24 9.5c3.54 0 6.71 1.22 9.21 3.6l6.85-6.85C35.9 2.38 30.47 0 24 0 14.62 0 6.51 5.38 2.56 13.22l7.98 6.19C12.43 13.72 17.74 9.5 24 9.5z"
      />
      <path
        fill="#4285F4"
        d="M46.98 24.55c0-1.57-.15-3.09-.38-4.55H24v9.02h12.94c-.58 2.96-2.26 5.48-4.78 7.18l7.73 6c4.51-4.18 7.09-10.36 7.09-17.65z"
      />
      <path
        fill="#FBBC05"
        d="M10.53 28.59a14.5 14.5 0 0 1 0-9.18l-7.98-6.19a24.08 24.08 0 0 0 0 21.56l7.98-6.19z"
      />
      <path
        fill="#34A853"
        d="M24 48c6.48 0 11.93-2.13 15.89-5.81l-7.73-6c-2.15 1.45-4.92 2.3-8.16 2.3-6.26 0-11.57-4.22-13.47-9.91l-7.98 6.19C6.51 42.62 14.62 48 24 48z"
      />
    </svg>
  );
}

interface AuthInputProps extends Omit<React.ComponentProps<typeof Input>, "className"> {
  icon: React.ReactNode;
  rightIcon?: React.ReactNode;
}

function AuthInput({ icon, rightIcon, ...props }: AuthInputProps) {
  return (
    <div className="relative">
      <span className="text-muted-foreground pointer-events-none absolute top-1/2 left-4 -translate-y-1/2">
        {icon}
      </span>
      <Input className={cn("rounded-2xl pl-12", rightIcon ? "pr-12" : "")} {...props} />
      {rightIcon ? (
        <span className="absolute top-1/2 right-4 -translate-y-1/2">{rightIcon}</span>
      ) : null}
    </div>
  );
}

function passwordChecks(password: string) {
  return {
    hasLength: password.length >= 8,
    hasNumber: /\d/.test(password),
    hasSpecial: /[^A-Za-z0-9]/.test(password),
    hasUppercase: /[A-Z]/.test(password),
  };
}

function validateRegisterForm(form: RegisterFormState, acceptedTerms: boolean): RegisterErrors {
  const checks = passwordChecks(form.password);
  const errors: RegisterErrors = {};

  if (!form.username.trim()) {
    errors.username = "Username is required.";
  } else if (form.username.trim().length < 3) {
    errors.username = "Username must be at least 3 characters.";
  }

  if (!form.email.trim()) {
    errors.email = "Email is required.";
  } else if (!/^[^\s@]+@[^\s@]+\.[^\s@]+$/.test(form.email)) {
    errors.email = "Enter a valid email address.";
  }

  if (!form.password) {
    errors.password = "Password is required.";
  } else if (Object.values(checks).some((value) => !value)) {
    errors.password = "Password must meet all strength requirements.";
  }

  if (!form.confirmPassword) {
    errors.confirmPassword = "Please confirm your password.";
  } else if (form.password !== form.confirmPassword) {
    errors.confirmPassword = "Passwords do not match.";
  }

  if (!form.dateOfBirth) {
    errors.dateOfBirth = "Date of birth is required.";
  } else if (new Date(form.dateOfBirth) > new Date()) {
    errors.dateOfBirth = "Date of birth cannot be in the future.";
  }

  if (!acceptedTerms) {
    errors.terms = "You must accept the Terms of Service and Privacy Policy.";
  }

  return errors;
}

function PasswordRequirement({ isMet, label }: { isMet: boolean; label: string }) {
  return (
    <li
      className={cn(
        "flex items-center gap-2 text-sm",
        isMet ? "text-success" : "text-muted-foreground",
      )}
    >
      <span className="flex size-4 items-center justify-center">
        {isMet ? <Check className="size-4" /> : <Circle className="size-3.5" />}
      </span>
      <span>{label}</span>
    </li>
  );
}

export default function RegisterPage() {
  const searchParams = useSearchParams();
  const { register } = useAuth();
  const [form, setForm] = useState(initialFormState);
  const [acceptedTerms, setAcceptedTerms] = useState(false);
  const [errors, setErrors] = useState<RegisterErrors>({});
  const [errorMessage, setErrorMessage] = useState<string | null>(null);
  const [isSubmitting, setIsSubmitting] = useState(false);
  const [showPassword, setShowPassword] = useState(false);
  const [showConfirmPassword, setShowConfirmPassword] = useState(false);

  const nextPath = useMemo(() => searchParams.get("next") ?? "/dashboard", [searchParams]);
  const checks = passwordChecks(form.password);
  const fulfilledChecks = Object.values(checks).filter(Boolean).length;
  const strengthLabel = fulfilledChecks === 4 ? "Strong" : fulfilledChecks >= 2 ? "Medium" : "Weak";

  function updateField<K extends keyof RegisterFormState>(key: K, value: RegisterFormState[K]) {
    setForm((current) => ({ ...current, [key]: value }));
    setErrors((current) => ({ ...current, [key]: undefined }));
  }

  async function submitRegistration() {
    const nextErrors = validateRegisterForm(form, acceptedTerms);
    setErrors(nextErrors);
    setErrorMessage(null);

    if (Object.keys(nextErrors).length > 0) {
      return;
    }

    setIsSubmitting(true);

    try {
      await register({
        date_of_birth: form.dateOfBirth,
        email: form.email.trim(),
        password: form.password,
        username: form.username.trim(),
      });
      window.location.assign(nextPath);
    } catch (error) {
      setErrorMessage(getErrorMessage(error, "Unable to create your account."));
    } finally {
      setIsSubmitting(false);
    }
  }

  function handleSubmit(event: React.FormEvent<HTMLFormElement>) {
    event.preventDefault();
    void submitRegistration();
  }

  return (
    <GuestOnlyRoute fallbackPath="/dashboard">
      <AuthShell>
        <Card className="border-0 bg-transparent shadow-none">
          <CardHeader className="px-0 pt-0">
            <CardTitle className="text-4xl sm:text-[2.7rem]">Create your account</CardTitle>
            <CardDescription className="text-base">
              Sign up with your credentials and date of birth.
            </CardDescription>
          </CardHeader>

          <CardContent className="px-0 pb-0">
            {errorMessage ? (
              <div className="border-destructive/30 bg-destructive/10 text-destructive mb-4 rounded-2xl border px-4 py-3 text-sm">
                {errorMessage}
              </div>
            ) : null}

            <form className="space-y-5" onSubmit={handleSubmit}>
              <div className="space-y-2">
                <Label htmlFor="register-email">Email</Label>
                <AuthInput
                  autoComplete="email"
                  icon={<Mail className="size-[1.05rem]" />}
                  id="register-email"
                  onChange={(event) => updateField("email", event.target.value)}
                  placeholder="you@example.com"
                  type="email"
                  value={form.email}
                />
                {errors.email ? <p className="text-destructive text-sm">{errors.email}</p> : null}
              </div>

              <div className="space-y-2">
                <Label htmlFor="register-username">Username</Label>
                <AuthInput
                  autoComplete="username"
                  icon={<UserRound className="size-[1.05rem]" />}
                  id="register-username"
                  onChange={(event) => updateField("username", event.target.value)}
                  placeholder="johndoe"
                  type="text"
                  value={form.username}
                />
                {errors.username ? (
                  <p className="text-destructive text-sm">{errors.username}</p>
                ) : (
                  <p className="text-muted-foreground text-sm">
                    This will be your public display handle.
                  </p>
                )}
              </div>

              <div className="space-y-2">
                <Label htmlFor="register-password">Password</Label>
                <AuthInput
                  autoComplete="new-password"
                  icon={<LockKeyhole className="size-[1.05rem]" />}
                  id="register-password"
                  onChange={(event) => updateField("password", event.target.value)}
                  placeholder="Create a strong password"
                  rightIcon={
                    <button
                      aria-label={showPassword ? "Hide password" : "Show password"}
                      className="text-muted-foreground hover:text-foreground transition-colors"
                      onClick={() => setShowPassword((current) => !current)}
                      type="button"
                    >
                      {showPassword ? (
                        <EyeOff className="size-[1.05rem]" />
                      ) : (
                        <Eye className="size-[1.05rem]" />
                      )}
                    </button>
                  }
                  type={showPassword ? "text" : "password"}
                  value={form.password}
                />

                <div className="mt-3 flex gap-2">
                  {[0, 1, 2, 3].map((index) => (
                    <span
                      key={index}
                      className={cn(
                        "h-1.5 flex-1 rounded-full",
                        index < fulfilledChecks ? "bg-accent" : "bg-border",
                      )}
                    />
                  ))}
                </div>

                <p className="text-accent text-sm font-semibold">{strengthLabel}</p>

                <ul className="space-y-2">
                  <PasswordRequirement isMet={checks.hasLength} label="At least 8 characters" />
                  <PasswordRequirement
                    isMet={checks.hasUppercase}
                    label="Contains uppercase letter"
                  />
                  <PasswordRequirement isMet={checks.hasNumber} label="Contains number" />
                  <PasswordRequirement
                    isMet={checks.hasSpecial}
                    label="Contains special character"
                  />
                </ul>

                {errors.password ? (
                  <p className="text-destructive text-sm">{errors.password}</p>
                ) : null}
              </div>

              <div className="space-y-2">
                <Label htmlFor="register-confirm-password">Confirm Password</Label>
                <AuthInput
                  autoComplete="new-password"
                  icon={<LockKeyhole className="size-[1.05rem]" />}
                  id="register-confirm-password"
                  onChange={(event) => updateField("confirmPassword", event.target.value)}
                  placeholder="Re-enter your password"
                  rightIcon={
                    <button
                      aria-label={
                        showConfirmPassword ? "Hide confirm password" : "Show confirm password"
                      }
                      className="text-muted-foreground hover:text-foreground transition-colors"
                      onClick={() => setShowConfirmPassword((current) => !current)}
                      type="button"
                    >
                      {showConfirmPassword ? (
                        <EyeOff className="size-[1.05rem]" />
                      ) : (
                        <Eye className="size-[1.05rem]" />
                      )}
                    </button>
                  }
                  type={showConfirmPassword ? "text" : "password"}
                  value={form.confirmPassword}
                />
                {errors.confirmPassword ? (
                  <p className="text-destructive text-sm">{errors.confirmPassword}</p>
                ) : null}
              </div>

              <div className="space-y-2">
                <Label htmlFor="register-dob">Date of Birth</Label>
                <AuthInput
                  icon={<CalendarDays className="size-[1.05rem]" />}
                  id="register-dob"
                  max={new Date().toISOString().slice(0, 10)}
                  onChange={(event) => updateField("dateOfBirth", event.target.value)}
                  type="date"
                  value={form.dateOfBirth}
                />
                {errors.dateOfBirth ? (
                  <p className="text-destructive text-sm">{errors.dateOfBirth}</p>
                ) : (
                  <p className="text-muted-foreground text-sm">
                    Required for age-restricted events.
                  </p>
                )}
              </div>

              <div className="space-y-2">
                <label className="text-muted-foreground flex items-start gap-3 text-sm">
                  <Checkbox
                    aria-label="Accept terms"
                    checked={acceptedTerms}
                    onCheckedChange={(checked) => {
                      setAcceptedTerms(checked === true);
                      setErrors((current) => ({ ...current, terms: undefined }));
                    }}
                    className="mt-0.5"
                  />
                  <span>
                    I agree to the{" "}
                    <span className="text-accent font-semibold">Terms of Service</span> and{" "}
                    <span className="text-accent font-semibold">Privacy Policy</span>.
                  </span>
                </label>
                {errors.terms ? <p className="text-destructive text-sm">{errors.terms}</p> : null}
              </div>

              <Button
                className="h-12 w-full rounded-2xl text-sm font-semibold"
                disabled={isSubmitting}
              >
                {isSubmitting ? "Creating account..." : "Create Account"}
              </Button>
            </form>

            <div className="my-6 flex items-center gap-4">
              <Separator className="flex-1" />
              <span className="text-muted-foreground text-sm">or</span>
              <Separator className="flex-1" />
            </div>

            <Button
              asChild
              className="h-12 w-full rounded-2xl text-sm font-semibold"
              variant="outline"
            >
              <a href={getGoogleLoginUrl("signup")} rel="noreferrer">
                <GoogleIcon />
                Continue with Google
              </a>
            </Button>

            <p className="text-muted-foreground mt-6 text-center text-sm">
              Already have an account?{" "}
              <Link className="text-accent font-semibold hover:underline" href="/login">
                Sign In
              </Link>
            </p>
          </CardContent>
        </Card>
      </AuthShell>
    </GuestOnlyRoute>
  );
}
