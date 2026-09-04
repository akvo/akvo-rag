"use client";

import { useState, useCallback } from "react";
import { FileIcon, defaultStyles } from "react-file-icon";
import { Button } from "@/components/ui/button";
import { Card } from "@/components/ui/card";
import { Progress } from "@/components/ui/progress";
import { Tabs, TabsContent, TabsList, TabsTrigger } from "@/components/ui/tabs";
import { Input } from "@/components/ui/input";
import { Label } from "@/components/ui/label";
import { useToast } from "@/components/ui/use-toast";
import {
  Loader2,
  Upload,
  X,
  Settings,
  FileText,
  Copy,
  Check,
  Search,
  Layers,
  Sparkles,
  SlidersHorizontal,
  Hash,
  Eye,
} from "lucide-react";
import { Badge } from "@/components/ui/badge";
import { cn } from "@/lib/utils";
import { api, ApiError } from "@/lib/api";
import { useDropzone } from "react-dropzone";
import {
  Select,
  SelectContent,
  SelectItem,
  SelectTrigger,
  SelectValue,
} from "@/components/ui/select";
import {
  Accordion,
  AccordionContent,
  AccordionItem,
  AccordionTrigger,
} from "@/components/ui/accordion";

interface DocumentUploadStepsProps {
  knowledgeBaseId: number;
  onComplete?: () => void;
}

interface FileStatus {
  file: File;
  status:
    | "pending"
    | "uploading"
    | "uploaded"
    | "processing"
    | "completed"
    | "error";
  uploadId?: string | number;
  documentId?: string | number;
  tempPath?: string;
  error?: string;
}

interface UploadResult {
  id?: string | number;
  upload_id?: string | number;
  document_id?: string | number;
  file_name: string;
  status: "exists" | "pending" | "uploaded" | "PROCESSING" | "completed";
  message?: string;
  skip_processing: boolean;
  temp_path?: string;
}

interface PreviewChunk {
  content: string;
  metadata: Record<string, any>;
}

interface PreviewResponse {
  chunks: PreviewChunk[];
  total_chunks: number;
}

interface TaskResponse {
  tasks: Array<{
    upload_id: string | number;
    task_id: string | number;
  }>;
}

interface TaskStatus {
  document_id: string | number;
  status: "pending" | "processing" | "completed" | "failed";
  error_message?: string;
}

interface TaskStatusMap {
  [key: string]: TaskStatus;
}

interface TaskStatusResponse {
  [key: string]: TaskStatus;
}

export function DocumentUploadSteps({
  knowledgeBaseId,
  onComplete,
}: DocumentUploadStepsProps) {
  const [currentStep, setCurrentStep] = useState(1);
  const [files, setFiles] = useState<FileStatus[]>([]);
  const [uploadedDocuments, setUploadedDocuments] = useState<
    Record<string, PreviewResponse>
  >({});
  const [selectedDocumentId, setSelectedDocumentId] = useState<
    string | number | null
  >(null);
  const [taskStatuses, setTaskStatuses] = useState<TaskStatusMap>({});
  const [isLoading, setIsLoading] = useState(false);
  const [chunkSize, setChunkSize] = useState(1000);
  const [chunkOverlap, setChunkOverlap] = useState(200);
  const [chunkSearchQuery, setChunkSearchQuery] = useState("");
  const [copiedChunkIdx, setCopiedChunkIdx] = useState<number | null>(null);
  const { toast } = useToast();

  const handleCopyChunk = async (text: string, index: number) => {
    try {
      await navigator.clipboard.writeText(text);
      setCopiedChunkIdx(index);
      toast({
        title: "Copied chunk",
        description: `Chunk #${index + 1} content copied to clipboard.`,
      });
      setTimeout(() => setCopiedChunkIdx(null), 2000);
    } catch {
      toast({
        title: "Copy failed",
        description: "Failed to copy chunk content to clipboard.",
        variant: "destructive",
      });
    }
  };

  const onDrop = useCallback((acceptedFiles: File[]) => {
    setFiles((prev) => [
      ...prev,
      ...acceptedFiles.map((file) => ({
        file,
        status: "pending" as const,
      })),
    ]);
  }, []);

  const { getRootProps, getInputProps, isDragActive } = useDropzone({
    onDrop,
    accept: {
      "application/pdf": [".pdf"],
      "application/vnd.openxmlformats-officedocument.wordprocessingml.document":
        [".docx"],
      "text/plain": [".txt"],
      "text/markdown": [".md"],
    },
  });

  const removeFile = (file: File) => {
    setFiles((prev) => prev.filter((f) => f.file !== file));
  };

  // Step 1: Upload files
  const handleFileUpload = async () => {
    const pendingFiles = files.filter((f) => f.status === "pending" || f.status === "error");
    if (pendingFiles.length === 0) return;

    setIsLoading(true);
    try {
      const formData = new FormData();
      pendingFiles.forEach((fileStatus) => {
        formData.append("files", fileStatus.file);
      });

      const data = await api.post(
        `/api/knowledge-base/${knowledgeBaseId}/documents/upload`,
        formData
      );
      const dataArray = (Array.isArray(data) ? data : [data]) as UploadResult[];

      // Update file statuses with robust fallback matching
      const updatedFiles = files.map((f, idx) => {
        const uploadResult =
          dataArray.find(
            (d) =>
              d.file_name === f.file.name ||
              (d as any).filename === f.file.name ||
              (d as any).original_filename === f.file.name
          ) || dataArray[idx];

        if (uploadResult) {
          if (uploadResult.status === "exists") {
            return {
              ...f,
              status: "completed" as const,
              documentId:
                uploadResult.document_id ??
                (uploadResult as any).id ??
                idx + 1,
              error: uploadResult.message,
            };
          } else {
            const fallbackId =
              uploadResult.upload_id ??
              uploadResult.document_id ??
              (uploadResult as any).id ??
              idx + 1;
            return {
              ...f,
              status: "uploaded" as const,
              uploadId: fallbackId,
              documentId:
                uploadResult.document_id ??
                (uploadResult as any).id ??
                fallbackId,
              tempPath:
                uploadResult.temp_path ||
                (uploadResult as any).file_path ||
                "",
            };
          }
        }
        return f;
      });

      setFiles(updatedFiles);

      // Auto-select first uploaded document so preview button is active immediately
      const firstUploaded = updatedFiles.find(
        (f) => f.status === "uploaded" || f.status === "processing"
      );
      if (firstUploaded) {
        setSelectedDocumentId(
          firstUploaded.documentId ?? firstUploaded.uploadId ?? 1
        );
      }

      setCurrentStep(2);
      toast({
        title: "Upload successful",
        description: `${dataArray.length} files uploaded and enqueued for processing.`,
      });
    } catch (error) {
      toast({
        title: "Upload failed",
        description:
          error instanceof ApiError ? error.message : "Something went wrong",
        variant: "destructive",
      });
    } finally {
      setIsLoading(false);
    }
  };

  // Step 2: Preview chunks
  const handlePreview = async () => {
    const selectedFile = files.find(
      (f) =>
        f.documentId === selectedDocumentId || f.uploadId === selectedDocumentId
    );
    if (!selectedFile) return;

    setIsLoading(true);
    try {
      const data = await api.post(
        `/api/knowledge-base/${knowledgeBaseId}/documents/preview`,
        {
          document_ids: [selectedDocumentId],
          file_paths: selectedFile.tempPath ? [selectedFile.tempPath] : [],
          chunk_size: chunkSize,
          chunk_overlap: chunkOverlap,
        }
      );

      setUploadedDocuments(data);

      toast({
        title: "Preview generated",
        description: "Document preview generated successfully.",
      });
    } catch (error) {
      toast({
        title: "Preview failed",
        description:
          error instanceof ApiError ? error.message : "Something went wrong",
        variant: "destructive",
      });
    } finally {
      setIsLoading(false);
    }
  };

  // Step 3: Process documents
  const handleProcess = async (uploadResults?: UploadResult[]) => {
    const resultsToProcess =
      uploadResults ||
      files
        .filter((f) => f.status === "uploaded" || f.status === "processing")
        .map((f) => ({
          upload_id: f.uploadId!,
          document_id: f.documentId ?? f.uploadId!,
          file_name: f.file.name,
          chunk_size: chunkSize,
          chunk_overlap: chunkOverlap,
          status: "pending" as const,
          skip_processing: false,
          temp_path: f.tempPath!,
        }));

    if (resultsToProcess.length === 0) return;

    setIsLoading(true);
    try {
      const data = (await api.post(
        `/api/knowledge-base/${knowledgeBaseId}/documents/process`,
        resultsToProcess
      )) as TaskResponse;

      // Initialize task statuses
      const initialStatuses = data.tasks.reduce<TaskStatusMap>(
        (acc, task) => ({
          ...acc,
          [task.task_id]: {
            document_id: task.upload_id,
            status: "pending" as const,
          },
        }),
        {}
      );
      setTaskStatuses(initialStatuses);

      // Start polling for task status
      setTimeout(() => {
        pollTaskStatus(data.tasks.map((t) => t.task_id));
      }, 2000);
    } catch (error) {
      setIsLoading(false);
      toast({
        title: "Processing failed",
        description:
          error instanceof ApiError ? error.message : "Something went wrong",
        variant: "destructive",
      });
    }
  };

  // Poll task status
  const pollTaskStatus = async (taskIds: (string | number)[]) => {
    const poll = async () => {
      try {
        const response = (await api.get(
          `/api/knowledge-base/${knowledgeBaseId}/documents/tasks?task_ids=${taskIds.join(
            ","
          )}`
        )) as TaskStatusResponse;

        setTaskStatuses(response || {});

        // Check if all tasks are completed or failed
        const allDone = Object.values(response || {}).every(
          (task) => task.status === "completed" || task.status === "failed"
        );

        if (allDone) {
          setIsLoading(false);
          const hasErrors = Object.values(response || {}).some(
            (task) => task.status === "failed"
          );
          if (!hasErrors) {
            toast({
              title: "Processing completed",
              description: "All documents have been processed successfully.",
            });
            onComplete?.();
          } else {
            toast({
              title: "Processing completed with errors",
              description: "Some documents failed to process.",
              variant: "destructive",
            });
          }
        } else {
          // Continue polling
          setTimeout(poll, 2000);
        }
      } catch (error) {
        setIsLoading(false);
        toast({
          title: "Status check failed",
          description:
            error instanceof ApiError ? error.message : "Something went wrong",
          variant: "destructive",
        });
      }
    };

    poll();
  };

  const handleProcessClick = (e: React.MouseEvent) => {
    e.preventDefault();
    handleProcess();
  };

  return (
    <div className="w-full max-w-4xl mx-auto">
      <div className="mb-8">
        <div className="flex justify-between mb-2">
          {[
            { step: 1, icon: Upload, label: "Upload" },
            { step: 2, icon: FileText, label: "Preview" },
            { step: 3, icon: Settings, label: "Process" },
          ].map(({ step, icon: Icon, label }, index, array) => (
            <div
              key={step}
              className="flex flex-col items-center space-y-2 flex-1"
            >
              <div
                className={cn(
                  "w-12 h-12 rounded-full flex items-center justify-center border-2 transition-colors",
                  currentStep === step
                    ? "bg-primary text-primary-foreground border-primary"
                    : currentStep > step
                    ? "bg-primary/20 border-primary/20"
                    : "bg-background border-input"
                )}
              >
                <Icon className="w-6 h-6" />
              </div>
              <span className="text-sm font-medium">
                {step}. {label}
              </span>
              {index < array.length - 1 && (
                <div
                  className={cn(
                    "h-0.5 w-full mt-2",
                    currentStep > step ? "bg-primary/20" : "bg-input"
                  )}
                />
              )}
            </div>
          ))}
        </div>
      </div>

      <Tabs value={String(currentStep)} className="w-full">
        <TabsContent value="1" className="mt-6">
          <Card className="p-6">
            <div className="space-y-4">
              <div
                {...getRootProps()}
                className={cn(
                  "border-2 border-dashed rounded-lg p-8 text-center transition-colors",
                  isDragActive
                    ? "border-primary bg-primary/5"
                    : "hover:border-primary/50"
                )}
              >
                <input {...getInputProps()} />
                <Upload className="w-12 h-12 mx-auto text-muted-foreground" />
                <p className="mt-2 text-sm font-medium">
                  Drop your files here or click to browse
                </p>
                <p className="text-xs text-muted-foreground">
                  Supports PDF, DOCX, TXT, and MD files
                </p>
              </div>
              {files.length > 0 && (
                <div className="space-y-2 max-h-[300px] overflow-y-auto">
                  {files.map((fileStatus) => (
                    <div
                      key={fileStatus.file.name}
                      className="flex items-center justify-between p-4 rounded-lg border"
                    >
                      <div className="flex items-center space-x-4">
                        <div className="w-8 h-8">
                          <FileIcon
                            extension={fileStatus.file.name.split(".").pop()}
                            {...defaultStyles[
                              fileStatus.file.name
                                .split(".")
                                .pop() as keyof typeof defaultStyles
                            ]}
                          />
                        </div>
                        <div>
                          <p className="text-sm font-medium">
                            {fileStatus.file.name}
                          </p>
                          <p className="text-xs text-muted-foreground">
                            {(fileStatus.file.size / 1024 / 1024).toFixed(2)} MB
                          </p>
                        </div>
                      </div>
                      <div className="flex items-center space-x-2">
                        {fileStatus.status === "uploaded" && (
                          <span className="text-green-500 text-sm">
                            Uploaded
                          </span>
                        )}
                        {fileStatus.status === "error" && (
                          <span className="text-red-500 text-sm">
                            {fileStatus.error}
                          </span>
                        )}
                        <button
                          onClick={() => removeFile(fileStatus.file)}
                          className="p-1 hover:bg-accent rounded-full"
                        >
                          <X className="h-4 w-4" />
                        </button>
                      </div>
                    </div>
                  ))}
                </div>
              )}

              <Button
                onClick={handleFileUpload}
                disabled={
                  !files.some((f) => f.status === "pending") || isLoading
                }
                className="w-full"
              >
                {isLoading && <Loader2 className="mr-2 h-4 w-4 animate-spin" />}
                Upload Files
              </Button>
            </div>
          </Card>
        </TabsContent>

        <TabsContent value="2" className="mt-4">
          <Card className="p-4 sm:p-5">
            <div className="space-y-4">
              <div>
                <h3 className="text-base sm:text-lg font-semibold flex items-center gap-2">
                  <FileText className="h-5 w-5 text-primary" />
                  Select Document to Preview
                </h3>
                <p className="text-xs sm:text-sm text-muted-foreground mt-0.5">
                  Choose an uploaded document, fine-tune chunking hyperparameters, and preview the semantic chunks before vector ingestion.
                </p>
              </div>

              {/* Document Selector */}
              <div className="flex items-center space-x-4">
                <Select
                  value={selectedDocumentId?.toString()}
                  onValueChange={(value: string) =>
                    setSelectedDocumentId(value)
                  }
                >
                  <SelectTrigger className="w-full">
                    <SelectValue placeholder="Select a document to preview" />
                  </SelectTrigger>
                  <SelectContent>
                    {files
                      .filter(
                        (f) =>
                          f.status === "uploaded" ||
                          f.status === "processing" ||
                          f.status === "completed"
                      )
                      .map((f, idx) => {
                        const valId = (
                          f.uploadId ??
                          f.documentId ??
                          idx + 1
                        ).toString();
                        return (
                          <SelectItem key={valId} value={valId}>
                            {f.file.name}
                          </SelectItem>
                        );
                      })}
                  </SelectContent>
                </Select>
              </div>

              {/* Chunking Presets */}
              <div className="space-y-2.5 rounded-lg border bg-muted/20 p-3">
                <div className="flex items-center justify-between">
                  <div className="flex items-center gap-1.5">
                    <Sparkles className="h-4 w-4 text-primary" />
                    <span className="text-xs sm:text-sm font-medium">Chunk Strategy Presets</span>
                  </div>
                  <span className="text-[11px] text-muted-foreground">
                    Current: {chunkSize} tokens / {chunkOverlap} overlap
                  </span>
                </div>

                <div className="grid grid-cols-1 sm:grid-cols-3 gap-2">
                  {[
                    {
                      label: "Granular",
                      size: 500,
                      overlap: 100,
                      desc: "Exact facts & citations",
                    },
                    {
                      label: "Balanced",
                      size: 1000,
                      overlap: 200,
                      desc: "Standard QA & search",
                    },
                    {
                      label: "Context-Rich",
                      size: 2000,
                      overlap: 400,
                      desc: "Narrative & synthesis",
                    },
                  ].map((preset) => {
                    const isSelected =
                      chunkSize === preset.size && chunkOverlap === preset.overlap;
                    return (
                      <button
                        key={preset.label}
                        type="button"
                        onClick={() => {
                          setChunkSize(preset.size);
                          setChunkOverlap(preset.overlap);
                        }}
                        className={cn(
                          "flex flex-col items-start p-3 rounded-md border text-left transition-all",
                          isSelected
                            ? "border-primary bg-primary/10 shadow-sm"
                            : "border-border/60 hover:border-primary/50 hover:bg-muted/40"
                        )}
                      >
                        <div className="flex items-center justify-between w-full">
                          <span className="text-xs font-semibold">{preset.label}</span>
                          {isSelected && (
                            <Badge variant="default" className="text-[10px] px-1.5 py-0 h-4">
                              Active
                            </Badge>
                          )}
                        </div>
                        <span className="text-[11px] text-muted-foreground mt-0.5">
                          {preset.size} / {preset.overlap} tokens
                        </span>
                        <span className="text-[10px] text-muted-foreground/80 mt-1">
                          {preset.desc}
                        </span>
                      </button>
                    );
                  })}
                </div>
              </div>

              {/* Custom Settings Accordion */}
              <Accordion type="single" collapsible className="w-full">
                <AccordionItem value="settings">
                  <AccordionTrigger className="text-sm py-2">
                    <div className="flex items-center gap-2">
                      <SlidersHorizontal className="h-4 w-4" />
                      <span>Custom Token Settings</span>
                    </div>
                  </AccordionTrigger>
                  <AccordionContent>
                    <div className="grid gap-4 md:grid-cols-2 pt-2">
                      <div className="space-y-2">
                        <Label htmlFor="chunk-size">Chunk Size (tokens)</Label>
                        <Input
                          id="chunk-size"
                          type="number"
                          value={chunkSize}
                          onChange={(e) =>
                            setChunkSize(parseInt(e.target.value) || 0)
                          }
                        />
                      </div>
                      <div className="space-y-2">
                        <Label htmlFor="chunk-overlap">
                          Chunk Overlap (tokens)
                        </Label>
                        <Input
                          id="chunk-overlap"
                          type="number"
                          value={chunkOverlap}
                          onChange={(e) =>
                            setChunkOverlap(parseInt(e.target.value) || 0)
                          }
                        />
                      </div>
                    </div>
                  </AccordionContent>
                </AccordionItem>
              </Accordion>

              {/* Action Buttons */}
              <div className="flex space-x-4">
                <Button
                  onClick={handlePreview}
                  disabled={isLoading || !selectedDocumentId}
                  className="flex-1"
                >
                  {isLoading ? (
                    <>
                      <Loader2 className="mr-2 h-4 w-4 animate-spin" />
                      Generating Preview...
                    </>
                  ) : (
                    <>
                      <Eye className="mr-2 h-4 w-4" />
                      Preview Chunks
                    </>
                  )}
                </Button>
                <Button
                  onClick={() => setCurrentStep(3)}
                  variant="secondary"
                  className="flex-1"
                >
                  Continue to Processing
                </Button>
              </div>

              {/* Preview Display Section */}
              {(() => {
                const currentPreview: PreviewResponse | undefined =
                  (selectedDocumentId != null
                    ? uploadedDocuments[String(selectedDocumentId)] ||
                      uploadedDocuments[selectedDocumentId as any]
                    : undefined) || Object.values(uploadedDocuments)[0];

                if (!currentPreview || !currentPreview.chunks?.length) {
                  return null;
                }

                const selectedFile =
                  files.find(
                    (f: FileStatus) =>
                      String(f.uploadId ?? f.documentId) ===
                        String(selectedDocumentId) ||
                      f.documentId === selectedDocumentId ||
                      f.uploadId === selectedDocumentId
                  ) || files[0];

                const allChunks = currentPreview.chunks || [];
                const totalChars = allChunks.reduce(
                  (sum, c) => sum + (c.content?.length || 0),
                  0
                );
                const avgChars =
                  allChunks.length > 0
                    ? Math.round(totalChars / allChunks.length)
                    : 0;
                const avgWords =
                  allChunks.length > 0
                    ? Math.round(
                        allChunks.reduce(
                          (sum, c) =>
                            sum + (c.content ? c.content.trim().split(/\s+/).length : 0),
                          0
                        ) / allChunks.length
                      )
                    : 0;

                const query = chunkSearchQuery.trim().toLowerCase();
                const filteredChunks = query
                  ? allChunks
                      .map((chunk, origIdx) => ({ chunk, origIdx }))
                      .filter(
                        ({ chunk, origIdx }) =>
                          chunk.content.toLowerCase().includes(query) ||
                          `chunk ${origIdx + 1}`.includes(query)
                      )
                  : allChunks.map((chunk, origIdx) => ({ chunk, origIdx }));

                return (
                  <div className="space-y-4 pt-2">
                    {/* Metrics Summary Ribbon */}
                    <div className="grid grid-cols-2 md:grid-cols-4 gap-3">
                      <div className="p-3 rounded-lg border bg-card text-card-foreground shadow-sm">
                        <div className="flex items-center justify-between text-xs text-muted-foreground">
                          <span>Total Chunks</span>
                          <Layers className="h-3.5 w-3.5 text-primary" />
                        </div>
                        <div className="text-xl font-bold mt-1">
                          {currentPreview.total_chunks || allChunks.length}
                        </div>
                        <div className="text-[11px] text-muted-foreground mt-0.5">
                          {allChunks.length} chunks previewed
                        </div>
                      </div>

                      <div className="p-3 rounded-lg border bg-card text-card-foreground shadow-sm">
                        <div className="flex items-center justify-between text-xs text-muted-foreground">
                          <span>Avg Chunk Size</span>
                          <Sparkles className="h-3.5 w-3.5 text-primary" />
                        </div>
                        <div className="text-xl font-bold mt-1">
                          ~{avgChars} chars
                        </div>
                        <div className="text-[11px] text-muted-foreground mt-0.5">
                          ~{avgWords} words/chunk
                        </div>
                      </div>

                      <div className="p-3 rounded-lg border bg-card text-card-foreground shadow-sm">
                        <div className="flex items-center justify-between text-xs text-muted-foreground">
                          <span>Window Size</span>
                          <SlidersHorizontal className="h-3.5 w-3.5 text-primary" />
                        </div>
                        <div className="text-xl font-bold mt-1">
                          {chunkSize}
                        </div>
                        <div className="text-[11px] text-muted-foreground mt-0.5">
                          target tokens
                        </div>
                      </div>

                      <div className="p-3 rounded-lg border bg-card text-card-foreground shadow-sm">
                        <div className="flex items-center justify-between text-xs text-muted-foreground">
                          <span>Overlap</span>
                          <Hash className="h-3.5 w-3.5 text-primary" />
                        </div>
                        <div className="text-xl font-bold mt-1">
                          {chunkOverlap}
                        </div>
                        <div className="text-[11px] text-muted-foreground mt-0.5">
                          {Math.round((chunkOverlap / (chunkSize || 1)) * 100)}% context overlap
                        </div>
                      </div>
                    </div>

                    {/* Search & Header */}
                    <div className="flex flex-col sm:flex-row sm:items-center justify-between gap-3 pt-2">
                      <div>
                        <h4 className="text-sm font-semibold flex items-center gap-2">
                          <span>Previewing: {selectedFile?.file?.name || "Document"}</span>
                        </h4>
                        <p className="text-xs text-muted-foreground">
                          {query
                            ? `Showing ${filteredChunks.length} of ${allChunks.length} chunks matching "${chunkSearchQuery}"`
                            : `Showing all ${allChunks.length} preview chunks`}
                        </p>
                      </div>

                      <div className="relative w-full sm:w-64">
                        <Search className="absolute left-2.5 top-2.5 h-3.5 w-3.5 text-muted-foreground" />
                        <Input
                          placeholder="Search in chunks..."
                          value={chunkSearchQuery}
                          onChange={(e) => setChunkSearchQuery(e.target.value)}
                          className="h-8 pl-8 pr-7 text-xs"
                        />
                        {chunkSearchQuery && (
                          <button
                            type="button"
                            onClick={() => setChunkSearchQuery("")}
                            className="absolute right-2 top-2.5 text-muted-foreground hover:text-foreground"
                          >
                            <X className="h-3.5 w-3.5" />
                          </button>
                        )}
                      </div>
                    </div>

                    {/* Chunk Cards Stream */}
                    <div className="max-h-[320px] sm:max-h-[360px] overflow-y-auto space-y-2.5 rounded-lg border bg-muted/10 p-3">
                      {filteredChunks.length === 0 ? (
                        <div className="flex flex-col items-center justify-center h-48 text-center text-muted-foreground p-6">
                          <Search className="h-8 w-8 mb-2 opacity-40" />
                          <p className="text-sm font-medium">No chunks matched your search</p>
                          <p className="text-xs mt-1">Try a different keyword or clear the search query.</p>
                          <Button
                            variant="outline"
                            size="sm"
                            onClick={() => setChunkSearchQuery("")}
                            className="mt-3 text-xs h-7"
                          >
                            Clear Search
                          </Button>
                        </div>
                      ) : (
                        filteredChunks.map(({ chunk, origIdx }) => {
                          const isCopied = copiedChunkIdx === origIdx;
                          const chunkWordCount = chunk.content
                            ? chunk.content.trim().split(/\s+/).length
                            : 0;

                          return (
                            <div
                              key={origIdx}
                              className="group relative rounded-lg border bg-card text-card-foreground shadow-sm transition-all hover:border-primary/40 hover:shadow"
                            >
                              {/* Card Header */}
                              <div className="flex items-center justify-between border-b px-4 py-2.5 bg-muted/30">
                                <div className="flex items-center gap-2 flex-wrap">
                                  <Badge
                                    variant="secondary"
                                    className="font-mono text-xs font-semibold px-2 py-0.5"
                                  >
                                    Chunk #{origIdx + 1}
                                  </Badge>
                                  <span className="text-[11px] text-muted-foreground">
                                    {chunk.content.length} chars • ~{chunkWordCount} words
                                  </span>
                                  {chunk.metadata &&
                                    Object.entries(chunk.metadata).map(([k, v]) => {
                                      if (!v || typeof v === "object") return null;
                                      return (
                                        <Badge
                                          key={k}
                                          variant="outline"
                                          className="text-[10px] px-1.5 py-0 text-muted-foreground font-normal"
                                        >
                                          {k}: {String(v)}
                                        </Badge>
                                      );
                                    })}
                                </div>

                                <Button
                                  variant="ghost"
                                  size="sm"
                                  onClick={() => handleCopyChunk(chunk.content, origIdx)}
                                  className="h-7 px-2 text-xs text-muted-foreground hover:text-foreground"
                                  title="Copy chunk text"
                                >
                                  {isCopied ? (
                                    <>
                                      <Check className="mr-1 h-3.5 w-3.5 text-green-500" />
                                      <span className="text-green-500">Copied</span>
                                    </>
                                  ) : (
                                    <>
                                      <Copy className="mr-1 h-3.5 w-3.5" />
                                      <span>Copy</span>
                                    </>
                                  )}
                                </Button>
                              </div>

                              {/* Card Content */}
                              <div className="p-4">
                                <pre className="whitespace-pre-wrap font-sans text-xs leading-relaxed text-foreground/90 select-text overflow-x-auto">
                                  {chunk.content}
                                </pre>
                              </div>
                            </div>
                          );
                        })
                      )}
                    </div>
                  </div>
                );
              })()}
            </div>
          </Card>
        </TabsContent>
        <TabsContent value="3" className="mt-6">
          <Card className="p-6">
            <div className="space-y-4">
              <div className="max-h-[300px] overflow-y-auto space-y-2 rounded-lg border p-4">
                {files
                  .filter(
                    (f) =>
                      f.status === "uploaded" ||
                      f.status === "processing" ||
                      f.status === "completed"
                  )
                  .map((file, idx) => {
                    const fileUploadId =
                      file.uploadId ?? file.documentId ?? idx + 1;
                    const task = Object.values(taskStatuses).find(
                      (t) =>
                        t.document_id === file.documentId ||
                        t.document_id === fileUploadId
                    );
                    return (
                      <div
                        key={fileUploadId}
                        className="p-4 border rounded-lg space-y-2"
                      >
                        <div className="flex items-center justify-between">
                          <div className="flex items-center space-x-4">
                            <div className="w-8 h-8">
                              <FileIcon
                                extension={file.file.name.split(".").pop()}
                                {...defaultStyles[
                                  file.file.name
                                    .split(".")
                                    .pop() as keyof typeof defaultStyles
                                ]}
                              />
                            </div>
                            <div>
                              <p className="text-sm font-medium">
                                {file.file.name}
                              </p>
                              <p className="text-xs text-muted-foreground">
                                {(file.file.size / 1024 / 1024).toFixed(2)} MB
                              </p>
                              {task && (
                                <p className="text-xs text-muted-foreground">
                                  Status: {task.status || "pending"}
                                </p>
                              )}
                            </div>
                          </div>
                          {task?.status === "failed" && (
                            <p className="text-sm text-destructive">
                              {task.error_message}
                            </p>
                          )}
                        </div>
                        {task &&
                          (task.status === "pending" ||
                            task.status === "processing") && (
                            <Progress
                              value={task.status === "processing" ? 50 : 25}
                              className="w-full"
                            />
                          )}
                      </div>
                    );
                  })}
              </div>

              <Button
                onClick={handleProcessClick}
                disabled={
                  isLoading ||
                  files.filter(
                    (f) =>
                      f.status === "uploaded" || f.status === "processing"
                  ).length === 0
                }
                className="w-full"
              >
                {isLoading ? (
                  <>
                    <Loader2 className="mr-2 h-4 w-4 animate-spin" />
                    Processing...
                  </>
                ) : (
                  <>
                    <Settings className="mr-2 h-4 w-4" />
                    Process
                  </>
                )}
              </Button>
            </div>
          </Card>
        </TabsContent>
      </Tabs>
    </div>
  );
}
