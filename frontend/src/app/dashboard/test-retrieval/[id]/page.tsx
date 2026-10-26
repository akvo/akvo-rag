"use client";

import React, { useState, useEffect, useCallback } from "react";
import Link from "next/link";
import {
  Search,
  ArrowLeft,
  Sparkles,
  Database,
  AlertCircle,
  FileText,
  Copy,
  Check,
  Hash,
  BookOpen,
  Layers,
  ChevronRight,
  ExternalLink,
} from "lucide-react";
import DashboardLayout from "@/components/layout/dashboard-layout";
import { Button } from "@/components/ui/button";
import { Input } from "@/components/ui/input";
import { useToast } from "@/components/ui/use-toast";
import { api, ApiError } from "@/lib/api";
import {
  Select,
  SelectContent,
  SelectItem,
  SelectTrigger,
  SelectValue,
} from "@/components/ui/select";

interface KnowledgeBase {
  id: number;
  name: string;
  description: string;
  documents?: any[];
}

interface RetrievalResult {
  chunk_id?: string;
  kb_id?: number;
  document_id?: string;
  content: string;
  score?: number;
  metadata?: {
    source?: string;
    filename?: string;
    page?: number;
    [key: string]: any;
  };
}

export default function TestRetrievalPage({ params }: { params: { id: string } }) {
  const [query, setQuery] = useState("");
  const [results, setResults] = useState<RetrievalResult[]>([]);
  const [hasSearched, setHasSearched] = useState(false);
  const [knowledgeBase, setKnowledgeBase] = useState<KnowledgeBase | null>(null);
  const [initialLoading, setInitialLoading] = useState(true);
  const [fetchError, setFetchError] = useState<string | null>(null);
  const [loading, setLoading] = useState(false);
  const [topK, setTopK] = useState("5");
  const [copiedIndex, setCopiedIndex] = useState<number | null>(null);

  const { toast } = useToast();

  const fetchKnowledgeBase = useCallback(async () => {
    setInitialLoading(true);
    setFetchError(null);
    try {
      const kbId = parseInt(params.id, 10);
      if (isNaN(kbId)) {
        throw new Error("Invalid Knowledge Base ID");
      }
      const data = await api.get(`/api/knowledge-base/${kbId}`);
      setKnowledgeBase(data);
    } catch (error) {
      const message =
        error instanceof ApiError
          ? error.message
          : error instanceof Error
          ? error.message
          : "Failed to fetch knowledge base";
      console.error("Failed to fetch knowledge base:", error);
      setFetchError(message);
      toast({
        title: "Error Loading Repository",
        description: message,
        variant: "destructive",
      });
    } finally {
      setInitialLoading(false);
    }
  }, [params.id, toast]);

  useEffect(() => {
    fetchKnowledgeBase();
  }, [fetchKnowledgeBase]);

  const handleTest = async (overrideQuery?: string) => {
    const q = (overrideQuery ?? query).trim();
    if (!q) {
      toast({
        title: "Query Required",
        description: "Please enter a search phrase to test semantic similarity.",
        variant: "destructive",
      });
      return;
    }

    const kbId = parseInt(params.id, 10);
    if (isNaN(kbId)) {
      toast({
        title: "Invalid ID",
        description: "Knowledge Base ID is invalid.",
        variant: "destructive",
      });
      return;
    }

    setLoading(true);
    setHasSearched(true);
    try {
      const data = await api.post("/api/knowledge-base/test-retrieval", {
        query: q,
        kb_id: kbId,
        top_k: parseInt(topK, 10) || 5,
      });

      const extractedResults = Array.isArray(data)
        ? data
        : data?.results || data?.chunks || [];

      setResults(Array.isArray(extractedResults) ? extractedResults : []);
    } catch (error) {
      toast({
        title: "Retrieval Test Failed",
        description:
          error instanceof Error ? error.message : "Unknown error occurred",
        variant: "destructive",
      });
      setResults([]);
    } finally {
      setLoading(false);
    }
  };

  const copyChunkContent = (text: string, index: number) => {
    navigator.clipboard.writeText(text);
    setCopiedIndex(index);
    toast({
      title: "Chunk Copied",
      description: "Chunk text copied to clipboard.",
    });
    setTimeout(() => setCopiedIndex(null), 2000);
  };

  const sampleQueries = [
    "What are the main objectives and scope?",
    "Summarize the key requirements and constraints.",
    "Explain the architecture and data flows.",
  ];

  return (
    <DashboardLayout>
      <div className="space-y-8 pb-16">
        {/* Navigation & Breadcrumb */}
        <div className="flex items-center justify-between">
          <Link
            href="/dashboard/knowledge"
            className="inline-flex items-center text-xs font-medium text-muted-foreground hover:text-foreground transition-colors gap-1.5 group"
          >
            <ArrowLeft className="h-3.5 w-3.5 transition-transform group-hover:-translate-x-1" />
            Back to Knowledge Bases
          </Link>

          {knowledgeBase && (
            <Link
              href={`/dashboard/knowledge/${knowledgeBase.id}`}
              className="inline-flex items-center text-xs font-medium text-primary hover:underline gap-1"
            >
              <BookOpen className="h-3.5 w-3.5" />
              Manage Documents
              <ChevronRight className="h-3 w-3" />
            </Link>
          )}
        </div>

        {/* Initial Loading Skeleton */}
        {initialLoading ? (
          <div className="rounded-xl border border-border/70 bg-card/50 p-8 space-y-4 animate-pulse">
            <div className="h-6 w-48 bg-muted rounded-md" />
            <div className="h-4 w-96 bg-muted/60 rounded-md" />
            <div className="h-12 w-full bg-muted/40 rounded-lg mt-6" />
          </div>
        ) : fetchError ? (
          <div className="rounded-xl border border-destructive/30 bg-destructive/5 text-center p-8 space-y-4">
            <div className="w-12 h-12 rounded-full bg-destructive/10 text-destructive flex items-center justify-center mx-auto">
              <AlertCircle className="h-6 w-6" />
            </div>
            <div className="space-y-1">
              <h2 className="text-lg font-bold text-foreground">
                Knowledge Base Not Found
              </h2>
              <p className="text-sm text-muted-foreground">{fetchError}</p>
            </div>
            <Link href="/dashboard/knowledge">
              <Button variant="outline" size="sm">
                Return to Knowledge Bases
              </Button>
            </Link>
          </div>
        ) : (
          <>
            {/* Header Title Banner */}
            <div className="rounded-xl border border-border/70 bg-card/70 backdrop-blur-xl p-6 shadow-sm space-y-3">
              <div className="flex flex-col sm:flex-row sm:items-center justify-between gap-4">
                <div className="space-y-1">
                  <div className="flex items-center gap-2">
                    <span className="inline-flex items-center gap-1.5 px-2.5 py-0.5 rounded-full text-xs font-semibold bg-primary/10 text-primary border border-primary/20">
                      <Sparkles className="h-3 w-3" />
                      Semantic Vector Diagnostic
                    </span>
                    <span className="text-xs text-muted-foreground font-mono">
                      KB #{knowledgeBase?.id}
                    </span>
                  </div>
                  <h1 className="text-2xl font-bold tracking-tight text-foreground">
                    {knowledgeBase?.name}
                  </h1>
                </div>

                <div className="flex items-center gap-2">
                  <Link href={`/dashboard/knowledge/${knowledgeBase?.id}`}>
                    <Button variant="outline" size="sm" className="h-9 gap-1.5 text-xs">
                      <Layers className="h-3.5 w-3.5" />
                      Inspector View
                    </Button>
                  </Link>
                </div>
              </div>

              <p className="text-sm text-muted-foreground max-w-3xl">
                {knowledgeBase?.description ||
                  "Test and inspect cosine similarity retrieval rankings across indexed vector embeddings in this repository."}
              </p>
            </div>

            {/* Query & Parameter Card */}
            <div className="rounded-xl border border-border/70 bg-card/70 backdrop-blur-xl p-6 shadow-sm space-y-5">
              <div className="space-y-1.5">
                <label
                  htmlFor="query-input"
                  className="text-xs font-semibold text-foreground uppercase tracking-wider"
                >
                  Semantic Query
                </label>
                <div className="flex flex-col sm:flex-row items-stretch gap-3">
                  <div className="relative flex-1">
                    <Search className="absolute left-3.5 top-1/2 -translate-y-1/2 h-4 w-4 text-muted-foreground" />
                    <Input
                      id="query-input"
                      placeholder="Ask a question or enter keywords to retrieve top matching chunks..."
                      value={query}
                      onChange={(e) => setQuery(e.target.value)}
                      className="pl-10 h-11 text-sm bg-background/80 rounded-lg border border-input focus:ring-2 focus:ring-primary/20 focus:border-primary"
                      onKeyDown={(e) =>
                        e.key === "Enter" && !loading && handleTest()
                      }
                      disabled={loading}
                    />
                  </div>

                  <div className="flex items-center gap-2">
                    <Select
                      value={topK}
                      onValueChange={setTopK}
                      disabled={loading}
                    >
                      <SelectTrigger className="w-[120px] h-11 bg-background/80 border border-input text-xs font-medium">
                        <SelectValue placeholder="Top K" />
                      </SelectTrigger>
                      <SelectContent>
                        <SelectItem value="1">Top 1 Chunk</SelectItem>
                        <SelectItem value="3">Top 3 Chunks</SelectItem>
                        <SelectItem value="5">Top 5 Chunks</SelectItem>
                        <SelectItem value="8">Top 8 Chunks</SelectItem>
                        <SelectItem value="10">Top 10 Chunks</SelectItem>
                      </SelectContent>
                    </Select>

                    <Button
                      onClick={() => handleTest()}
                      disabled={loading || !query.trim()}
                      className="h-11 px-5 bg-primary text-primary-foreground hover:bg-primary/90 font-medium gap-2 shrink-0"
                    >
                      {loading ? (
                        <>
                          <Sparkles className="h-4 w-4 animate-spin" />
                          Searching...
                        </>
                      ) : (
                        <>
                          <Search className="h-4 w-4" />
                          Test Retrieval
                        </>
                      )}
                    </Button>
                  </div>
                </div>
              </div>

              {/* Sample Quick Queries */}
              <div className="flex items-center gap-2 flex-wrap pt-1">
                <span className="text-[11px] text-muted-foreground font-medium">
                  Try prompt:
                </span>
                {sampleQueries.map((sq, i) => (
                  <button
                    key={i}
                    onClick={() => {
                      setQuery(sq);
                      handleTest(sq);
                    }}
                    disabled={loading}
                    className="text-xs px-2.5 py-1 rounded-md bg-muted/60 hover:bg-muted text-muted-foreground hover:text-foreground border border-border/50 transition-colors"
                  >
                    "{sq}"
                  </button>
                ))}
              </div>
            </div>

            {/* Results Section */}
            {Array.isArray(results) && results.length > 0 && (
              <div className="space-y-4">
                <div className="flex items-center justify-between px-1">
                  <div className="flex items-center gap-2">
                    <h2 className="text-lg font-bold tracking-tight text-foreground flex items-center gap-2">
                      <Sparkles className="h-4 w-4 text-primary" />
                      Retrieved Vector Chunks ({results.length})
                    </h2>
                  </div>
                  <span className="text-xs text-muted-foreground">
                    Ranked by Cosine Similarity Metric
                  </span>
                </div>

                <div className="grid gap-4">
                  {results.map((result, index) => {
                    const score =
                      typeof result.score === "number" ? result.score : null;
                    const relevancePercent =
                      score !== null ? (score * 100).toFixed(1) : null;

                    // Color tiered badges
                    let scoreBadgeClass =
                      "bg-slate-500/10 text-slate-600 dark:text-slate-400 border-slate-500/20";
                    if (score !== null) {
                      if (score >= 0.75) {
                        scoreBadgeClass =
                          "bg-emerald-500/10 text-emerald-600 dark:text-emerald-400 border-emerald-500/20 font-semibold";
                      } else if (score >= 0.6) {
                        scoreBadgeClass =
                          "bg-blue-500/10 text-blue-600 dark:text-blue-400 border-blue-500/20";
                      } else {
                        scoreBadgeClass =
                          "bg-amber-500/10 text-amber-600 dark:text-amber-400 border-amber-500/20";
                      }
                    }

                    const sourceName =
                      result.metadata?.filename ||
                      result.metadata?.source ||
                      result.document_id ||
                      "Document Source";

                    return (
                      <div
                        key={result.chunk_id || index}
                        className="group rounded-xl border border-border/70 bg-card/70 backdrop-blur-xl p-5 shadow-sm hover:shadow-md hover:border-primary/30 transition-all space-y-3"
                      >
                        {/* Chunk Top Meta Row */}
                        <div className="flex flex-wrap items-center justify-between gap-3 border-b border-border/50 pb-3">
                          <div className="flex items-center gap-2.5 flex-wrap">
                            <span className="flex items-center justify-center w-6 h-6 rounded-full bg-primary/10 text-primary text-xs font-bold">
                              #{index + 1}
                            </span>

                            {relevancePercent !== null && (
                              <span
                                className={`inline-flex items-center gap-1 px-2.5 py-0.5 rounded-full text-xs border ${scoreBadgeClass}`}
                              >
                                <Sparkles className="h-3 w-3" />
                                {relevancePercent}% Match
                              </span>
                            )}

                            <span className="inline-flex items-center gap-1.5 text-xs text-foreground font-medium bg-muted/50 px-2.5 py-1 rounded-md border border-border/40">
                              <FileText className="h-3.5 w-3.5 text-muted-foreground" />
                              {sourceName}
                            </span>

                            {result.metadata?.page && (
                              <span className="text-xs text-muted-foreground bg-muted/40 px-2 py-0.5 rounded">
                                Page {result.metadata.page}
                              </span>
                            )}
                          </div>

                          <div className="flex items-center gap-2">
                            {result.chunk_id && (
                              <span className="text-[11px] font-mono text-muted-foreground flex items-center gap-1">
                                <Hash className="h-3 w-3" />
                                {result.chunk_id.slice(0, 8)}...
                              </span>
                            )}

                            <Button
                              variant="ghost"
                              size="sm"
                              onClick={() => copyChunkContent(result.content, index)}
                              className="h-8 px-2 text-xs text-muted-foreground hover:text-foreground gap-1"
                            >
                              {copiedIndex === index ? (
                                <>
                                  <Check className="h-3.5 w-3.5 text-emerald-500" />
                                  <span className="text-emerald-600 dark:text-emerald-400">
                                    Copied
                                  </span>
                                </>
                              ) : (
                                <>
                                  <Copy className="h-3.5 w-3.5" />
                                  <span>Copy</span>
                                </>
                              )}
                            </Button>
                          </div>
                        </div>

                        {/* Chunk Text Content */}
                        <div className="p-4 rounded-lg bg-background/60 border border-border/40 text-sm leading-relaxed whitespace-pre-wrap font-sans text-foreground select-text">
                          {result.content}
                        </div>

                        {/* Chunk Character Count Footer */}
                        <div className="flex items-center justify-between text-[11px] text-muted-foreground px-1 pt-1">
                          <span>
                            Length: {result.content.length} characters • ~
                            {Math.round(result.content.length / 4)} tokens
                          </span>
                          {result.document_id && (
                            <Link
                              href={`/dashboard/knowledge/${knowledgeBase?.id}`}
                              className="hover:text-primary transition-colors inline-flex items-center gap-1"
                            >
                              Inspect in KB
                              <ExternalLink className="h-3 w-3" />
                            </Link>
                          )}
                        </div>
                      </div>
                    );
                  })}
                </div>
              </div>
            )}

            {/* Empty Search Results */}
            {hasSearched &&
              !loading &&
              Array.isArray(results) &&
              results.length === 0 && (
                <div className="rounded-xl border border-dashed border-border/80 bg-card/40 p-12 text-center space-y-3">
                  <div className="w-12 h-12 rounded-full bg-muted flex items-center justify-center text-muted-foreground mx-auto">
                    <Search className="h-6 w-6" />
                  </div>
                  <h3 className="text-base font-semibold text-foreground">
                    No Matching Chunks Found
                  </h3>
                  <p className="text-sm text-muted-foreground max-w-md mx-auto">
                    No vector chunks met the similarity threshold for "{query}".
                    Try broadening your search query or increasing Top K chunks.
                  </p>
                </div>
              )}
          </>
        )}
      </div>
    </DashboardLayout>
  );
}
