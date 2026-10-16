"use client";

import { FC, useEffect, useRef, useState } from "react";
import {
  X,
  Layers,
  FileText,
  Copy,
  Check,
  Hash,
  BookOpen,
  Loader2,
  AlertCircle,
} from "lucide-react";
import { Badge } from "@/components/ui/badge";
import { api, ApiError } from "@/lib/api";
import { useToast } from "@/components/ui/use-toast";

export interface DocumentChunkItem {
  id: string;
  chunk_index: number;
  file_name: string;
  text: string;
  char_count: number;
  token_count: number;
  page?: number | null;
  metadata?: Record<string, any>;
}

interface ChunkInspectorDrawerProps {
  isOpen: boolean;
  onClose: () => void;
  knowledgeBaseId: number;
  documentId: number | null;
  fileName: string;
}

export const ChunkInspectorDrawer: FC<ChunkInspectorDrawerProps> = ({
  isOpen,
  onClose,
  knowledgeBaseId,
  documentId,
  fileName,
}) => {
  const [chunks, setChunks] = useState<DocumentChunkItem[]>([]);
  const [loading, setLoading] = useState<boolean>(false);
  const [error, setError] = useState<string | null>(null);
  const [copiedId, setCopiedId] = useState<string | null>(null);
  const { toast } = useToast();

  const onCloseRef = useRef(onClose);
  useEffect(() => {
    onCloseRef.current = onClose;
  }, [onClose]);

  // Data fetching effect
  useEffect(() => {
    if (!isOpen || !documentId) {
      setChunks([]);
      return;
    }

    let isMounted = true;
    setLoading(true);
    setError(null);

    const fetchChunks = async () => {
      try {
        const res: any = await api.get(
          `/api/v1/knowledge-bases/${knowledgeBaseId}/documents/${documentId}/chunks`
        );
        if (isMounted) {
          const chunkData = Array.isArray(res.chunks)
            ? res.chunks
            : Array.isArray(res)
            ? res
            : [];
          setChunks(chunkData);
        }
      } catch (err) {
        if (isMounted) {
          const apiErr = err as ApiError;
          setError(
            apiErr.message ||
              "Failed to load document chunks from vector knowledge base."
          );
        }
      } finally {
        if (isMounted) {
          setLoading(false);
        }
      }
    };

    fetchChunks();

    return () => {
      isMounted = false;
    };
  }, [isOpen, knowledgeBaseId, documentId]);

  // Keyboard listener effect
  useEffect(() => {
    if (!isOpen) return;
    const handleKeyDown = (e: KeyboardEvent) => {
      if (e.key === "Escape") onCloseRef.current();
    };
    window.addEventListener("keydown", handleKeyDown);
    return () => window.removeEventListener("keydown", handleKeyDown);
  }, [isOpen]);

  if (!isOpen || !documentId) return null;

  const totalTokens = chunks.reduce((acc, c) => acc + (c.token_count || 0), 0);
  const totalChars = chunks.reduce((acc, c) => acc + (c.char_count || 0), 0);

  const copyChunkText = (id: string, text: string) => {
    navigator.clipboard.writeText(text);
    setCopiedId(id);
    toast({
      title: "Chunk copied",
      description: "Text excerpt copied to clipboard.",
    });
    setTimeout(() => setCopiedId(null), 2000);
  };

  return (
    <>
      {/* Backdrop */}
      <div
        onClick={onClose}
        className="fixed inset-0 z-50 bg-black/40 backdrop-blur-sm transition-opacity duration-200"
      />

      {/* Slide-Over Panel */}
      <div className="fixed inset-y-0 right-0 z-50 flex w-full max-w-xl flex-col bg-background border-l shadow-2xl transition-transform duration-300 ease-in-out sm:max-w-2xl">
        {/* Header */}
        <div className="flex items-center justify-between border-b px-6 py-4 bg-muted/30">
          <div className="flex items-center gap-3 min-w-0">
            <div className="flex h-9 w-9 shrink-0 items-center justify-center rounded-lg bg-primary/10 text-primary">
              <Layers className="h-5 w-5" />
            </div>
            <div className="min-w-0">
              <div className="flex items-center gap-2">
                <h3 className="text-base font-semibold text-foreground truncate max-w-[280px] sm:max-w-md">
                  {fileName}
                </h3>
                <Badge variant="outline" className="text-[11px] font-mono shrink-0">
                  ID: #{documentId}
                </Badge>
              </div>
              <p className="text-xs text-muted-foreground truncate">
                Document Chunk Inspector & Token Breakdown
              </p>
            </div>
          </div>

          <button
            onClick={onClose}
            className="rounded-full p-1.5 text-muted-foreground hover:bg-muted hover:text-foreground transition-colors"
            title="Close drawer (Esc)"
          >
            <X className="h-5 w-5" />
          </button>
        </div>

        {/* Aggregate Stats Summary Bar */}
        <div className="grid grid-cols-3 divide-x border-b bg-card text-center text-xs">
          <div className="py-2.5 px-3">
            <p className="text-muted-foreground">Total Chunks</p>
            <p className="font-semibold text-foreground text-sm mt-0.5">
              {loading ? "..." : chunks.length}
            </p>
          </div>
          <div className="py-2.5 px-3">
            <p className="text-muted-foreground">Est. Tokens</p>
            <p className="font-semibold text-foreground text-sm mt-0.5">
              {loading ? "..." : totalTokens.toLocaleString()}
            </p>
          </div>
          <div className="py-2.5 px-3">
            <p className="text-muted-foreground">Characters</p>
            <p className="font-semibold text-foreground text-sm mt-0.5">
              {loading ? "..." : totalChars.toLocaleString()}
            </p>
          </div>
        </div>

        {/* Scrollable Content */}
        <div className="flex-1 overflow-y-auto px-6 py-6 space-y-4">
          {loading && (
            <div className="flex flex-col items-center justify-center h-64 gap-3 text-muted-foreground">
              <Loader2 className="h-8 w-8 animate-spin text-primary" />
              <p className="text-xs">Loading chunks...</p>
            </div>
          )}

          {error && (
            <div className="rounded-xl border border-red-200 bg-red-50 p-4 text-xs text-red-800 dark:border-red-900/50 dark:bg-red-950/30 dark:text-red-300 flex items-start gap-3">
              <AlertCircle className="h-5 w-5 text-red-600 shrink-0 mt-0.5" />
              <div>
                <p className="font-medium">Failed to retrieve chunks</p>
                <p className="mt-0.5 leading-relaxed">{error}</p>
              </div>
            </div>
          )}

          {!loading && !error && chunks.length === 0 && (
            <div className="rounded-xl border border-dashed p-8 text-center text-muted-foreground space-y-2">
              <FileText className="h-8 w-8 mx-auto text-muted-foreground/60" />
              <p className="text-sm font-medium text-foreground">No chunks found</p>
              <p className="text-xs">
                This document may still be processing or has not generated any text chunks yet.
              </p>
            </div>
          )}

          {!loading &&
            !error &&
            chunks.map((chunk) => {
              const isCopied = copiedId === chunk.id;
              return (
                <div
                  key={chunk.id || chunk.chunk_index}
                  className="rounded-xl border bg-card p-4 shadow-sm hover:border-primary/30 transition-all space-y-3"
                >
                  {/* Chunk Header */}
                  <div className="flex items-center justify-between">
                    <div className="flex items-center gap-2">
                      <span className="inline-flex items-center gap-1 rounded-md bg-primary/10 px-2 py-0.5 text-xs font-semibold text-primary">
                        <Hash className="h-3 w-3" />
                        Chunk #{chunk.chunk_index}
                      </span>
                      {chunk.page && (
                        <Badge variant="outline" className="text-[11px] font-normal">
                          Page {chunk.page}
                        </Badge>
                      )}
                      <span className="text-[11px] text-muted-foreground font-mono">
                        {chunk.token_count} tokens • {chunk.char_count} chars
                      </span>
                    </div>

                    <button
                      onClick={() => copyChunkText(chunk.id, chunk.text)}
                      className="rounded-md p-1.5 text-muted-foreground hover:bg-muted hover:text-foreground transition-colors"
                      title="Copy chunk text"
                    >
                      {isCopied ? (
                        <Check className="h-4 w-4 text-emerald-600" />
                      ) : (
                        <Copy className="h-4 w-4" />
                      )}
                    </button>
                  </div>

                  {/* Chunk Text Excerpt */}
                  <div className="rounded-lg bg-muted/30 p-3.5 text-xs text-foreground/90 font-sans leading-relaxed whitespace-pre-wrap selection:bg-primary/20 border">
                    {chunk.text || "No text excerpt available."}
                  </div>

                  {/* Chunk ID */}
                  <div className="flex items-center justify-between text-[10px] text-muted-foreground/80 font-mono">
                    <span className="truncate max-w-[320px]">
                      Hash ID: {chunk.id}
                    </span>
                    {chunk.metadata?.section && (
                      <span className="truncate max-w-[140px] text-primary">
                        {chunk.metadata.section}
                      </span>
                    )}
                  </div>
                </div>
              );
            })}
        </div>

        {/* Footer */}
        <div className="border-t px-6 py-4 bg-muted/20 flex items-center justify-between">
          <span className="text-xs text-muted-foreground">
            Press <kbd className="px-1.5 py-0.5 rounded bg-muted border font-mono text-[10px]">Esc</kbd> to dismiss
          </span>
          <button
            onClick={onClose}
            className="rounded-lg bg-primary px-4 py-2 text-xs font-semibold text-primary-foreground hover:bg-primary/90 transition-colors"
          >
            Done
          </button>
        </div>
      </div>
    </>
  );
};
