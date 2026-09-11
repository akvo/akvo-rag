import Link from "next/link";
import Image from "next/image";
import {
  Zap,
  Database,
  Sparkles,
  ShieldCheck,
  FileText,
  Terminal,
  ArrowRight,
  Search,
  Key,
  CheckCircle2,
  Layers,
  Server,
  Sliders,
} from "lucide-react";

export default function Home() {
  return (
    <main className="min-h-screen bg-white text-slate-900 selection:bg-[#03AD8C] selection:text-white relative overflow-hidden">
      {/* Subtle ambient light gradient accents in Akvo Teal */}
      <div className="absolute top-0 left-1/2 -translate-x-1/2 w-[1100px] h-[550px] bg-gradient-to-b from-[#03AD8C]/10 via-teal-50/40 to-transparent blur-[100px] pointer-events-none -z-10" />
      <div className="absolute top-[750px] right-0 w-[500px] h-[500px] bg-gradient-to-bl from-slate-100/80 via-[#03AD8C]/5 to-transparent blur-[120px] pointer-events-none -z-10" />

      {/* Top Navigation Bar */}
      <nav className="border-b border-slate-200/80 bg-white/90 backdrop-blur-md sticky top-0 z-50">
        <div className="max-w-7xl mx-auto px-4 sm:px-6 lg:px-8 h-16 flex items-center justify-between">
          <div className="flex items-center gap-3">
            <Image
              src="/logo.svg"
              alt="Akvo Logo"
              width={32}
              height={32}
              className="w-8 h-8 rounded-lg shadow-sm"
              priority
            />
            <div className="flex items-center gap-2">
              <span className="font-bold text-lg text-slate-900 tracking-tight">Akvo RAG</span>
              <span className="text-[10px] font-bold uppercase tracking-wider px-2 py-0.5 rounded-full bg-[#03AD8C]/10 text-[#027a63] border border-[#03AD8C]/20">
                v2.0
              </span>
            </div>
          </div>

          <div className="hidden md:flex items-center gap-8 text-sm font-medium text-slate-600">
            <a href="#architecture" className="hover:text-[#03AD8C] transition-colors">
              Architecture
            </a>
            <a href="#features" className="hover:text-[#03AD8C] transition-colors">
              Features
            </a>
            <a href="#preview" className="hover:text-[#03AD8C] transition-colors">
              Live Preview
            </a>
          </div>

          <div className="flex items-center gap-3">
            <Link
              href="/login"
              className="px-4 py-2 text-sm font-medium text-slate-700 hover:text-slate-900 hover:bg-slate-100 rounded-lg transition-all"
            >
              Sign In
            </Link>
            <Link
              href="/register"
              className="px-4 py-2 text-sm font-medium text-white bg-[#03AD8C] hover:bg-[#028f74] rounded-lg shadow-sm shadow-[#03AD8C]/30 transition-all flex items-center gap-1.5"
            >
              Get Started <ArrowRight className="w-4 h-4" />
            </Link>
          </div>
        </div>
      </nav>

      {/* Hero Section */}
      <section className="max-w-7xl mx-auto px-4 sm:px-6 lg:px-8 pt-20 pb-16 text-center">
        {/* Release Pill */}
        <div className="inline-flex items-center gap-2 px-3.5 py-1.5 rounded-full bg-slate-50 border border-slate-200 text-xs font-medium text-slate-700 mb-8 shadow-sm">
          <span className="flex h-2 w-2 rounded-full bg-[#03AD8C] animate-pulse" />
          <span>Dual-Tier Model Optimization & Prompt Caching Active</span>
          <span className="text-slate-400">•</span>
          <span className="text-[#027a63] font-semibold">gpt-4o-mini + gpt-4o</span>
        </div>

        {/* Hero Title */}
        <h1 className="text-5xl sm:text-6xl lg:text-7xl font-extrabold tracking-tight text-slate-900 max-w-4xl mx-auto leading-[1.1]">
          Enterprise Document Retrieval &{" "}
          <span className="text-transparent bg-clip-text bg-gradient-to-r from-[#03AD8C] via-[#028f74] to-[#02725d]">
            Grounded AI Dialogue
          </span>
        </h1>

        {/* Hero Subtitle */}
        <p className="mt-6 text-lg sm:text-xl text-slate-600 max-w-2xl mx-auto font-normal leading-relaxed">
          High-throughput microservice RAG platform with sub-second intent routing, automatic OpenAI prompt caching, and strict citation provenance for domain knowledge.
        </p>

        {/* Action CTAs */}
        <div className="mt-10 flex flex-col sm:flex-row gap-4 justify-center items-center">
          <Link
            href="/register"
            className="px-8 py-3.5 bg-[#03AD8C] hover:bg-[#028f74] text-white rounded-xl text-base font-semibold shadow-lg shadow-[#03AD8C]/20 transition-all duration-200 flex items-center gap-2 w-full sm:w-auto justify-center"
          >
            Launch Free Workspace <ArrowRight className="w-4 h-4" />
          </Link>
          <Link
            href="/login"
            className="px-8 py-3.5 bg-white hover:bg-slate-50 text-slate-700 border border-slate-300 hover:border-slate-400 rounded-xl text-base font-semibold shadow-sm transition-all duration-200 w-full sm:w-auto text-center"
          >
            Sign In to Dashboard
          </Link>
        </div>

        {/* Live Architecture Technology Pills */}
        <div id="architecture" className="mt-16 pt-10 border-t border-slate-200">
          <p className="text-xs font-semibold uppercase tracking-widest text-slate-500 mb-6">
            Production Microservice Stack & Execution Pipeline
          </p>
          <div className="flex flex-wrap items-center justify-center gap-3 max-w-5xl mx-auto">
            <div className="flex items-center gap-2 px-3.5 py-2 rounded-xl bg-slate-50 border border-slate-200 text-sm font-medium text-slate-700 shadow-sm hover:border-[#03AD8C]/50 transition-colors">
              <Zap className="w-4 h-4 text-amber-500" />
              <span>Dual-Tier gpt-4o-mini + gpt-4o</span>
            </div>
            <div className="flex items-center gap-2 px-3.5 py-2 rounded-xl bg-slate-50 border border-slate-200 text-sm font-medium text-slate-700 shadow-sm hover:border-[#03AD8C]/50 transition-colors">
              <Server className="w-4 h-4 text-red-500" />
              <span>Redis 7.2 RPC Dispatcher</span>
            </div>
            <div className="flex items-center gap-2 px-3.5 py-2 rounded-xl bg-slate-50 border border-slate-200 text-sm font-medium text-slate-700 shadow-sm hover:border-[#03AD8C]/50 transition-colors">
              <Database className="w-4 h-4 text-[#03AD8C]" />
              <span>PostgreSQL 17 Database</span>
            </div>
            <div className="flex items-center gap-2 px-3.5 py-2 rounded-xl bg-slate-50 border border-slate-200 text-sm font-medium text-slate-700 shadow-sm hover:border-[#03AD8C]/50 transition-colors">
              <Layers className="w-4 h-4 text-emerald-600" />
              <span>Vector KB MCP (ChromaDB)</span>
            </div>
            <div className="flex items-center gap-2 px-3.5 py-2 rounded-xl bg-slate-50 border border-slate-200 text-sm font-medium text-slate-700 shadow-sm hover:border-[#03AD8C]/50 transition-colors">
              <FileText className="w-4 h-4 text-purple-600" />
              <span>MinIO S3 Async Ingestion</span>
            </div>
            <div className="flex items-center gap-2 px-3.5 py-2 rounded-xl bg-slate-50 border border-slate-200 text-sm font-medium text-slate-700 shadow-sm hover:border-[#03AD8C]/50 transition-colors">
              <Sparkles className="w-4 h-4 text-teal-600" />
              <span>FastAPI & Next.js 14</span>
            </div>
          </div>
        </div>
      </section>

      {/* Interactive Product Feature Grid */}
      <section id="features" className="max-w-7xl mx-auto px-4 sm:px-6 lg:px-8 py-20 border-t border-slate-200 bg-slate-50/50">
        <div className="text-center max-w-3xl mx-auto mb-16">
          <h2 className="text-xs font-semibold uppercase tracking-widest text-[#03AD8C] mb-3">
            Core Platform Capabilities
          </h2>
          <p className="text-3xl sm:text-4xl font-bold tracking-tight text-slate-900">
            Engineered for Grounded Accuracy & Enterprise Scale
          </p>
          <p className="mt-4 text-slate-600">
            From automated document chunking to strict citation suppression and prompt overlays.
          </p>
        </div>

        <div className="grid grid-cols-1 md:grid-cols-2 lg:grid-cols-3 gap-8">
          {/* Card 1: Dual-Tier & Prompt Caching */}
          <div className="p-8 rounded-2xl bg-white border border-slate-200 hover:border-[#03AD8C] hover:shadow-md transition-all duration-300 group">
            <div className="h-12 w-12 rounded-xl bg-[#03AD8C]/10 border border-[#03AD8C]/20 flex items-center justify-center mb-6 group-hover:bg-[#03AD8C]/20 transition-colors">
              <Zap className="w-6 h-6 text-[#03AD8C]" />
            </div>
            <h3 className="text-xl font-semibold text-slate-900 mb-3">
              Dual-Tier Model Optimization
            </h3>
            <p className="text-slate-600 text-sm leading-relaxed mb-4">
              Lightning-fast intent routing and contextualization with <code className="text-[#027a63] font-medium">gpt-4o-mini</code> (&lt;1s), reserving <code className="text-[#027a63] font-medium">gpt-4o</code> for grounded response synthesis.
            </p>
            <div className="flex items-center gap-2 text-xs font-semibold text-[#03AD8C]">
              <CheckCircle2 className="w-4 h-4 text-[#03AD8C]" />
              100% Invariant Prompt Caching Hits
            </div>
          </div>

          {/* Card 2: Knowledge Base & S3 Ingestion */}
          <div className="p-8 rounded-2xl bg-white border border-slate-200 hover:border-[#03AD8C] hover:shadow-md transition-all duration-300 group">
            <div className="h-12 w-12 rounded-xl bg-emerald-50 border border-emerald-100 flex items-center justify-center mb-6 group-hover:bg-emerald-100 transition-colors">
              <Database className="w-6 h-6 text-emerald-600" />
            </div>
            <h3 className="text-xl font-semibold text-slate-900 mb-3">
              Knowledge Base Ingestion
            </h3>
            <p className="text-slate-600 text-sm leading-relaxed mb-4">
              High-throughput async document processing for PDF, DOCX, TXT, and Markdown via MinIO S3 object storage with native Redis worker queues.
            </p>
            <div className="flex items-center gap-2 text-xs font-semibold text-emerald-600">
              <CheckCircle2 className="w-4 h-4 text-emerald-600" />
              Deterministic Chunk ID Hashing
            </div>
          </div>

          {/* Card 3: Vector Search Playground */}
          <div className="p-8 rounded-2xl bg-white border border-slate-200 hover:border-[#03AD8C] hover:shadow-md transition-all duration-300 group">
            <div className="h-12 w-12 rounded-xl bg-purple-50 border border-purple-100 flex items-center justify-center mb-6 group-hover:bg-purple-100 transition-colors">
              <Search className="w-6 h-6 text-purple-600" />
            </div>
            <h3 className="text-xl font-semibold text-slate-900 mb-3">
              Vector Search Playground
            </h3>
            <p className="text-slate-600 text-sm leading-relaxed mb-4">
              Interactive retrieval sandbox allowing real-time inspection of ChromaDB vector matches, score threshold tuning, and multi-KB query aggregation.
            </p>
            <div className="flex items-center gap-2 text-xs font-semibold text-purple-600">
              <CheckCircle2 className="w-4 h-4 text-purple-600" />
              1536-dim Embedding Dimension Guard
            </div>
          </div>

          {/* Card 4: Multi-Tenant App Keys */}
          <div className="p-8 rounded-2xl bg-white border border-slate-200 hover:border-[#03AD8C] hover:shadow-md transition-all duration-300 group">
            <div className="h-12 w-12 rounded-xl bg-amber-50 border border-amber-100 flex items-center justify-center mb-6 group-hover:bg-amber-100 transition-colors">
              <Key className="w-6 h-6 text-amber-600" />
            </div>
            <h3 className="text-xl font-semibold text-slate-900 mb-3">
              Multi-Tenant App Keys
            </h3>
            <p className="text-slate-600 text-sm leading-relaxed mb-4">
              Tenant-scoped API keys (<code className="text-amber-700 font-medium">tok_...</code>) granting external host platforms (e.g., AgriConnect) seamless access to isolated knowledge collections.
            </p>
            <div className="flex items-center gap-2 text-xs font-semibold text-amber-600">
              <CheckCircle2 className="w-4 h-4 text-amber-600" />
              Canonical /api/v1 REST & SSE Endpoints
            </div>
          </div>

          {/* Card 5: Strict Citations & Grounding */}
          <div className="p-8 rounded-2xl bg-white border border-slate-200 hover:border-[#03AD8C] hover:shadow-md transition-all duration-300 group">
            <div className="h-12 w-12 rounded-xl bg-[#03AD8C]/10 border border-[#03AD8C]/20 flex items-center justify-center mb-6 group-hover:bg-[#03AD8C]/20 transition-colors">
              <ShieldCheck className="w-6 h-6 text-[#03AD8C]" />
            </div>
            <h3 className="text-xl font-semibold text-slate-900 mb-3">
              Strict Citations & Grounding
            </h3>
            <p className="text-slate-600 text-sm leading-relaxed mb-4">
              Guaranteed citation provenance (<code className="text-[#027a63] font-medium">[[citation:1]]</code>). When source documents lack evidence, citations are suppressed to prevent hallucinations.
            </p>
            <div className="flex items-center gap-2 text-xs font-semibold text-[#03AD8C]">
              <CheckCircle2 className="w-4 h-4 text-[#03AD8C]" />
              ≥85% Golden Set Faithfulness Standard
            </div>
          </div>

          {/* Card 6: Dynamic 3-Tier Prompt Resolver */}
          <div className="p-8 rounded-2xl bg-white border border-slate-200 hover:border-[#03AD8C] hover:shadow-md transition-all duration-300 group">
            <div className="h-12 w-12 rounded-xl bg-rose-50 border border-rose-100 flex items-center justify-center mb-6 group-hover:bg-rose-100 transition-colors">
              <Sliders className="w-6 h-6 text-rose-600" />
            </div>
            <h3 className="text-xl font-semibold text-slate-900 mb-3">
              3-Tier Prompt Resolver
            </h3>
            <p className="text-slate-600 text-sm leading-relaxed mb-4">
              Hierarchical prompt resolution (App Overlay ➔ Global Database ➔ System Fallback) backed by PostgreSQL 17 for zero-downtime prompt engineering.
            </p>
            <div className="flex items-center gap-2 text-xs font-semibold text-rose-600">
              <CheckCircle2 className="w-4 h-4 text-rose-600" />
              Real-time Fine-Tuning Console
            </div>
          </div>
        </div>
      </section>

      {/* Live Interactive Preview Mockup */}
      <section id="preview" className="max-w-7xl mx-auto px-4 sm:px-6 lg:px-8 py-20 border-t border-slate-200">
        <div className="text-center max-w-3xl mx-auto mb-12">
          <h2 className="text-xs font-semibold uppercase tracking-widest text-[#03AD8C] mb-3">
            Real-Time State Machine
          </h2>
          <p className="text-3xl font-bold tracking-tight text-slate-900">
            Experience Grounded Citations in Action
          </p>
        </div>

        {/* Mockup Card */}
        <div className="max-w-4xl mx-auto rounded-2xl bg-white border border-slate-200 shadow-xl overflow-hidden">
          {/* Mockup Header */}
          <div className="px-6 py-4 border-b border-slate-200 bg-slate-50 flex items-center justify-between">
            <div className="flex items-center gap-2">
              <div className="h-3 w-3 rounded-full bg-rose-400" />
              <div className="h-3 w-3 rounded-full bg-amber-400" />
              <div className="h-3 w-3 rounded-full bg-emerald-400" />
              <span className="ml-3 text-xs font-mono text-slate-600">Akvo RAG Dialogue Playground</span>
            </div>
            <div className="flex items-center gap-3">
              <span className="text-xs font-mono px-2 py-0.5 rounded bg-emerald-50 text-emerald-700 border border-emerald-200">
                Intent: knowledge_query (142ms)
              </span>
              <span className="text-xs font-mono px-2 py-0.5 rounded bg-[#03AD8C]/10 text-[#027a63] border border-[#03AD8C]/20">
                gpt-4o synthesis
              </span>
            </div>
          </div>

          {/* Mockup Body */}
          <div className="p-6 space-y-6">
            {/* User Message */}
            <div className="flex items-start gap-4">
              <div className="h-8 w-8 rounded-lg bg-slate-100 border border-slate-200 flex items-center justify-center text-xs font-bold text-slate-700">
                U
              </div>
              <div className="flex-1 bg-slate-50 rounded-xl p-4 border border-slate-200 text-sm text-slate-800">
                What is the recommended soil pH and harvesting practice for Hass avocados?
              </div>
            </div>

            {/* Microservice Vector KB Output */}
            <div className="ml-12 p-3.5 rounded-xl bg-slate-50 border border-slate-200 text-xs font-mono text-slate-700 space-y-2">
              <div className="flex items-center justify-between text-slate-600">
                <span className="flex items-center gap-1.5 text-[#03AD8C] font-semibold">
                  <Terminal className="w-3.5 h-3.5" /> Vector KB MCP Match (2 Chunks Retrieved)
                </span>
                <span className="text-[#027a63] font-semibold">Score: 0.94</span>
              </div>
              <p className="text-slate-600 italic">
                &ldquo;Hass avocados thrive in soil pH 6.0 to 6.5. Always clip fruit leaving a short 5mm stalk to prevent fungal rot.&rdquo;
              </p>
              <div className="text-[11px] text-slate-500">
                Source: <span className="text-slate-700 font-medium">avocado_agronomy_guide.pdf (Page 12)</span> • KB ID: 1
              </div>
            </div>

            {/* Assistant Synthesized Answer */}
            <div className="flex items-start gap-4">
              <div className="h-8 w-8 rounded-lg bg-[#03AD8C] flex items-center justify-center text-xs font-bold text-white shadow-sm">
                AI
              </div>
              <div className="flex-1 bg-emerald-50/40 rounded-xl p-4 border border-emerald-100 text-sm text-slate-900 space-y-3">
                <p>
                  According to official agronomy guidelines, Hass avocados grow optimally in well-draining soil with a pH range of <strong>6.0 to 6.5</strong>{" "}
                  <span className="inline-flex items-center px-1.5 py-0.5 rounded bg-[#03AD8C]/15 text-[#027a63] font-mono text-xs border border-[#03AD8C]/30 cursor-pointer hover:bg-[#03AD8C]/25">
                    [[citation:1]]
                  </span>.
                </p>
                <p>
                  For harvesting, fruit should be clipped from the branch leaving a short 5mm stem attached rather than pulled, as pulling causes stem-end fungal infections during post-harvest storage.
                </p>
                <div className="pt-2 border-t border-emerald-100 flex items-center gap-2 text-xs text-slate-500">
                  <Sparkles className="w-3.5 h-3.5 text-[#03AD8C]" />
                  <span>Grounding confidence: <strong>98.4%</strong></span>
                  <span>•</span>
                  <span>OpenAI Prompt Cache: <strong>HIT</strong> (1,048 tokens cached)</span>
                </div>
              </div>
            </div>
          </div>
        </div>
      </section>

      {/* Bottom Call to Action */}
      <section className="max-w-7xl mx-auto px-4 sm:px-6 lg:px-8 py-20">
        <div className="relative rounded-3xl bg-gradient-to-r from-[#03AD8C] via-[#028f74] to-[#02725d] p-12 sm:p-16 text-center text-white shadow-xl shadow-[#03AD8C]/20">
          <h2 className="text-3xl sm:text-4xl font-extrabold mb-4">
            Ready to deploy enterprise AI knowledge retrieval?
          </h2>
          <p className="text-emerald-50 text-lg max-w-2xl mx-auto mb-8">
            Experience sub-second intent routing, strict citations, and seamless host application integration with Akvo RAG.
          </p>
          <div className="flex flex-col sm:flex-row gap-4 justify-center items-center">
            <Link
              href="/register"
              className="px-8 py-4 bg-white hover:bg-slate-50 text-[#027a63] rounded-xl text-base font-semibold shadow-md transition-all duration-200"
            >
              Get Started for Free
            </Link>
            <Link
              href="/login"
              className="px-8 py-4 bg-[#02725d] hover:bg-[#02604e] text-white border border-white/20 rounded-xl text-base font-semibold transition-all duration-200"
            >
              Sign In to Existing Account
            </Link>
          </div>
        </div>
      </section>

      {/* Footer */}
      <footer className="border-t border-slate-200 bg-slate-50 py-12 text-center text-slate-500 text-sm">
        <div className="max-w-7xl mx-auto px-4 flex flex-col sm:flex-row items-center justify-between gap-4">
          <div className="flex items-center gap-2">
            <Image
              src="/logo.svg"
              alt="Akvo Logo"
              width={20}
              height={20}
              className="w-5 h-5 rounded"
            />
            <span className="font-semibold text-slate-700">Akvo RAG</span>
            <span>— Better data, bigger impact. Built by Akvo.</span>
          </div>
          <div className="flex items-center gap-6">
            <Link href="/login" className="hover:text-slate-700 transition-colors">
              Sign In
            </Link>
            <Link href="/register" className="hover:text-slate-700 transition-colors">
              Register
            </Link>
          </div>
        </div>
      </footer>
    </main>
  );
}
