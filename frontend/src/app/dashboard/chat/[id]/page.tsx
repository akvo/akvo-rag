"use client";

import { useEffect, useRef, useState, useMemo } from "react";
import { useRouter, useSearchParams } from "next/navigation";
import { useChat } from "ai/react";
import Image from "next/image";
import {
  Send,
  User,
  Bot,
  Sparkles,
  Layers,
  Globe,
  Download,
  Copy,
  Check,
  Loader2,
} from "lucide-react";
import DashboardLayout from "@/components/layout/dashboard-layout";
import { api, ApiError, API_PREFIX } from "@/lib/api";
import { useToast } from "@/components/ui/use-toast";
import { Answer, Citation } from "@/components/chat/answer";
import {
  CitationDrawer,
  CitationDrawerItem,
} from "@/components/chat/citation-drawer";
import {
  ChatSidebar,
  ChatSessionSummary,
} from "@/components/chat/chat-sidebar";

interface Message {
  id: string;
  role: "assistant" | "user" | "system" | "data";
  content: string;
  citations?: Citation[];
}

interface ChatMessage {
  id: number;
  content: string;
  role: "assistant" | "user";
  created_at: string;
}

interface KnowledgeBaseItem {
  id: number;
  name: string;
  description?: string;
}

interface Chat {
  id: number;
  title: string;
  created_at?: string;
  messages: ChatMessage[];
  knowledge_bases: Array<{
    knowledge_base: {
      id: number;
      name: string;
    };
  }>;
}

export default function ChatDetailPage({ params }: { params: { id: string } }) {
  const router = useRouter();
  const searchParams = useSearchParams();
  const autoPrompt = searchParams ? searchParams.get("prompt") : null;
  const autoPromptExecutedRef = useRef(false);

  const { toast } = useToast();
  const [chat, setChat] = useState<Chat | null>(null);
  const [allChats, setAllChats] = useState<ChatSessionSummary[]>([]);
  const [loadingChats, setLoadingChats] = useState(true);
  const [loadingChat, setLoadingChat] = useState(true);
  const messagesEndRef = useRef<HTMLDivElement>(null);

  // Citation Drawer state
  const [selectedCitation, setSelectedCitation] =
    useState<CitationDrawerItem | null>(null);
  const [isDrawerOpen, setIsDrawerOpen] = useState(false);

  const {
    messages,
    input,
    handleInputChange,
    handleSubmit,
    isLoading,
    setMessages,
    append,
  } = useChat({
    api: `${API_PREFIX}/chat/${params.id}/messages`,
    headers: {
      Authorization: `Bearer ${
        typeof window !== "undefined"
          ? window.localStorage.getItem("token")
          : ""
      }`,
    },
  });

  useEffect(() => {
    fetchSidebarChats();
  }, []);

  useEffect(() => {
    setLoadingChat(true);
    setChat(null);
    setMessages([]);
    fetchChat();
  }, [params.id]);

  useEffect(() => {
    if (!loadingChat) {
      scrollToBottom();
    }
  }, [messages, loadingChat]);

  const fetchSidebarChats = async () => {
    try {
      const data = await api.get("/api/chat");
      setAllChats(data);
    } catch (error) {
      console.error("Failed to fetch conversations for sidebar:", error);
    } finally {
      setLoadingChats(false);
    }
  };

  const fetchChat = async () => {
    setLoadingChat(true);
    try {
      const data: Chat = await api.get(`/api/chat/${params.id}`);
      setChat(data);

      // Ensure active chat appears in the left sidebar
      setAllChats((prev) => {
        if (prev.some((c) => String(c.id) === String(data.id))) return prev;
        return [
          {
            id: data.id,
            title: data.title,
            created_at: data.created_at || new Date().toISOString(),
          },
          ...prev,
        ];
      });

      // If navigation passed an auto-prompt on empty chat, submit it immediately
      if (
        autoPrompt &&
        !autoPromptExecutedRef.current &&
        data.messages.length === 0
      ) {
        autoPromptExecutedRef.current = true;
        append({
          role: "user",
          content: autoPrompt,
        });
      }

      const formattedMessages = data.messages.map((msg) => {
        if (msg.role !== "assistant" || !msg.content)
          return {
            id: msg.id.toString(),
            role: msg.role,
            content: msg.content,
          };

        try {
          if (!msg.content.includes("__LLM_RESPONSE__")) {
            return {
              id: msg.id.toString(),
              role: msg.role,
              content: msg.content,
            };
          }

          const [base64Part, responseText] =
            msg.content.split("__LLM_RESPONSE__");

          const contextData = base64Part
            ? (JSON.parse(atob(base64Part.trim())) as {
                context: Array<{
                  page_content: string;
                  metadata: Record<string, any>;
                }>;
              })
            : null;

          const citations: Citation[] =
            contextData?.context.map((citation, index) => ({
              id: index + 1,
              text: citation.page_content,
              metadata: citation.metadata,
            })) || [];

          return {
            id: msg.id.toString(),
            role: msg.role,
            content: responseText || "",
            citations,
          };
        } catch (e) {
          console.error("Failed to process message:", e);
          return {
            id: msg.id.toString(),
            role: msg.role,
            content: msg.content,
          };
        }
      });
      setMessages(formattedMessages);
    } catch (error) {
      console.error("Failed to fetch chat:", error);
      if (error instanceof ApiError) {
        toast({
          title: "Error",
          description: error.message,
          variant: "destructive",
        });
      }
      router.push("/dashboard/chat");
    } finally {
      setLoadingChat(false);
    }
  };

  const handleDeleteSidebarChat = async (id: number) => {
    if (!confirm("Are you sure you want to delete this conversation?")) return;
    try {
      await api.delete(`/api/chat/${id}`);
      setAllChats((prev) => prev.filter((c) => c.id !== id));
      toast({
        title: "Success",
        description: "Conversation deleted",
      });
      if (String(id) === params.id) {
        router.push("/dashboard/chat");
      }
    } catch (error) {
      console.error("Failed to delete chat:", error);
    }
  };

  const handleRenameSidebarChat = async (id: number, newTitle: string) => {
    try {
      await api.put(`/api/chat/${id}`, { title: newTitle });
      setAllChats((prev) =>
        prev.map((c) => (c.id === id ? { ...c, title: newTitle } : c))
      );
      if (String(id) === params.id) {
        setChat((prev) => (prev ? { ...prev, title: newTitle } : prev));
      }
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

  const handleExportMarkdown = () => {
    if (!chat || processedMessages.length === 0) return;
    const dateStr = new Date().toISOString().split("T")[0];
    let mdContent = `# ${chat.title}\n*Exported on ${dateStr} from Akvo RAG*\n\n---\n\n`;

    processedMessages.forEach((msg) => {
      const roleName = msg.role === "assistant" ? "🤖 **Akvo Assistant**" : "👤 **User**";
      mdContent += `### ${roleName}\n\n${msg.content}\n\n`;
      if (msg.citations && msg.citations.length > 0) {
        mdContent += `**Citations:**\n`;
        msg.citations.forEach((c) => {
          mdContent += `- [${c.id}] ${c.metadata?.file_name || "Document"}: "${c.text.slice(0, 150).replace(/\n/g, " ")}..."\n`;
        });
        mdContent += `\n`;
      }
      mdContent += `---\n\n`;
    });

    const blob = new Blob([mdContent], { type: "text/markdown;charset=utf-8" });
    const url = URL.createObjectURL(blob);
    const link = document.createElement("a");
    link.href = url;
    link.download = `${chat.title.replace(/[^a-zA-Z0-9_-]/g, "_")}_${dateStr}.md`;
    document.body.appendChild(link);
    link.click();
    document.body.removeChild(link);
    URL.revokeObjectURL(url);
    toast({ title: "Exported", description: "Conversation saved as Markdown" });
  };

  const handleExportJSON = () => {
    if (!chat || processedMessages.length === 0) return;
    const exportData = {
      id: chat.id,
      title: chat.title,
      exported_at: new Date().toISOString(),
      knowledge_bases: chat.knowledge_bases,
      messages: processedMessages.map((m) => ({
        id: m.id,
        role: m.role,
        content: m.content,
        citations: m.citations || [],
      })),
    };

    const blob = new Blob([JSON.stringify(exportData, null, 2)], {
      type: "application/json;charset=utf-8",
    });
    const url = URL.createObjectURL(blob);
    const link = document.createElement("a");
    link.href = url;
    link.download = `${chat.title.replace(/[^a-zA-Z0-9_-]/g, "_")}_export.json`;
    document.body.appendChild(link);
    link.click();
    document.body.removeChild(link);
    URL.revokeObjectURL(url);
    toast({ title: "Exported", description: "Conversation saved as JSON" });
  };

  const [copiedExport, setCopiedExport] = useState(false);
  const handleCopyConversation = async () => {
    if (!chat || processedMessages.length === 0) return;
    let fullText = `${chat.title}\n\n`;
    processedMessages.forEach((m) => {
      fullText += `${m.role.toUpperCase()}:\n${m.content}\n\n`;
    });
    await navigator.clipboard.writeText(fullText);
    setCopiedExport(true);
    setTimeout(() => setCopiedExport(false), 2000);
    toast({ title: "Copied", description: "Conversation copied to clipboard" });
  };

  const scrollToBottom = () => {
    messagesEndRef.current?.scrollIntoView({ behavior: "smooth" });
  };

  const markdownParse = (text: string) => {
    return text.replace(/\[\[\s*([cC])itation\s*:\s*(\d+)\s*\]\]/gi, "[citation:$2]");
  };

  const processedMessages = useMemo(() => {
    return messages.map((message): {
      id: string;
      role: string;
      content: string;
      citations?: Citation[];
    } => {
      if (message.role !== "assistant" || !message.content) {
        return {
          id: message.id,
          role: message.role,
          content: message.content,
        };
      }

      try {
        if (!message.content.includes("__LLM_RESPONSE__")) {
          return {
            id: message.id,
            role: message.role,
            content: markdownParse(message.content),
          };
        }

        const [base64Part, responseText] =
          message.content.split("__LLM_RESPONSE__");

        const contextData = base64Part
          ? (JSON.parse(atob(base64Part.trim())) as {
              context: Array<{
                page_content: string;
                metadata: Record<string, any>;
              }>;
            })
          : null;

        const citations: Citation[] =
          contextData?.context.map((citation, index) => ({
            id: index + 1,
            text: citation.page_content,
            metadata: citation.metadata,
          })) || [];

        return {
          id: message.id,
          role: message.role,
          content: markdownParse(responseText || ""),
          citations,
        };
      } catch (e) {
        console.error("Failed to process message:", e);
        return {
          id: message.id,
          role: message.role,
          content: message.content,
        };
      }
    });
  }, [messages]);

  // Handle opening citation drawer from Answer component
  const handleOpenCitation = (
    citation: Citation,
    index: number,
    info?: any
  ) => {
    setSelectedCitation({
      id: index,
      text: citation.text,
      metadata: citation.metadata,
      kb_name: info?.knowledge_base?.name || citation.metadata?.kb_name,
      doc_name: info?.document?.file_name || citation.metadata?.file_name,
    });
    setIsDrawerOpen(true);
  };

  // Collect all citations in active message for drawer navigation
  const activeMessageCitations = useMemo(() => {
    const lastAssistantMsg = [...processedMessages]
      .reverse()
      .find((m) => m.role === "assistant" && m.citations && m.citations.length > 0);

    if (!lastAssistantMsg || !lastAssistantMsg.citations) return [];
    return lastAssistantMsg.citations.map((c, idx) => ({
      id: c.id || idx + 1,
      text: c.text,
      metadata: c.metadata,
      kb_name: c.metadata?.kb_name,
      doc_name: c.metadata?.file_name,
    }));
  }, [processedMessages]);

  return (
    <DashboardLayout>
      <div className="flex h-[calc(100vh-4.5rem)] overflow-hidden rounded-2xl border bg-background shadow-xs">
        {/* Left 2-Pane Conversation Sidebar */}
        <ChatSidebar
          chats={allChats}
          activeChatId={params.id}
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
                {loadingChat ? (
                  <Loader2 className="h-4 w-4 text-primary animate-spin" />
                ) : (
                  <Sparkles className="h-4 w-4 text-primary" />
                )}
              </div>
              <div className="min-w-0">
                {loadingChat ? (
                  <div className="space-y-1.5 py-0.5">
                    <div className="h-3.5 w-36 bg-muted animate-pulse rounded-md" />
                    <div className="h-2.5 w-24 bg-muted/60 animate-pulse rounded-md" />
                  </div>
                ) : (
                  <>
                    <h2 className="text-sm font-semibold text-foreground truncate">
                      {chat?.title || "Conversation"}
                    </h2>
                    <div className="flex items-center gap-2 text-[11px] text-muted-foreground">
                      <span className="flex items-center gap-1">
                        <Globe className="h-3 w-3 text-primary" />
                        {chat?.knowledge_bases && chat.knowledge_bases.length > 0
                          ? chat.knowledge_bases
                              .map((kb) => kb.knowledge_base.name)
                              .join(", ")
                          : "All Knowledge Bases"}
                      </span>
                      <span>•</span>
                      <span>{messages.length} messages</span>
                    </div>
                  </>
                )}
              </div>
            </div>

            {/* Actions & Scope Badge */}
            <div className="flex items-center gap-2">
              {/* Conversation Export Actions */}
              {!loadingChat && processedMessages.length > 0 && (
                <div className="flex items-center bg-muted/60 border rounded-xl p-0.5 gap-0.5 shadow-2xs">
                  <button
                    onClick={handleExportMarkdown}
                    className="flex items-center gap-1 px-2.5 py-1 text-xs font-medium rounded-lg text-muted-foreground hover:text-foreground hover:bg-background transition-all"
                    title="Export as Markdown (.md)"
                  >
                    <Download className="h-3.5 w-3.5 text-primary" />
                    <span className="hidden sm:inline">Export .md</span>
                  </button>
                  <button
                    onClick={handleExportJSON}
                    className="flex items-center gap-1 px-2 py-1 text-xs font-medium rounded-lg text-muted-foreground hover:text-foreground hover:bg-background transition-all"
                    title="Export as JSON (.json)"
                  >
                    <span>.json</span>
                  </button>
                  <button
                    onClick={handleCopyConversation}
                    className="flex items-center gap-1 px-2 py-1 text-xs font-medium rounded-lg text-muted-foreground hover:text-foreground hover:bg-background transition-all"
                    title="Copy full conversation text"
                  >
                    {copiedExport ? (
                      <Check className="h-3.5 w-3.5 text-emerald-500" />
                    ) : (
                      <Copy className="h-3.5 w-3.5" />
                    )}
                  </button>
                </div>
              )}

              <div className="hidden lg:flex items-center gap-1.5 bg-muted/60 border rounded-full px-3 py-1 text-xs text-muted-foreground">
                <Layers className="h-3.5 w-3.5 text-primary" />
                <span>ChromaDB Vector Store</span>
              </div>
            </div>
          </div>

          {/* Messages Stream Canvas */}
          <div className="flex-1 overflow-y-auto px-4 sm:px-8 py-6 space-y-6">
            {loadingChat ? (
              <div className="space-y-6 max-w-3xl animate-in fade-in duration-300">
                {/* Assistant Skeleton */}
                <div className="flex items-start gap-3.5">
                  <div className="h-8 w-8 rounded-xl bg-primary/10 border border-primary/20 flex items-center justify-center shrink-0">
                    <Bot className="h-4 w-4 text-primary animate-pulse" />
                  </div>
                  <div className="flex-1 rounded-2xl bg-card border px-5 py-4 space-y-2.5 shadow-xs">
                    <div className="h-4 w-3/4 bg-muted/80 rounded-md animate-pulse" />
                    <div className="h-4 w-full bg-muted/60 rounded-md animate-pulse" />
                    <div className="h-4 w-5/6 bg-muted/50 rounded-md animate-pulse" />
                  </div>
                </div>

                {/* User Skeleton */}
                <div className="flex items-start justify-end gap-3.5 ml-auto max-w-xl">
                  <div className="rounded-2xl bg-primary/20 px-5 py-3.5 space-y-2 w-64 shadow-xs">
                    <div className="h-3.5 w-full bg-primary/30 rounded-md animate-pulse" />
                    <div className="h-3.5 w-2/3 bg-primary/30 rounded-md animate-pulse" />
                  </div>
                  <div className="h-8 w-8 rounded-full bg-primary/20 border border-primary/30 flex items-center justify-center shrink-0">
                    <User className="h-4 w-4 text-primary" />
                  </div>
                </div>

                {/* Assistant Skeleton 2 */}
                <div className="flex items-start gap-3.5">
                  <div className="h-8 w-8 rounded-xl bg-primary/10 border border-primary/20 flex items-center justify-center shrink-0">
                    <Bot className="h-4 w-4 text-primary animate-pulse" />
                  </div>
                  <div className="flex-1 rounded-2xl bg-card border px-5 py-4 space-y-2.5 shadow-xs">
                    <div className="h-4 w-2/3 bg-muted/80 rounded-md animate-pulse" />
                    <div className="h-4 w-4/5 bg-muted/60 rounded-md animate-pulse" />
                  </div>
                </div>

                {/* Loading indicator bar */}
                <div className="flex items-center justify-center gap-2 pt-4 text-xs text-muted-foreground">
                  <Loader2 className="h-3.5 w-3.5 animate-spin text-primary" />
                  <span>Loading conversation...</span>
                </div>
              </div>
            ) : (
              <>
                {processedMessages.map((message) =>
                  message.role === "assistant" ? (
                    <div
                      key={message.id}
                      className="flex items-start gap-3.5 max-w-3xl"
                    >
                      <div className="h-8 w-8 rounded-xl bg-primary/10 border border-primary/20 flex items-center justify-center shrink-0 mt-0.5 shadow-xs overflow-hidden">
                        <Image
                          src="/logo.png"
                          width={20}
                          height={20}
                          className="rounded-md object-contain"
                          alt="Akvo RAG"
                        />
                      </div>
                      <div className="flex-1 min-w-0 rounded-2xl bg-card border px-5 py-4 text-foreground shadow-xs">
                        <Answer
                          key={message.id}
                          markdown={message.content}
                          citations={message.citations}
                          onOpenCitation={handleOpenCitation}
                        />
                      </div>
                    </div>
                  ) : (
                    <div
                      key={message.id}
                      className="flex items-start justify-end gap-3.5 max-w-3xl ml-auto"
                    >
                      <div className="rounded-2xl bg-primary px-5 py-3 text-sm font-medium text-primary-foreground shadow-sm max-w-[85%] leading-relaxed break-words">
                        {message.content}
                      </div>
                      <div className="h-8 w-8 rounded-full bg-primary/20 border border-primary/30 flex items-center justify-center shrink-0 mt-0.5 text-primary">
                        <User className="h-4 w-4" />
                      </div>
                    </div>
                  )
                )}

                {/* Streaming Thinking / Bouncing Indicator */}
                {isLoading &&
                  processedMessages[processedMessages.length - 1]?.role !==
                    "assistant" && (
                    <div className="flex items-start gap-3.5 max-w-3xl">
                      <div className="h-8 w-8 rounded-xl bg-primary/10 border border-primary/20 flex items-center justify-center shrink-0 shadow-xs">
                        <Bot className="h-4 w-4 text-primary animate-pulse" />
                      </div>
                      <div className="rounded-2xl bg-card border px-4 py-3 text-xs text-muted-foreground shadow-xs flex items-center gap-2">
                        <span className="font-medium text-foreground">
                          Searching vector knowledge bases & synthesizing...
                        </span>
                        <div className="flex items-center space-x-1">
                          <div className="w-1.5 h-1.5 rounded-full bg-primary animate-bounce" />
                          <div className="w-1.5 h-1.5 rounded-full bg-primary animate-bounce [animation-delay:0.2s]" />
                          <div className="w-1.5 h-1.5 rounded-full bg-primary animate-bounce [animation-delay:0.4s]" />
                        </div>
                      </div>
                    </div>
                  )}
              </>
            )}

            <div ref={messagesEndRef} />
          </div>

          {/* Instant Composer */}
          <div className="border-t bg-card/80 backdrop-blur-md p-4">
            <form onSubmit={handleSubmit} className="flex items-center gap-2">
              <input
                value={input}
                onChange={handleInputChange}
                disabled={loadingChat || isLoading}
                placeholder={
                  loadingChat
                    ? "Loading conversation..."
                    : "Ask a question about this knowledge base..."
                }
                className="flex-1 h-11 rounded-xl border bg-background px-4 text-sm outline-none ring-offset-background placeholder:text-muted-foreground focus-visible:ring-2 focus-visible:ring-primary/30 focus-visible:border-primary transition-all shadow-xs disabled:opacity-60"
              />
              <button
                type="submit"
                disabled={loadingChat || isLoading || !input.trim()}
                className="inline-flex items-center justify-center rounded-xl bg-primary text-primary-foreground font-semibold h-11 px-5 text-sm shadow-sm hover:bg-primary/90 hover:shadow disabled:opacity-50 transition-all gap-1.5 shrink-0"
              >
                <Send className="h-4 w-4" />
                <span className="hidden sm:inline">Send</span>
              </button>
            </form>
          </div>
        </div>

        {/* Slide-Over Citation Drawer */}
        <CitationDrawer
          isOpen={isDrawerOpen}
          onClose={() => setIsDrawerOpen(false)}
          citation={selectedCitation}
          allCitations={activeMessageCitations}
          onSelectCitation={(c) => setSelectedCitation(c)}
        />
      </div>
    </DashboardLayout>
  );
}
