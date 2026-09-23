"use client";

import React, { useState } from "react";
import { useRouter } from "next/navigation";
import Link from "next/link";
import { ArrowLeft, Database, Plus, RefreshCw, Sparkles } from "lucide-react";
import DashboardLayout from "@/components/layout/dashboard-layout";
import { api, ApiError } from "@/lib/api";
import { useToast } from "@/components/ui/use-toast";
import { Button } from "@/components/ui/button";

export default function NewKnowledgeBasePage() {
  const router = useRouter();
  const [error, setError] = useState("");
  const [isSubmitting, setIsSubmitting] = useState(false);
  const { toast } = useToast();

  const handleSubmit = async (e: React.FormEvent<HTMLFormElement>) => {
    e.preventDefault();
    setError("");
    setIsSubmitting(true);

    try {
      const formData = new FormData(e.currentTarget);
      const name = formData.get("name") as string;
      const description = formData.get("description") as string;

      const data = await api.post("/api/knowledge-base", {
        name,
        description,
      });

      toast({
        title: "Knowledge Base Created",
        description: `Successfully created "${name}". Redirecting to upload documents...`,
      });

      router.push(`/dashboard/knowledge/${data.id}`);
    } catch (err) {
      console.error("Failed to create knowledge base:", err);
      if (err instanceof ApiError) {
        setError(err.message);
        toast({
          title: "Creation Error",
          description: err.message,
          variant: "destructive",
        });
      } else {
        setError("Failed to create knowledge base. Please try again.");
      }
    } finally {
      setIsSubmitting(false);
    }
  };

  return (
    <DashboardLayout>
      <div className="max-w-2xl mx-auto space-y-6 pb-12">
        {/* Back Link */}
        <div>
          <Link
            href="/dashboard/knowledge"
            className="inline-flex items-center text-xs font-medium text-muted-foreground hover:text-foreground transition-colors gap-1.5"
          >
            <ArrowLeft className="h-3.5 w-3.5" />
            Back to Knowledge Bases
          </Link>
        </div>

        {/* Card Container */}
        <div className="rounded-xl border border-border/70 bg-card/70 backdrop-blur-xl p-8 shadow-sm space-y-6">
          <div className="space-y-1.5 border-b border-border/60 pb-5">
            <div className="flex items-center gap-2.5">
              <div className="p-2 rounded-lg bg-primary/10 text-primary">
                <Database className="h-5 w-5" />
              </div>
              <h1 className="text-2xl font-bold tracking-tight text-foreground">
                Create Knowledge Base
              </h1>
            </div>
            <p className="text-sm text-muted-foreground">
              Configure a new vector repository to ingest documents for semantic RAG querying.
            </p>
          </div>

          <form onSubmit={handleSubmit} className="space-y-6">
            <div className="space-y-2">
              <label
                htmlFor="name"
                className="text-sm font-semibold text-foreground"
              >
                Repository Name <span className="text-destructive">*</span>
              </label>
              <input
                id="name"
                name="name"
                type="text"
                required
                className="flex h-10 w-full rounded-lg border border-input bg-background/80 px-3.5 py-2 text-sm ring-offset-background placeholder:text-muted-foreground focus:outline-none focus:ring-2 focus:ring-primary/20 focus:border-primary transition-all disabled:opacity-50"
                placeholder="e.g. UNEP Climate Policy Index, Product Technical Specs"
              />
              <p className="text-xs text-muted-foreground">
                A concise and descriptive title for this knowledge base.
              </p>
            </div>

            <div className="space-y-2">
              <label
                htmlFor="description"
                className="text-sm font-semibold text-foreground"
              >
                Description
              </label>
              <textarea
                id="description"
                name="description"
                rows={3}
                className="flex min-h-[90px] w-full rounded-lg border border-input bg-background/80 px-3.5 py-2 text-sm ring-offset-background placeholder:text-muted-foreground focus:outline-none focus:ring-2 focus:ring-primary/20 focus:border-primary transition-all disabled:opacity-50"
                placeholder="Explain what topics or document types are indexed in this repository..."
              />
              <p className="text-xs text-muted-foreground">
                Optional overview explaining the domain and contents.
              </p>
            </div>

            {error && (
              <div className="p-3 rounded-lg bg-destructive/10 border border-destructive/20 text-destructive text-sm">
                {error}
              </div>
            )}

            <div className="flex items-center justify-end gap-3 pt-4 border-t border-border/60">
              <Button
                type="button"
                variant="outline"
                onClick={() => router.back()}
                disabled={isSubmitting}
              >
                Cancel
              </Button>
              <Button
                type="submit"
                disabled={isSubmitting}
                className="gap-1.5 bg-primary text-primary-foreground hover:bg-primary/90"
              >
                {isSubmitting ? (
                  <>
                    <RefreshCw className="h-4 w-4 animate-spin" />
                    Creating Repository...
                  </>
                ) : (
                  <>
                    <Plus className="h-4 w-4" />
                    Create Knowledge Base
                  </>
                )}
              </Button>
            </div>
          </form>
        </div>
      </div>
    </DashboardLayout>
  );
}
