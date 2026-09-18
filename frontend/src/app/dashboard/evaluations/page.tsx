'use client';

import React, { useState, useEffect, useCallback } from 'react';
import {
  Activity,
  Server,
  Database,
  Zap,
  Layers,
  HardDrive,
  Cpu,
  RefreshCw,
  CheckCircle2,
  AlertTriangle,
  XCircle,
  Clock,
  ExternalLink,
  ChevronRight,
  ShieldCheck,
  BarChart2,
  FileText,
  Search,
  Sparkles,
} from 'lucide-react';
import { api } from '@/lib/api';
import DashboardLayout from '@/components/layout/dashboard-layout';
import { useToast } from '@/components/ui/use-toast';
import { Tabs, TabsContent, TabsList, TabsTrigger } from '@/components/ui/tabs';
import { Dialog, DialogContent, DialogHeader, DialogTitle, DialogDescription } from '@/components/ui/dialog';

interface ContainerHealth {
  service_name: string;
  container_name: string;
  status: 'healthy' | 'degraded' | 'unhealthy' | string;
  latency_ms: number;
  port_mapping: string;
  details: Record<string, any>;
}

interface DetailedSystemHealth {
  overall_status: 'healthy' | 'degraded' | 'unhealthy' | string;
  timestamp: string;
  version: string;
  environment: string;
  uptime_seconds: number;
  services: ContainerHealth[];
}

interface GateCheck {
  metric: string;
  score: number;
  target: string;
  passed: boolean;
  info_only?: boolean;
}

interface MetricAverages {
  faithfulness?: number;
  answer_relevancy?: number;
  context_precision?: number;
  context_recall?: number;
  answer_similarity?: number;
  answer_correctness?: number;
}

interface EvaluationReportSummary {
  report_id: string;
  timestamp: string;
  kb_name: string;
  dataset?: string;
  total_queries: number;
  avg_latency_seconds: number;
  overall_passed: boolean;
  metric_averages: MetricAverages;
  gate_checks: GateCheck[];
}

interface QueryResult {
  query: string;
  answer?: string;
  reference_answer?: string;
  contexts: string[];
  response_time?: number;
  faithfulness?: number;
  answer_relevancy?: number;
  context_precision?: number;
  context_recall?: number;
}

interface EvaluationReportDetail extends EvaluationReportSummary {
  results: QueryResult[];
}

export default function EvaluationsPage() {
  const { toast } = useToast();
  const [activeTab, setActiveTab] = useState<'containers' | 'evaluations'>('containers');
  const [healthData, setHealthData] = useState<DetailedSystemHealth | null>(null);
  const [reports, setReports] = useState<EvaluationReportSummary[]>([]);
  const [selectedReport, setSelectedReport] = useState<EvaluationReportDetail | null>(null);
  const [loadingHealth, setLoadingHealth] = useState(true);
  const [loadingReports, setLoadingReports] = useState(true);
  const [loadingDetail, setLoadingDetail] = useState(false);
  const [autoRefreshInterval, setAutoRefreshInterval] = useState<number>(10); // seconds, 0 = off
  const [lastRefreshed, setLastRefreshed] = useState<Date>(new Date());
  const [detailModalOpen, setDetailModalOpen] = useState(false);

  const fetchHealth = useCallback(async () => {
    try {
      const data = await api.get('/api/system/health/detailed');
      setHealthData(data);
      setLastRefreshed(new Date());
    } catch {
      toast({
        title: 'Health Check Failed',
        description: 'Unable to retrieve container health telemetry.',
        variant: 'destructive',
      });
    } finally {
      setLoadingHealth(false);
    }
  }, [toast]);

  const fetchReports = useCallback(async () => {
    try {
      const data = await api.get('/api/system/evaluations/reports?limit=20');
      setReports(data);
    } catch {
      toast({
        title: 'Evaluation Reports Error',
        description: 'Failed to load RAG evaluation benchmark history.',
        variant: 'destructive',
      });
    } finally {
      setLoadingReports(false);
    }
  }, [toast]);

  const fetchReportDetail = async (reportId: string) => {
    setLoadingDetail(true);
    setDetailModalOpen(true);
    try {
      const detail = await api.get(`/api/system/evaluations/reports/${reportId}`);
      setSelectedReport(detail);
    } catch {
      toast({
        title: 'Error',
        description: 'Failed to load report queries.',
        variant: 'destructive',
      });
    } finally {
      setLoadingDetail(false);
    }
  };

  useEffect(() => {
    fetchHealth();
    fetchReports();
  }, [fetchHealth, fetchReports]);

  // Auto-refresh interval
  useEffect(() => {
    if (autoRefreshInterval <= 0) return;
    const interval = setInterval(() => {
      fetchHealth();
    }, autoRefreshInterval * 1000);
    return () => clearInterval(interval);
  }, [autoRefreshInterval, fetchHealth]);

  const formatUptime = (seconds: number) => {
    const hrs = Math.floor(seconds / 3600);
    const mins = Math.floor((seconds % 3600) / 60);
    const secs = Math.floor(seconds % 60);
    if (hrs > 0) return `${hrs}h ${mins}m ${secs}s`;
    if (mins > 0) return `${mins}m ${secs}s`;
    return `${secs}s`;
  };

  const getServiceIcon = (name: string) => {
    const lower = name.toLowerCase();
    if (lower.includes('postgres') || lower.includes('database')) return Database;
    if (lower.includes('redis') || lower.includes('cache')) return Zap;
    if (lower.includes('chroma') || lower.includes('vector')) return Layers;
    if (lower.includes('minio') || lower.includes('storage')) return HardDrive;
    if (lower.includes('query')) return Search;
    if (lower.includes('ingestion') || lower.includes('worker')) return Cpu;
    return Server;
  };

  const getLatencyBadgeClass = (latency: number) => {
    if (latency < 10) return 'bg-emerald-500/10 text-emerald-400 border-emerald-500/20';
    if (latency < 50) return 'bg-sky-500/10 text-sky-400 border-sky-500/20';
    if (latency < 150) return 'bg-amber-500/10 text-amber-400 border-amber-500/20';
    return 'bg-rose-500/10 text-rose-400 border-rose-500/20';
  };

  const latestReport = reports.length > 0 ? reports[0] : null;

  return (
    <DashboardLayout>
      <div className="p-8 max-w-7xl mx-auto space-y-8">
      {/* Header & Status Bar */}
      <div className="flex flex-col md:flex-row md:items-center justify-between gap-4 border-b border-border/60 pb-6">
        <div>
          <div className="flex items-center gap-3">
            <div className="h-10 w-10 rounded-xl bg-gradient-to-br from-indigo-500/20 to-purple-500/20 border border-indigo-500/30 flex items-center justify-center text-indigo-400">
              <Activity className="h-5 w-5" />
            </div>
            <div>
              <h1 className="text-2xl font-bold tracking-tight text-foreground flex items-center gap-2">
                System Observability & RAG Quality
              </h1>
              <p className="text-sm text-muted-foreground">
                Real-time 7-container topology telemetry and Ragas golden-set benchmark history.
              </p>
            </div>
          </div>
        </div>

        {/* Global Controls & Auto-refresh */}
        <div className="flex items-center gap-3">
          <div className="flex items-center gap-2 bg-muted/40 border border-border/60 px-3 py-1.5 rounded-lg text-xs">
            <Clock className="h-3.5 w-3.5 text-muted-foreground" />
            <span className="text-muted-foreground">Auto-refresh:</span>
            <select
              value={autoRefreshInterval}
              onChange={(e) => setAutoRefreshInterval(Number(e.target.value))}
              className="bg-transparent border-0 font-medium text-foreground focus:ring-0 cursor-pointer"
            >
              <option value={0}>Off</option>
              <option value={5}>5s</option>
              <option value={10}>10s</option>
              <option value={30}>30s</option>
            </select>
          </div>

          <button
            onClick={() => {
              fetchHealth();
              fetchReports();
            }}
            disabled={loadingHealth}
            className="flex items-center gap-2 px-3 py-1.5 rounded-lg bg-primary/10 hover:bg-primary/20 text-primary border border-primary/20 text-xs font-medium transition-colors"
          >
            <RefreshCw className={`h-3.5 w-3.5 ${loadingHealth ? 'animate-spin' : ''}`} />
            Refresh
          </button>
        </div>
      </div>

      {/* Health Overview Banner */}
      {healthData && (
        <div className="grid grid-cols-1 md:grid-cols-4 gap-4">
          <div className="p-4 rounded-xl border border-border/60 bg-card/60 backdrop-blur-sm flex items-center gap-4">
            <div
              className={`h-12 w-12 rounded-xl flex items-center justify-center ${
                healthData.overall_status === 'healthy'
                  ? 'bg-emerald-500/10 text-emerald-400 border border-emerald-500/20'
                  : healthData.overall_status === 'degraded'
                  ? 'bg-amber-500/10 text-amber-400 border border-amber-500/20'
                  : 'bg-rose-500/10 text-rose-400 border border-rose-500/20'
              }`}
            >
              {healthData.overall_status === 'healthy' ? (
                <CheckCircle2 className="h-6 w-6" />
              ) : healthData.overall_status === 'degraded' ? (
                <AlertTriangle className="h-6 w-6" />
              ) : (
                <XCircle className="h-6 w-6" />
              )}
            </div>
            <div>
              <p className="text-xs text-muted-foreground uppercase font-medium tracking-wider">Overall System</p>
              <p className="text-base font-semibold capitalize text-foreground">
                {healthData.overall_status === 'healthy'
                  ? 'All Systems Healthy'
                  : healthData.overall_status === 'degraded'
                  ? 'Degraded Performance'
                  : 'Service Outage'}
              </p>
            </div>
          </div>

          <div className="p-4 rounded-xl border border-border/60 bg-card/60 backdrop-blur-sm flex items-center gap-4">
            <div className="h-12 w-12 rounded-xl bg-indigo-500/10 border border-indigo-500/20 flex items-center justify-center text-indigo-400">
              <Server className="h-6 w-6" />
            </div>
            <div>
              <p className="text-xs text-muted-foreground uppercase font-medium tracking-wider">Containers Monitored</p>
              <p className="text-base font-semibold text-foreground">
                {healthData.services.filter((s) => s.status === 'healthy').length} / {healthData.services.length} Healthy
              </p>
            </div>
          </div>

          <div className="p-4 rounded-xl border border-border/60 bg-card/60 backdrop-blur-sm flex items-center gap-4">
            <div className="h-12 w-12 rounded-xl bg-violet-500/10 border border-violet-500/20 flex items-center justify-center text-violet-400">
              <Clock className="h-6 w-6" />
            </div>
            <div>
              <p className="text-xs text-muted-foreground uppercase font-medium tracking-wider">Backend Uptime</p>
              <p className="text-base font-semibold text-foreground">{formatUptime(healthData.uptime_seconds)}</p>
            </div>
          </div>

          <div className="p-4 rounded-xl border border-border/60 bg-card/60 backdrop-blur-sm flex items-center gap-4">
            <div className="h-12 w-12 rounded-xl bg-sky-500/10 border border-sky-500/20 flex items-center justify-center text-sky-400">
              <ShieldCheck className="h-6 w-6" />
            </div>
            <div>
              <p className="text-xs text-muted-foreground uppercase font-medium tracking-wider">Environment</p>
              <p className="text-base font-semibold uppercase text-foreground">
                {healthData.environment} (v{healthData.version})
              </p>
            </div>
          </div>
        </div>
      )}

      {/* Tabs */}
      <Tabs value={activeTab} onValueChange={(val) => setActiveTab(val as any)} className="w-full">
        <TabsList className="grid grid-cols-2 max-w-md">
          <TabsTrigger value="containers" className="flex items-center gap-2">
            <Server className="h-4 w-4" />
            7-Container Topology
          </TabsTrigger>
          <TabsTrigger value="evaluations" className="flex items-center gap-2">
            <BarChart2 className="h-4 w-4" />
            Ragas Quality Benchmarks
          </TabsTrigger>
        </TabsList>

        {/* TAB 1: 7-Container Topology */}
        <TabsContent value="containers" className="mt-6 space-y-6">
          <div className="grid grid-cols-1 md:grid-cols-2 lg:grid-cols-3 gap-5">
            {healthData?.services.map((svc) => {
              const Icon = getServiceIcon(svc.service_name);
              const isHealthy = svc.status === 'healthy';
              return (
                <div
                  key={svc.container_name}
                  className="rounded-xl border border-border/70 bg-card/70 backdrop-blur-sm p-5 shadow-sm hover:border-border transition-all space-y-4"
                >
                  <div className="flex items-start justify-between">
                    <div className="flex items-center gap-3">
                      <div className="h-10 w-10 rounded-lg bg-muted/60 border border-border/60 flex items-center justify-center text-foreground">
                        <Icon className="h-5 w-5 text-primary" />
                      </div>
                      <div>
                        <h3 className="font-semibold text-sm text-foreground">{svc.service_name}</h3>
                        <p className="text-xs text-muted-foreground font-mono">{svc.container_name}</p>
                      </div>
                    </div>

                    <span
                      className={`inline-flex items-center gap-1.5 px-2 py-0.5 rounded-full text-xs font-medium border ${
                        isHealthy
                          ? 'bg-emerald-500/10 text-emerald-400 border-emerald-500/20'
                          : 'bg-amber-500/10 text-amber-400 border-amber-500/20'
                      }`}
                    >
                      <span
                        className={`h-1.5 w-1.5 rounded-full ${
                          isHealthy ? 'bg-emerald-400 animate-pulse' : 'bg-amber-400'
                        }`}
                      />
                      {svc.status}
                    </span>
                  </div>

                  {/* Metrics Row */}
                  <div className="grid grid-cols-2 gap-2 pt-2 border-t border-border/40 text-xs">
                    <div>
                      <span className="text-muted-foreground">Latency:</span>
                      <div
                        className={`mt-0.5 inline-block font-mono font-medium px-2 py-0.5 rounded border text-xs ${getLatencyBadgeClass(
                          svc.latency_ms
                        )}`}
                      >
                        {svc.latency_ms} ms
                      </div>
                    </div>
                    <div>
                      <span className="text-muted-foreground">Port / Role:</span>
                      <p className="mt-0.5 font-mono text-foreground text-xs truncate">
                        {svc.port_mapping || 'Internal'}
                      </p>
                    </div>
                  </div>

                  {/* Details payload */}
                  {Object.keys(svc.details).length > 0 && (
                    <div className="bg-muted/30 rounded-lg p-2.5 border border-border/30 text-xs space-y-1">
                      {Object.entries(svc.details).map(([k, v]) => (
                        <div key={k} className="flex justify-between items-center text-xs">
                          <span className="text-muted-foreground font-mono">{k}:</span>
                          <span className="font-medium text-foreground font-mono truncate max-w-[160px]">
                            {String(v)}
                          </span>
                        </div>
                      ))}
                    </div>
                  )}
                </div>
              );
            })}
          </div>
        </TabsContent>

        {/* TAB 2: Ragas Quality Benchmarks */}
        <TabsContent value="evaluations" className="mt-6 space-y-6">
          {latestReport ? (
            <div className="space-y-6">
              {/* Latest Run Banner */}
              <div className="rounded-xl border border-primary/20 bg-gradient-to-r from-primary/5 via-primary/10 to-transparent p-6 space-y-4">
                <div className="flex flex-col md:flex-row md:items-center justify-between gap-3">
                  <div>
                    <div className="flex items-center gap-2">
                      <Sparkles className="h-5 w-5 text-primary" />
                      <h2 className="text-lg font-bold text-foreground">Latest Golden Evaluation Benchmark</h2>
                      <span
                        className={`px-2 py-0.5 rounded-full text-xs font-medium border ${
                          latestReport.overall_passed
                            ? 'bg-emerald-500/10 text-emerald-400 border-emerald-500/20'
                            : 'bg-rose-500/10 text-rose-400 border-rose-500/20'
                        }`}
                      >
                        {latestReport.overall_passed ? '✓ Quality Gates Passed' : '✗ Gates Failed'}
                      </span>
                    </div>
                    <p className="text-xs text-muted-foreground mt-1">
                      Evaluated on Knowledge Base: <strong className="text-foreground">{latestReport.kb_name}</strong> |{' '}
                      Dataset: <strong className="text-foreground">{latestReport.dataset || 'Validation Set'}</strong> |{' '}
                      Timestamp: {new Date(latestReport.timestamp).toLocaleString()}
                    </p>
                  </div>

                  <button
                    onClick={() => fetchReportDetail(latestReport.report_id)}
                    className="flex items-center gap-1.5 px-3 py-1.5 bg-primary text-primary-foreground hover:bg-primary/90 rounded-lg text-xs font-medium transition-colors self-start md:self-auto shadow-sm"
                  >
                    Inspect Queries
                    <ChevronRight className="h-3.5 w-3.5" />
                  </button>
                </div>

                {/* 4 Core KPI Tiles */}
                <div className="grid grid-cols-2 md:grid-cols-4 gap-4 pt-2">
                  <div className="bg-card/80 p-4 rounded-lg border border-border/50 space-y-1">
                    <p className="text-xs text-muted-foreground font-medium">Faithfulness (Factuality)</p>
                    <p className="text-2xl font-bold text-emerald-400">
                      {((latestReport.metric_averages.faithfulness || 0) * 100).toFixed(1)}%
                    </p>
                    <p className="text-[11px] text-muted-foreground">Target: &ge; 85.0%</p>
                  </div>

                  <div className="bg-card/80 p-4 rounded-lg border border-border/50 space-y-1">
                    <p className="text-xs text-muted-foreground font-medium">Answer Relevancy</p>
                    <p className="text-2xl font-bold text-sky-400">
                      {((latestReport.metric_averages.answer_relevancy || 0) * 100).toFixed(1)}%
                    </p>
                    <p className="text-[11px] text-muted-foreground">Target: &ge; 85.0%</p>
                  </div>

                  <div className="bg-card/80 p-4 rounded-lg border border-border/50 space-y-1">
                    <p className="text-xs text-muted-foreground font-medium">Context Precision</p>
                    <p className="text-2xl font-bold text-indigo-400">
                      {((latestReport.metric_averages.context_precision || 0) * 100).toFixed(1)}%
                    </p>
                    <p className="text-[11px] text-muted-foreground">Target: &ge; 90.0%</p>
                  </div>

                  <div className="bg-card/80 p-4 rounded-lg border border-border/50 space-y-1">
                    <p className="text-xs text-muted-foreground font-medium">Avg Latency per Query</p>
                    <p className="text-2xl font-bold text-foreground">{latestReport.avg_latency_seconds}s</p>
                    <p className="text-[11px] text-muted-foreground">Queries: {latestReport.total_queries}</p>
                  </div>
                </div>
              </div>

              {/* Gate Verification Matrix */}
              <div className="rounded-xl border border-border/60 bg-card/60 backdrop-blur-sm p-6 space-y-4">
                <h3 className="text-sm font-bold uppercase tracking-wider text-muted-foreground">
                  Quality Gate Verification Matrix
                </h3>
                <div className="grid grid-cols-1 md:grid-cols-3 gap-4">
                  {latestReport.gate_checks.map((gc) => (
                    <div
                      key={gc.metric}
                      className="p-3.5 rounded-lg border border-border/40 bg-muted/20 flex items-center justify-between"
                    >
                      <div>
                        <p className="text-sm font-medium text-foreground">{gc.metric}</p>
                        <p className="text-xs text-muted-foreground">
                          Target: {gc.target} | Score: {(gc.score * 100).toFixed(1)}%
                        </p>
                      </div>
                      <span
                        className={`px-2 py-0.5 rounded text-xs font-semibold ${
                          gc.passed
                            ? 'bg-emerald-500/10 text-emerald-400 border border-emerald-500/20'
                            : 'bg-rose-500/10 text-rose-400 border border-rose-500/20'
                        }`}
                      >
                        {gc.passed ? 'PASS' : 'FAIL'}
                      </span>
                    </div>
                  ))}
                </div>
              </div>

              {/* Historical Runs Table */}
              <div className="rounded-xl border border-border/60 bg-card/60 backdrop-blur-sm overflow-hidden">
                <div className="p-4 border-b border-border/60 bg-muted/30">
                  <h3 className="text-sm font-semibold text-foreground">Evaluation Benchmark Run History</h3>
                </div>
                <div className="overflow-x-auto">
                  <table className="w-full text-left text-sm">
                    <thead className="bg-muted/40 text-muted-foreground border-b border-border/40 text-xs">
                      <tr>
                        <th className="p-3.5 font-medium">Report ID / Timestamp</th>
                        <th className="p-3.5 font-medium">Knowledge Base</th>
                        <th className="p-3.5 font-medium">Queries</th>
                        <th className="p-3.5 font-medium">Faithfulness</th>
                        <th className="p-3.5 font-medium">Relevancy</th>
                        <th className="p-3.5 font-medium">Precision</th>
                        <th className="p-3.5 font-medium">Status</th>
                        <th className="p-3.5 font-medium text-right">Actions</th>
                      </tr>
                    </thead>
                    <tbody className="divide-y divide-border/40 text-xs">
                      {reports.map((r) => (
                        <tr key={r.report_id} className="hover:bg-muted/20 transition-colors">
                          <td className="p-3.5 font-mono text-foreground">
                            {new Date(r.timestamp).toLocaleString()}
                          </td>
                          <td className="p-3.5 font-medium text-foreground">{r.kb_name}</td>
                          <td className="p-3.5 text-muted-foreground">{r.total_queries}</td>
                          <td className="p-3.5 font-mono text-emerald-400">
                            {((r.metric_averages.faithfulness || 0) * 100).toFixed(1)}%
                          </td>
                          <td className="p-3.5 font-mono text-sky-400">
                            {((r.metric_averages.answer_relevancy || 0) * 100).toFixed(1)}%
                          </td>
                          <td className="p-3.5 font-mono text-indigo-400">
                            {((r.metric_averages.context_precision || 0) * 100).toFixed(1)}%
                          </td>
                          <td className="p-3.5">
                            <span
                              className={`px-2 py-0.5 rounded text-[11px] font-medium ${
                                r.overall_passed
                                  ? 'bg-emerald-500/10 text-emerald-400'
                                  : 'bg-rose-500/10 text-rose-400'
                              }`}
                            >
                              {r.overall_passed ? 'PASSED' : 'FAILED'}
                            </span>
                          </td>
                          <td className="p-3.5 text-right">
                            <button
                              onClick={() => fetchReportDetail(r.report_id)}
                              className="text-primary hover:underline font-medium"
                            >
                              Inspect
                            </button>
                          </td>
                        </tr>
                      ))}
                    </tbody>
                  </table>
                </div>
              </div>
            </div>
          ) : (
            <div className="text-center py-12 border border-dashed border-border rounded-xl text-muted-foreground space-y-2">
              <FileText className="h-8 w-8 mx-auto text-muted-foreground/60" />
              <p className="text-sm font-medium text-foreground">No evaluation runs recorded yet</p>
              <p className="text-xs">Run `./rag-evaluate` or headless evaluation tests to populate benchmark data.</p>
            </div>
          )}
        </TabsContent>
      </Tabs>

      {/* Query Inspection Modal */}
      <Dialog open={detailModalOpen} onOpenChange={setDetailModalOpen}>
        <DialogContent className="max-w-4xl max-h-[85vh] overflow-y-auto">
          <DialogHeader>
            <DialogTitle className="flex items-center gap-2">
              <BarChart2 className="h-5 w-5 text-primary" />
              Evaluation Run Query Inspector
            </DialogTitle>
            <DialogDescription>
              Inspecting ground truths, generated responses, and context retrievals for{' '}
              <strong className="text-foreground">{selectedReport?.kb_name}</strong>
            </DialogDescription>
          </DialogHeader>

          {loadingDetail ? (
            <div className="py-12 flex justify-center items-center">
              <RefreshCw className="h-6 w-6 animate-spin text-primary" />
            </div>
          ) : selectedReport?.results && selectedReport.results.length > 0 ? (
            <div className="space-y-6 mt-4">
              {selectedReport.results.map((res, idx) => (
                <div key={idx} className="rounded-xl border border-border/60 bg-muted/20 p-5 space-y-4">
                  <div className="flex items-start justify-between gap-4">
                    <span className="px-2 py-0.5 rounded bg-primary/10 text-primary font-mono text-xs font-bold">
                      Query #{idx + 1}
                    </span>
                    <div className="flex items-center gap-3 text-xs font-mono">
                      <span className="text-emerald-400">
                        Faithfulness: {((res.faithfulness || 0) * 100).toFixed(1)}%
                      </span>
                      <span className="text-sky-400">
                        Relevancy: {((res.answer_relevancy || 0) * 100).toFixed(1)}%
                      </span>
                      <span className="text-indigo-400">
                        Precision: {((res.context_precision || 0) * 100).toFixed(1)}%
                      </span>
                    </div>
                  </div>

                  <div>
                    <p className="text-xs font-semibold text-muted-foreground uppercase">Prompt Query</p>
                    <p className="text-sm font-medium text-foreground mt-0.5">{res.query}</p>
                  </div>

                  {res.answer && (
                    <div className="bg-card/70 p-3.5 rounded-lg border border-border/40">
                      <p className="text-xs font-semibold text-primary uppercase">Generated AI Answer</p>
                      <p className="text-xs text-foreground/90 mt-1 whitespace-pre-wrap leading-relaxed">{res.answer}</p>
                    </div>
                  )}

                  {res.reference_answer && (
                    <div className="bg-muted/40 p-3.5 rounded-lg border border-border/30">
                      <p className="text-xs font-semibold text-muted-foreground uppercase">Ground Truth Reference</p>
                      <p className="text-xs text-muted-foreground mt-1 whitespace-pre-wrap leading-relaxed line-clamp-4">
                        {res.reference_answer}
                      </p>
                    </div>
                  )}

                  {res.contexts && res.contexts.length > 0 && (
                    <div className="space-y-1.5">
                      <p className="text-xs font-semibold text-muted-foreground uppercase">
                        Retrieved Context Chunks ({res.contexts.length})
                      </p>
                      <div className="space-y-1.5 max-h-40 overflow-y-auto">
                        {res.contexts.map((ctx, cIdx) => (
                          <div
                            key={cIdx}
                            className="text-[11px] font-mono bg-background/80 border border-border/30 rounded p-2 text-muted-foreground line-clamp-2"
                          >
                            {ctx}
                          </div>
                        ))}
                      </div>
                    </div>
                  )}
                </div>
              ))}
            </div>
          ) : (
            <div className="py-8 text-center text-xs text-muted-foreground">
              No query breakdowns available for this run.
            </div>
          )}
        </DialogContent>
      </Dialog>
      </div>
    </DashboardLayout>
  );
}
