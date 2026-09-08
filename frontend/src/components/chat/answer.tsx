import React, {
  FC,
  useMemo,
  useEffect,
  useState,
  useRef,
  AnchorHTMLAttributes,
  ClassAttributes,
} from "react";
import { Skeleton } from "@/components/ui/skeleton";
import { Divider } from "@/components/ui/divider";
import Markdown from "react-markdown";
import remarkGfm from "remark-gfm";
import rehypeHighlight from "rehype-highlight";
import { api } from "@/lib/api";
import { FileIcon } from "react-file-icon";

export interface Citation {
  id: number;
  text: string;
  metadata: Record<string, any>;
}

interface KnowledgeBaseInfo {
  name: string;
}

interface DocumentInfo {
  file_name: string;
  knowledge_base: KnowledgeBaseInfo;
}

interface CitationInfo {
  knowledge_base: KnowledgeBaseInfo;
  document: DocumentInfo;
}

// Smart tooltip component that respects viewport boundaries with smooth transitions
const CitationTooltip: FC<{
  citation: Citation;
  citationIndex: number;
  citationInfo?: CitationInfo;
  children: React.ReactElement;
}> = ({ citation, citationIndex, citationInfo, children }) => {
  const [isRendered, setIsRendered] = useState(false);
  const [isActive, setIsActive] = useState(false);
  const [placement, setPlacement] = useState<"top" | "bottom">("top");
  const [position, setPosition] = useState({
    top: 0,
    left: 0,
    transformX: "-50%",
  });
  const tooltipRef = useRef<HTMLDivElement>(null);
  const triggerRef = useRef<HTMLElement>(null);
  const closeTimeoutRef = useRef<NodeJS.Timeout | null>(null);
  const isMouseOverRef = useRef(false);

  const calculatePosition = (triggerEl: HTMLElement) => {
    const rect = triggerEl.getBoundingClientRect();
    const padding = 12;
    const tooltipWidth = Math.min(window.innerWidth - 32, 460);

    const isTopHalf = rect.top < window.innerHeight / 2;
    const preferBottom = isTopHalf || rect.top < 220;

    let left = rect.left + rect.width / 2;
    let transformX = "-50%";

    if (left - tooltipWidth / 2 < padding) {
      left = padding;
      transformX = "0%";
    } else if (left + tooltipWidth / 2 > window.innerWidth - padding) {
      left = window.innerWidth - padding;
      transformX = "-100%";
    }

    const top = preferBottom ? rect.bottom + 8 : Math.max(padding, rect.top - 8);
    setPlacement(preferBottom ? "bottom" : "top");
    setPosition({ top, left, transformX });
  };

  const handleMouseEnter = (e: React.MouseEvent<HTMLElement>) => {
    if (closeTimeoutRef.current) {
      clearTimeout(closeTimeoutRef.current);
      closeTimeoutRef.current = null;
    }

    isMouseOverRef.current = true;
    calculatePosition(e.currentTarget);
    setIsRendered(true);

    requestAnimationFrame(() => {
      requestAnimationFrame(() => {
        setIsActive(true);
      });
    });
  };

  const handleMouseLeave = () => {
    isMouseOverRef.current = false;
    closeTimeoutRef.current = setTimeout(() => {
      if (!isMouseOverRef.current) {
        setIsActive(false);
        setTimeout(() => {
          setIsRendered(false);
        }, 200);
      }
    }, 180);
  };

  const handleTooltipMouseEnter = () => {
    isMouseOverRef.current = true;
    if (closeTimeoutRef.current) {
      clearTimeout(closeTimeoutRef.current);
      closeTimeoutRef.current = null;
    }
  };

  const handleTooltipMouseLeave = () => {
    isMouseOverRef.current = false;
    closeTimeoutRef.current = setTimeout(() => {
      setIsActive(false);
      setTimeout(() => {
        setIsRendered(false);
      }, 200);
    }, 120);
  };

  useEffect(() => {
    return () => {
      if (closeTimeoutRef.current) {
        clearTimeout(closeTimeoutRef.current);
      }
    };
  }, []);

  useEffect(() => {
    if (isRendered && tooltipRef.current && triggerRef.current) {
      const tooltip = tooltipRef.current;
      const tooltipRect = tooltip.getBoundingClientRect();
      const triggerRect = triggerRef.current.getBoundingClientRect();
      const padding = 12;

      let finalTop =
        placement === "top"
          ? triggerRect.top - tooltipRect.height - 8
          : triggerRect.bottom + 8;

      if (placement === "top" && finalTop < padding) {
        finalTop = triggerRect.bottom + 8;
      } else if (
        placement === "bottom" &&
        finalTop + tooltipRect.height > window.innerHeight - padding
      ) {
        finalTop = Math.max(
          padding,
          triggerRect.top - tooltipRect.height - 8
        );
      }

      setPosition((prev) => ({
        ...prev,
        top: Math.max(
          padding,
          Math.min(
            window.innerHeight - tooltipRect.height - padding,
            finalTop
          )
        ),
      }));
    }
  }, [isRendered, placement]);

  const fileExt =
    citationInfo?.document?.file_name?.split(".").pop() ||
    citation.metadata?.file_name?.split(".").pop() ||
    citation.metadata?.source?.split(".").pop() ||
    "txt";

  const kbName =
    citationInfo?.knowledge_base?.name ||
    citation.metadata?.kb_name ||
    (citation.metadata?.kb_id ? `Knowledge Base #${citation.metadata.kb_id}` : "Knowledge Base");

  const docName =
    citationInfo?.document?.file_name ||
    citation.metadata?.file_name ||
    citation.metadata?.source ||
    (citation.metadata?.document_id ? `Document #${citation.metadata.document_id}` : `Source Document #${citationIndex}`);

  return (
    <>
      {React.cloneElement(children, {
        onMouseEnter: handleMouseEnter,
        onMouseLeave: handleMouseLeave,
        ref: triggerRef,
      })}
      {isRendered && (
        <div
          ref={tooltipRef}
          className={`fixed z-50 max-w-xl w-[calc(100vw-32px)] sm:w-[460px] p-4 rounded-xl shadow-2xl bg-popover text-popover-foreground border bg-background/98 backdrop-blur-md transition-all duration-200 ease-out origin-${
            placement === "top" ? "bottom" : "top"
          } ${
            isActive
              ? "opacity-100 scale-100 translate-y-0"
              : placement === "top"
              ? "opacity-0 scale-95 translate-y-1.5 pointer-events-none"
              : "opacity-0 scale-95 -translate-y-1.5 pointer-events-none"
          }`}
          style={{
            top: `${position.top}px`,
            left: `${position.left}px`,
            transform: `translateX(${position.transformX})`,
            maxHeight: "calc(100vh - 48px)",
            overflowY: "auto",
          }}
          onMouseEnter={handleTooltipMouseEnter}
          onMouseLeave={handleTooltipMouseLeave}
          onClick={(e) => e.stopPropagation()}
        >
          <div className="text-sm space-y-3">
            {/* Header with document & KB info */}
            <div className="flex items-center gap-2.5 text-xs font-medium text-foreground bg-muted/60 p-2.5 rounded-lg border">
              <div className="w-5 h-5 flex-shrink-0 flex items-center justify-center">
                <FileIcon
                  extension={fileExt}
                  color="#E2E8F0"
                  labelColor="#64748B"
                />
              </div>
              <div className="min-w-0 flex-1">
                <p className="font-semibold truncate text-xs">{docName}</p>
                <p className="text-[11px] text-muted-foreground truncate">{kbName}</p>
              </div>
              <span className="text-[10px] font-sans font-semibold px-1.5 py-0.5 rounded bg-primary/10 text-primary border border-primary/20">
                [{citationIndex}]
              </span>
            </div>

            <Divider />

            {/* Citation Content Snippet */}
            <div className="space-y-1">
              <span className="text-[11px] font-semibold text-muted-foreground uppercase tracking-wider">
                Source Excerpt
              </span>
              <p className="text-xs text-foreground/90 leading-relaxed max-h-48 overflow-y-auto bg-muted/20 p-2.5 rounded-md border font-sans whitespace-pre-wrap select-text">
                {citation.text || `Citation reference #${citationIndex} from ${docName}`}
              </p>
            </div>

            {/* Metadata tags */}
            {citation.metadata && Object.keys(citation.metadata).length > 0 && (
              <div className="text-[11px] text-muted-foreground bg-muted/40 p-2 rounded-md border space-y-1">
                <div className="font-medium text-foreground/80 mb-1">Metadata:</div>
                <div className="flex flex-wrap gap-1.5">
                  {Object.entries(citation.metadata).map(([key, value]) => {
                    if (value == null || typeof value === "object") return null;
                    return (
                      <span
                        key={key}
                        className="inline-flex items-center gap-1 px-1.5 py-0.5 rounded bg-background border text-[10px]"
                      >
                        <strong className="text-foreground/70">{key}:</strong>
                        <span className="truncate max-w-[160px]">{String(value)}</span>
                      </span>
                    );
                  })}
                </div>
              </div>
            )}
          </div>
        </div>
      )}
    </>
  );
};

export const Answer: FC<{
  markdown: string;
  citations?: Citation[];
}> = ({ markdown, citations = [] }) => {
  const [citationInfoMap, setCitationInfoMap] = useState<
    Record<string, CitationInfo>
  >({});

  const fetchedKeys = useRef<Set<string>>(new Set());
  const isFetchingRef = useRef(false);

  // Robust markdown normalization for citations and thinking blocks
  const processedMarkdown = useMemo(() => {
    if (!markdown) return "";
    let text = markdown
      .replace(/<think>/g, "## 💭 深度思考\n```think")
      .replace(/<\/think>/g, "```");

    // 1. Normalize [[citation:X]] or [[Citation: X]] -> [citation:X]
    text = text.replace(/\[\[\s*[cC]itation\s*:\s*(\d+)\s*\]\]/gi, "[citation:$1]");

    // 2. Unpack comma-separated citations: [citation: 1, 2, 3] -> [citation:1][citation:2][citation:3]
    text = text.replace(
      /\[\s*[cC]itation\s*:\s*([\d,\s]+)\]/gi,
      (match, idsStr) => {
        const ids = idsStr
          .split(",")
          .map((s: string) => s.trim())
          .filter((s: string) => /^\d+$/.test(s));
        if (ids.length === 0) return match;
        return ids.map((id: string) => `[citation:${id}]`).join("");
      }
    );

    // 3. Unpack bracketed comma numbers: [1, 2, 3] -> [citation:1][citation:2][citation:3] when citations are available
    if (citations && citations.length > 0) {
      text = text.replace(
        /\[\s*(\d+(?:\s*,\s*\d+)+)\s*\]/g,
        (match, idsStr) => {
          const ids = idsStr
            .split(",")
            .map((s: string) => s.trim())
            .filter((s: string) => /^\d+$/.test(s));
          if (ids.length === 0) return match;
          return ids.map((id: string) => `[citation:${id}]`).join("");
        }
      );
    }

    // 4. Convert [citation:X] or [Citation: X] to markdown citation link [citation:X](citation:X)
    text = text.replace(
      /\[\s*[cC]itation\s*:\s*(\d+)\s*\]/gi,
      "[citation:$1](citation:$1)"
    );

    // 5. Handle legacy [citation](X) format -> [citation:X](citation:X)
    text = text.replace(
      /\[citation\]\((\d+)\)/gi,
      "[citation:$1](citation:$1)"
    );

    // 6. Handle [X](citation:X) or [X](X) format -> [citation:X](citation:X)
    text = text.replace(
      /\[(\d+)\]\((?:citation:)?\1\)/gi,
      "[citation:$1](citation:$1)"
    );

    // 7. If plain bracketed [X] exists and corresponds to a valid citation index (1..citations.length), convert to [citation:X](citation:X)
    if (citations && citations.length > 0) {
      text = text.replace(
        /\[(\d+)\](?!\s*[:\(])/g,
        (match, idStr) => {
          const num = parseInt(idStr, 10);
          if (num >= 1 && num <= citations.length) {
            return `[citation:${num}](citation:${num})`;
          }
          return match;
        }
      );
    }

    // 8. Clean up whitespace between consecutive citation links (e.g. "[citation:1](citation:1) [citation:2](citation:2)" -> "[citation:1](citation:1)[citation:2](citation:2)")
    text = text.replace(
      /(\]\(citation:\d+\))\s+(\[citation:\d+\])/g,
      "$1$2"
    );

    // 9. Clean up whitespace before punctuation immediately following citations (e.g. "[citation:1] ." -> "[citation:1].", "[citation:1] ," -> "[citation:1],")
    text = text.replace(
      /(\[[^\]]+\]\([^\)]+\))\s+([.,;:!?])/g,
      "$1$2"
    );

    return text;
  }, [markdown, citations]);

  useEffect(() => {
    if (isFetchingRef.current || citations.length === 0) return;

    const fetchCitationInfo = async () => {
      isFetchingRef.current = true;
      const newInfoMap: Record<string, CitationInfo> = {};

      const promises = citations
        .filter((citation) => {
          const kb_id =
            citation.metadata?.kb_id ?? citation.metadata?.knowledge_base_id;
          const document_id =
            citation.metadata?.document_id ?? citation.metadata?.doc_id;
          if (!kb_id || !document_id) return false;

          const key = `${kb_id}-${document_id}`;
          if (fetchedKeys.current.has(key)) return false;

          fetchedKeys.current.add(key);
          return true;
        })
        .map(async (citation) => {
          const kb_id =
            citation.metadata?.kb_id ?? citation.metadata?.knowledge_base_id;
          const document_id =
            citation.metadata?.document_id ?? citation.metadata?.doc_id;
          const key = `${kb_id}-${document_id}`;

          try {
            const [kb, doc] = await Promise.all([
              api.get(`/api/knowledge-base/${kb_id}`),
              api.get(`/api/knowledge-base/${kb_id}/documents/${document_id}`),
            ]);

            newInfoMap[key] = {
              knowledge_base: {
                name: kb.name || `KB #${kb_id}`,
              },
              document: {
                file_name: doc.file_name || `Doc #${document_id}`,
                knowledge_base: {
                  name: kb.name || `KB #${kb_id}`,
                },
              },
            };
          } catch (error) {
            console.error("Failed to fetch citation info:", error);
            fetchedKeys.current.delete(key);
          }
        });

      await Promise.all(promises);

      if (Object.keys(newInfoMap).length > 0) {
        setCitationInfoMap((prev) => ({
          ...prev,
          ...newInfoMap,
        }));
      }

      isFetchingRef.current = false;
    };

    fetchCitationInfo();
  }, [citations]);

  const CitationLink = (
    props: ClassAttributes<HTMLAnchorElement> &
      AnchorHTMLAttributes<HTMLAnchorElement>
  ) => {
    const href = String(props.href || "");
    const childrenText = React.Children.toArray(props.children)
      .map((c) =>
        typeof c === "string" || typeof c === "number" ? String(c) : ""
      )
      .join("")
      .trim();

    // 1. Try matching from href: e.g. "citation:1", "1", "/1", "#1", "#citation-1"
    let citationId: number | null = null;
    const hrefMatch = href.match(/^(?:citation:|\/|#|#citation-)?(\d+)$/i);
    if (hrefMatch) {
      citationId = parseInt(hrefMatch[1], 10);
    } else {
      // 2. Try matching from childrenText: e.g. "[1]", "1", "citation:1", "[citation:1]"
      const childMatch = childrenText.match(
        /^(?:\[?\s*(?:citation:)?\s*(\d+)\s*\]?)$/i
      );
      if (
        childMatch &&
        (href.startsWith("citation:") ||
          href === "" ||
          href === "#" ||
          href === "/" ||
          !href.startsWith("http"))
      ) {
        citationId = parseInt(childMatch[1], 10);
      }
    }

    // If it's not a citation at all, render as normal external web link
    if (!citationId) {
      return (
        <a
          {...props}
          target="_blank"
          rel="noopener noreferrer"
          className="text-primary underline font-medium hover:text-primary/80 transition-colors"
        >
          {props.children}
        </a>
      );
    }

    const citation =
      (citations && citations[citationId - 1]) || {
        id: citationId,
        text: "",
        metadata: {},
      };

    const kb_id =
      citation.metadata?.kb_id ?? citation.metadata?.knowledge_base_id;
    const document_id =
      citation.metadata?.document_id ?? citation.metadata?.doc_id;
    const citationKey = `${kb_id}-${document_id}`;
    const citationInfo = citationInfoMap[citationKey];

    return (
      <CitationTooltip
        citation={citation}
        citationIndex={citationId}
        citationInfo={citationInfo}
      >
        <span className="inline-flex items-baseline mx-0.5 select-none align-baseline">
          <span
            role="button"
            tabIndex={0}
            aria-label={`Citation [${citationId}]`}
            className="inline-flex items-center justify-center font-sans text-[10px] font-semibold text-primary bg-primary/10 hover:bg-primary hover:text-primary-foreground rounded px-1 py-0.5 border border-primary/20 hover:border-primary transition-all duration-150 cursor-pointer select-none leading-none -translate-y-0.5"
            onClick={(e) => {
              e.preventDefault();
              e.stopPropagation();
            }}
            onKeyDown={(e) => {
              if (e.key === "Enter" || e.key === " ") {
                e.preventDefault();
                e.stopPropagation();
              }
            }}
          >
            [{citationId}]
          </span>
        </span>
      </CitationTooltip>
    );
  };

  if (!markdown) {
    return (
      <div className="flex flex-col gap-2">
        <Skeleton className="max-w-sm h-4 bg-zinc-200" />
        <Skeleton className="max-w-lg h-4 bg-zinc-200" />
        <Skeleton className="max-w-2xl h-4 bg-zinc-200" />
        <Skeleton className="max-w-lg h-4 bg-zinc-200" />
        <Skeleton className="max-w-xl h-4 bg-zinc-200" />
      </div>
    );
  }

  return (
    <div className="prose prose-sm max-w-full leading-relaxed prose-p:leading-relaxed prose-p:my-2">
      <Markdown
        remarkPlugins={[remarkGfm]}
        rehypePlugins={[rehypeHighlight]}
        components={{
          a: CitationLink,
        }}
      >
        {processedMarkdown}
      </Markdown>
    </div>
  );
};