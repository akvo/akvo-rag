"use client";

import { useParams, useSearchParams } from "next/navigation";
import { useState, useCallback } from "react";
import { DocumentUploadSteps } from "@/components/knowledge-base/document-upload-steps";
import { DocumentList } from "@/components/knowledge-base/document-list";
import { Button } from "@/components/ui/button";
import {
  Dialog,
  DialogContent,
  DialogDescription,
  DialogHeader,
  DialogTitle,
  DialogTrigger,
} from "@/components/ui/dialog";
import { PlusIcon } from "lucide-react";
import DashboardLayout from "@/components/layout/dashboard-layout";

export default function KnowledgeBasePage() {
  const params = useParams();
  const knowledgeBaseId = parseInt(params.id as string);
  const [refreshKey, setRefreshKey] = useState(0);
  const [dialogOpen, setDialogOpen] = useState(false);

  const searchParams = useSearchParams();
  const kbOwner = parseInt(searchParams.get("kb_owner") || "1");

  const handleUploadComplete = useCallback(() => {
    setRefreshKey((prev) => prev + 1);
    setDialogOpen(false);
  }, []);

  return (
    <DashboardLayout>
      <div className="flex justify-between items-start mb-8">
        <div className="space-y-5">
          <h1 className="text-3xl font-bold">Knowledge Base</h1>
          {/* TODO:: Enable this once view document validated
          <p className="text-sm text-gray-700 bg-gray-50 border-l-4 border-gray-400 p-2 rounded">
            Select a document name or view button to preview or download the file.
          </p> */}
        </div>
        {
          kbOwner ? (
            <Dialog open={dialogOpen} onOpenChange={setDialogOpen}>
              <DialogTrigger asChild>
                <Button>
                  <PlusIcon className="w-4 h-4 mr-2" />
                  Add Document
                </Button>
              </DialogTrigger>
              <DialogContent className="max-w-4xl">
                <DialogHeader>
                  <DialogTitle>Add Document</DialogTitle>
                  <DialogDescription>
                    Upload a document to your knowledge base. Supported formats:
                    PDF, DOCX, Markdown, and Text files.
                  </DialogDescription>
                </DialogHeader>
                <DocumentUploadSteps
                  knowledgeBaseId={knowledgeBaseId}
                  onComplete={handleUploadComplete}
                />
              </DialogContent>
            </Dialog>
          ) : null
        }
      </div>

      <div className="mt-8">
        <DocumentList key={refreshKey} knowledgeBaseId={knowledgeBaseId} />
      </div>
    </DashboardLayout>
  );
}
