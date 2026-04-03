"use client";

import Link from "next/link";
import { useMemo, useState } from "react";
import { useSearchParams } from "next/navigation";
import { Eye, EyeOff, LockKeyhole, Mail } from "lucide-react";

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

const reasonMessages: Record<string, string> = {
  "oauth-failed": "Google sign-in could not be completed. Please try again.",
  protected: "Please sign in to access the dashboard.",
  "session-expired": "Your session expired. Please sign in again.",
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

export default function LoginPage() {
  const searchParams = useSearchParams();
  const { login } = useAuth();
  const [email, setEmail] = useState("");
  const [password, setPassword] = useState("");
  const [errorMessage, setErrorMessage] = useState<string | null>(null);
  const [isSubmitting, setIsSubmitting] = useState(false);
  const [showPassword, setShowPassword] = useState(false);

  const nextPath = useMemo(() => searchParams.get("next") ?? "/dashboard", [searchParams]);
  const reason = searchParams.get("reason");
  const bannerMessage = reason ? reasonMessages[reason] : null;

  async function submitLogin() {
    setErrorMessage(null);
    setIsSubmitting(true);

    try {
      await login({ email, password });
      window.location.assign(nextPath);
    } catch (error) {
      setErrorMessage(getErrorMessage(error, "Unable to sign in."));
    } finally {
      setIsSubmitting(false);
    }
  }

  function handleSubmit(event: React.FormEvent<HTMLFormElement>) {
    event.preventDefault();
    void submitLogin();
  }

  return (
    <GuestOnlyRoute fallbackPath="/dashboard">
      <AuthShell>
        <Card className="border-0 bg-transparent shadow-none">
          <CardHeader className="px-0 pt-0">
            <CardTitle className="text-4xl sm:text-[2.7rem]">Welcome back</CardTitle>
            <CardDescription className="text-base">Sign in to your account</CardDescription>
          </CardHeader>

          <CardContent className="px-0 pb-0">
            {bannerMessage ? (
              <div className="border-accent/25 bg-accent/10 text-foreground mb-4 rounded-2xl border px-4 py-3 text-sm">
                {bannerMessage}
              </div>
            ) : null}

            {errorMessage ? (
              <div className="border-destructive/30 bg-destructive/10 text-destructive mb-4 rounded-2xl border px-4 py-3 text-sm">
                {errorMessage}
              </div>
            ) : null}

            <form className="space-y-5" onSubmit={handleSubmit}>
              <div className="space-y-2">
                <Label htmlFor="email">Email</Label>
                <AuthInput
                  autoComplete="email"
                  icon={<Mail className="size-[1.05rem]" />}
                  id="email"
                  name="email"
                  onChange={(event) => setEmail(event.target.value)}
                  placeholder="you@example.com"
                  type="email"
                  value={email}
                />
              </div>

              <div className="space-y-2">
                <Label htmlFor="password">Password</Label>
                <AuthInput
                  autoComplete="current-password"
                  icon={<LockKeyhole className="size-[1.05rem]" />}
                  id="password"
                  name="password"
                  onChange={(event) => setPassword(event.target.value)}
                  placeholder="Enter your password"
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
                  value={password}
                />
              </div>

              <div className="flex items-center justify-between gap-3 text-sm">
                <label className="text-muted-foreground flex items-center gap-2">
                  <Checkbox aria-label="Remember me" />
                  <span>Remember me</span>
                </label>
                <button
                  className="text-accent font-medium transition-opacity hover:opacity-80"
                  type="button"
                >
                  Forgot password?
                </button>
              </div>

              <Button
                className="h-12 w-full rounded-2xl text-sm font-semibold"
                disabled={isSubmitting}
              >
                {isSubmitting ? "Signing in..." : "Sign In"}
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
              <a href={getGoogleLoginUrl("login")} rel="noreferrer">
                <GoogleIcon />
                Continue with Google
              </a>
            </Button>

            <p className="text-muted-foreground mt-6 text-center text-sm">
              Don&apos;t have an account?{" "}
              <Link className="text-accent font-semibold hover:underline" href="/register">
                Sign Up
              </Link>
            </p>
          </CardContent>
        </Card>
      </AuthShell>
    </GuestOnlyRoute>
  );
}
