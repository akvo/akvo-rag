"use client";

import { useState } from "react";
import Link from "next/link";
import Image from "next/image";
import {
  Mail,
  ArrowRight,
  ArrowLeft,
  CheckCircle2,
  AlertCircle,
  ShieldCheck,
} from "lucide-react";
import { api, ApiError } from "@/lib/api";

export default function ForgotPasswordPage() {
  const [email, setEmail] = useState("");
  const [loading, setLoading] = useState(false);
  const [success, setSuccess] = useState(false);
  const [error, setError] = useState("");

  const handleSubmit = async (e: React.FormEvent<HTMLFormElement>) => {
    e.preventDefault();
    setError("");
    setLoading(true);

    try {
      await api.post("/api/auth/forgot-password", { email });
      setSuccess(true);
    } catch (err) {
      if (err instanceof ApiError) {
        setError(err.message);
      } else {
        setError("Failed to send reset email. Please try again later.");
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
          Reset password
        </h1>
        <p className="mt-2 text-sm text-slate-600">
          Enter your registered email address to receive password recovery instructions
        </p>
      </div>

      {/* Main card */}
      <div className="mt-8 sm:mx-auto sm:w-full sm:max-w-md px-4 sm:px-0">
        <div className="bg-white py-8 px-6 sm:px-10 rounded-2xl border border-slate-200/80 shadow-xl shadow-slate-200/40 space-y-6">
          {success ? (
            <div className="text-center space-y-5">
              <div className="mx-auto flex items-center justify-center h-14 w-14 rounded-2xl bg-emerald-50 border border-emerald-200 text-emerald-600 shadow-sm">
                <CheckCircle2 className="h-7 w-7" />
              </div>
              <div>
                <h2 className="text-xl font-bold text-slate-900">Check Your Inbox</h2>
                <p className="mt-2 text-xs text-slate-600 leading-relaxed">
                  If an account exists with <strong className="text-slate-900">{email}</strong>, you will receive a secure password reset link shortly.
                </p>
              </div>
              <div className="pt-2">
                <Link
                  href="/login"
                  className="w-full flex items-center justify-center py-2.5 px-4 rounded-xl shadow-md shadow-[#03AD8C]/25 text-sm font-semibold text-white bg-[#03AD8C] hover:bg-[#028f74] focus:outline-none focus:ring-4 focus:ring-[#03AD8C]/20 transition-all gap-2"
                >
                  <ArrowLeft className="w-4 h-4" />
                  <span>Return to Sign In</span>
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

              <form className="space-y-5" onSubmit={handleSubmit}>
                <div>
                  <label
                    htmlFor="email"
                    className="block text-xs font-semibold uppercase tracking-wider text-slate-700 mb-1.5"
                  >
                    Email Address
                  </label>
                  <div className="relative rounded-xl shadow-sm">
                    <div className="absolute inset-y-0 left-0 pl-3.5 flex items-center pointer-events-none">
                      <Mail className="h-4 w-4 text-slate-400" />
                    </div>
                    <input
                      id="email"
                      name="email"
                      type="email"
                      required
                      disabled={loading}
                      value={email}
                      onChange={(e) => setEmail(e.target.value)}
                      className="block w-full pl-10 pr-3.5 py-2.5 rounded-xl border border-slate-200 bg-white text-slate-900 placeholder:text-slate-400 text-sm focus:outline-none focus:border-[#03AD8C] focus:ring-4 focus:ring-[#03AD8C]/15 transition-all disabled:opacity-60 disabled:cursor-not-allowed"
                      placeholder="name@company.com"
                    />
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
                      <span>Sending reset link...</span>
                    </>
                  ) : (
                    <>
                      <span>Send Reset Link</span>
                      <ArrowRight className="w-4 h-4" />
                    </>
                  )}
                </button>
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
          <span>Single-Use Cryptographic Reset Tokens</span>
        </div>
      </div>
    </main>
  );
}
