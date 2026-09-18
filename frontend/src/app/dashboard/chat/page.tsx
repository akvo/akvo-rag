"use client";

import { useEffect, useState } from "react";
import { useRouter } from "next/navigation";
import Image from "next/image";
import {
  Send,
  Sparkles,
  Layers,
  Globe,
  BookOpen,
  HelpCircle,
  FileText,
  Lightbulb,
  Search,
  Check,
} from "lucide-react";
import DashboardLayout from "@/components/layout/dashboard-layout";
import { api, ApiError } from "@/lib/api";
import { useToast } from "@/components/ui/use-toast";
import { Tag } from "@/components/ui/tag";
import {
  ChatSidebar,
  ChatSessionSummary,
} from "@/components/chat/chat-sidebar";

interface KnowledgeBaseItem {
  id: number;
  name: string;
  description?: string;
  is_superuser?: boolean;
}

const STARTER_PROMPTS = [
  {
    icon: Sparkles,
    title: "Summarize Documents",
    prompt: "Summarize the main insights and recommendations from the uploaded knowledge base.",
  },
  {
    icon: FileText,
    title: "Key Findings Analysis",
    prompt: "What are the key findings, methodologies, and outcomes described across our documents?",
  },
  {
    icon: Lightbulb,
    title: "Identify Action Items",
    prompt: "Extract the core action items and best practices recommended in the knowledge base.",
  },
  {
    icon: HelpCircle,
    title: "Ask a Specific Question",
    prompt: "Explain the technical architecture and data retrieval workflow used in this system.",
  },
];

export default function ChatOverviewPage() {
  const router = useRouter();
  const { toast } = useToast();
  const [chats, setChats] = useState<ChatSessionSummary[]>([]);
  const [loadingChats, setLoadingChats] = useState(true);
  const [input, setInput] = useState("");
  const [isSubmitting, setIsSubmitting] = useState(false);

  // Knowledge Base selection state
  const [availableKBs, setAvailableKBs] = useState<KnowledgeBaseItem[]>([]);
  const [selectedKBFilter, setSelectedKBFilter] = useState<number[]>([]);
  const [kbSearchTerm, setKbSearchTerm] = useState("");
  const [loadingKBs, setLoadingKBs] = useState(true);

  useEffect(() => {
    fetchChats();
    fetchAvailableKnowledgeBases();
  }, []);

  const fetchChats = async () => {
    try {
      const data = await api.get("/api/chat");
      setChats(data);
    } catch (error) {
      console.error("Failed to fetch chats:", error);
    } finally {
      setLoadingChats(false);
    }
  };

  const fetchAvailableKnowledgeBases = async () => {
    try {
      const data = await api.get("/api/knowledge-base");
      setAvailableKBs(data);
    } catch (error) {
      console.error("Failed to fetch knowledge bases:", error);
    } finally {
      setLoadingKBs(false);
    }
  };

  const handleDeleteSidebarChat = async (id: number) => {
    if (!confirm("Are you sure you want to delete this conversation?")) return;
    try {
      await api.delete(`/api/chat/${id}`);
      setChats((prev) => prev.filter((c) => c.id !== id));
      toast({
        title: "Success",
        description: "Conversation deleted",
      });
    } catch (error) {
      console.error("Failed to delete chat:", error);
    }
  };

  const handleRenameSidebarChat = async (id: number, newTitle: string) => {
    try {
      await api.put(`/api/chat/${id}`, { title: newTitle });
      setChats((prev) =>
        prev.map((c) => (c.id === id ? { ...c, title: newTitle } : c))
      );
      toast({
        title: "Success",
        description: "Conversation renamed",
      });
    } catch (error) {
      console.error("Failed to rename chat:", error);
      toast({
        title: "Error",
        description: "Failed to rename conversation",
        variant: "destructive",
      });
    }
  };

  const toggleKBSelection = (kbId: number) => {
    setSelectedKBFilter((prev) =>
      prev.includes(kbId) ? prev.filter((id) => id !== kbId) : [...prev, kbId]
    );
  };

  const selectAllKBs = () => {
    setSelectedKBFilter([]);
  };

  const handleStartConversation = async (promptText: string) => {
    if (!promptText.trim() || isSubmitting) return;

    setIsSubmitting(true);
    try {
      // Derive a short title from the prompt
      const title =
        promptText.length > 40
          ? `${promptText.substring(0, 40)}...`
          : promptText;

      const newChat = await api.post("/api/chat", {
        title,
        knowledge_base_ids: selectedKBFilter,
      });

      // Navigate to chat detail page and auto-send prompt
      router.push(
        `/dashboard/chat/${newChat.id}?prompt=${encodeURIComponent(promptText)}`
      );
    } catch (error) {
      console.error("Failed to initialize new conversation:", error);
      if (error instanceof ApiError) {
        toast({
          title: "Error",
          description: error.message,
          variant: "destructive",
        });
      } else {
        toast({
          title: "Error",
          description: "Failed to start chat",
          variant: "destructive",
        });
      }
    } finally {
      setIsSubmitting(false);
    }
  };

  const filteredKBs = availableKBs.filter(
    (kb) =>
      kb.name.toLowerCase().includes(kbSearchTerm.toLowerCase()) ||
      (kb.description &&
        kb.description.toLowerCase().includes(kbSearchTerm.toLowerCase()))
  );

  return (
    <DashboardLayout>
      <div className="flex h-[calc(100vh-4.5rem)] overflow-hidden rounded-2xl border bg-background shadow-xs">
        {/* Left 2-Pane Conversation Sidebar */}
        <ChatSidebar
          chats={chats}
          onDeleteChat={handleDeleteSidebarChat}
          onRenameChat={handleRenameSidebarChat}
          isLoading={loadingChats}
        />

        {/* Central Chat Canvas */}
        <div className="flex flex-1 flex-col h-full relative overflow-hidden bg-background">
          {/* Canvas Top Bar */}
          <div className="flex items-center justify-between border-b px-6 py-3.5 bg-card/60 backdrop-blur-sm z-10">
            <div className="flex items-center gap-3 min-w-0">
              <div className="h-8 w-8 rounded-lg bg-primary/10 flex items-center justify-center shrink-0">
                <Sparkles className="h-4 w-4 text-primary" />
              </div>
              <div>
                <h2 className="text-sm font-semibold text-foreground">
                  Start New Conversation
                </h2>
                <p className="text-[11px] text-muted-foreground">
                  {selectedKBFilter.length === 0
                    ? "Searching across All Knowledge Bases"
                    : `Scoped to ${selectedKBFilter.length} Selected Knowledge Base(s)`}
                </p>
              </div>
            </div>

            <div className="hidden sm:flex items-center gap-1.5 bg-muted/60 border rounded-full px-3 py-1 text-xs text-muted-foreground">
              <Layers className="h-3.5 w-3.5 text-primary" />
              <span>ChromaDB Vector Store</span>
            </div>
          </div>

          {/* Canvas Center / Interactive Workspace */}
          <div className="flex-1 overflow-y-auto px-4 sm:px-8 py-6 max-w-4xl mx-auto w-full space-y-6">
            {/* Hero Header */}
            <div className="text-center space-y-2">
              <div className="inline-flex h-12 w-12 items-center justify-center rounded-2xl bg-primary/10 border border-primary/20 shadow-sm mx-auto overflow-hidden">
                <Image
                  src="/logo.png"
                  width={32}
                  height={32}
                  className="rounded-md object-contain"
                  alt="Akvo RAG"
                />
              </div>
              <h1 className="text-2xl sm:text-3xl font-bold tracking-tight bg-gradient-to-r from-primary to-primary/60 bg-clip-text text-transparent">
                What would you like to explore?
              </h1>
              <p className="text-xs sm:text-sm text-muted-foreground max-w-md mx-auto">
                Select your knowledge base scope first, then ask a question to start exploring.
              </p>
            </div>

            {/* Step 1: Select Knowledge Base Scope */}
            <div className="space-y-3 bg-card rounded-2xl border p-5 shadow-xs">
              <div className="flex flex-col sm:flex-row sm:items-center justify-between gap-2">
                <div className="flex items-center gap-2">
                  <span className="flex h-6 w-6 items-center justify-center rounded-full bg-primary text-primary-foreground text-xs font-bold">
                    1
                  </span>
                  <h3 className="text-sm font-semibold text-foreground">
                    Select Knowledge Base Scope
                  </h3>
                </div>

                {/* Search input for KBs */}
                <div className="relative w-full sm:w-64">
                  <Search className="absolute left-2.5 top-1/2 -translate-y-1/2 h-3.5 w-3.5 text-muted-foreground" />
                  <input
                    type="text"
                    placeholder="Search knowledge bases..."
                    value={kbSearchTerm}
                    onChange={(e) => setKbSearchTerm(e.target.value)}
                    className="w-full pl-8 pr-3 py-1.5 text-xs rounded-xl border bg-background outline-none focus:ring-1 focus:ring-primary focus:border-primary transition-all placeholder:text-muted-foreground"
                  />
                </div>
              </div>

              {/* KB Grid */}
              <div className="grid gap-2.5 sm:grid-cols-2 max-h-56 overflow-y-auto pr-1">
                {/* All Knowledge Bases Option */}
                <button
                  type="button"
                  onClick={selectAllKBs}
                  className={`flex items-start gap-3 p-3 rounded-xl border text-left transition-all ${
                    selectedKBFilter.length === 0
                      ? "border-primary bg-primary/5 shadow-xs ring-1 ring-primary/20"
                      : "hover:border-primary/40 bg-background"
                  }`}
                >
                  <div
                    className={`h-7 w-7 rounded-lg flex items-center justify-center shrink-0 mt-0.5 ${
                      selectedKBFilter.length === 0
                        ? "bg-primary text-primary-foreground"
                        : "bg-muted text-muted-foreground"
                    }`}
                  >
                    <Globe className="h-4 w-4" />
                  </div>
                  <div className="flex-1 min-w-0">
                    <div className="flex items-center justify-between">
                      <h4 className="text-xs font-semibold text-foreground">
                        All Knowledge Bases
                      </h4>
                      {selectedKBFilter.length === 0 && (
                        <span className="flex h-4 w-4 items-center justify-center rounded-full bg-primary text-primary-foreground text-[10px]">
                          <Check className="h-2.5 w-2.5" />
                        </span>
                      )}
                    </div>
                    <p className="text-[11px] text-muted-foreground mt-0.5">
                      Search across all available collections
                    </p>
                  </div>
                </button>

                {/* Individual KB Cards */}
                {filteredKBs.map((kb) => {
                  const isSelected = selectedKBFilter.includes(kb.id);
                  return (
                    <button
                      key={kb.id}
                      type="button"
                      onClick={() => toggleKBSelection(kb.id)}
                      className={`flex items-start gap-3 p-3 rounded-xl border text-left transition-all ${
                        isSelected
                          ? "border-primary bg-primary/5 shadow-xs ring-1 ring-primary/20"
                          : "hover:border-primary/40 bg-background"
                      }`}
                    >
                      <div
                        className={`h-7 w-7 rounded-lg flex items-center justify-center shrink-0 mt-0.5 ${
                          isSelected
                            ? "bg-primary text-primary-foreground"
                            : "bg-muted text-muted-foreground"
                        }`}
                      >
                        <BookOpen className="h-4 w-4" />
                      </div>
                      <div className="flex-1 min-w-0">
                        <div className="flex items-center justify-between gap-1">
                          <h4 className="text-xs font-semibold text-foreground truncate">
                            {kb.name}
                          </h4>
                          {isSelected && (
                            <span className="flex h-4 w-4 items-center justify-center rounded-full bg-primary text-primary-foreground text-[10px] shrink-0">
                              <Check className="h-2.5 w-2.5" />
                            </span>
                          )}
                        </div>
                        <div className="flex items-center gap-1.5 mt-0.5">
                          {kb.is_superuser ? (
                            <Tag label="Public" color="bg-green-100 text-green-800 text-[10px]" />
                          ) : (
                            <Tag label="Private" color="bg-muted text-muted-foreground text-[10px]" />
                          )}
                          <p className="text-[11px] text-muted-foreground truncate">
                            {kb.description || "No description"}
                          </p>
                        </div>
                      </div>
                    </button>
                  );
                })}
              </div>
            </div>

            {/* Step 2: Suggested Starter Prompts */}
            <div className="space-y-3">
              <div className="flex items-center gap-2">
                <span className="flex h-6 w-6 items-center justify-center rounded-full bg-primary text-primary-foreground text-xs font-bold">
                  2
                </span>
                <h3 className="text-sm font-semibold text-foreground">
                  Ask a question or select a starter prompt
                </h3>
              </div>

              <div className="grid gap-2.5 sm:grid-cols-2">
                {STARTER_PROMPTS.map((starter, idx) => {
                  const IconComponent = starter.icon;
                  return (
                    <button
                      key={idx}
                      type="button"
                      onClick={() => {
                        setInput(starter.prompt);
                        handleStartConversation(starter.prompt);
                      }}
                      disabled={isSubmitting}
                      className="flex items-start gap-3 p-3.5 rounded-xl border bg-card hover:bg-muted/40 text-left transition-all hover:shadow-xs group disabled:opacity-50"
                    >
                      <div className="h-7 w-7 rounded-lg bg-primary/10 text-primary flex items-center justify-center shrink-0 group-hover:bg-primary group-hover:text-primary-foreground transition-colors">
                        <IconComponent className="h-3.5 w-3.5" />
                      </div>
                      <div className="flex-1 min-w-0">
                        <h4 className="text-xs font-semibold text-foreground group-hover:text-primary transition-colors">
                          {starter.title}
                        </h4>
                        <p className="text-[11px] text-muted-foreground mt-0.5 line-clamp-2">
                          {starter.prompt}
                        </p>
                      </div>
                    </button>
                  );
                })}
              </div>
            </div>
          </div>

          {/* Instant Composer */}
          <div className="border-t bg-card/80 backdrop-blur-md p-4">
            <form
              onSubmit={(e) => {
                e.preventDefault();
                handleStartConversation(input);
              }}
              className="flex items-center gap-2"
            >
              <input
                value={input}
                onChange={(e) => setInput(e.target.value)}
                placeholder={
                  selectedKBFilter.length === 0
                    ? "Ask a question across All Knowledge Bases..."
                    : `Ask a question to ${selectedKBFilter.length} selected knowledge base(s)...`
                }
                className="flex-1 h-11 rounded-xl border bg-background px-4 text-sm outline-none ring-offset-background placeholder:text-muted-foreground focus-visible:ring-2 focus-visible:ring-primary/30 focus-visible:border-primary transition-all shadow-xs"
              />
              <button
                type="submit"
                disabled={isSubmitting || !input.trim()}
                className="inline-flex items-center justify-center rounded-xl bg-primary text-primary-foreground font-semibold h-11 px-5 text-sm shadow-sm hover:bg-primary/90 hover:shadow disabled:opacity-50 transition-all gap-1.5 shrink-0"
              >
                <Send className="h-4 w-4" />
                <span className="hidden sm:inline">
                  {isSubmitting ? "Starting..." : "Start Chat"}
                </span>
              </button>
            </form>
          </div>
        </div>
      </div>
    </DashboardLayout>
  );
}
