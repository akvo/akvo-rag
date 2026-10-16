"use client";

import { useState } from "react";
import { useRouter, useSearchParams } from "next/navigation";
import Link from "next/link";
import Image from "next/image";
import {
  User,
  Lock,
  Eye,
  EyeOff,
  ArrowRight,
  CheckCircle2,
  AlertCircle,
  X,
  ShieldCheck,
} from "lucide-react";
import { api, ApiError } from "@/lib/api";
import { useUser } from "@/contexts/userContext";

export const dynamic = "force-dynamic";

interface LoginResponse {
  access_token: string;
  token_type: string;
}

export default function LoginPage() {
  const router = useRouter();
  const searchParams = useSearchParams();
  const [error, setError] = useState("");
  const [loading, setLoading] = useState(false);
  const [showPassword, setShowPassword] = useState(false);
  const { isNewUser, setIsNewUser } = useUser();
  const [showResetSuccess, setShowResetSuccess] = useState(
    searchParams?.get("reset") === "success"
  );

  const handleSubmit = async (e: React.FormEvent<HTMLFormElement>) => {
    e.preventDefault();
    setError("");
    setLoading(true);

    const formData = new FormData(e.currentTarget);
    const username = formData.get("username");
    const password = formData.get("password");

    try {
      const formUrlEncoded = new URLSearchParams();
      formUrlEncoded.append("username", username as string);
      formUrlEncoded.append("password", password as string);

      const data: LoginResponse = await api.post("/api/auth/token", formUrlEncoded, {
        headers: {
          "Content-Type": "application/x-www-form-urlencoded",
        },
      });

      localStorage.setItem("token", data.access_token);
      router.push("/dashboard");
    } catch (err) {
      setIsNewUser(false);
      if (err instanceof ApiError) {
        setError(err.message);
      } else {
        setError("Login failed. Please verify your credentials and try again.");
      }
    } finally {
      setLoading(false);
    }
  };

  return (
    <main className="min-h-screen bg-white text-slate-900 flex flex-col justify-center py-12 sm:px-6 lg:px-8 relative selection:bg-[#03AD8C] selection:text-white overflow-hidden">
      {/* Ambient background light gradients */}
      <div className="absolute top-0 left-1/2 -translate-x-1/2 w-[800px] h-[400px] bg-gradient-to-b from-[#03AD8C]/10 via-teal-50/30 to-transparent blur-[100px] pointer-events-none -z-10" />
      <div className="absolute bottom-0 right-0 w-[450px] h-[450px] bg-gradient-to-tl from-slate-100/80 via-[#03AD8C]/5 to-transparent blur-[120px] pointer-events-none -z-10" />

      {/* Top brand container */}
      <div className="sm:mx-auto sm:w-full sm:max-w-md text-center px-4">
        <Link href="/" className="inline-flex items-center gap-2.5 mb-6 group">
          <Image
            src="/logo.svg"
            alt="Akvo Logo"
            width={40}
            height={40}
            className="w-10 h-10 rounded-xl shadow-sm group-hover:scale-105 transition-transform"
            priority
          />
          <div className="text-left">
            <span className="font-bold text-xl text-slate-900 tracking-tight block">
              Akvo RAG
            </span>
            <span className="text-[10px] font-semibold text-[#027a63] tracking-wider uppercase block">
              Enterprise Dialogue Platform
            </span>
          </div>
        </Link>
        <h1 className="text-2xl sm:text-3xl font-extrabold text-slate-900 tracking-tight">
          Welcome back
        </h1>
        <p className="mt-2 text-sm text-slate-600">
          Sign in to access your knowledge bases and AI workspaces
        </p>
      </div>

      {/* Main card */}
      <div className="mt-8 sm:mx-auto sm:w-full sm:max-w-md px-4 sm:px-0">
        <div className="bg-white py-8 px-6 sm:px-10 rounded-2xl border border-slate-200/80 shadow-xl shadow-slate-200/40 space-y-6">
          {/* New User Banner */}
          {isNewUser && (
            <div className="p-4 rounded-xl bg-emerald-50 border border-emerald-200/80 text-emerald-800 text-sm flex items-start gap-3">
              <CheckCircle2 className="w-5 h-5 text-emerald-600 flex-shrink-0 mt-0.5" />
              <div className="flex-1">
                <p className="font-medium text-emerald-900">Account Created!</p>
                <p className="text-xs text-emerald-700 mt-0.5">
                  Your account has been registered. Please contact your administrator to activate workspace access.
                </p>
              </div>
              <button
                type="button"
                className="text-emerald-700 hover:text-emerald-900"
                onClick={() => setIsNewUser(false)}
                aria-label="Dismiss message"
              >
                <X className="w-4 h-4" />
              </button>
            </div>
          )}

          {/* Reset Success Banner */}
          {showResetSuccess && (
            <div className="p-4 rounded-xl bg-emerald-50 border border-emerald-200/80 text-emerald-800 text-sm flex items-start gap-3">
              <CheckCircle2 className="w-5 h-5 text-emerald-600 flex-shrink-0 mt-0.5" />
              <div className="flex-1">
                <p className="font-medium text-emerald-900">Password Reset Successful</p>
                <p className="text-xs text-emerald-700 mt-0.5">
                  You can now sign in using your new credentials.
                </p>
              </div>
              <button
                type="button"
                className="text-emerald-700 hover:text-emerald-900"
                onClick={() => setShowResetSuccess(false)}
                aria-label="Dismiss message"
              >
                <X className="w-4 h-4" />
              </button>
            </div>
          )}

          {/* Error Banner */}
          {error && (
            <div className="p-4 rounded-xl bg-rose-50 border border-rose-200 text-rose-700 text-sm flex items-start gap-3">
              <AlertCircle className="w-5 h-5 text-rose-600 flex-shrink-0 mt-0.5" />
              <p className="flex-1 text-xs leading-relaxed font-medium">{error}</p>
            </div>
          )}

          {/* Login Form */}
          <form className="space-y-5" onSubmit={handleSubmit}>
            <div>
              <label
                htmlFor="username"
                className="block text-xs font-semibold uppercase tracking-wider text-slate-700 mb-1.5"
              >
                Username
              </label>
              <div className="relative rounded-xl shadow-sm">
                <div className="absolute inset-y-0 left-0 pl-3.5 flex items-center pointer-events-none">
                  <User className="h-4 w-4 text-slate-400" />
                </div>
                <input
                  id="username"
                  name="username"
                  type="text"
                  required
                  disabled={loading}
                  className="block w-full pl-10 pr-3.5 py-2.5 rounded-xl border border-slate-200 bg-white text-slate-900 placeholder:text-slate-400 text-sm focus:outline-none focus:border-[#03AD8C] focus:ring-4 focus:ring-[#03AD8C]/15 transition-all disabled:opacity-60 disabled:cursor-not-allowed"
                  placeholder="Enter your username"
                />
              </div>
            </div>

            <div>
              <div className="flex items-center justify-between mb-1.5">
                <label
                  htmlFor="password"
                  className="block text-xs font-semibold uppercase tracking-wider text-slate-700"
                >
                  Password
                </label>
                <Link
                  href="/forgot-password"
                  className="text-xs font-medium text-slate-600 hover:text-[#03AD8C] transition-colors"
                >
                  Forgot password?
                </Link>
              </div>
              <div className="relative rounded-xl shadow-sm">
                <div className="absolute inset-y-0 left-0 pl-3.5 flex items-center pointer-events-none">
                  <Lock className="h-4 w-4 text-slate-400" />
                </div>
                <input
                  id="password"
                  name="password"
                  type={showPassword ? "text" : "password"}
                  required
                  disabled={loading}
                  className="block w-full pl-10 pr-10 py-2.5 rounded-xl border border-slate-200 bg-white text-slate-900 placeholder:text-slate-400 text-sm focus:outline-none focus:border-[#03AD8C] focus:ring-4 focus:ring-[#03AD8C]/15 transition-all disabled:opacity-60 disabled:cursor-not-allowed"
                  placeholder="Enter your password"
                />
                <button
                  type="button"
                  onClick={() => setShowPassword(!showPassword)}
                  className="absolute inset-y-0 right-0 pr-3.5 flex items-center text-slate-400 hover:text-slate-600 transition-colors"
                  aria-label={showPassword ? "Hide password" : "Show password"}
                >
                  {showPassword ? (
                    <EyeOff className="h-4 w-4" />
                  ) : (
                    <Eye className="h-4 w-4" />
                  )}
                </button>
              </div>
            </div>

            <button
              type="submit"
              disabled={loading}
              className="w-full flex items-center justify-center py-2.5 px-4 rounded-xl shadow-md shadow-[#03AD8C]/25 text-sm font-semibold text-white bg-[#03AD8C] hover:bg-[#028f74] focus:outline-none focus:ring-4 focus:ring-[#03AD8C]/20 disabled:opacity-50 disabled:cursor-not-allowed transition-all gap-2"
            >
              {loading ? (
                <>
                  <div className="w-4 h-4 border-2 border-white/30 border-t-white rounded-full animate-spin" />
                  <span>Signing in...</span>
                </>
              ) : (
                <>
                  <span>Sign in</span>
                  <ArrowRight className="w-4 h-4" />
                </>
              )}
            </button>
          </form>

          {/* Switch to Register */}
          <div className="pt-4 border-t border-slate-100 text-center">
            <p className="text-xs text-slate-600">
              Don&apos;t have an account?{" "}
              <Link
                href="/register"
                className="font-semibold text-[#03AD8C] hover:text-[#028f74] hover:underline transition-colors"
              >
                Create one now
              </Link>
            </p>
          </div>
        </div>

        {/* Security badge footer */}
        <div className="mt-6 flex items-center justify-center gap-2 text-xs text-slate-400">
          <ShieldCheck className="w-4 h-4 text-[#03AD8C]" />
          <span>Secured with AES-256 Token Encryption & Tenant Isolation</span>
        </div>
      </div>
    </main>
  );
}
