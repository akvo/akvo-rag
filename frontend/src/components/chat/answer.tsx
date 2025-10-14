import React, {
  FC,
  useMemo,
  useEffect,
  useState,
  useRef
} from "react";
import { AnchorHTMLAttributes, ClassAttributes } from "react";
import { Skeleton } from "@/components/ui/skeleton";
import { Divider } from "@/components/ui/divider";
import Markdown from "react-markdown";
import remarkGfm from "remark-gfm";
import rehypeHighlight from "rehype-highlight";
import { api } from "@/lib/api";
import { FileIcon } from "react-file-icon";

interface Citation {
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

// Smart tooltip component that respects viewport boundaries
const CitationTooltip: FC<{
  citation: Citation;
  citationInfo?: CitationInfo;
  children: React.ReactElement;
}> = ({ citation, citationInfo, children }) => {
  const [isVisible, setIsVisible] = useState(false);
  const [position, setPosition] = useState({ top: 0, left: 0 });
  const [adjustedPosition, setAdjustedPosition] = useState({ top: 0, left: 0, transformX: '-50%' });
  const tooltipRef = useRef<HTMLDivElement>(null);
  const triggerRef = useRef<HTMLElement>(null);
  const closeTimeoutRef = useRef<NodeJS.Timeout | null>(null);
  const isMouseOverRef = useRef(false);

  const handleMouseEnter = (e: React.MouseEvent) => {
    // Clear any pending close timeout
    if (closeTimeoutRef.current) {
      clearTimeout(closeTimeoutRef.current);
      closeTimeoutRef.current = null;
    }

    isMouseOverRef.current = true;

    const rect = e.currentTarget.getBoundingClientRect();
    setPosition({
      top: rect.top,
      left: rect.left + rect.width / 2,
    });
    setIsVisible(true);
  };

  const handleMouseLeave = () => {
    isMouseOverRef.current = false;
    // Delay closing to allow mouse to move to tooltip
    closeTimeoutRef.current = setTimeout(() => {
      if (!isMouseOverRef.current) {
        setIsVisible(false);
      }
    }, 150);
  };

  const handleTooltipMouseEnter = () => {
    // Cancel close if mouse enters tooltip
    isMouseOverRef.current = true;
    if (closeTimeoutRef.current) {
      clearTimeout(closeTimeoutRef.current);
      closeTimeoutRef.current = null;
    }
  };

  const handleTooltipMouseLeave = () => {
    isMouseOverRef.current = false;
    // Close when mouse leaves tooltip
    closeTimeoutRef.current = setTimeout(() => {
      setIsVisible(false);
    }, 100);
  };

  // Cleanup timeout on unmount
  useEffect(() => {
    return () => {
      if (closeTimeoutRef.current) {
        clearTimeout(closeTimeoutRef.current);
      }
    };
  }, []);

  useEffect(() => {
    if (isVisible && tooltipRef.current) {
      const tooltip = tooltipRef.current;
      const tooltipRect = tooltip.getBoundingClientRect();
      const padding = 10; // Padding from viewport edges

      let finalTop = position.top - tooltipRect.height - padding;
      let finalLeft = position.left;
      let transformX = '-50%'; // Default centered transform

      // Check if tooltip goes above viewport - show below instead
      if (finalTop < padding) {
        const triggerElement = triggerRef.current;
        if (triggerElement) {
          const triggerRect = triggerElement.getBoundingClientRect();
          finalTop = triggerRect.bottom + padding;
        }
      }

      // Check if tooltip goes below viewport - move up
      if (finalTop + tooltipRect.height > window.innerHeight - padding) {
        finalTop = window.innerHeight - tooltipRect.height - padding;
      }

      // Calculate with centered transform
      const leftEdge = finalLeft - (tooltipRect.width / 2);
      const rightEdge = finalLeft + (tooltipRect.width / 2);

      // Adjust horizontal position if overflowing
      if (leftEdge < padding) {
        // Align to left edge
        finalLeft = padding;
        transformX = '0%';
      } else if (rightEdge > window.innerWidth - padding) {
        // Align to right edge
        finalLeft = window.innerWidth - padding;
        transformX = '-100%';
      }

      setAdjustedPosition({ top: finalTop, left: finalLeft, transformX });
    }
  }, [isVisible, position]);

  return (
    <>
      {React.cloneElement(children, {
        onMouseEnter: handleMouseEnter,
        onMouseLeave: handleMouseLeave,
        ref: triggerRef,
      })}
      {isVisible && (
        <div
          ref={tooltipRef}
          className="fixed z-50 max-w-2xl w-[calc(100vw-100px)] p-4 rounded-lg shadow-lg bg-white border"
          style={{
            top: `${adjustedPosition.top}px`,
            left: `${adjustedPosition.left}px`,
            transform: `translateX(${adjustedPosition.transformX})`,
            maxHeight: 'calc(100vh - 40px)',
            overflowY: 'auto',
          }}
          onMouseEnter={handleTooltipMouseEnter}
          onMouseLeave={handleTooltipMouseLeave}
        >
          <div className="text-sm space-y-3">
            {citationInfo ? (
              <div className="flex items-center gap-2 text-xs font-medium text-gray-700 bg-gray-50 p-2 rounded">
                <div className="w-5 h-5 flex items-center justify-center">
                  <FileIcon
                    extension={
                      citationInfo.document.file_name.split(".").pop() || ""
                    }
                    color="#E2E8F0"
                    labelColor="#94A3B8"
                  />
                </div>
                <span className="truncate">
                  {citationInfo.knowledge_base.name} /{" "}
                  {citationInfo.document.file_name}
                </span>
              </div>
            ) : (
              <div className="text-xs text-gray-500 italic">Loading...</div>
            )}
            <Divider />
            <p className="text-gray-700 leading-relaxed">{citation.text}</p>
            <Divider />
            {Object.keys(citation.metadata).length > 0 && (
              <div className="text-xs text-gray-500 bg-gray-50 p-2 rounded">
                <div className="font-medium mb-2">Debug Info:</div>
                <div className="space-y-1">
                  {Object.entries(citation.metadata).map(([key, value]) => (
                    <div key={key} className="flex">
                      <span className="font-medium min-w-[100px]">
                        {key}:
                      </span>
                      <span className="text-gray-600">{String(value)}</span>
                    </div>
                  ))}
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
  const [citationInfoMap, setCitationInfoMap] = useState<Record<string, CitationInfo>>({});

  const fetchedKeys = useRef<Set<string>>(new Set());
  const isFetchingRef = useRef(false);

  const processedMarkdown = useMemo(() => {
    return markdown
      .replace(/<think>/g, "## 💭 深度思考\n```think")
      .replace(/<\/think>/g, "```");
  }, [markdown]);

  useEffect(() => {
    if (isFetchingRef.current || citations.length === 0) return;

    const fetchCitationInfo = async () => {
      isFetchingRef.current = true;
      const newInfoMap: Record<string, CitationInfo> = {};

      const promises = citations
        .filter((citation) => {
          const { kb_id, document_id } = citation.metadata;
          if (!kb_id || !document_id) return false;

          const key = `${kb_id}-${document_id}`;
          if (fetchedKeys.current.has(key)) return false;

          fetchedKeys.current.add(key);
          return true;
        })
        .map(async (citation) => {
          const { kb_id, document_id } = citation.metadata;
          const key = `${kb_id}-${document_id}`;

          try {
            const [kb, doc] = await Promise.all([
              api.get(`/api/knowledge-base/${kb_id}`),
              api.get(`/api/knowledge-base/${kb_id}/documents/${document_id}`),
            ]);

            newInfoMap[key] = {
              knowledge_base: {
                name: kb.name,
              },
              document: {
                file_name: doc.file_name,
                knowledge_base: {
                  name: kb.name,
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
  }, [citations.length]);

  const CitationLink = (
    props: ClassAttributes<HTMLAnchorElement> &
      AnchorHTMLAttributes<HTMLAnchorElement>
  ) => {
    const citationId = props.href?.match(/^(\d+)$/)?.[1];
    const citation = citationId
      ? citations[parseInt(citationId) - 1]
      : null;

    if (!citation) {
      return <a>[{props.href}]</a>;
    }

    const citationKey = `${citation.metadata.kb_id}-${citation.metadata.document_id}`;
    const citationInfo = citationInfoMap[citationKey];

    return (
      <CitationTooltip citation={citation} citationInfo={citationInfo}>
        <a
          {...props}
          href="#"
          role="button"
          className="inline-flex items-center gap-1 px-1.5 py-0.5 text-xs font-medium text-blue-600 bg-blue-50 rounded hover:bg-blue-100 transition-colors relative cursor-pointer"
          onClick={(e) => e.preventDefault()}
        >
          <span className="absolute -top-3 -right-1">[{props.href}]</span>
        </a>
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
    <div className="prose prose-sm max-w-full">
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