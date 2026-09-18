"use client";

import React, { FC, useState, useMemo, useRef, useEffect } from "react";
import Link from "next/link";
import {
  Plus,
  MessageSquare,
  Search,
  Trash2,
  ChevronLeft,
  ChevronRight,
  Bot,
  Sparkles,
  BookOpen,
  Edit2,
  Check,
  X,
  Loader2,
} from "lucide-react";
import { formatDistanceToNow } from "date-fns";

export interface ChatSessionSummary {
  id: number;
  title: string;
  created_at: string;
  updated_at?: string;
  messages_count?: number;
  last_message?: string;
}

interface ChatSidebarProps {
  chats: ChatSessionSummary[];
  activeChatId?: string | number;
  onDeleteChat?: (id: number) => void;
  onRenameChat?: (id: number, newTitle: string) => Promise<void> | void;
  onNewChat?: () => void;
  isLoading?: boolean;
}

export const ChatSidebar: FC<ChatSidebarProps> = ({
  chats,
  activeChatId,
  onDeleteChat,
  onRenameChat,
  onNewChat,
  isLoading = false,
}) => {
  const [searchTerm, setSearchTerm] = useState("");
  const [isCollapsed, setIsCollapsed] = useState(false);
  const [editingChatId, setEditingChatId] = useState<number | null>(null);
  const [editingTitle, setEditingTitle] = useState("");
  const [navigatingChatId, setNavigatingChatId] = useState<number | null>(null);
  const activeItemRef = useRef<HTMLDivElement>(null);
  const editInputRef = useRef<HTMLInputElement>(null);

  useEffect(() => {
    setNavigatingChatId(null);
  }, [activeChatId]);

  const sortedChats = useMemo(() => {
    return [...chats]
      .filter((chat) =>
        chat.title.toLowerCase().includes(searchTerm.toLowerCase())
      )
      .sort((a, b) => {
        if (a.created_at && b.created_at) {
          const timeA = new Date(a.created_at).getTime();
          const timeB = new Date(b.created_at).getTime();
          if (timeB !== timeA) return timeB - timeA;
        }
        return b.id - a.id;
      });
  }, [chats, searchTerm]);

  useEffect(() => {
    if (editingChatId && editInputRef.current) {
      editInputRef.current.focus();
      editInputRef.current.select();
    }
  }, [editingChatId]);

  const handleStartRename = (e: React.MouseEvent, chat: ChatSessionSummary) => {
    e.preventDefault();
    e.stopPropagation();
    setEditingChatId(chat.id);
    setEditingTitle(chat.title);
  };

  const handleSaveRename = async (e?: React.FormEvent) => {
    if (e) {
      e.preventDefault();
      e.stopPropagation();
    }
    if (!editingChatId || !editingTitle.trim()) {
      setEditingChatId(null);
      return;
    }
    if (onRenameChat) {
      await onRenameChat(editingChatId, editingTitle.trim());
    }
    setEditingChatId(null);
  };

  const handleCancelRename = (e?: React.MouseEvent) => {
    if (e) {
      e.preventDefault();
      e.stopPropagation();
    }
    setEditingChatId(null);
  };

  return (
    <div
      className={`relative flex flex-col h-full bg-card border-r transition-all duration-300 ease-in-out ${
        isCollapsed ? "w-16" : "w-72 sm:w-80"
      }`}
    >
      {/* Header & New Chat Button */}
      <div className="p-3.5 border-b flex flex-col gap-2.5">
        <div className="flex items-center justify-between">
          {!isCollapsed && (
            <div className="flex items-center gap-2">
              <Sparkles className="h-4 w-4 text-primary" />
              <span className="text-sm font-semibold tracking-tight text-foreground">
                Conversations
              </span>
            </div>
          )}
          <button
            onClick={() => setIsCollapsed(!isCollapsed)}
            className="p-1.5 rounded-lg text-muted-foreground hover:bg-muted hover:text-foreground transition-colors ml-auto"
            title={isCollapsed ? "Expand sidebar" : "Collapse sidebar"}
          >
            {isCollapsed ? (
              <ChevronRight className="h-4 w-4" />
            ) : (
              <ChevronLeft className="h-4 w-4" />
            )}
          </button>
        </div>

        {/* Primary Action Button */}
        {onNewChat ? (
          <button
            onClick={onNewChat}
            className={`flex items-center justify-center rounded-xl bg-primary text-primary-foreground font-medium transition-all shadow-sm hover:bg-primary/90 hover:shadow ${
              isCollapsed ? "h-10 w-10 p-0 mx-auto" : "h-10 px-4 py-2 w-full gap-2 text-sm"
            }`}
            title="Start New Chat"
          >
            <Plus className="h-4 w-4 shrink-0" />
            {!isCollapsed && <span>New Chat</span>}
          </button>
        ) : (
          <Link
            href="/dashboard/chat"
            className={`flex items-center justify-center rounded-xl bg-primary text-primary-foreground font-medium transition-all shadow-sm hover:bg-primary/90 hover:shadow ${
              isCollapsed ? "h-10 w-10 p-0 mx-auto" : "h-10 px-4 py-2 w-full gap-2 text-sm"
            }`}
            title="Start New Chat"
          >
            <Plus className="h-4 w-4 shrink-0" />
            {!isCollapsed && <span>New Chat</span>}
          </Link>
        )}

        {/* Search input (when expanded) */}
        {!isCollapsed && (
          <div className="relative mt-1">
            <Search className="absolute left-3 top-1/2 -translate-y-1/2 h-3.5 w-3.5 text-muted-foreground" />
            <input
              type="text"
              placeholder="Search conversations..."
              value={searchTerm}
              onChange={(e) => setSearchTerm(e.target.value)}
              className="w-full pl-8 pr-3 py-1.5 text-xs rounded-lg border bg-background/50 focus:bg-background focus:ring-2 focus:ring-primary/20 focus:border-primary transition-all outline-none"
            />
          </div>
        )}
      </div>

      {/* Chat Session List */}
      <div className="flex-1 overflow-y-auto p-2 space-y-1">
        {isLoading ? (
          <div className="p-4 space-y-2">
            {[1, 2, 3, 4].map((n) => (
              <div
                key={n}
                className="h-12 rounded-lg bg-muted/40 animate-pulse"
              />
            ))}
          </div>
        ) : sortedChats.length === 0 ? (
          <div className="p-4 text-center text-xs text-muted-foreground">
            {!isCollapsed && (
              <p>
                {searchTerm
                  ? "No matching conversations"
                  : "No conversations yet"}
              </p>
            )}
          </div>
        ) : (
          sortedChats.map((chat) => {
            const isActive = String(chat.id) === String(activeChatId);

            const isEditing = editingChatId === chat.id;

            const isNavigating = navigatingChatId === chat.id;

            return (
              <div
                key={chat.id}
                ref={isActive ? activeItemRef : undefined}
                className={`group relative flex items-center rounded-xl transition-all ${
                  isActive
                    ? "bg-primary/10 text-primary font-medium shadow-xs"
                    : isNavigating
                    ? "bg-primary/5 text-primary animate-pulse"
                    : "text-foreground/80 hover:bg-muted/70 hover:text-foreground"
                }`}
              >
                {isEditing && !isCollapsed ? (
                  <form
                    onSubmit={handleSaveRename}
                    className="flex items-center gap-1.5 p-2 w-full"
                  >
                    <input
                      ref={editInputRef}
                      type="text"
                      value={editingTitle}
                      onChange={(e) => setEditingTitle(e.target.value)}
                      onKeyDown={(e) => {
                        if (e.key === "Escape") handleCancelRename();
                      }}
                      className="flex-1 text-xs px-2 py-1 rounded-md border bg-background text-foreground focus:outline-none focus:ring-1 focus:ring-primary"
                    />
                    <button
                      type="submit"
                      className="p-1 rounded-md text-emerald-600 hover:bg-emerald-50 dark:hover:bg-emerald-950/40"
                      title="Save (Enter)"
                    >
                      <Check className="h-3.5 w-3.5" />
                    </button>
                    <button
                      type="button"
                      onClick={handleCancelRename}
                      className="p-1 rounded-md text-muted-foreground hover:bg-muted"
                      title="Cancel (Esc)"
                    >
                      <X className="h-3.5 w-3.5" />
                    </button>
                  </form>
                ) : (
                  <>
                    <Link
                      href={`/dashboard/chat/${chat.id}`}
                      onClick={() => {
                        if (!isActive) setNavigatingChatId(chat.id);
                      }}
                      className={`flex items-center gap-3 min-w-0 flex-1 p-2.5 ${
                        isCollapsed ? "justify-center" : ""
                      }`}
                      title={chat.title}
                    >
                      <div
                        className={`h-7 w-7 rounded-lg flex items-center justify-center shrink-0 ${
                          isActive
                            ? "bg-primary text-primary-foreground"
                            : isNavigating
                            ? "bg-primary/20 text-primary"
                            : "bg-muted text-muted-foreground group-hover:text-foreground"
                        }`}
                      >
                        {isNavigating ? (
                          <Loader2 className="h-3.5 w-3.5 animate-spin text-primary" />
                        ) : (
                          <MessageSquare className="h-3.5 w-3.5" />
                        )}
                      </div>

                      {!isCollapsed && (
                        <div className="min-w-0 flex-1">
                          <p className="text-xs truncate font-medium">{chat.title}</p>
                          {chat.created_at && (
                            <p className="text-[10px] text-muted-foreground truncate mt-0.5">
                              {formatDistanceToNow(new Date(chat.created_at), {
                                addSuffix: true,
                              })}
                            </p>
                          )}
                        </div>
                      )}
                    </Link>

                    {/* Action buttons on hover */}
                    {!isCollapsed && (
                      <div className="flex items-center opacity-0 group-hover:opacity-100 pr-1.5 transition-opacity">
                        {onRenameChat && (
                          <button
                            onClick={(e) => handleStartRename(e, chat)}
                            className="p-1.5 rounded-md hover:bg-muted text-muted-foreground hover:text-foreground transition-colors"
                            title="Rename conversation"
                          >
                            <Edit2 className="h-3.5 w-3.5" />
                          </button>
                        )}
                        {onDeleteChat && (
                          <button
                            onClick={(e) => {
                              e.preventDefault();
                              e.stopPropagation();
                              onDeleteChat(chat.id);
                            }}
                            className="p-1.5 rounded-md hover:bg-destructive/10 text-muted-foreground hover:text-destructive transition-colors"
                            title="Delete conversation"
                          >
                            <Trash2 className="h-3.5 w-3.5" />
                          </button>
                        )}
                      </div>
                    )}
                  </>
                )}
              </div>
            );
          })
        )}
      </div>

      {/* Footer info */}
      {!isCollapsed && (
        <div className="p-3 border-t bg-muted/10 text-center">
          <div className="flex items-center justify-center gap-1.5 text-[11px] text-muted-foreground">
            <BookOpen className="h-3.5 w-3.5 text-primary" />
            <span>Akvo RAG Multi-KB Chat</span>
          </div>
        </div>
      )}
    </div>
  );
};
