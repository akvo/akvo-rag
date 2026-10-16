"use client";

import { useState, useEffect } from "react";
import Link from "next/link";
import { Button } from "@/components/ui/button";
import { Input } from "@/components/ui/input";
import { Card, CardContent } from "@/components/ui/card";
import { useToast } from "@/components/ui/use-toast";
import { api, ApiError } from "@/lib/api";
import DashboardLayout from "@/components/layout/dashboard-layout";
import {
  Search,
  ArrowRight,
  ArrowLeft,
  Sparkles,
  Database,
  AlertCircle,
  FileText,
} from "lucide-react";
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

export default function TestPage({ params }: { params: { id: string } }) {
  const [query, setQuery] = useState("");
  const [results, setResults] = useState<RetrievalResult[]>([]);
  const [hasSearched, setHasSearched] = useState(false);
  const [knowledgeBase, setKnowledgeBase] = useState<KnowledgeBase | null>(null);
  const [initialLoading, setInitialLoading] = useState(true);
  const [fetchError, setFetchError] = useState<string | null>(null);
  const [loading, setLoading] = useState(false);
  const [topK, setTopK] = useState("3");
  const { toast } = useToast();

  useEffect(() => {
    const fetchKnowledgeBase = async () => {
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
          title: "Error",
          description: message,
          variant: "destructive",
        });
      } finally {
        setInitialLoading(false);
      }
    };

    fetchKnowledgeBase();
  }, [params.id, toast]);

  const handleTest = async () => {
    if (!query.trim()) {
      toast({
        title: "Please fill in all fields",
        description: "Please enter query text",
        variant: "destructive",
      });
      return;
    }

    const kbId = parseInt(params.id, 10);
    if (isNaN(kbId)) {
      toast({
        title: "Invalid ID",
        description: "Knowledge Base ID is invalid",
        variant: "destructive",
      });
      return;
    }

    setLoading(true);
    setHasSearched(true);
    try {
      const data = await api.post("/api/knowledge-base/test-retrieval", {
        query: query.trim(),
        kb_id: kbId,
        top_k: parseInt(topK, 10) || 3,
      });

      const extractedResults = Array.isArray(data)
        ? data
        : data?.results || data?.chunks || [];

      setResults(Array.isArray(extractedResults) ? extractedResults : []);
    } catch (error) {
      toast({
        title: "Test Failed",
        description:
          error instanceof Error ? error.message : "Unknown error occurred",
        variant: "destructive",
      });
      setResults([]);
    } finally {
      setLoading(false);
    }
  };

  return (
    <DashboardLayout>
      <div className="min-h-screen bg-gradient-to-b from-background to-background/50">
        <div className="max-w-6xl mx-auto py-12 px-6">
          {/* Header & Navigation */}
          <div className="mb-8">
            <Link
              href="/dashboard/knowledge"
              className="inline-flex items-center text-sm font-medium text-muted-foreground hover:text-foreground transition-colors mb-6 group"
            >
              <ArrowLeft className="mr-2 h-4 w-4 transition-transform group-hover:-translate-x-1" />
              Back to Knowledge Bases
            </Link>

            {initialLoading ? (
              <div className="text-center py-12 space-y-4 animate-pulse">
                <div className="h-10 w-80 bg-primary/10 rounded-lg mx-auto" />
                <div className="h-5 w-60 bg-muted/40 rounded-lg mx-auto" />
              </div>
            ) : fetchError ? (
              <Card className="border-destructive/30 bg-destructive/5 text-center p-8">
                <AlertCircle className="h-10 w-10 text-destructive mx-auto mb-4" />
                <h2 className="text-xl font-semibold mb-2">
                  Knowledge Base Not Found
                </h2>
                <p className="text-muted-foreground mb-6">{fetchError}</p>
                <Button asChild variant="outline">
                  <Link href="/dashboard/knowledge">Return to Knowledge Bases</Link>
                </Button>
              </Card>
            ) : (
              <div className="text-center mb-12">
                <div className="inline-flex items-center gap-2 px-3 py-1 rounded-full bg-primary/10 text-primary text-xs font-semibold mb-4">
                  <Database className="h-3.5 w-3.5" />
                  Vector Retrieval Diagnostic
                </div>
                <h1 className="text-4xl font-bold tracking-tighter bg-clip-text text-transparent bg-gradient-to-r from-primary to-primary/60">
                  Knowledge Base Retrieval Test
                </h1>
                {knowledgeBase && (
                  <p className="mt-4 text-lg text-muted-foreground">
                    <span className="font-semibold text-foreground">
                      {knowledgeBase.name}
                    </span>
                    {knowledgeBase.description && <span className="mx-2">•</span>}
                    <span className="italic">{knowledgeBase.description}</span>
                  </p>
                )}
              </div>
            )}
          </div>

          {!initialLoading && !fetchError && (
            <>
              {/* Query & Parameter Card */}
              <Card className="backdrop-blur-sm bg-card/50 border-primary/20 shadow-md">
                <CardContent className="p-8">
                  <div className="flex flex-col sm:flex-row gap-4">
                    <div className="relative flex-1">
                      <div className="absolute inset-y-0 left-0 pl-4 flex items-center pointer-events-none">
                        <Search className="h-5 w-5 text-muted-foreground" />
                      </div>
                      <Input
                        placeholder="Enter query text to test vector retrieval..."
                        value={query}
                        onChange={(e) => setQuery(e.target.value)}
                        className="pl-12 h-14 text-lg bg-background/50 border-primary/20 focus:border-primary"
                        onKeyDown={(e) =>
                          e.key === "Enter" && !loading && handleTest()
                        }
                        disabled={loading}
                      />
                      <Button
                        onClick={handleTest}
                        size="lg"
                        className="absolute right-0 top-0 h-14 px-8 bg-primary hover:bg-primary/90"
                        disabled={loading || !query.trim()}
                      >
                        {loading ? (
                          <span className="flex items-center">
                            <Sparkles className="animate-spin mr-2 h-4 w-4" />
                            Searching...
                          </span>
                        ) : (
                          <span className="flex items-center">
                            Search
                            <ArrowRight className="ml-2 h-4 w-4" />
                          </span>
                        )}
                      </Button>
                    </div>

                    <Select
                      value={topK}
                      onValueChange={setTopK}
                      disabled={loading}
                    >
                      <SelectTrigger className="w-full sm:w-[140px] h-14 bg-background/50 border-primary/20">
                        <SelectValue placeholder="Top K" />
                      </SelectTrigger>
                      <SelectContent>
                        <SelectItem value="1">Top 1</SelectItem>
                        <SelectItem value="3">Top 3</SelectItem>
                        <SelectItem value="5">Top 5</SelectItem>
                        <SelectItem value="10">Top 10</SelectItem>
                      </SelectContent>
                    </Select>
                  </div>
                </CardContent>
              </Card>

              {/* Search Results */}
              {Array.isArray(results) && results.length > 0 && (
                <div className="mt-12 space-y-8">
                  <div className="flex items-center justify-between">
                    <h2 className="text-2xl font-semibold flex items-center gap-2">
                      <Sparkles className="h-6 w-6 text-primary" />
                      Search Results ({results.length})
                    </h2>
                    <span className="text-sm text-muted-foreground">
                      Ranked by cosine similarity
                    </span>
                  </div>

                  <div className="grid gap-6">
                    {results.map((result, index) => {
                      const relevanceScore =
                        typeof result.score === "number"
                          ? (result.score * 100).toFixed(2)
                          : null;
                      const sourceName =
                        result.metadata?.source ||
                        result.metadata?.filename ||
                        result.document_id ||
                        "Document";

                      return (
                        <Card
                          key={result.chunk_id || index}
                          className="overflow-hidden border-0 shadow-lg hover:shadow-xl transition-shadow duration-300 bg-card/50 backdrop-blur-sm"
                        >
                          <CardContent className="p-8">
                            <div className="flex flex-wrap items-center justify-between gap-4 mb-6">
                              <div className="flex items-center gap-4">
                                {relevanceScore !== null && (
                                  <span className="px-4 py-1.5 rounded-full bg-primary/10 text-primary font-medium text-sm">
                                    Relevance: {relevanceScore}%
                                  </span>
                                )}
                                <span className="text-sm text-muted-foreground flex items-center gap-2">
                                  <FileText className="h-4 w-4" />
                                  Source: {sourceName}
                                </span>
                              </div>
                              {result.metadata?.page && (
                                <span className="text-xs text-muted-foreground bg-muted/50 px-2.5 py-1 rounded">
                                  Page {result.metadata.page}
                                </span>
                              )}
                            </div>
                            <p className="text-lg leading-relaxed whitespace-pre-wrap prose prose-gray dark:prose-invert max-w-none">
                              {result.content}
                            </p>
                          </CardContent>
                        </Card>
                      );
                    })}
                  </div>
                </div>
              )}

              {/* Empty State */}
              {hasSearched &&
                !loading &&
                Array.isArray(results) &&
                results.length === 0 && (
                  <div className="mt-12 text-center py-16 border border-dashed border-primary/20 rounded-2xl bg-card/20">
                    <Search className="h-10 w-10 text-muted-foreground/50 mx-auto mb-4" />
                    <h3 className="text-lg font-semibold mb-2">
                      No Matching Chunks Found
                    </h3>
                    <p className="text-muted-foreground max-w-md mx-auto">
                      No vector chunks met the retrieval criteria for this query.
                      Try adjusting your search terms or increasing Top K.
                    </p>
                  </div>
                )}
            </>
          )}
        </div>
      </div>
    </DashboardLayout>
  );
}
