"use client";

import { motion, useReducedMotion } from "motion/react";

import Wordmark from "@/components/landing/Wordmark";
import { Button, Card } from "@/components/ui";
import { API_BASE } from "@/lib/api/base";
import { ease } from "@/lib/motion";

export default function SigninPage() {
  const reduced = useReducedMotion() ?? false;

  function handleSignIn() {
    // Hand off to the backend's Google OAuth flow; it redirects back to the app.
    window.location.href = `${API_BASE}/auth/google/login`;
  }

  return (
    <motion.div
      initial={reduced ? { opacity: 0 } : { opacity: 0, scale: 0.98 }}
      animate={reduced ? { opacity: 1 } : { opacity: 1, scale: 1 }}
      transition={{ duration: 0.25, ease: ease.out }}
      className="w-full max-w-[400px]"
    >
      <Card className="rounded-panel p-8">
        <div className="flex justify-center">
          <Wordmark />
        </div>
        <p className="mx-auto mt-4 max-w-[320px] text-center text-[14px] leading-[1.6] text-text-muted">
          Sign in to save your plans, build your skill profile, and get matched
          to jobs.
        </p>
        <Button
          size="lg"
          onClick={handleSignIn}
          leftIcon={<GoogleIcon />}
          className="mt-6 w-full"
        >
          Continue with Google
        </Button>
        <p className="mt-4 text-center text-[12px] text-text-muted">
          By continuing, you agree to our Terms and Privacy Policy.
        </p>
      </Card>
    </motion.div>
  );
}

function GoogleIcon() {
  return (
    <svg viewBox="0 0 18 18" xmlns="http://www.w3.org/2000/svg" aria-hidden>
      <path
        fill="#4285F4"
        d="M17.64 9.205c0-.639-.057-1.252-.164-1.841H9v3.481h4.844a4.14 4.14 0 0 1-1.796 2.716v2.259h2.908c1.702-1.567 2.684-3.875 2.684-6.615z"
      />
      <path
        fill="#34A853"
        d="M9 18c2.43 0 4.467-.806 5.956-2.18l-2.908-2.259c-.806.54-1.837.86-3.048.86-2.344 0-4.328-1.584-5.036-3.711H.957v2.332A8.997 8.997 0 0 0 9 18z"
      />
      <path
        fill="#FBBC05"
        d="M3.964 10.71A5.41 5.41 0 0 1 3.682 9c0-.593.102-1.17.282-1.71V4.958H.957A8.996 8.996 0 0 0 0 9c0 1.452.348 2.827.957 4.042l3.007-2.332z"
      />
      <path
        fill="#EA4335"
        d="M9 3.58c1.321 0 2.508.454 3.44 1.345l2.582-2.58C13.463.891 11.426 0 9 0A8.997 8.997 0 0 0 .957 4.958L3.964 7.29C4.672 5.163 6.656 3.58 9 3.58z"
      />
    </svg>
  );
}
