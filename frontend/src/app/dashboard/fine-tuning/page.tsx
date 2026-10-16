'use client';

import { useEffect, useState, useMemo } from 'react';
import { api } from '@/lib/api';
import DashboardLayout from '@/components/layout/dashboard-layout';
import { Button } from '@/components/ui/button';
import { useToast } from '@/components/ui/use-toast';
import { formatDateTime } from '@/lib/utils';
import {
  Sparkles,
  Sliders,
  History,
  Play,
  RotateCcw,
  CheckCircle2,
  AlertCircle,
  Save,
  Code2,
  Clock,
  User,
  Copy,
  Check,
  FileCode,
  Zap,
  Info,
  HelpCircle,
} from 'lucide-react';

interface UserInfo {
  id: number;
  email: string;
}

interface PromptVersion {
  id: number;
  content: string;
  version_number: number;
  is_active: boolean;
  activated_by_user?: UserInfo;
  activation_reason?: string;
  created_at: string;
  updated_at?: string;
}

interface PromptResponse {
  name: string;
  active_version: PromptVersion | null;
  all_versions: PromptVersion[];
}

interface PromptTestResult {
  formatted_prompt: string;
  estimated_tokens: number;
  character_count: number;
  missing_variables: string[];
  detected_variables: string[];
}

const PROMPT_METADATA: Record<
  string,
  {
    title: string;
    simpleRole: string;
    simpleWhen: string;
    simpleExample: string;
    stageBadge: string;
    expectedInputs: { name: string; desc: string }[];
    defaultVars: Record<string, string>;
  }
> = {
  contextualize_q_system_prompt: {
    title: 'Contextualize Query Node',
    simpleRole: 'Rewrites short follow-up questions into complete searches',
    simpleWhen:
      'Used automatically when you ask a follow-up question in an existing chat. If you type "Tell me more" or "What about in winter?", this prompt reads your conversation history and rewrites your message into a full question so document search works accurately.',
    simpleExample: 'User asks: "Can you give examples?" ➔ Rewritten to: "What are examples of crop rotation in dry climates?"',
    stageBadge: 'Pre-Search Query Rewriter',
    expectedInputs: [
      { name: 'chat_history', desc: 'Previous messages in the chat session' },
      { name: 'question', desc: 'The latest follow-up question asked by user' },
    ],
    defaultVars: {
      chat_history: 'User: What are sustainable soil practices?\nAssistant: Crop rotation and cover cropping improve organic matter.',
      question: 'Can you give more examples of them in dry climates?',
    },
  },
  qa_strict_prompt: {
    title: 'QA Strict Grounding Node',
    simpleRole: 'Answers strictly from your uploaded files with citations',
    simpleWhen:
      'The standard answer generator for chat. After relevant document paragraphs are found, this prompt instructs the AI to answer using ONLY the facts from those documents and forbids making up any unmentioned information.',
    simpleExample: 'Answer format: "Organic mulching reduces evaporation by 40% [citation:1]."',
    stageBadge: 'Default Document Answerer',
    expectedInputs: [
      { name: 'context', desc: 'Matching paragraphs found in your uploaded knowledge base' },
      { name: 'question', desc: 'The question to answer' },
    ],
    defaultVars: {
      context:
        'Document: UNEP Soil Report 2024\nSection: Water retention methods recommend organic mulching to reduce surface evaporation by up to 40%.',
      question: 'How does organic mulching improve water retention?',
    },
  },
  qa_flexible_prompt: {
    title: 'QA Flexible Synthesis Node',
    simpleRole: 'Combines uploaded files with general AI knowledge',
    simpleWhen:
      'Used when you want broader advice. It uses your uploaded documents where possible, but can also use general AI knowledge to provide wider explanations and practical suggestions.',
    simpleExample: 'Answers with document facts plus general agricultural recommendations.',
    stageBadge: 'Hybrid & Open Advisor',
    expectedInputs: [
      { name: 'context', desc: 'Matching paragraphs from your documents (if available)' },
      { name: 'question', desc: 'The user question or request' },
    ],
    defaultVars: {
      context:
        'Document: East Africa Agronomy Handbook\nKey crop rotation intervals for sorghum and legumes are 3-4 months.',
      question: 'What crop rotations work best for smallholder sorghum farmers?',
    },
  },
};

export default function FineTuningPage() {
  const { toast } = useToast();
  const [prompts, setPrompts] = useState<Record<string, PromptResponse>>({});
  const [selectedPromptKey, setSelectedPromptKey] = useState<string>('contextualize_q_system_prompt');
  const [loading, setLoading] = useState(true);

  // Editor states
  const [editorContent, setEditorContent] = useState<string>('');
  const [changeReason, setChangeReason] = useState<string>('');
  const [isSaving, setIsSaving] = useState(false);

  // Playground test states
  const [testVariables, setTestVariables] = useState<Record<string, string>>({});
  const [testResult, setTestResult] = useState<PromptTestResult | null>(null);
  const [isTesting, setIsTesting] = useState(false);
  const [activeRightTab, setActiveRightTab] = useState<'playground' | 'history'>('playground');

  // Rollback confirmation
  const [rollbackVersion, setRollbackVersion] = useState<PromptVersion | null>(null);
  const [rollbackReason, setRollbackReason] = useState<string>('');
  const [isRollingBack, setIsRollingBack] = useState(false);

  // Global Settings
  const [globalTopK, setGlobalTopK] = useState<number>(4);
  const [topKInput, setTopKInput] = useState<string>('4');
  const [isUpdatingTopK, setIsUpdatingTopK] = useState(false);

  // Copied indicator
  const [copiedPreview, setCopiedPreview] = useState(false);

  useEffect(() => {
    fetchPrompts();
    fetchGlobalTopK();
  }, []);

  // Update editor and test variables when selected prompt changes
  useEffect(() => {
    const active = prompts[selectedPromptKey]?.active_version;
    if (active) {
      setEditorContent(active.content);
      const defaults = PROMPT_METADATA[selectedPromptKey]?.defaultVars || {};
      setTestVariables({ ...defaults });
    }
  }, [selectedPromptKey, prompts]);

  // Detect variable placeholders in real time
  const detectedVariables = useMemo(() => {
    const matches = editorContent.match(/\{([a-zA-Z0-9_]+)\}/g) || [];
    return Array.from(new Set(matches.map((m) => m.slice(1, -1))));
  }, [editorContent]);

  const fetchPrompts = async () => {
    setLoading(true);
    try {
      const list: PromptResponse[] = await api.get('/api/prompt');
      const map: Record<string, PromptResponse> = {};

      for (const item of list) {
        try {
          const detail: PromptResponse = await api.get(`/api/prompt/${item.name}`);
          map[item.name] = detail;
        } catch {
          map[item.name] = item;
        }
      }
      setPrompts(map);

      if (list.length > 0 && !map[selectedPromptKey]) {
        setSelectedPromptKey(list[0].name);
      }
    } catch (err: any) {
      console.error('Failed to load prompts:', err);
      toast({
        title: 'Error',
        description: err.message || 'Failed to load system prompts',
        variant: 'destructive',
      });
    } finally {
      setLoading(false);
    }
  };

  const fetchGlobalTopK = async () => {
    try {
      const response = await api.get('/api/system-settings/top_k');
      const valStr = String(response.data?.value || response.value || '4');
      const val = parseInt(valStr, 10);
      setGlobalTopK(val);
      setTopKInput(valStr);
    } catch (err: any) {
      console.error('Failed to fetch top_k:', err);
    }
  };

  const handleSavePrompt = async () => {
    if (!editorContent.trim()) {
      toast({ title: 'Validation Error', description: 'Prompt content cannot be empty', variant: 'destructive' });
      return;
    }

    setIsSaving(true);
    try {
      await api.put(`/api/prompt/${selectedPromptKey}`, {
        content: editorContent,
        activation_reason: changeReason.trim() || 'Prompt updated via Studio Editor',
      });
      toast({
        title: 'Prompt Saved & Activated',
        description: `New version published for ${PROMPT_METADATA[selectedPromptKey]?.title || selectedPromptKey}`,
      });
      setChangeReason('');
      await fetchPrompts();
    } catch (err: any) {
      toast({
        title: 'Save Failed',
        description: err.message || 'Failed to save prompt',
        variant: 'destructive',
      });
    } finally {
      setIsSaving(false);
    }
  };

  const handleTestPrompt = async () => {
    setIsTesting(true);
    try {
      const res: PromptTestResult = await api.post('/api/prompt/test', {
        template: editorContent,
        variables: testVariables,
      });
      setTestResult(res);
      setActiveRightTab('playground');
    } catch (err: any) {
      toast({
        title: 'Test Failed',
        description: err.message || 'Failed to format prompt',
        variant: 'destructive',
      });
    } finally {
      setIsTesting(false);
    }
  };

  const handleRollback = async () => {
    if (!rollbackVersion) return;
    setIsRollingBack(true);
    try {
      await api.put(`/api/prompt/${selectedPromptKey}/reactivate/${rollbackVersion.id}`, {
        reactivation_reason: rollbackReason.trim() || `Reactivated v${rollbackVersion.version_number}`,
      });
      toast({
        title: 'Version Reactivated',
        description: `Reactivated v${rollbackVersion.version_number} as active prompt`,
      });
      setRollbackVersion(null);
      setRollbackReason('');
      await fetchPrompts();
    } catch (err: any) {
      toast({
        title: 'Rollback Failed',
        description: err.message || 'Failed to reactivate version',
        variant: 'destructive',
      });
    } finally {
      setIsRollingBack(false);
    }
  };

  const handleUpdateTopK = async () => {
    const num = parseInt(topKInput, 10);
    if (isNaN(num) || num < 1 || num > 20) {
      toast({
        title: 'Invalid Range',
        description: 'Top-K chunks must be a number between 1 and 20',
        variant: 'destructive',
      });
      return;
    }
    setIsUpdatingTopK(true);
    try {
      await api.put('/api/system-settings/top_k', { top_k: num });
      setGlobalTopK(num);
      toast({
        title: 'Setting Saved',
        description: `Global retrieval chunk limit set to ${num}`,
      });
    } catch (err: any) {
      toast({
        title: 'Update Failed',
        description: err.message || 'Failed to update retrieval setting',
        variant: 'destructive',
      });
    } finally {
      setIsUpdatingTopK(false);
    }
  };

  const currentMeta = PROMPT_METADATA[selectedPromptKey] || {
    title: selectedPromptKey,
    simpleRole: '',
    simpleWhen: '',
    simpleExample: '',
    stageBadge: '',
    expectedInputs: [],
    defaultVars: {},
  };
  const currentPrompt = prompts[selectedPromptKey];
  const allVersions = currentPrompt?.all_versions || [];

  return (
    <DashboardLayout>
      <div className="space-y-6 pb-12">
        {/* Studio Top Banner & Global Retrieval Controls */}
        <div className="flex flex-col lg:flex-row lg:items-center justify-between gap-4 rounded-2xl border bg-card p-6 shadow-xs">
          <div className="space-y-1">
            <div className="flex items-center gap-2">
              <div className="h-8 w-8 rounded-xl bg-primary/10 flex items-center justify-center text-primary">
                <Sparkles className="h-4 w-4" />
              </div>
              <h1 className="text-xl font-bold tracking-tight text-foreground">
                System Prompts & Model Studio
              </h1>
            </div>
            <p className="text-xs text-muted-foreground max-w-xl">
              Configure and test runtime system prompts powering the LangGraph RAG pipeline. Hover over any prompt tab below to see exactly when and how it is used.
            </p>
          </div>

          {/* Global Top-K Retrieval Parameter Card */}
          <div className="flex items-center gap-3 bg-muted/50 border rounded-xl p-3 shadow-2xs self-start lg:self-auto">
            <Sliders className="h-4 w-4 text-primary shrink-0" />
            <div>
              <div className="flex items-center gap-1.5">
                <span className="text-xs font-semibold text-foreground">Global Retrieval Top-K:</span>
                <span className="text-xs font-mono font-bold text-primary bg-primary/10 px-1.5 py-0.5 rounded">
                  {globalTopK} chunks
                </span>
              </div>
              <p className="text-[10px] text-muted-foreground">Max chunks retrieved from ChromaDB per query</p>
            </div>
            <div className="flex items-center gap-1.5 ml-2">
              <input
                type="number"
                min="1"
                max="20"
                value={topKInput}
                onChange={(e) => setTopKInput(e.target.value)}
                className="w-14 h-8 text-center text-xs font-mono rounded-lg border bg-background text-foreground outline-none focus:ring-1 focus:ring-primary"
              />
              <Button
                size="sm"
                onClick={handleUpdateTopK}
                disabled={isUpdatingTopK || String(globalTopK) === topKInput}
                className="h-8 text-xs font-medium px-2.5"
              >
                {isUpdatingTopK ? '...' : 'Save'}
              </Button>
            </div>
          </div>
        </div>

        {/* 3 Prompt Tabs with Intuitive Tooltips */}
        <div className="grid grid-cols-1 md:grid-cols-3 gap-3.5">
          {Object.keys(PROMPT_METADATA).map((key) => {
            const meta = PROMPT_METADATA[key];
            const isSelected = selectedPromptKey === key;
            const promptData = prompts[key];
            const versionNum = promptData?.active_version?.version_number || 1;

            return (
              <div
                key={key}
                onClick={() => setSelectedPromptKey(key)}
                className={`relative group cursor-pointer flex flex-col justify-between p-4 rounded-2xl border transition-all ${
                  isSelected
                    ? 'border-primary bg-primary/5 ring-2 ring-primary/20 shadow-xs'
                    : 'border-border bg-card hover:border-primary/40 hover:bg-muted/30'
                }`}
              >
                <div className="space-y-1.5">
                  <div className="flex items-center justify-between gap-2">
                    <span className="text-xs font-bold text-foreground truncate">
                      {meta.title}
                    </span>
                    <span
                      className={`text-[10px] font-medium px-2 py-0.5 rounded-full shrink-0 ${
                        isSelected
                          ? 'bg-primary text-primary-foreground font-semibold'
                          : 'bg-muted text-muted-foreground'
                      }`}
                    >
                      v{versionNum} Active
                    </span>
                  </div>

                  <p className="text-[11px] text-muted-foreground leading-snug">
                    {meta.simpleRole}
                  </p>
                </div>

                {/* Tooltip trigger bar */}
                <div className="mt-3 pt-2.5 border-t border-border/60 flex items-center justify-between">
                  <div className="relative group/tooltip inline-flex items-center gap-1.5 text-[11px] text-primary font-medium">
                    <HelpCircle className="h-3.5 w-3.5" />
                    <span>When is this used?</span>

                    {/* Floating Tooltip Box */}
                    <div className="pointer-events-none absolute bottom-full left-0 mb-2 w-72 sm:w-80 rounded-xl bg-popover border text-popover-foreground p-3 shadow-lg opacity-0 translate-y-1 group-hover/tooltip:opacity-100 group-hover/tooltip:translate-y-0 transition-all duration-200 z-30 text-xs">
                      <div className="font-semibold text-primary mb-1 flex items-center gap-1">
                        <Info className="h-3.5 w-3.5" />
                        {meta.title}
                      </div>
                      <p className="text-foreground leading-relaxed mb-2 font-normal">
                        {meta.simpleWhen}
                      </p>
                      <div className="text-[11px] bg-muted/60 p-2 rounded-lg border border-border/50 text-muted-foreground">
                        <strong className="text-foreground">Example: </strong>
                        {meta.simpleExample}
                      </div>
                      {/* Triangle arrow */}
                      <div className="absolute top-full left-4 -mt-1 border-4 border-transparent border-t-popover" />
                    </div>
                  </div>

                  <span className="text-[10px] text-muted-foreground font-mono">
                    {meta.stageBadge}
                  </span>
                </div>
              </div>
            );
          })}
        </div>

        {/* Studio 2-Pane Workspace */}
        <div className="grid grid-cols-1 lg:grid-cols-12 gap-6 items-start">
          {/* Left Pane (7 Cols): Template Editor & Variable Bindings */}
          <div className="lg:col-span-7 space-y-4 bg-card rounded-2xl border p-5 shadow-xs">
            {/* Header with simple context box */}
            <div className="border-b pb-3 space-y-2.5">
              <div className="flex items-center justify-between">
                <div className="flex items-center gap-2">
                  <Code2 className="h-4 w-4 text-primary" />
                  <h3 className="text-sm font-semibold text-foreground">
                    Template Editor ({currentMeta.title})
                  </h3>
                </div>
                <span className="text-xs font-medium text-primary bg-primary/10 px-2.5 py-0.5 rounded-full">
                  {currentMeta.stageBadge}
                </span>
              </div>

              {/* Simple Clear Explainer Box */}
              <div className="bg-muted/40 border rounded-xl p-3 text-xs space-y-2">
                <div className="flex items-start gap-2">
                  <Info className="h-4 w-4 text-primary shrink-0 mt-0.5" />
                  <div className="space-y-1">
                    <p className="text-foreground leading-relaxed">
                      <strong>When this prompt is used: </strong>
                      {currentMeta.simpleWhen}
                    </p>
                    <p className="text-muted-foreground text-[11px]">
                      <strong className="text-foreground">Example: </strong>
                      {currentMeta.simpleExample}
                    </p>
                  </div>
                </div>

                {/* Expected inputs contract */}
                <div className="pt-2 border-t border-border/50 flex flex-wrap items-center gap-2">
                  <span className="text-[11px] font-semibold text-foreground">Available Variables:</span>
                  {currentMeta.expectedInputs.map((inp) => (
                    <span
                      key={inp.name}
                      className="inline-flex items-center gap-1 text-[10px] font-mono bg-background border px-2 py-0.5 rounded-md text-foreground"
                    >
                      <strong className="text-primary">{`{${inp.name}}`}</strong>: {inp.desc}
                    </span>
                  ))}
                </div>
              </div>
            </div>

            {/* Variable Tag Badges */}
            <div className="flex flex-wrap items-center gap-1.5">
              <span className="text-[11px] text-muted-foreground font-medium mr-1">
                Detected Placeholders:
              </span>
              {detectedVariables.length === 0 ? (
                <span className="text-[11px] text-muted-foreground italic">None detected</span>
              ) : (
                detectedVariables.map((v) => (
                  <button
                    key={v}
                    type="button"
                    onClick={() => {
                      setEditorContent((prev) => `${prev} {${v}}`);
                    }}
                    className="inline-flex items-center gap-1 text-[11px] font-mono bg-primary/10 text-primary px-2 py-0.5 rounded-md hover:bg-primary/20 transition-colors"
                    title={`Click to insert {${v}}`}
                  >
                    <span>{`{${v}}`}</span>
                  </button>
                ))
              )}
            </div>

            {/* Editor Textarea */}
            <div className="relative">
              <textarea
                value={editorContent}
                onChange={(e) => setEditorContent(e.target.value)}
                rows={12}
                placeholder="Enter prompt template text with {variables}..."
                className="w-full font-mono text-xs rounded-xl border bg-background p-4 leading-relaxed outline-none focus:ring-2 focus:ring-primary/20 focus:border-primary transition-all text-foreground resize-y shadow-2xs"
              />
            </div>

            {/* Dynamic Variable Input Table */}
            {detectedVariables.length > 0 && (
              <div className="space-y-2.5 pt-2 border-t">
                <div className="flex items-center justify-between">
                  <div className="flex items-center gap-1.5">
                    <Zap className="h-3.5 w-3.5 text-amber-500" />
                    <span className="text-xs font-semibold text-foreground">
                      Playground Test Variables
                    </span>
                  </div>
                  <span className="text-[11px] text-muted-foreground">
                    Provide sample values for live simulation
                  </span>
                </div>

                <div className="space-y-2 max-h-56 overflow-y-auto pr-1">
                  {detectedVariables.map((variable) => (
                    <div
                      key={variable}
                      className="flex flex-col sm:flex-row sm:items-start gap-2 bg-muted/40 p-2.5 rounded-xl border"
                    >
                      <label className="text-xs font-mono font-semibold text-primary sm:w-28 shrink-0 pt-1">
                        {`{${variable}}`}:
                      </label>
                      <textarea
                        rows={2}
                        value={testVariables[variable] || ''}
                        onChange={(e) =>
                          setTestVariables((prev) => ({
                            ...prev,
                            [variable]: e.target.value,
                          }))
                        }
                        placeholder={`Enter sample value for {${variable}}...`}
                        className="flex-1 text-xs rounded-lg border bg-background p-2 font-mono outline-none focus:ring-1 focus:ring-primary text-foreground"
                      />
                    </div>
                  ))}
                </div>
              </div>
            )}

            {/* Save & Publish Section */}
            <div className="space-y-2.5 pt-3 border-t">
              <label className="text-xs font-semibold text-foreground block">
                Changelog / Activation Reason:
              </label>
              <input
                type="text"
                value={changeReason}
                onChange={(e) => setChangeReason(e.target.value)}
                placeholder="e.g. Clarified citation formatting and tone instructions"
                className="w-full h-9 px-3 text-xs rounded-xl border bg-background text-foreground outline-none focus:ring-1 focus:ring-primary placeholder:text-muted-foreground"
              />
              <div className="flex items-center justify-between gap-2 pt-1">
                <Button
                  variant="outline"
                  size="sm"
                  onClick={handleTestPrompt}
                  disabled={isTesting || !editorContent.trim()}
                  className="gap-1.5 text-xs"
                >
                  <Play className="h-3.5 w-3.5 text-primary" />
                  {isTesting ? 'Simulating...' : 'Run Simulation'}
                </Button>

                <Button
                  size="sm"
                  onClick={handleSavePrompt}
                  disabled={isSaving || !editorContent.trim()}
                  className="gap-1.5 text-xs font-semibold"
                >
                  <Save className="h-3.5 w-3.5" />
                  {isSaving ? 'Publishing...' : 'Save & Publish New Version'}
                </Button>
              </div>
            </div>
          </div>

          {/* Right Pane (5 Cols): Live Preview Playground & Version History */}
          <div className="lg:col-span-5 space-y-4">
            {/* Tab Switches */}
            <div className="flex items-center bg-muted/60 border rounded-xl p-1 gap-1 shadow-2xs">
              <button
                type="button"
                onClick={() => setActiveRightTab('playground')}
                className={`flex-1 flex items-center justify-center gap-1.5 py-1.5 text-xs font-medium rounded-lg transition-all ${
                  activeRightTab === 'playground'
                    ? 'bg-background text-foreground font-semibold shadow-xs'
                    : 'text-muted-foreground hover:text-foreground'
                }`}
              >
                <Play className="h-3.5 w-3.5 text-primary" />
                <span>Live Playground</span>
              </button>
              <button
                type="button"
                onClick={() => setActiveRightTab('history')}
                className={`flex-1 flex items-center justify-center gap-1.5 py-1.5 text-xs font-medium rounded-lg transition-all ${
                  activeRightTab === 'history'
                    ? 'bg-background text-foreground font-semibold shadow-xs'
                    : 'text-muted-foreground hover:text-foreground'
                }`}
              >
                <History className="h-3.5 w-3.5 text-primary" />
                <span>Version History ({allVersions.length})</span>
              </button>
            </div>

            {/* Tab 1: Live Playground View */}
            {activeRightTab === 'playground' && (
              <div className="bg-card rounded-2xl border p-5 space-y-4 shadow-xs">
                <div className="flex items-center justify-between">
                  <div className="flex items-center gap-2">
                    <Sparkles className="h-4 w-4 text-primary" />
                    <h4 className="text-xs font-semibold text-foreground">
                      Compiled Prompt Preview
                    </h4>
                  </div>
                  {testResult && (
                    <div className="flex items-center gap-2 text-[11px]">
                      <span className="font-mono bg-primary/10 text-primary px-2 py-0.5 rounded-full font-bold">
                        ~{testResult.estimated_tokens} tokens
                      </span>
                      <span className="text-muted-foreground">
                        {testResult.character_count} chars
                      </span>
                    </div>
                  )}
                </div>

                {/* Live Output */}
                <div className="relative rounded-xl border bg-muted/30 p-4 min-h-[260px] max-h-[380px] overflow-y-auto text-xs font-mono leading-relaxed text-foreground whitespace-pre-wrap">
                  {testResult ? (
                    testResult.formatted_prompt
                  ) : (
                    <div className="flex flex-col items-center justify-center h-48 text-center text-muted-foreground space-y-2">
                      <Play className="h-8 w-8 text-muted-foreground/40" />
                      <p className="text-xs">
                        Click <strong>Run Simulation</strong> to compile and evaluate this prompt with current test variables.
                      </p>
                    </div>
                  )}
                </div>

                {/* Warnings / Missing Variables Indicator */}
                {testResult && testResult.missing_variables.length > 0 && (
                  <div className="flex items-start gap-2 p-3 rounded-xl bg-amber-500/10 border border-amber-500/20 text-amber-800 dark:text-amber-300 text-xs">
                    <AlertCircle className="h-4 w-4 shrink-0 mt-0.5" />
                    <div>
                      <p className="font-semibold">Missing Test Variables:</p>
                      <p className="text-[11px] mt-0.5">
                        {testResult.missing_variables.join(', ')} were left unformatted.
                      </p>
                    </div>
                  </div>
                )}

                {testResult && (
                  <div className="flex justify-end">
                    <Button
                      variant="outline"
                      size="sm"
                      onClick={async () => {
                        await navigator.clipboard.writeText(testResult.formatted_prompt);
                        setCopiedPreview(true);
                        setTimeout(() => setCopiedPreview(false), 2000);
                      }}
                      className="gap-1.5 text-xs"
                    >
                      {copiedPreview ? (
                        <Check className="h-3.5 w-3.5 text-emerald-600" />
                      ) : (
                        <Copy className="h-3.5 w-3.5" />
                      )}
                      <span>{copiedPreview ? 'Copied' : 'Copy Compiled Text'}</span>
                    </Button>
                  </div>
                )}
              </div>
            )}

            {/* Tab 2: Version History & Rollback */}
            {activeRightTab === 'history' && (
              <div className="bg-card rounded-2xl border p-5 space-y-3 shadow-xs max-h-[520px] overflow-y-auto">
                <div className="flex items-center justify-between border-b pb-2.5">
                  <h4 className="text-xs font-semibold text-foreground flex items-center gap-1.5">
                    <History className="h-3.5 w-3.5 text-primary" />
                    Version Timeline
                  </h4>
                  <span className="text-[11px] text-muted-foreground">
                    {allVersions.length} total revision(s)
                  </span>
                </div>

                {allVersions.length === 0 ? (
                  <div className="text-center py-8 text-xs text-muted-foreground">
                    No revision history available for this prompt.
                  </div>
                ) : (
                  allVersions.map((v) => (
                    <div
                      key={v.id}
                      className={`p-3.5 rounded-xl border space-y-2 transition-all ${
                        v.is_active
                          ? 'border-primary bg-primary/5 shadow-2xs'
                          : 'bg-background hover:border-primary/30'
                      }`}
                    >
                      <div className="flex items-center justify-between">
                        <div className="flex items-center gap-2">
                          <span
                            className={`text-xs font-bold font-mono px-2 py-0.5 rounded-md ${
                              v.is_active
                                ? 'bg-primary text-primary-foreground'
                                : 'bg-muted text-muted-foreground'
                            }`}
                          >
                            v{v.version_number}
                          </span>
                          {v.is_active && (
                            <span className="flex items-center gap-1 text-[11px] font-semibold text-emerald-600 dark:text-emerald-400">
                              <CheckCircle2 className="h-3 w-3" />
                              Active
                            </span>
                          )}
                        </div>
                        <span className="text-[10px] text-muted-foreground flex items-center gap-1">
                          <Clock className="h-3 w-3" />
                          {formatDateTime(v.created_at || v.updated_at || '')}
                        </span>
                      </div>

                      {v.activation_reason && (
                        <p className="text-[11px] text-muted-foreground italic line-clamp-2">
                          &ldquo;{v.activation_reason}&rdquo;
                        </p>
                      )}

                      <div className="flex items-center justify-between pt-1 text-[11px]">
                        <span className="text-muted-foreground flex items-center gap-1">
                          <User className="h-3 w-3 text-primary" />
                          {v.activated_by_user?.email || 'System Default'}
                        </span>

                        {!v.is_active && (
                          <button
                            type="button"
                            onClick={() => {
                              setRollbackVersion(v);
                              setRollbackReason(`Rollback to revision v${v.version_number}`);
                            }}
                            className="inline-flex items-center gap-1 text-xs font-semibold text-primary hover:underline"
                          >
                            <RotateCcw className="h-3 w-3" />
                            Rollback to this
                          </button>
                        )}
                      </div>
                    </div>
                  ))
                )}
              </div>
            )}
          </div>
        </div>

        {/* Rollback Confirmation Modal */}
        {rollbackVersion && (
          <div className="fixed inset-0 z-50 flex items-center justify-center bg-black/50 backdrop-blur-xs p-4">
            <div className="w-full max-w-md bg-card rounded-2xl border p-6 space-y-4 shadow-xl">
              <div className="flex items-center gap-2 text-foreground">
                <RotateCcw className="h-5 w-5 text-primary" />
                <h3 className="text-base font-bold">
                  Rollback to Revision v{rollbackVersion.version_number}?
                </h3>
              </div>
              <p className="text-xs text-muted-foreground leading-relaxed">
                This will activate version {rollbackVersion.version_number} as the active prompt for{' '}
                <strong>{PROMPT_METADATA[selectedPromptKey]?.title || selectedPromptKey}</strong> across all RAG queries.
              </p>

              <div className="space-y-1.5">
                <label className="text-xs font-semibold text-foreground">
                  Reactivation Reason:
                </label>
                <input
                  type="text"
                  value={rollbackReason}
                  onChange={(e) => setRollbackReason(e.target.value)}
                  placeholder="Reason for rolling back..."
                  className="w-full h-9 px-3 text-xs rounded-xl border bg-background text-foreground outline-none focus:ring-1 focus:ring-primary"
                />
              </div>

              <div className="flex justify-end gap-2 pt-2">
                <Button
                  variant="outline"
                  size="sm"
                  onClick={() => setRollbackVersion(null)}
                  disabled={isRollingBack}
                >
                  Cancel
                </Button>
                <Button
                  size="sm"
                  onClick={handleRollback}
                  disabled={isRollingBack}
                  className="font-semibold"
                >
                  {isRollingBack ? 'Reactivating...' : 'Confirm Rollback'}
                </Button>
              </div>
            </div>
          </div>
        )}
      </div>
    </DashboardLayout>
  );
}
