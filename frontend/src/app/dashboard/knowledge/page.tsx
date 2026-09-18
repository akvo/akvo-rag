"use client";

import React, { useEffect, useState, useMemo } from "react";
import Link from "next/link";
import { FileIcon, defaultStyles } from "react-file-icon";
import {
  ArrowRight,
  Plus,
  Trash2,
  Search,
  Database,
  FileText,
  Globe,
  Lock,
  Sparkles,
  FolderOpen,
  Calendar,
  AlertTriangle,
  RefreshCw,
  X,
  Layers,
} from "lucide-react";
import DashboardLayout from "@/components/layout/dashboard-layout";
import { api, ApiError } from "@/lib/api";
import { useToast } from "@/components/ui/use-toast";
import { useUser } from "@/contexts/userContext";
import { Button } from "@/components/ui/button";
import {
  Dialog,
  DialogContent,
  DialogDescription,
  DialogFooter,
  DialogHeader,
  DialogTitle,
} from "@/components/ui/dialog";

interface KnowledgeBase {
  id: number;
  name: string;
  description: string;
  documents?: Document[];
  created_at: string;
  user_id: number;
  is_superuser: boolean;
}

interface Document {
  id: number;
  file_name: string;
  file_path: string;
  file_size: number;
  file_url: string;
  content_type: string;
  knowledge_base_id: number;
  created_at: string;
  updated_at: string;
  processing_tasks?: any[];
}

export default function KnowledgeBasePage() {
  const [knowledgeBases, setKnowledgeBases] = useState<KnowledgeBase[]>([]);
  const [loading, setLoading] = useState(true);
  const [refreshing, setRefreshing] = useState(false);
  const [searchQuery, setSearchQuery] = useState("");
  const [scopeFilter, setScopeFilter] = useState<"all" | "public" | "private">("all");

  // Deletion Modal State
  const [deleteModalOpen, setDeleteModalOpen] = useState(false);
  const [kbToDelete, setKbToDelete] = useState<KnowledgeBase | null>(null);
  const [deleting, setDeleting] = useState(false);

  const { toast } = useToast();
  const { user } = useUser();

  const allow_delete = true;

  const fetchKnowledgeBases = React.useCallback(async (isManualRefresh = false) => {
    if (isManualRefresh) setRefreshing(true);
    else setLoading(true);

    try {
      const data = await api.get("/api/knowledge-base");
      setKnowledgeBases(data || []);
    } catch (error) {
      console.error("Failed to fetch knowledge bases:", error);
      if (error instanceof ApiError) {
        toast({
          title: "Error",
          description: error.message,
          variant: "destructive",
        });
      }
    } finally {
      setLoading(false);
      setRefreshing(false);
    }
  }, [toast]);

  useEffect(() => {
    fetchKnowledgeBases();
  }, [fetchKnowledgeBases]);

  // Compute KPI Statistics
  const stats = useMemo(() => {
    const totalKbs = knowledgeBases.length;
    const totalDocs = knowledgeBases.reduce(
      (acc, kb) => acc + (kb.documents?.length || 0),
      0
    );
    const publicKbs = knowledgeBases.filter((kb) => kb.is_superuser).length;
    const privateKbs = totalKbs - publicKbs;

    return { totalKbs, totalDocs, publicKbs, privateKbs };
  }, [knowledgeBases]);

  // Filtered Knowledge Bases
  const filteredKnowledgeBases = useMemo(() => {
    return knowledgeBases.filter((kb) => {
      // Scope Filter
      if (scopeFilter === "public" && !kb.is_superuser) return false;
      if (scopeFilter === "private" && kb.is_superuser) return false;

      // Search Query
      if (!searchQuery.trim()) return true;
      const query = searchQuery.toLowerCase();
      const matchName = kb.name.toLowerCase().includes(query);
      const matchDesc = (kb.description || "").toLowerCase().includes(query);
      const matchDoc = (kb.documents || []).some((doc) =>
        doc.file_name.toLowerCase().includes(query)
      );

      return matchName || matchDesc || matchDoc;
    });
  }, [knowledgeBases, scopeFilter, searchQuery]);

  const openDeleteModal = (kb: KnowledgeBase) => {
    setKbToDelete(kb);
    setDeleteModalOpen(true);
  };

  const confirmDelete = async () => {
    if (!kbToDelete) return;
    setDeleting(true);
    try {
      await api.delete(`/api/knowledge-base/${kbToDelete.id}`);
      setKnowledgeBases((prev) => prev.filter((kb) => kb.id !== kbToDelete.id));
      toast({
        title: "Success",
        description: `Knowledge base "${kbToDelete.name}" deleted successfully.`,
      });
      setDeleteModalOpen(false);
      setKbToDelete(null);
    } catch (error) {
      console.error("Failed to delete knowledge base:", error);
      if (error instanceof ApiError) {
        toast({
          title: "Error Deleting Knowledge Base",
          description: error.message,
          variant: "destructive",
        });
      }
    } finally {
      setDeleting(false);
    }
  };

  return (
    <DashboardLayout>
      <div className="space-y-8 pb-12">
        {/* Header Title & Actions */}
        <div className="flex flex-col sm:flex-row sm:items-center justify-between gap-4">
          <div>
            <div className="flex items-center gap-2.5">
              <div className="p-2 rounded-lg bg-primary/10 text-primary">
                <Database className="h-6 w-6" />
              </div>
              <h1 className="text-3xl font-bold tracking-tight text-foreground">
                Knowledge Repositories
              </h1>
            </div>
            <p className="text-sm text-muted-foreground mt-1">
              Curate, organize, and inspect document repositories indexed for RAG vector retrieval.
            </p>
          </div>
          <div className="flex items-center gap-3">
            <Button
              variant="outline"
              size="sm"
              onClick={() => fetchKnowledgeBases(true)}
              disabled={loading || refreshing}
              className="h-10 px-3 text-muted-foreground hover:text-foreground"
            >
              <RefreshCw
                className={`h-4 w-4 mr-2 ${refreshing ? "animate-spin" : ""}`}
              />
              Refresh
            </Button>
            <Link href="/dashboard/knowledge/new">
              <Button className="h-10 px-4 bg-primary text-primary-foreground hover:bg-primary/90 shadow-sm font-medium">
                <Plus className="mr-2 h-4 w-4" />
                New Knowledge Base
              </Button>
            </Link>
          </div>
        </div>

        {/* KPI Summary Cards */}
        <div className="grid grid-cols-2 md:grid-cols-4 gap-4">
          <div className="rounded-xl border border-border/70 bg-card/70 backdrop-blur-xl p-5 shadow-sm">
            <div className="flex items-center justify-between">
              <span className="text-xs font-medium text-muted-foreground uppercase tracking-wider">
                Total Repositories
              </span>
              <div className="p-2 rounded-md bg-primary/10 text-primary">
                <Database className="h-4 w-4" />
              </div>
            </div>
            <div className="mt-3 flex items-baseline gap-2">
              <span className="text-2xl font-bold text-foreground">
                {stats.totalKbs}
              </span>
              <span className="text-xs text-muted-foreground">configured</span>
            </div>
          </div>

          <div className="rounded-xl border border-border/70 bg-card/70 backdrop-blur-xl p-5 shadow-sm">
            <div className="flex items-center justify-between">
              <span className="text-xs font-medium text-muted-foreground uppercase tracking-wider">
                Total Documents
              </span>
              <div className="p-2 rounded-md bg-emerald-500/10 text-emerald-600 dark:text-emerald-400">
                <FileText className="h-4 w-4" />
              </div>
            </div>
            <div className="mt-3 flex items-baseline gap-2">
              <span className="text-2xl font-bold text-foreground">
                {stats.totalDocs}
              </span>
              <span className="text-xs text-muted-foreground">indexed chunks</span>
            </div>
          </div>

          <div className="rounded-xl border border-border/70 bg-card/70 backdrop-blur-xl p-5 shadow-sm">
            <div className="flex items-center justify-between">
              <span className="text-xs font-medium text-muted-foreground uppercase tracking-wider">
                Public Repositories
              </span>
              <div className="p-2 rounded-md bg-blue-500/10 text-blue-600 dark:text-blue-400">
                <Globe className="h-4 w-4" />
              </div>
            </div>
            <div className="mt-3 flex items-baseline gap-2">
              <span className="text-2xl font-bold text-foreground">
                {stats.publicKbs}
              </span>
              <span className="text-xs text-muted-foreground">global access</span>
            </div>
          </div>

          <div className="rounded-xl border border-border/70 bg-card/70 backdrop-blur-xl p-5 shadow-sm">
            <div className="flex items-center justify-between">
              <span className="text-xs font-medium text-muted-foreground uppercase tracking-wider">
                Private Stores
              </span>
              <div className="p-2 rounded-md bg-violet-500/10 text-violet-600 dark:text-violet-400">
                <Lock className="h-4 w-4" />
              </div>
            </div>
            <div className="mt-3 flex items-baseline gap-2">
              <span className="text-2xl font-bold text-foreground">
                {stats.privateKbs}
              </span>
              <span className="text-xs text-muted-foreground">tenant-isolated</span>
            </div>
          </div>
        </div>

        {/* Search & Scope Filters Bar */}
        <div className="flex flex-col sm:flex-row items-stretch sm:items-center justify-between gap-4 p-2 rounded-xl border border-border/70 bg-card/50 backdrop-blur-sm">
          {/* Scope Filters */}
          <div className="flex items-center p-1 bg-muted/50 rounded-lg border border-border/50">
            <button
              onClick={() => setScopeFilter("all")}
              className={`px-3 py-1.5 text-xs font-medium rounded-md transition-all ${
                scopeFilter === "all"
                  ? "bg-background text-foreground shadow-sm font-semibold"
                  : "text-muted-foreground hover:text-foreground"
              }`}
            >
              All ({stats.totalKbs})
            </button>
            <button
              onClick={() => setScopeFilter("public")}
              className={`px-3 py-1.5 text-xs font-medium rounded-md transition-all ${
                scopeFilter === "public"
                  ? "bg-background text-foreground shadow-sm font-semibold"
                  : "text-muted-foreground hover:text-foreground"
              }`}
            >
              Public ({stats.publicKbs})
            </button>
            <button
              onClick={() => setScopeFilter("private")}
              className={`px-3 py-1.5 text-xs font-medium rounded-md transition-all ${
                scopeFilter === "private"
                  ? "bg-background text-foreground shadow-sm font-semibold"
                  : "text-muted-foreground hover:text-foreground"
              }`}
            >
              Private ({stats.privateKbs})
            </button>
          </div>

          {/* Search Input */}
          <div className="relative flex-1 max-w-md">
            <Search className="absolute left-3 top-1/2 -translate-y-1/2 h-4 w-4 text-muted-foreground" />
            <input
              type="text"
              value={searchQuery}
              onChange={(e) => setSearchQuery(e.target.value)}
              placeholder="Search knowledge bases or document names..."
              className="w-full pl-9 pr-8 py-2 text-sm bg-background/80 rounded-lg border border-input focus:outline-none focus:ring-2 focus:ring-primary/20 focus:border-primary transition-all placeholder:text-muted-foreground"
            />
            {searchQuery && (
              <button
                onClick={() => setSearchQuery("")}
                className="absolute right-2.5 top-1/2 -translate-y-1/2 p-1 text-muted-foreground hover:text-foreground"
              >
                <X className="h-3.5 w-3.5" />
              </button>
            )}
          </div>
        </div>

        {/* Main Knowledge Base Cards Grid */}
        <div className="grid gap-6">
          {/* Skeleton Loading State */}
          {loading && (
            <div className="space-y-4">
              {[1, 2, 3].map((i) => (
                <div
                  key={i}
                  className="rounded-xl border border-border/70 bg-card/50 p-6 space-y-4 animate-pulse"
                >
                  <div className="flex justify-between items-start">
                    <div className="space-y-2">
                      <div className="h-6 w-48 bg-muted rounded-md" />
                      <div className="h-4 w-72 bg-muted/60 rounded-md" />
                      <div className="h-3 w-36 bg-muted/40 rounded-md" />
                    </div>
                    <div className="flex gap-2">
                      <div className="h-8 w-24 bg-muted rounded-md" />
                      <div className="h-8 w-24 bg-muted rounded-md" />
                    </div>
                  </div>
                  <div className="pt-4 border-t border-border/50 grid grid-cols-2 sm:grid-cols-4 gap-3">
                    {[1, 2, 3, 4].map((j) => (
                      <div key={j} className="h-20 bg-muted/30 rounded-lg" />
                    ))}
                  </div>
                </div>
              ))}
            </div>
          )}

          {/* Cards List */}
          {!loading &&
            filteredKnowledgeBases.map((kb) => {
              const docCount = kb.documents?.length || 0;
              const formattedDate = new Date(kb.created_at).toLocaleDateString(
                undefined,
                { year: "numeric", month: "short", day: "numeric" }
              );

              return (
                <div
                  key={kb.id}
                  className="group rounded-xl border border-border/70 bg-card/70 backdrop-blur-xl p-6 shadow-sm hover:shadow-md hover:border-border transition-all space-y-5"
                >
                  {/* Card Header & Controls */}
                  <div className="flex flex-col md:flex-row md:items-start justify-between gap-4">
                    <div className="space-y-1.5">
                      <div className="flex items-center gap-2.5 flex-wrap">
                        {kb.is_superuser ? (
                          <span className="inline-flex items-center gap-1.5 px-2.5 py-0.5 rounded-full text-xs font-semibold bg-emerald-500/10 text-emerald-600 dark:text-emerald-400 border border-emerald-500/20">
                            <Globe className="h-3 w-3" />
                            Public Index
                          </span>
                        ) : (
                          <span className="inline-flex items-center gap-1.5 px-2.5 py-0.5 rounded-full text-xs font-semibold bg-slate-500/10 text-slate-600 dark:text-slate-400 border border-slate-500/20">
                            <Lock className="h-3 w-3" />
                            Private Store
                          </span>
                        )}
                        <h3 className="text-xl font-bold tracking-tight text-foreground group-hover:text-primary transition-colors">
                          {kb.name}
                        </h3>
                      </div>

                      <p className="text-sm text-muted-foreground max-w-2xl">
                        {kb.description || "No description provided for this knowledge base."}
                      </p>

                      <div className="flex items-center gap-4 text-xs text-muted-foreground pt-1">
                        <span className="inline-flex items-center gap-1">
                          <Layers className="h-3.5 w-3.5 text-primary/70" />
                          {docCount} {docCount === 1 ? "document" : "documents"}
                        </span>
                        <span>•</span>
                        <span className="inline-flex items-center gap-1">
                          <Calendar className="h-3.5 w-3.5 text-muted-foreground/70" />
                          Created {formattedDate}
                        </span>
                      </div>
                    </div>

                    {/* Action Buttons */}
                    <div className="flex items-center gap-2 self-start flex-wrap">
                      <Link
                        href={`/dashboard/test-retrieval/${kb.id}`}
                        className="inline-flex items-center"
                      >
                        <Button
                          variant="secondary"
                          size="sm"
                          className="h-9 px-3 text-xs font-medium gap-1.5 shadow-none hover:bg-secondary/80"
                        >
                          <Sparkles className="h-3.5 w-3.5 text-primary" />
                          Test Retrieval
                        </Button>
                      </Link>

                      <Link
                        href={`/dashboard/knowledge/${kb.id}?kb_owner=${
                          kb.user_id === user?.id ? 1 : 1
                        }`}
                        className="inline-flex items-center"
                      >
                        <Button
                          variant="outline"
                          size="sm"
                          className="h-9 px-3 text-xs font-medium gap-1.5"
                        >
                          <FolderOpen className="h-3.5 w-3.5 text-muted-foreground" />
                          Manage Documents
                        </Button>
                      </Link>

                      {(kb.user_id === user?.id || allow_delete) && (
                        <Button
                          variant="ghost"
                          size="sm"
                          onClick={() => openDeleteModal(kb)}
                          className="h-9 w-9 p-0 text-muted-foreground hover:text-destructive hover:bg-destructive/10 transition-colors"
                          title="Delete Knowledge Base"
                        >
                          <Trash2 className="h-4 w-4" />
                        </Button>
                      )}
                    </div>
                  </div>

                  {/* Document Preview Gallery */}
                  {docCount > 0 ? (
                    <div className="border-t border-border/50 pt-4">
                      <div className="flex items-center justify-between mb-3">
                        <span className="text-xs font-semibold text-muted-foreground uppercase tracking-wider">
                          Indexed Documents ({docCount})
                        </span>
                        <Link
                          href={`/dashboard/knowledge/${kb.id}`}
                          className="text-xs font-medium text-primary hover:underline inline-flex items-center gap-1"
                        >
                          View all in Document Inspector
                          <ArrowRight className="h-3 w-3" />
                        </Link>
                      </div>

                      <div className="grid grid-cols-2 sm:grid-cols-3 md:grid-cols-4 lg:grid-cols-6 gap-3">
                        {kb.documents?.slice(0, 5).map((doc) => {
                          const ext =
                            doc.file_name.split(".").pop()?.toLowerCase() || "file";
                          const isPdf = doc.content_type?.toLowerCase().includes("pdf") || ext === "pdf";
                          const isDoc = doc.content_type?.toLowerCase().includes("doc") || ext === "docx" || ext === "doc";
                          const isTxt = doc.content_type?.toLowerCase().includes("txt") || ext === "txt";
                          const isMd = doc.content_type?.toLowerCase().includes("md") || ext === "md";

                          return (
                            <Link
                              key={doc.id}
                              href={`/dashboard/knowledge/${kb.id}`}
                              className="group/doc flex flex-col items-center justify-between p-3 rounded-lg border border-border/60 bg-background/50 hover:bg-accent/40 hover:border-primary/30 transition-all text-center h-[130px]"
                            >
                              <div className="w-8 h-8 flex items-center justify-center shrink-0">
                                {isPdf ? (
                                  <FileIcon extension="pdf" {...defaultStyles.pdf} />
                                ) : isDoc ? (
                                  <FileIcon extension="docx" {...defaultStyles.docx} />
                                ) : isTxt ? (
                                  <FileIcon extension="txt" {...defaultStyles.txt} />
                                ) : isMd ? (
                                  <FileIcon extension="md" {...defaultStyles.md} />
                                ) : (
                                  <FileIcon
                                    extension={ext}
                                    color="#E2E8F0"
                                    labelColor="#94A3B8"
                                  />
                                )}
                              </div>
                              <span
                                className="text-xs font-medium text-foreground line-clamp-2 break-all px-1 group-hover/doc:text-primary transition-colors"
                                title={doc.file_name}
                              >
                                {doc.file_name}
                              </span>
                              <span className="text-[10px] text-muted-foreground">
                                {new Date(doc.created_at).toLocaleDateString()}
                              </span>
                            </Link>
                          );
                        })}

                        {docCount > 5 && (
                          <Link
                            href={`/dashboard/knowledge/${kb.id}`}
                            className="flex flex-col items-center justify-center p-3 rounded-lg border border-dashed border-border/80 bg-muted/20 hover:bg-accent/50 hover:border-primary/40 transition-all text-center h-[130px] group/more"
                          >
                            <div className="p-2 rounded-full bg-muted text-muted-foreground group-hover/more:text-primary group-hover/more:bg-primary/10 transition-colors mb-1.5">
                              <ArrowRight className="h-4 w-4" />
                            </div>
                            <span className="text-xs font-semibold text-foreground">
                              +{docCount - 5} more
                            </span>
                            <span className="text-[10px] text-muted-foreground">
                              Inspect All
                            </span>
                          </Link>
                        )}
                      </div>
                    </div>
                  ) : (
                    <div className="border-t border-border/50 pt-4">
                      <div className="flex items-center justify-between p-3.5 rounded-lg border border-dashed border-border/70 bg-muted/10 text-xs text-muted-foreground">
                        <span>No documents indexed in this repository yet.</span>
                        <Link
                          href={`/dashboard/knowledge/${kb.id}?kb_owner=1`}
                          className="font-medium text-primary hover:underline inline-flex items-center gap-1"
                        >
                          <Plus className="h-3 w-3" />
                          Add Document
                        </Link>
                      </div>
                    </div>
                  )}
                </div>
              );
            })}

          {/* Empty State */}
          {!loading && filteredKnowledgeBases.length === 0 && (
            <div className="rounded-xl border border-dashed border-border/80 bg-card/50 p-12 text-center space-y-4">
              <div className="mx-auto w-12 h-12 rounded-full bg-muted flex items-center justify-center text-muted-foreground">
                <Database className="h-6 w-6" />
              </div>
              <div className="space-y-1">
                <h3 className="text-base font-semibold text-foreground">
                  {searchQuery ? "No matching knowledge bases found" : "No knowledge bases created yet"}
                </h3>
                <p className="text-sm text-muted-foreground max-w-sm mx-auto">
                  {searchQuery
                    ? `No knowledge base or document matched "${searchQuery}". Try clearing your search or filter.`
                    : "Create your first knowledge base to upload documents and begin semantic RAG querying."}
                </p>
              </div>
              {searchQuery ? (
                <Button
                  variant="outline"
                  size="sm"
                  onClick={() => {
                    setSearchQuery("");
                    setScopeFilter("all");
                  }}
                  className="mt-2"
                >
                  Clear Filters
                </Button>
              ) : (
                <Link href="/dashboard/knowledge/new">
                  <Button size="sm" className="mt-2">
                    <Plus className="h-4 w-4 mr-1.5" />
                    Create Knowledge Base
                  </Button>
                </Link>
              )}
            </div>
          )}
        </div>

        {/* Delete Confirmation Modal */}
        <Dialog open={deleteModalOpen} onOpenChange={setDeleteModalOpen}>
          <DialogContent className="max-w-md">
            <DialogHeader className="space-y-3">
              <div className="w-10 h-10 rounded-full bg-destructive/10 text-destructive flex items-center justify-center">
                <AlertTriangle className="h-5 w-5" />
              </div>
              <DialogTitle className="text-lg font-bold">
                Delete Knowledge Base
              </DialogTitle>
              <DialogDescription className="text-sm text-muted-foreground space-y-2">
                <span>
                  Are you sure you want to permanently delete{" "}
                  <strong className="text-foreground font-semibold">
                    {kbToDelete?.name}
                  </strong>
                  ?
                </span>
                <span className="block text-xs text-destructive/90 bg-destructive/5 border border-destructive/20 p-2.5 rounded-md mt-2">
                  ⚠️ This will permanently remove the repository, all{" "}
                  <strong>{kbToDelete?.documents?.length || 0} attached documents</strong>, and their indexed vector embeddings from ChromaDB. This action cannot be undone.
                </span>
              </DialogDescription>
            </DialogHeader>

            <DialogFooter className="gap-2 sm:gap-0 mt-4">
              <Button
                variant="outline"
                onClick={() => {
                  setDeleteModalOpen(false);
                  setKbToDelete(null);
                }}
                disabled={deleting}
              >
                Cancel
              </Button>
              <Button
                variant="destructive"
                onClick={confirmDelete}
                disabled={deleting}
                className="gap-1.5"
              >
                {deleting ? (
                  <>
                    <RefreshCw className="h-4 w-4 animate-spin" />
                    Deleting...
                  </>
                ) : (
                  <>
                    <Trash2 className="h-4 w-4" />
                    Delete Knowledge Base
                  </>
                )}
              </Button>
            </DialogFooter>
          </DialogContent>
        </Dialog>
      </div>
    </DashboardLayout>
  );
}
