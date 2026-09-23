"use client";

import React, { useEffect, useState, useCallback } from "react";
import Link from "next/link";
import DashboardLayout from "@/components/layout/dashboard-layout";
import {
  MessageSquare,
  Database,
  Key,
  Sliders,
  Activity,
  Users,
  ArrowRight,
  Plus,
  Sparkles,
  Search,
  Layers,
  CheckCircle2,
  Shield,
  FileText,
  Clock,
  Compass,
} from "lucide-react";
import { api, ApiError } from "@/lib/api";
import { useUser } from "@/contexts/userContext";
import { Button } from "@/components/ui/button";

interface DashboardStats {
  knowledgeBases: number;
  chats: number;
  apps: number;
  systemHealthy: boolean;
}

export default function DashboardPage() {
  const { user } = useUser();
  const [stats, setStats] = useState<DashboardStats>({
    knowledgeBases: 0,
    chats: 0,
    apps: 0,
    systemHealthy: true,
  });
  const [loading, setLoading] = useState(true);

  const fetchDashboardData = useCallback(async () => {
    setLoading(true);
    try {
      const [kbRes, chatRes] = await Promise.allSettled([
        api.get("/api/knowledge-base"),
        api.get("/api/chat"),
      ]);

      const kbCount =
        kbRes.status === "fulfilled" && Array.isArray(kbRes.value)
          ? kbRes.value.length
          : 0;
      const chatCount =
        chatRes.status === "fulfilled" && Array.isArray(chatRes.value)
          ? chatRes.value.length
          : 0;

      let appCount = 0;
      if (user?.is_superuser) {
        try {
          const appData = await api.get("/api/apps");
          if (Array.isArray(appData)) {
            appCount = appData.length;
          }
        } catch {
          // Ignore if non-superuser or app endpoint error
        }
      }

      setStats({
        knowledgeBases: kbCount,
        chats: chatCount,
        apps: appCount,
        systemHealthy: true,
      });
    } catch (error) {
      console.error("Failed to fetch dashboard data:", error);
      if (error instanceof ApiError && error.status === 401) {
        return;
      }
    } finally {
      setLoading(false);
    }
  }, [user]);

  useEffect(() => {
    fetchDashboardData();
  }, [fetchDashboardData]);

  const platformModules = [
    {
      title: "AI Chat Workspace",
      description:
        "Engage in grounded conversations with citation drawers, KaTeX math rendering, and multi-knowledge base scoping.",
      href: "/dashboard/chat",
      icon: MessageSquare,
      color: "text-primary bg-primary/10 border-primary/20",
      cta: "Open Chat Canvas",
    },
    {
      title: "Knowledge Repositories",
      description:
        "Manage vector repositories, inspect extracted document chunks, and monitor asynchronous ingestion pipelines.",
      href: "/dashboard/knowledge",
      icon: Database,
      color: "text-emerald-600 dark:text-emerald-400 bg-emerald-500/10 border-emerald-500/20",
      cta: "Manage Repositories",
    },
    {
      title: "Semantic Vector Diagnostics",
      description:
        "Test cosine similarity retrieval, inspect top-matching chunks, and calibrate ranking thresholds.",
      href: stats.knowledgeBases > 0 ? `/dashboard/test-retrieval/1` : `/dashboard/knowledge`,
      icon: Sparkles,
      color: "text-amber-600 dark:text-amber-400 bg-amber-500/10 border-amber-500/20",
      cta: "Run Diagnostic Test",
    },
    {
      title: "Dynamic Prompt Studio",
      description:
        "Author centralized system prompts, test variable substitutions in live playground, and rollback versions.",
      href: "/dashboard/fine-tuning",
      icon: Sliders,
      color: "text-blue-600 dark:text-blue-400 bg-blue-500/10 border-blue-500/20",
      cta: "Open Prompt Studio",
    },
    {
      title: "Tenant Apps & API Keys",
      description:
        "Register external tenant applications, provision developer API keys, and enforce instant kill-switch access.",
      href: "/dashboard/api-keys",
      icon: Key,
      color: "text-violet-600 dark:text-violet-400 bg-violet-500/10 border-violet-500/20",
      cta: "Manage API Access",
    },
    {
      title: "Observability & Ragas Evals",
      description:
        "Monitor 7-container real-time health telemetry and evaluate RAG golden-set faithfulness and relevance scores.",
      href: "/dashboard/evaluations",
      icon: Activity,
      color: "text-rose-600 dark:text-rose-400 bg-rose-500/10 border-rose-500/20",
      cta: "View Telemetry & Evals",
    },
  ];

  return (
    <DashboardLayout>
      <div className="space-y-8 pb-12">
        {/* Hero Section */}
        <div className="relative overflow-hidden rounded-2xl border border-border/70 bg-card/70 backdrop-blur-xl p-8 shadow-sm">
          <div className="flex flex-col lg:flex-row lg:items-center justify-between gap-6 relative z-10">
            <div className="space-y-3">
              <div className="inline-flex items-center gap-2 px-3 py-1 rounded-full bg-primary/10 text-primary text-xs font-semibold border border-primary/20">
                <Compass className="h-3.5 w-3.5" />
                Akvo RAG Intelligence Platform
              </div>
              <h1 className="text-3xl sm:text-4xl font-bold tracking-tight text-foreground">
                Welcome back,{" "}
                <span className="bg-clip-text text-transparent bg-gradient-to-r from-primary via-emerald-600 to-teal-500 dark:from-primary dark:to-emerald-400">
                  {user?.username || "Researcher"}
                </span>
              </h1>
              <p className="text-sm sm:text-base text-muted-foreground max-w-2xl">
                Your unified hub for enterprise vector retrieval, grounded conversational AI,
                system telemetry, and tenant application governance.
              </p>
            </div>

            <div className="flex flex-wrap items-center gap-3 self-start lg:self-auto">
              <Link href="/dashboard/chat">
                <Button className="h-11 px-5 bg-primary text-primary-foreground hover:bg-primary/90 shadow-sm font-medium gap-2">
                  <MessageSquare className="h-4 w-4" />
                  New Chat Session
                </Button>
              </Link>
              <Link href="/dashboard/knowledge/new">
                <Button variant="outline" className="h-11 px-4 gap-2">
                  <Plus className="h-4 w-4" />
                  New Knowledge Base
                </Button>
              </Link>
            </div>
          </div>
        </div>

        {/* Real-time KPI Stats Grid */}
        <div className="grid grid-cols-2 md:grid-cols-4 gap-4">
          <div className="rounded-xl border border-border/70 bg-card/70 backdrop-blur-xl p-5 shadow-sm">
            <div className="flex items-center justify-between">
              <span className="text-xs font-medium text-muted-foreground uppercase tracking-wider">
                Knowledge Bases
              </span>
              <div className="p-2 rounded-md bg-emerald-500/10 text-emerald-600 dark:text-emerald-400">
                <Database className="h-4 w-4" />
              </div>
            </div>
            <div className="mt-3 flex items-baseline gap-2">
              <span className="text-2xl font-bold text-foreground">
                {loading ? "..." : stats.knowledgeBases}
              </span>
              <span className="text-xs text-muted-foreground">indexed stores</span>
            </div>
            <Link
              href="/dashboard/knowledge"
              className="mt-3 inline-flex items-center text-xs font-medium text-primary hover:underline gap-1"
            >
              Manage repositories <ArrowRight className="h-3 w-3" />
            </Link>
          </div>

          <div className="rounded-xl border border-border/70 bg-card/70 backdrop-blur-xl p-5 shadow-sm">
            <div className="flex items-center justify-between">
              <span className="text-xs font-medium text-muted-foreground uppercase tracking-wider">
                Chat Sessions
              </span>
              <div className="p-2 rounded-md bg-primary/10 text-primary">
                <MessageSquare className="h-4 w-4" />
              </div>
            </div>
            <div className="mt-3 flex items-baseline gap-2">
              <span className="text-2xl font-bold text-foreground">
                {loading ? "..." : stats.chats}
              </span>
              <span className="text-xs text-muted-foreground">conversations</span>
            </div>
            <Link
              href="/dashboard/chat"
              className="mt-3 inline-flex items-center text-xs font-medium text-primary hover:underline gap-1"
            >
              Resume chats <ArrowRight className="h-3 w-3" />
            </Link>
          </div>

          <div className="rounded-xl border border-border/70 bg-card/70 backdrop-blur-xl p-5 shadow-sm">
            <div className="flex items-center justify-between">
              <span className="text-xs font-medium text-muted-foreground uppercase tracking-wider">
                Tenant Apps
              </span>
              <div className="p-2 rounded-md bg-violet-500/10 text-violet-600 dark:text-violet-400">
                <Key className="h-4 w-4" />
              </div>
            </div>
            <div className="mt-3 flex items-baseline gap-2">
              <span className="text-2xl font-bold text-foreground">
                {loading ? "..." : stats.apps}
              </span>
              <span className="text-xs text-muted-foreground">registered apps</span>
            </div>
            <Link
              href="/dashboard/api-keys"
              className="mt-3 inline-flex items-center text-xs font-medium text-primary hover:underline gap-1"
            >
              API Key Portal <ArrowRight className="h-3 w-3" />
            </Link>
          </div>

          <div className="rounded-xl border border-border/70 bg-card/70 backdrop-blur-xl p-5 shadow-sm">
            <div className="flex items-center justify-between">
              <span className="text-xs font-medium text-muted-foreground uppercase tracking-wider">
                Infrastructure
              </span>
              <div className="p-2 rounded-md bg-blue-500/10 text-blue-600 dark:text-blue-400">
                <Activity className="h-4 w-4" />
              </div>
            </div>
            <div className="mt-3 flex items-baseline gap-2">
              <span className="inline-flex items-center gap-1.5 text-sm font-bold text-emerald-600 dark:text-emerald-400">
                <CheckCircle2 className="h-4 w-4" />
                Operational
              </span>
              <span className="text-xs text-muted-foreground">7 microservices</span>
            </div>
            <Link
              href="/dashboard/evaluations"
              className="mt-3 inline-flex items-center text-xs font-medium text-primary hover:underline gap-1"
            >
              View diagnostics <ArrowRight className="h-3 w-3" />
            </Link>
          </div>
        </div>

        {/* Platform Modules Launchpad */}
        <div className="space-y-4">
          <div className="flex items-center justify-between">
            <h2 className="text-xl font-bold tracking-tight text-foreground flex items-center gap-2">
              <Layers className="h-5 w-5 text-primary" />
              Platform Workspace & Tools
            </h2>
            <span className="text-xs text-muted-foreground">
              Select a module to launch workflow
            </span>
          </div>

          <div className="grid grid-cols-1 md:grid-cols-2 lg:grid-cols-3 gap-5">
            {platformModules.map((mod) => {
              const Icon = mod.icon;
              return (
                <div
                  key={mod.title}
                  className="group rounded-xl border border-border/70 bg-card/70 backdrop-blur-xl p-6 shadow-sm hover:shadow-md hover:border-primary/30 transition-all flex flex-col justify-between space-y-4"
                >
                  <div className="space-y-3">
                    <div className="flex items-center justify-between">
                      <div className={`p-2.5 rounded-xl border ${mod.color}`}>
                        <Icon className="h-5 w-5" />
                      </div>
                      <ArrowRight className="h-4 w-4 text-muted-foreground/50 group-hover:text-primary group-hover:translate-x-1 transition-all" />
                    </div>
                    <div className="space-y-1">
                      <h3 className="text-base font-bold text-foreground group-hover:text-primary transition-colors">
                        {mod.title}
                      </h3>
                      <p className="text-xs text-muted-foreground leading-relaxed">
                        {mod.description}
                      </p>
                    </div>
                  </div>

                  <Link href={mod.href} className="pt-2">
                    <Button
                      variant="secondary"
                      size="sm"
                      className="w-full text-xs font-medium group-hover:bg-primary group-hover:text-primary-foreground transition-all"
                    >
                      {mod.cta}
                    </Button>
                  </Link>
                </div>
              );
            })}
          </div>
        </div>

        {/* Getting Started / Architecture Guide */}
        <div className="rounded-xl border border-border/70 bg-card/70 backdrop-blur-xl p-6 shadow-sm space-y-5">
          <div className="flex items-center gap-2.5 border-b border-border/60 pb-4">
            <div className="p-2 rounded-lg bg-primary/10 text-primary">
              <Sparkles className="h-5 w-5" />
            </div>
            <div>
              <h3 className="text-lg font-bold text-foreground">
                RAG Retrieval & Generation Workflow
              </h3>
              <p className="text-xs text-muted-foreground">
                How document indexing, vector search, and grounded LLM generation work together
              </p>
            </div>
          </div>

          <div className="grid grid-cols-1 md:grid-cols-3 gap-4">
            <div className="p-4 rounded-lg bg-background/60 border border-border/50 space-y-2">
              <div className="flex items-center gap-2 text-xs font-bold text-primary uppercase tracking-wider">
                <span className="flex h-5 w-5 items-center justify-center rounded-full bg-primary/10 text-primary text-[11px]">
                  1
                </span>
                Document Ingestion
              </div>
              <h4 className="text-sm font-semibold text-foreground">
                Create & Ingest Documents
              </h4>
              <p className="text-xs text-muted-foreground leading-relaxed">
                Upload PDF, DOCX, Markdown, or Text files to dedicated knowledge bases. The MCP worker parses, chunks, and indexes embeddings into ChromaDB.
              </p>
              <Link
                href="/dashboard/knowledge/new"
                className="inline-flex items-center text-xs font-medium text-primary hover:underline gap-1 pt-1"
              >
                Create repository <ArrowRight className="h-3 w-3" />
              </Link>
            </div>

            <div className="p-4 rounded-lg bg-background/60 border border-border/50 space-y-2">
              <div className="flex items-center gap-2 text-xs font-bold text-emerald-600 dark:text-emerald-400 uppercase tracking-wider">
                <span className="flex h-5 w-5 items-center justify-center rounded-full bg-emerald-500/10 text-emerald-600 dark:text-emerald-400 text-[11px]">
                  2
                </span>
                Vector Diagnostics
              </div>
              <h4 className="text-sm font-semibold text-foreground">
                Validate Retrieval Quality
              </h4>
              <p className="text-xs text-muted-foreground leading-relaxed">
                Test query semantic similarity in the vector diagnostic suite to inspect cosine similarity scores, chunk boundaries, and token metrics.
              </p>
              <Link
                href="/dashboard/knowledge"
                className="inline-flex items-center text-xs font-medium text-primary hover:underline gap-1 pt-1"
              >
                Inspect chunks <ArrowRight className="h-3 w-3" />
              </Link>
            </div>

            <div className="p-4 rounded-lg bg-background/60 border border-border/50 space-y-2">
              <div className="flex items-center gap-2 text-xs font-bold text-violet-600 dark:text-violet-400 uppercase tracking-wider">
                <span className="flex h-5 w-5 items-center justify-center rounded-full bg-violet-500/10 text-violet-600 dark:text-violet-400 text-[11px]">
                  3
                </span>
                Conversational Synthesis
              </div>
              <h4 className="text-sm font-semibold text-foreground">
                Chat With Citations
              </h4>
              <p className="text-xs text-muted-foreground leading-relaxed">
                Initiate scoped dialogue sessions. Inspect exact source citations, page numbers, and math formulas with KaTeX typesetting.
              </p>
              <Link
                href="/dashboard/chat"
                className="inline-flex items-center text-xs font-medium text-primary hover:underline gap-1 pt-1"
              >
                Start chatting <ArrowRight className="h-3 w-3" />
              </Link>
            </div>
          </div>
        </div>
      </div>
    </DashboardLayout>
  );
}
