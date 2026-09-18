"use client";

import { useState, useEffect } from "react";
import { useRouter, useSearchParams } from "next/navigation";
import Link from "next/link";
import Image from "next/image";
import {
  Lock,
  Eye,
  EyeOff,
  ArrowRight,
  ArrowLeft,
  AlertCircle,
  ShieldCheck,
  Check,
  XCircle,
} from "lucide-react";
import { api, ApiError } from "@/lib/api";

export const dynamic = "force-dynamic";

export default function ResetPasswordPage() {
  const router = useRouter();
  const searchParams = useSearchParams();
  const token = searchParams?.get("token");

  const [newPassword, setNewPassword] = useState("");
  const [confirmPassword, setConfirmPassword] = useState("");
  const [showNewPassword, setShowNewPassword] = useState(false);
  const [showConfirmPassword, setShowConfirmPassword] = useState(false);
  const [loading, setLoading] = useState(false);
  const [verifying, setVerifying] = useState(true);
  const [validToken, setValidToken] = useState(false);
  const [error, setError] = useState("");
  const [validationErrors, setValidationErrors] = useState({
    password: "",
    confirmPassword: "",
  });

  useEffect(() => {
    const verifyToken = async () => {
      if (!token) {
        setError("Missing or invalid password reset token.");
        setVerifying(false);
        return;
      }

      try {
        await api.get(`/api/auth/verify-reset-token/${token}`);
        setValidToken(true);
      } catch (err) {
        setError("This password reset link is invalid or has already expired.");
      } finally {
        setVerifying(false);
      }
    };

    verifyToken();
  }, [token]);

  const passwordChecks = {
    length: newPassword.length >= 8,
    uppercase: /[A-Z]/.test(newPassword),
    lowercase: /[a-z]/.test(newPassword),
    number: /[0-9]/.test(newPassword),
  };

  const validatePassword = (password: string) => {
    if (password.length < 8) {
      setValidationErrors((prev) => ({
        ...prev,
        password: "Password must be at least 8 characters long",
      }));
      return false;
    }
    if (!/[A-Z]/.test(password)) {
      setValidationErrors((prev) => ({
        ...prev,
        password: "Password must contain at least one uppercase letter",
      }));
      return false;
    }
    if (!/[a-z]/.test(password)) {
      setValidationErrors((prev) => ({
        ...prev,
        password: "Password must contain at least one lowercase letter",
      }));
      return false;
    }
    if (!/[0-9]/.test(password)) {
      setValidationErrors((prev) => ({
        ...prev,
        password: "Password must contain at least one number",
      }));
      return false;
    }
    setValidationErrors((prev) => ({ ...prev, password: "" }));
    return true;
  };

  const handleSubmit = async (e: React.FormEvent<HTMLFormElement>) => {
    e.preventDefault();
    setError("");
    setValidationErrors({ password: "", confirmPassword: "" });

    const isPasswordValid = validatePassword(newPassword);

    if (newPassword !== confirmPassword) {
      setValidationErrors((prev) => ({
        ...prev,
        confirmPassword: "Passwords do not match",
      }));
      return;
    }

    if (!isPasswordValid) {
      return;
    }

    setLoading(true);

    try {
      await api.post("/api/auth/reset-password", {
        token,
        new_password: newPassword,
      });

      router.push("/login?reset=success");
    } catch (err) {
      if (err instanceof ApiError) {
        setError(err.message);
      } else {
        setError("Failed to reset password. Please try again.");
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
          Create new password
        </h1>
        <p className="mt-2 text-sm text-slate-600">
          Enter a secure replacement password for your account
        </p>
      </div>

      {/* Main card */}
      <div className="mt-8 sm:mx-auto sm:w-full sm:max-w-md px-4 sm:px-0">
        <div className="bg-white py-8 px-6 sm:px-10 rounded-2xl border border-slate-200/80 shadow-xl shadow-slate-200/40 space-y-6">
          {verifying ? (
            <div className="py-8 text-center space-y-4">
              <div className="w-10 h-10 border-3 border-[#03AD8C]/30 border-t-[#03AD8C] rounded-full animate-spin mx-auto" />
              <p className="text-xs font-medium text-slate-600">
                Verifying password reset authorization token...
              </p>
            </div>
          ) : !validToken ? (
            <div className="text-center space-y-5">
              <div className="mx-auto flex items-center justify-center h-14 w-14 rounded-2xl bg-rose-50 border border-rose-200 text-rose-600 shadow-sm">
                <XCircle className="h-7 w-7" />
              </div>
              <div>
                <h2 className="text-xl font-bold text-slate-900">Invalid Link</h2>
                <p className="mt-2 text-xs text-slate-600 leading-relaxed">
                  {error || "This reset token is invalid, expired, or has already been used."}
                </p>
              </div>
              <div className="pt-2">
                <Link
                  href="/forgot-password"
                  className="w-full flex items-center justify-center py-2.5 px-4 rounded-xl shadow-md shadow-[#03AD8C]/25 text-sm font-semibold text-white bg-[#03AD8C] hover:bg-[#028f74] focus:outline-none focus:ring-4 focus:ring-[#03AD8C]/20 transition-all gap-2"
                >
                  <ArrowLeft className="w-4 h-4" />
                  <span>Request New Reset Link</span>
                </Link>
              </div>
            </div>
          ) : (
            <>
              {error && (
                <div className="p-4 rounded-xl bg-rose-50 border border-rose-200 text-rose-700 text-sm flex items-start gap-3">
                  <AlertCircle className="w-5 h-5 text-rose-600 flex-shrink-0 mt-0.5" />
                  <p className="flex-1 text-xs leading-relaxed font-medium">{error}</p>
                </div>
              )}

              <form className="space-y-4" onSubmit={handleSubmit}>
                <div>
                  <label
                    htmlFor="newPassword"
                    className="block text-xs font-semibold uppercase tracking-wider text-slate-700 mb-1.5"
                  >
                    New Password
                  </label>
                  <div className="relative rounded-xl shadow-sm">
                    <div className="absolute inset-y-0 left-0 pl-3.5 flex items-center pointer-events-none">
                      <Lock className="h-4 w-4 text-slate-400" />
                    </div>
                    <input
                      id="newPassword"
                      name="newPassword"
                      type={showNewPassword ? "text" : "password"}
                      required
                      disabled={loading}
                      value={newPassword}
                      onChange={(e) => {
                        setNewPassword(e.target.value);
                        validatePassword(e.target.value);
                      }}
                      className={`block w-full pl-10 pr-10 py-2.5 rounded-xl border ${
                        validationErrors.password ? "border-rose-300 ring-1 ring-rose-300" : "border-slate-200"
                      } bg-white text-slate-900 placeholder:text-slate-400 text-sm focus:outline-none focus:border-[#03AD8C] focus:ring-4 focus:ring-[#03AD8C]/15 transition-all disabled:opacity-60 disabled:cursor-not-allowed`}
                      placeholder="Enter new password"
                    />
                    <button
                      type="button"
                      onClick={() => setShowNewPassword(!showNewPassword)}
                      className="absolute inset-y-0 right-0 pr-3.5 flex items-center text-slate-400 hover:text-slate-600 transition-colors"
                      aria-label={showNewPassword ? "Hide password" : "Show password"}
                    >
                      {showNewPassword ? <EyeOff className="h-4 w-4" /> : <Eye className="h-4 w-4" />}
                    </button>
                  </div>
                  {validationErrors.password && (
                    <p className="mt-1 text-xs text-rose-600">{validationErrors.password}</p>
                  )}

                  {/* Password Requirement Checklist Pills */}
                  <div className="mt-2.5 grid grid-cols-2 gap-1.5 text-[11px]">
                    <div
                      className={`flex items-center gap-1.5 px-2 py-1 rounded-md transition-colors ${
                        passwordChecks.length
                          ? "bg-emerald-50 text-emerald-700 border border-emerald-200/60 font-medium"
                          : "bg-slate-50 text-slate-500 border border-slate-200/50"
                      }`}
                    >
                      <Check className={`w-3 h-3 ${passwordChecks.length ? "text-emerald-600" : "text-slate-300"}`} />
                      <span>8+ characters</span>
                    </div>
                    <div
                      className={`flex items-center gap-1.5 px-2 py-1 rounded-md transition-colors ${
                        passwordChecks.uppercase
                          ? "bg-emerald-50 text-emerald-700 border border-emerald-200/60 font-medium"
                          : "bg-slate-50 text-slate-500 border border-slate-200/50"
                      }`}
                    >
                      <Check className={`w-3 h-3 ${passwordChecks.uppercase ? "text-emerald-600" : "text-slate-300"}`} />
                      <span>Uppercase letter</span>
                    </div>
                    <div
                      className={`flex items-center gap-1.5 px-2 py-1 rounded-md transition-colors ${
                        passwordChecks.lowercase
                          ? "bg-emerald-50 text-emerald-700 border border-emerald-200/60 font-medium"
                          : "bg-slate-50 text-slate-500 border border-slate-200/50"
                      }`}
                    >
                      <Check className={`w-3 h-3 ${passwordChecks.lowercase ? "text-emerald-600" : "text-slate-300"}`} />
                      <span>Lowercase letter</span>
                    </div>
                    <div
                      className={`flex items-center gap-1.5 px-2 py-1 rounded-md transition-colors ${
                        passwordChecks.number
                          ? "bg-emerald-50 text-emerald-700 border border-emerald-200/60 font-medium"
                          : "bg-slate-50 text-slate-500 border border-slate-200/50"
                      }`}
                    >
                      <Check className={`w-3 h-3 ${passwordChecks.number ? "text-emerald-600" : "text-slate-300"}`} />
                      <span>At least 1 number</span>
                    </div>
                  </div>
                </div>

                <div>
                  <label
                    htmlFor="confirmPassword"
                    className="block text-xs font-semibold uppercase tracking-wider text-slate-700 mb-1.5"
                  >
                    Confirm Password
                  </label>
                  <div className="relative rounded-xl shadow-sm">
                    <div className="absolute inset-y-0 left-0 pl-3.5 flex items-center pointer-events-none">
                      <Lock className="h-4 w-4 text-slate-400" />
                    </div>
                    <input
                      id="confirmPassword"
                      name="confirmPassword"
                      type={showConfirmPassword ? "text" : "password"}
                      required
                      disabled={loading}
                      value={confirmPassword}
                      onChange={(e) => setConfirmPassword(e.target.value)}
                      className={`block w-full pl-10 pr-10 py-2.5 rounded-xl border ${
                        validationErrors.confirmPassword ? "border-rose-300 ring-1 ring-rose-300" : "border-slate-200"
                      } bg-white text-slate-900 placeholder:text-slate-400 text-sm focus:outline-none focus:border-[#03AD8C] focus:ring-4 focus:ring-[#03AD8C]/15 transition-all disabled:opacity-60 disabled:cursor-not-allowed`}
                      placeholder="Repeat new password"
                    />
                    <button
                      type="button"
                      onClick={() => setShowConfirmPassword(!showConfirmPassword)}
                      className="absolute inset-y-0 right-0 pr-3.5 flex items-center text-slate-400 hover:text-slate-600 transition-colors"
                      aria-label={showConfirmPassword ? "Hide password" : "Show password"}
                    >
                      {showConfirmPassword ? <EyeOff className="h-4 w-4" /> : <Eye className="h-4 w-4" />}
                    </button>
                  </div>
                  {validationErrors.confirmPassword && (
                    <p className="mt-1 text-xs text-rose-600">{validationErrors.confirmPassword}</p>
                  )}
                </div>

                <div className="pt-2">
                  <button
                    type="submit"
                    disabled={loading}
                    className="w-full flex items-center justify-center py-2.5 px-4 rounded-xl shadow-md shadow-[#03AD8C]/25 text-sm font-semibold text-white bg-[#03AD8C] hover:bg-[#028f74] focus:outline-none focus:ring-4 focus:ring-[#03AD8C]/20 disabled:opacity-50 disabled:cursor-not-allowed transition-all gap-2"
                  >
                    {loading ? (
                      <>
                        <div className="w-4 h-4 border-2 border-white/30 border-t-white rounded-full animate-spin" />
                        <span>Updating password...</span>
                      </>
                    ) : (
                      <>
                        <span>Reset Password</span>
                        <ArrowRight className="w-4 h-4" />
                      </>
                    )}
                  </button>
                </div>
              </form>

              <div className="pt-4 border-t border-slate-100 text-center">
                <Link
                  href="/login"
                  className="inline-flex items-center gap-1.5 text-xs font-semibold text-slate-600 hover:text-[#03AD8C] transition-colors"
                >
                  <ArrowLeft className="w-3.5 h-3.5" />
                  <span>Back to Sign In</span>
                </Link>
              </div>
            </>
          )}
        </div>

        {/* Security badge footer */}
        <div className="mt-6 flex items-center justify-center gap-2 text-xs text-slate-400">
          <ShieldCheck className="w-4 h-4 text-[#03AD8C]" />
          <span>Secure Password Update via PBKDF2 / Argon2</span>
        </div>
      </div>
    </main>
  );
}
