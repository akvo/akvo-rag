"use client";

import React, { FC } from "react";
import { X, ExternalLink, FileText, CheckCircle2, Layers, BookOpen } from "lucide-react";
import { FileIcon } from "react-file-icon";

export interface CitationMetadata {
  kb_id?: number;
  kb_name?: string;
  doc_id?: number;
  document_id?: number;
  file_name?: string;
  source?: string;
  page?: number;
  chunk_id?: number | string;
  chunk_index?: number;
  score?: number;
  similarity?: number;
  [key: string]: any;
}

export interface CitationDrawerItem {
  id: number;
  text: string;
  metadata?: CitationMetadata;
  kb_name?: string;
  doc_name?: string;
}

interface CitationDrawerProps {
  isOpen: boolean;
  onClose: () => void;
  citation: CitationDrawerItem | null;
  allCitations?: CitationDrawerItem[];
  onSelectCitation?: (citation: CitationDrawerItem) => void;
}

export const CitationDrawer: FC<CitationDrawerProps> = ({
  isOpen,
  onClose,
  citation,
  allCitations = [],
  onSelectCitation,
}) => {
  if (!isOpen || !citation) return null;

  const fileExt =
    citation.doc_name?.split(".").pop() ||
    citation.metadata?.file_name?.split(".").pop() ||
    citation.metadata?.source?.split(".").pop() ||
    "txt";

  const docName =
    citation.doc_name ||
    citation.metadata?.file_name ||
    citation.metadata?.source ||
    `Source Document #${citation.id}`;

  const kbName =
    citation.kb_name ||
    citation.metadata?.kb_name ||
    (citation.metadata?.kb_id ? `Knowledge Base #${citation.metadata.kb_id}` : "Global Knowledge Base");

  const pageNum = citation.metadata?.page || citation.metadata?.page_number;
  const chunkIndex = citation.metadata?.chunk_index ?? citation.metadata?.chunk_id;
  const similarityScore = citation.metadata?.score ?? citation.metadata?.similarity;

  const formattedScore =
    typeof similarityScore === "number"
      ? `${Math.round((1 - Math.min(similarityScore, 1)) * 100)}% Match`
      : "Highly Relevant";

  return (
    <>
      {/* Backdrop */}
      <div
        onClick={onClose}
        className="fixed inset-0 z-50 bg-black/40 backdrop-blur-sm transition-opacity duration-200"
      />

      {/* Slide-Over Panel */}
      <div className="fixed inset-y-0 right-0 z-50 flex w-full max-w-lg flex-col bg-background border-l shadow-2xl transition-transform duration-300 ease-in-out sm:max-w-xl">
        {/* Header */}
        <div className="flex items-center justify-between border-b px-6 py-4 bg-muted/30">
          <div className="flex items-center gap-3 min-w-0">
            <div className="flex h-9 w-9 shrink-0 items-center justify-center rounded-lg bg-primary/10 text-primary">
              <BookOpen className="h-5 w-5" />
            </div>
            <div className="min-w-0">
              <div className="flex items-center gap-2">
                <h3 className="text-base font-semibold text-foreground truncate">
                  Source Reference [{citation.id}]
                </h3>
                <span className="rounded-full bg-primary/10 px-2 py-0.5 text-[11px] font-medium text-primary border border-primary/20">
                  {formattedScore}
                </span>
              </div>
              <p className="text-xs text-muted-foreground truncate">{kbName}</p>
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

        {/* Citations navigation pills if multiple */}
        {allCitations.length > 1 && (
          <div className="flex items-center gap-1.5 border-b px-6 py-2.5 overflow-x-auto bg-muted/10">
            <span className="text-xs font-medium text-muted-foreground mr-1 shrink-0">
              Citations:
            </span>
            {allCitations.map((c) => {
              const isSelected = c.id === citation.id;
              return (
                <button
                  key={c.id}
                  onClick={() => onSelectCitation && onSelectCitation(c)}
                  className={`px-2.5 py-1 text-xs font-medium rounded-md transition-all shrink-0 ${
                    isSelected
                      ? "bg-primary text-primary-foreground shadow-sm"
                      : "bg-muted hover:bg-muted/80 text-muted-foreground hover:text-foreground"
                  }`}
                >
                  [{c.id}]
                </button>
              );
            })}
          </div>
        )}

        {/* Scrollable Body */}
        <div className="flex-1 overflow-y-auto px-6 py-6 space-y-6">
          {/* Document Card */}
          <div className="rounded-xl border bg-card p-4 shadow-sm space-y-3">
            <div className="flex items-start gap-3">
              <div className="h-8 w-8 shrink-0 flex items-center justify-center">
                <FileIcon extension={fileExt} color="#0D9488" labelColor="#0F766E" />
              </div>
              <div className="min-w-0 flex-1">
                <h4 className="text-sm font-semibold text-foreground break-words">
                  {docName}
                </h4>
                <div className="flex flex-wrap items-center gap-2 mt-1 text-xs text-muted-foreground">
                  <span className="inline-flex items-center gap-1">
                    <Layers className="h-3.5 w-3.5 text-primary" />
                    {kbName}
                  </span>
                  {pageNum && (
                    <>
                      <span>•</span>
                      <span>Page {pageNum}</span>
                    </>
                  )}
                  {chunkIndex !== undefined && (
                    <>
                      <span>•</span>
                      <span>Chunk #{chunkIndex}</span>
                    </>
                  )}
                </div>
              </div>
            </div>
          </div>

          {/* Excerpt Section */}
          <div className="space-y-2">
            <div className="flex items-center justify-between">
              <span className="text-xs font-bold uppercase tracking-wider text-muted-foreground flex items-center gap-1.5">
                <FileText className="h-4 w-4 text-primary" />
                Retrieved Context Excerpt
              </span>
              <span className="text-[11px] text-muted-foreground">
                Grounded source used for AI synthesis
              </span>
            </div>

            <div className="rounded-xl border bg-muted/30 p-4 font-sans text-sm text-foreground/90 leading-relaxed whitespace-pre-wrap selection:bg-primary/20 shadow-inner">
              {citation.text || "No excerpt text available for this reference."}
            </div>
          </div>

          {/* Quality & Grounding Indicator */}
          <div className="rounded-lg bg-primary/5 border border-primary/10 p-3.5 flex items-start gap-3">
            <CheckCircle2 className="h-4 w-4 text-primary mt-0.5 shrink-0" />
            <div className="text-xs space-y-1">
              <p className="font-medium text-foreground">Verified Vector Grounding</p>
              <p className="text-muted-foreground leading-normal">
                This document chunk was retrieved with semantic similarity from ChromaDB and injected into the LangGraph state machine.
              </p>
            </div>
          </div>
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
