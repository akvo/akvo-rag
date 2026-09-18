'use client';

import { useState, useEffect } from 'react';
import {
  Plus,
  Copy,
  Check,
  Key,
  AppWindow,
  Globe,
  Layers,
  ShieldAlert,
  RotateCcw,
  Trash2,
  ExternalLink,
  Code2,
  Info,
  CheckCircle2,
  AlertTriangle,
  Lock,
  Eye,
  EyeOff,
  BookOpen,
  HelpCircle,
  Shield,
  Ban,
} from 'lucide-react';
import DashboardLayout from '@/components/layout/dashboard-layout';
import { Button } from '@/components/ui/button';
import { Switch } from '@/components/ui/switch';
import { useToast } from '@/components/ui/use-toast';
import { useUser } from '@/contexts/userContext';
import { api } from '@/lib/api';
import { formatDateTime } from '@/lib/utils';

export interface APIKey {
  id: number;
  name: string;
  key: string;
  is_active: boolean;
  last_used_at: string | null;
  created_at: string;
  updated_at: string;
}

export interface TenantApp {
  app_id: string;
  app_name: string;
  domain: string;
  default_chat_prompt?: string;
  chat_callback_url?: string;
  upload_callback_url?: string;
  scopes: string[];
  status: string;
  knowledge_bases: Array<{
    knowledge_base_id: number;
    is_default: boolean;
  }>;
}

interface KnowledgeBaseItem {
  id: number;
  name: string;
  description?: string;
}

export default function APIKeysAndAppsPage() {
  const { user: authUser } = useUser();
  const { toast } = useToast();

  // Active Tab
  const [activeTab, setActiveTab] = useState<'apps' | 'personal'>('apps');

  // Personal API Keys state
  const [apiKeys, setApiKeys] = useState<APIKey[]>([]);
  const [loadingKeys, setLoadingKeys] = useState(true);
  const [isCreateKeyOpen, setIsCreateKeyOpen] = useState(false);
  const [newKeyName, setNewKeyName] = useState('');
  const [isCreatingKey, setIsCreatingKey] = useState(false);
  const [pendingKeyToggle, setPendingKeyToggle] = useState<APIKey | null>(null);

  // Tenant Apps state
  const [apps, setApps] = useState<TenantApp[]>([]);
  const [loadingApps, setLoadingApps] = useState(true);
  const [availableKBs, setAvailableKBs] = useState<KnowledgeBaseItem[]>([]);
  const [isRegisterAppOpen, setIsRegisterAppOpen] = useState(false);
  const [isRegisteringApp, setIsRegisteringApp] = useState(false);
  const [pendingAppToggle, setPendingAppToggle] = useState<TenantApp | null>(null);
  const [isTogglingApp, setIsTogglingApp] = useState(false);

  // App form state
  const [appName, setAppName] = useState('');
  const [domain, setDomain] = useState('');
  const [defaultPrompt, setDefaultPrompt] = useState('');
  const [chatCallback, setChatCallback] = useState('');
  const [uploadCallback, setUploadCallback] = useState('');
  const [selectedKBIds, setSelectedKBIds] = useState<number[]>([]);

  // One-time Token Reveal Modal State
  const [revealedCredentials, setRevealedCredentials] = useState<{
    appName: string;
    clientId: string;
    accessToken: string;
  } | null>(null);

  // Copy indicator states
  const [copiedKeyId, setCopiedKeyId] = useState<number | null>(null);
  const [copiedToken, setCopiedToken] = useState(false);
  const [copiedCurl, setCopiedCurl] = useState(false);

  useEffect(() => {
    fetchPersonalKeys();
    if (authUser?.is_superuser) {
      fetchTenantApps();
    } else {
      setActiveTab('personal');
      setLoadingApps(false);
    }
    fetchKnowledgeBases();
  }, [authUser]);

  const fetchPersonalKeys = async () => {
    setLoadingKeys(true);
    try {
      const data = await api.get('/api/api-keys');
      setApiKeys(data);
    } catch {
      toast({ title: 'Error', description: 'Failed to load personal API keys', variant: 'destructive' });
    } finally {
      setLoadingKeys(false);
    }
  };

  const fetchTenantApps = async () => {
    setLoadingApps(true);
    try {
      const data = await api.get('/api/apps');
      setApps(data);
    } catch {
      // Non-superusers will fail cleanly
    } finally {
      setLoadingApps(false);
    }
  };

  const fetchKnowledgeBases = async () => {
    try {
      const data = await api.get('/api/knowledge-base');
      setAvailableKBs(data);
    } catch {
      console.error('Failed to load KBs');
    }
  };

  const handleCreatePersonalKey = async () => {
    if (!newKeyName.trim()) {
      toast({ title: 'Validation Error', description: 'Please enter a name for the key', variant: 'destructive' });
      return;
    }
    setIsCreatingKey(true);
    try {
      const created = await api.post('/api/api-keys', { name: newKeyName, is_active: true });
      setApiKeys((prev) => [created, ...prev]);
      setNewKeyName('');
      setIsCreateKeyOpen(false);
      toast({ title: 'API Key Created', description: `Key "${created.name}" is now active` });
    } catch (err: any) {
      toast({ title: 'Error', description: err.message || 'Failed to create key', variant: 'destructive' });
    } finally {
      setIsCreatingKey(false);
    }
  };

  const confirmTogglePersonalKey = async () => {
    if (!pendingKeyToggle) return;
    try {
      const updated = await api.put(`/api/api-keys/${pendingKeyToggle.id}`, { is_active: !pendingKeyToggle.is_active });
      setApiKeys((prev) => prev.map((k) => (k.id === pendingKeyToggle.id ? { ...k, is_active: updated.is_active } : k)));
      toast({ title: 'Key Updated', description: `Key "${updated.name}" is now ${updated.is_active ? 'Active' : 'Disabled'}` });
    } catch (err: any) {
      toast({ title: 'Error', description: err.message || 'Failed to toggle key status', variant: 'destructive' });
    } finally {
      setPendingKeyToggle(null);
    }
  };

  const handleDeletePersonalKey = async (id: number) => {
    if (!confirm('Are you sure you want to permanently delete this API key?')) return;
    try {
      await api.delete(`/api/api-keys/${id}`);
      setApiKeys((prev) => prev.filter((k) => k.id !== id));
      toast({ title: 'Key Deleted', description: 'API key permanently revoked' });
    } catch (err: any) {
      toast({ title: 'Error', description: err.message || 'Failed to delete key', variant: 'destructive' });
    }
  };

  const handleRegisterApp = async () => {
    if (!appName.trim() || !domain.trim()) {
      toast({ title: 'Validation Error', description: 'App Name and Domain are required', variant: 'destructive' });
      return;
    }
    setIsRegisteringApp(true);
    try {
      const res = await api.post('/api/apps/register', {
        app_name: appName.trim(),
        domain: domain.trim(),
        default_chat_prompt: defaultPrompt.trim() || undefined,
        chat_callback: chatCallback.trim() || undefined,
        upload_callback: uploadCallback.trim() || undefined,
      });

      // Show one-time token reveal modal
      setRevealedCredentials({
        appName: appName.trim(),
        clientId: res.client_id,
        accessToken: res.access_token,
      });

      setIsRegisterAppOpen(false);
      setAppName('');
      setDomain('');
      setDefaultPrompt('');
      setChatCallback('');
      setUploadCallback('');
      setSelectedKBIds([]);

      await fetchTenantApps();
      toast({ title: 'Tenant App Registered', description: `App "${appName}" created successfully` });
    } catch (err: any) {
      toast({ title: 'Registration Failed', description: err.message || 'Failed to register app', variant: 'destructive' });
    } finally {
      setIsRegisteringApp(false);
    }
  };

  const confirmToggleAppStatus = async () => {
    if (!pendingAppToggle) return;
    setIsTogglingApp(true);
    const nextStatus = pendingAppToggle.status === 'active' ? 'inactive' : 'active';
    try {
      const updated = await api.put(`/api/apps/${pendingAppToggle.app_id}/status`, { status: nextStatus });
      setApps((prev) => prev.map((a) => (a.app_id === pendingAppToggle.app_id ? { ...a, status: updated.status } : a)));
      toast({ title: 'App Status Updated', description: `${pendingAppToggle.app_name} is now ${nextStatus === 'active' ? 'Active' : 'Suspended'}` });
    } catch (err: any) {
      toast({ title: 'Error', description: err.message || 'Failed to update app status', variant: 'destructive' });
    } finally {
      setIsTogglingApp(false);
      setPendingAppToggle(null);
    }
  };

  return (
    <DashboardLayout>
      <div className="space-y-6 pb-12">
        {/* Header Studio Banner */}
        <div className="flex flex-col sm:flex-row sm:items-center justify-between gap-4 rounded-2xl border bg-card p-6 shadow-xs">
          <div className="space-y-1">
            <div className="flex items-center gap-2">
              <div className="h-8 w-8 rounded-xl bg-primary/10 flex items-center justify-center text-primary">
                <Key className="h-4 w-4" />
              </div>
              <h1 className="text-xl font-bold tracking-tight text-foreground">
                Tenant Apps & API Key Portal
              </h1>
            </div>
            <p className="text-xs text-muted-foreground max-w-xl">
              Manage consumer tenant application credentials (AgriConnect, CoM) and generate personal developer API keys for programmatic access.
            </p>
          </div>

          {/* Action Trigger Buttons */}
          <div className="flex items-center gap-2 self-start sm:self-auto">
            {activeTab === 'apps' && authUser?.is_superuser && (
              <Button onClick={() => setIsRegisterAppOpen(true)} className="gap-1.5 text-xs font-semibold">
                <Plus className="h-3.5 w-3.5" />
                <span>Register Tenant App</span>
              </Button>
            )}

            {activeTab === 'personal' && (
              <Button onClick={() => setIsCreateKeyOpen(true)} className="gap-1.5 text-xs font-semibold">
                <Plus className="h-3.5 w-3.5" />
                <span>Create Developer Key</span>
              </Button>
            )}
          </div>
        </div>

        {/* Tab Selector */}
        <div className="flex items-center bg-muted/60 border rounded-xl p-1 gap-1 w-full sm:w-fit shadow-2xs">
          {authUser?.is_superuser && (
            <button
              type="button"
              onClick={() => setActiveTab('apps')}
              className={`flex items-center gap-2 px-4 py-2 text-xs font-medium rounded-lg transition-all ${
                activeTab === 'apps'
                  ? 'bg-background text-foreground font-semibold shadow-xs'
                  : 'text-muted-foreground hover:text-foreground'
              }`}
            >
              <AppWindow className="h-4 w-4 text-primary" />
              <span>Tenant Applications ({apps.length})</span>
            </button>
          )}

          <button
            type="button"
            onClick={() => setActiveTab('personal')}
            className={`flex items-center gap-2 px-4 py-2 text-xs font-medium rounded-lg transition-all ${
              activeTab === 'personal'
                ? 'bg-background text-foreground font-semibold shadow-xs'
                : 'text-muted-foreground hover:text-foreground'
            }`}
          >
            <Key className="h-4 w-4 text-primary" />
            <span>Developer API Keys ({apiKeys.length})</span>
          </button>
        </div>

        {/* Tab 1: Tenant Applications (Super-Admin) */}
        {activeTab === 'apps' && authUser?.is_superuser && (
          <div className="space-y-4">
            {loadingApps ? (
              <div className="p-8 text-center text-xs text-muted-foreground">Loading tenant applications...</div>
            ) : apps.length === 0 ? (
              <div className="rounded-2xl border bg-card p-12 text-center space-y-3">
                <AppWindow className="h-10 w-10 text-muted-foreground/40 mx-auto" />
                <h3 className="text-sm font-bold text-foreground">No Tenant Apps Registered Yet</h3>
                <p className="text-xs text-muted-foreground max-w-sm mx-auto">
                  Register third-party host applications (e.g. AgriConnect) to generate scoped access tokens and callback integrations.
                </p>
                <Button size="sm" onClick={() => setIsRegisterAppOpen(true)} className="gap-1 text-xs">
                  <Plus className="h-3.5 w-3.5" />
                  <span>Register First App</span>
                </Button>
              </div>
            ) : (
              <div className="grid grid-cols-1 md:grid-cols-2 gap-4">
                {apps.map((app) => (
                  <div
                    key={app.app_id}
                    className="rounded-2xl border bg-card p-5 space-y-4 shadow-xs hover:border-primary/40 transition-all"
                  >
                    <div className="flex items-start justify-between gap-2">
                      <div className="space-y-1 min-w-0">
                        <div className="flex items-center gap-2">
                          <h3 className="text-sm font-bold text-foreground truncate">{app.app_name}</h3>

                          {/* Status Badge with Interactive Tooltip */}
                          <div className="relative group/status cursor-help inline-flex items-center gap-1">
                            <span
                              className={`text-[10px] font-semibold px-2 py-0.5 rounded-full flex items-center gap-1 ${
                                app.status === 'active'
                                  ? 'bg-emerald-500/10 text-emerald-600 dark:text-emerald-400'
                                  : 'bg-amber-500/10 text-amber-600 dark:text-amber-400'
                              }`}
                            >
                              <span
                                className={`h-1.5 w-1.5 rounded-full ${
                                  app.status === 'active' ? 'bg-emerald-500' : 'bg-amber-500'
                                }`}
                              />
                              {app.status === 'active' ? 'ACTIVE' : 'SUSPENDED'}
                            </span>
                            <HelpCircle className="h-3 w-3 text-muted-foreground hover:text-foreground" />

                            {/* Tooltip on Status */}
                            <div className="pointer-events-none absolute bottom-full left-0 mb-2 w-64 rounded-xl bg-popover border text-popover-foreground p-3 shadow-lg opacity-0 translate-y-1 group-hover/status:opacity-100 group-hover/status:translate-y-0 transition-all duration-200 z-30 text-xs">
                              <p className="font-semibold text-foreground mb-1">
                                {app.status === 'active' ? '🟢 Active App' : '🟠 Suspended (Inactive)'}
                              </p>
                              <p className="text-[11px] text-muted-foreground leading-relaxed">
                                {app.status === 'active'
                                  ? 'This app is authorized. All incoming API queries and webhooks are processed normally.'
                                  : 'Access is suspended. Any API requests using this token are rejected with 403 Forbidden. Data and tokens are preserved.'}
                              </p>
                              <div className="absolute top-full left-4 -mt-1 border-4 border-transparent border-t-popover" />
                            </div>
                          </div>
                        </div>
                        <div className="flex items-center gap-2 text-xs text-muted-foreground">
                          <Globe className="h-3.5 w-3.5 text-primary" />
                          <span>{app.domain}</span>
                        </div>
                      </div>

                      {/* Switch triggering confirmation modal */}
                      <div className="flex items-center gap-2">
                        <Switch
                          checked={app.status === 'active'}
                          onCheckedChange={() => setPendingAppToggle(app)}
                          title={`Toggle ${app.app_name} status`}
                        />
                      </div>
                    </div>

                    {/* Metadata & Permissions Grid */}
                    <div className="bg-muted/40 rounded-xl p-3 space-y-2 text-xs border">
                      <div className="flex items-center justify-between text-[11px]">
                        <span className="text-muted-foreground">Client ID:</span>
                        <span className="font-mono text-foreground">{app.app_id.slice(0, 16)}...</span>
                      </div>

                      <div className="flex items-center justify-between text-[11px]">
                        <span className="text-muted-foreground">Scoped Knowledge Bases:</span>
                        <span className="font-semibold text-primary">
                          {app.knowledge_bases ? app.knowledge_bases.length : 0} KB(s) Assigned
                        </span>
                      </div>

                      {app.chat_callback_url && (
                        <div className="flex items-center justify-between text-[11px]">
                          <span className="text-muted-foreground">Chat Webhook:</span>
                          <span className="font-mono text-foreground truncate max-w-[180px]">
                            {app.chat_callback_url}
                          </span>
                        </div>
                      )}
                    </div>

                    <div className="flex items-center justify-between pt-1 text-[11px] text-muted-foreground">
                      <span className="flex items-center gap-1">
                        <Layers className="h-3.5 w-3.5 text-primary" />
                        Scopes: {app.scopes ? app.scopes.join(', ') : 'standard'}
                      </span>
                    </div>
                  </div>
                ))}
              </div>
            )}
          </div>
        )}

        {/* Tab 2: Developer API Keys */}
        {activeTab === 'personal' && (
          <div className="space-y-4">
            {loadingKeys ? (
              <div className="p-8 text-center text-xs text-muted-foreground">Loading API keys...</div>
            ) : apiKeys.length === 0 ? (
              <div className="rounded-2xl border bg-card p-12 text-center space-y-3">
                <Key className="h-10 w-10 text-muted-foreground/40 mx-auto" />
                <h3 className="text-sm font-bold text-foreground">No Developer API Keys Found</h3>
                <p className="text-xs text-muted-foreground max-w-sm mx-auto">
                  Create personal API keys to integrate custom scripts, Python tools, or external services with Akvo RAG.
                </p>
                <Button size="sm" onClick={() => setIsCreateKeyOpen(true)} className="gap-1 text-xs">
                  <Plus className="h-3.5 w-3.5" />
                  <span>Create API Key</span>
                </Button>
              </div>
            ) : (
              <div className="rounded-2xl border bg-card overflow-hidden shadow-xs">
                <div className="overflow-x-auto">
                  <table className="w-full text-xs text-left">
                    <thead className="bg-muted/50 border-b text-muted-foreground font-semibold">
                      <tr>
                        <th className="py-3 px-4">Key Name</th>
                        <th className="py-3 px-4">Key Secret</th>
                        <th className="py-3 px-4">Status</th>
                        <th className="py-3 px-4">Created</th>
                        <th className="py-3 px-4">Last Used</th>
                        <th className="py-3 px-4 text-right">Actions</th>
                      </tr>
                    </thead>
                    <tbody className="divide-y divide-border">
                      {apiKeys.map((k) => (
                        <tr key={k.id} className="hover:bg-muted/20 transition-colors">
                          <td className="py-3.5 px-4 font-semibold text-foreground">{k.name}</td>
                          <td className="py-3.5 px-4 font-mono text-muted-foreground">
                            <span className="bg-muted px-2 py-1 rounded-md text-[11px]">
                              {k.key ? `${k.key.slice(0, 8)}...${k.key.slice(-4)}` : '••••••••••••••••'}
                            </span>
                          </td>
                          <td className="py-3.5 px-4">
                            <span
                              className={`inline-flex items-center gap-1 px-2 py-0.5 rounded-full text-[10px] font-semibold ${
                                k.is_active
                                  ? 'bg-emerald-500/10 text-emerald-600 dark:text-emerald-400'
                                  : 'bg-muted text-muted-foreground'
                              }`}
                            >
                              <span className={`h-1.5 w-1.5 rounded-full ${k.is_active ? 'bg-emerald-500' : 'bg-muted-foreground'}`} />
                              {k.is_active ? 'Active' : 'Disabled'}
                            </span>
                          </td>
                          <td className="py-3.5 px-4 text-muted-foreground text-[11px]">
                            {formatDateTime(k.created_at)}
                          </td>
                          <td className="py-3.5 px-4 text-muted-foreground text-[11px]">
                            {k.last_used_at ? formatDateTime(k.last_used_at) : 'Never'}
                          </td>
                          <td className="py-3.5 px-4 text-right">
                            <div className="flex items-center justify-end gap-2">
                              <button
                                type="button"
                                onClick={async () => {
                                  await navigator.clipboard.writeText(k.key);
                                  setCopiedKeyId(k.id);
                                  setTimeout(() => setCopiedKeyId(null), 2000);
                                  toast({ title: 'Copied', description: 'API key copied to clipboard' });
                                }}
                                className="p-1.5 rounded-lg text-muted-foreground hover:text-foreground hover:bg-muted transition-colors"
                                title="Copy Key"
                              >
                                {copiedKeyId === k.id ? (
                                  <Check className="h-3.5 w-3.5 text-emerald-600" />
                                ) : (
                                  <Copy className="h-3.5 w-3.5" />
                                )}
                              </button>

                              <Switch
                                checked={k.is_active}
                                onCheckedChange={() => setPendingKeyToggle(k)}
                                title="Toggle key active status"
                              />

                              <button
                                type="button"
                                onClick={() => handleDeletePersonalKey(k.id)}
                                className="p-1.5 rounded-lg text-muted-foreground hover:text-destructive hover:bg-destructive/10 transition-colors"
                                title="Delete Key"
                              >
                                <Trash2 className="h-3.5 w-3.5" />
                              </button>
                            </div>
                          </td>
                        </tr>
                      ))}
                    </tbody>
                  </table>
                </div>
              </div>
            )}

            {/* Quick Developer Integration Snippet */}
            <div className="bg-card rounded-2xl border p-5 space-y-3 shadow-xs">
              <div className="flex items-center justify-between">
                <div className="flex items-center gap-2">
                  <Code2 className="h-4 w-4 text-primary" />
                  <h4 className="text-xs font-semibold text-foreground">API Integration Example (cURL)</h4>
                </div>
                <Button
                  variant="outline"
                  size="sm"
                  onClick={async () => {
                    const sampleCode = `curl -X POST "http://localhost:8000/api/v1/chat/messages" \\\n  -H "Authorization: Bearer YOUR_API_KEY" \\\n  -H "Content-Type: application/json" \\\n  -d '{"messages": [{"role": "user", "content": "Explain sustainable soil practices"}]}'`;
                    await navigator.clipboard.writeText(sampleCode);
                    setCopiedCurl(true);
                    setTimeout(() => setCopiedCurl(false), 2000);
                  }}
                  className="gap-1 text-xs h-7 px-2"
                >
                  {copiedCurl ? <Check className="h-3 w-3 text-emerald-600" /> : <Copy className="h-3 w-3" />}
                  <span>{copiedCurl ? 'Copied' : 'Copy cURL'}</span>
                </Button>
              </div>

              <div className="rounded-xl bg-muted/40 p-3 font-mono text-[11px] text-muted-foreground overflow-x-auto">
                <code>
                  {`curl -X POST "http://localhost:8000/api/v1/chat/messages" \\\n  -H "Authorization: Bearer YOUR_API_KEY" \\\n  -H "Content-Type: application/json" \\\n  -d '{"messages": [{"role": "user", "content": "Explain sustainable soil practices"}]}'`}
                </code>
              </div>
            </div>
          </div>
        )}

        {/* Modal 1: Register Tenant App Modal */}
        {isRegisterAppOpen && (
          <div className="fixed inset-0 z-50 flex items-center justify-center bg-black/50 backdrop-blur-xs p-4">
            <div className="w-full max-w-lg bg-card rounded-2xl border p-6 space-y-4 shadow-xl max-h-[90vh] overflow-y-auto">
              <div className="flex items-center gap-2 text-foreground">
                <AppWindow className="h-5 w-5 text-primary" />
                <h3 className="text-base font-bold">Register Consumer Tenant App</h3>
              </div>
              <p className="text-xs text-muted-foreground">
                Register an external application to generate dedicated client credentials and callback webhooks.
              </p>

              <div className="space-y-3">
                <div className="space-y-1">
                  <label className="text-xs font-semibold text-foreground">Application Name *</label>
                  <input
                    type="text"
                    value={appName}
                    onChange={(e) => setAppName(e.target.value)}
                    placeholder="e.g. AgriConnect Portal"
                    className="w-full h-9 px-3 text-xs rounded-xl border bg-background text-foreground outline-none focus:ring-1 focus:ring-primary"
                  />
                </div>

                <div className="space-y-1">
                  <label className="text-xs font-semibold text-foreground">Allowed Domain / Host *</label>
                  <input
                    type="text"
                    value={domain}
                    onChange={(e) => setDomain(e.target.value)}
                    placeholder="e.g. agriconnect.example.com"
                    className="w-full h-9 px-3 text-xs rounded-xl border bg-background text-foreground outline-none focus:ring-1 focus:ring-primary"
                  />
                </div>

                <div className="space-y-1">
                  <label className="text-xs font-semibold text-foreground">Default Chat System Prompt (Optional)</label>
                  <textarea
                    rows={2}
                    value={defaultPrompt}
                    onChange={(e) => setDefaultPrompt(e.target.value)}
                    placeholder="Custom prompt instructions for this tenant..."
                    className="w-full p-2.5 text-xs rounded-xl border bg-background text-foreground outline-none focus:ring-1 focus:ring-primary font-mono"
                  />
                </div>

                <div className="grid grid-cols-1 sm:grid-cols-2 gap-2">
                  <div className="space-y-1">
                    <label className="text-xs font-semibold text-foreground">Chat Callback URL</label>
                    <input
                      type="url"
                      value={chatCallback}
                      onChange={(e) => setChatCallback(e.target.value)}
                      placeholder="https://app.com/callback/chat"
                      className="w-full h-9 px-3 text-xs rounded-xl border bg-background text-foreground outline-none focus:ring-1 focus:ring-primary"
                    />
                  </div>
                  <div className="space-y-1">
                    <label className="text-xs font-semibold text-foreground">Upload Callback URL</label>
                    <input
                      type="url"
                      value={uploadCallback}
                      onChange={(e) => setUploadCallback(e.target.value)}
                      placeholder="https://app.com/callback/upload"
                      className="w-full h-9 px-3 text-xs rounded-xl border bg-background text-foreground outline-none focus:ring-1 focus:ring-primary"
                    />
                  </div>
                </div>
              </div>

              <div className="flex justify-end gap-2 pt-2 border-t">
                <Button variant="outline" size="sm" onClick={() => setIsRegisterAppOpen(false)} disabled={isRegisteringApp}>
                  Cancel
                </Button>
                <Button size="sm" onClick={handleRegisterApp} disabled={isRegisteringApp} className="font-semibold">
                  {isRegisteringApp ? 'Registering...' : 'Register App'}
                </Button>
              </div>
            </div>
          </div>
        )}

        {/* Modal 2: One-Time Token Reveal Modal */}
        {revealedCredentials && (
          <div className="fixed inset-0 z-50 flex items-center justify-center bg-black/60 backdrop-blur-xs p-4">
            <div className="w-full max-w-lg bg-card rounded-2xl border-2 border-primary/40 p-6 space-y-4 shadow-2xl animate-in zoom-in-95 duration-200">
              <div className="flex items-center gap-2.5 text-foreground">
                <div className="h-9 w-9 rounded-xl bg-primary/10 flex items-center justify-center text-primary">
                  <Lock className="h-5 w-5" />
                </div>
                <div>
                  <h3 className="text-base font-bold">App Credentials Generated</h3>
                  <p className="text-xs text-muted-foreground">{revealedCredentials.appName}</p>
                </div>
              </div>

              {/* Security Banner */}
              <div className="bg-amber-500/10 border border-amber-500/30 text-amber-800 dark:text-amber-300 p-3 rounded-xl flex items-start gap-2.5 text-xs">
                <ShieldAlert className="h-4 w-4 shrink-0 mt-0.5 text-amber-500" />
                <div>
                  <p className="font-bold">Save this Access Token immediately!</p>
                  <p className="text-[11px] mt-0.5 leading-relaxed">
                    For security reasons, this token will <strong>never be displayed again</strong>. If lost, you will need to rotate the app credentials.
                  </p>
                </div>
              </div>

              {/* Copyable Credentials Box */}
              <div className="space-y-3 bg-muted/40 p-4 rounded-xl border">
                <div className="space-y-1">
                  <label className="text-[11px] font-semibold text-muted-foreground">Client ID:</label>
                  <div className="flex items-center justify-between gap-2 bg-background border px-3 py-1.5 rounded-lg font-mono text-xs">
                    <span className="truncate">{revealedCredentials.clientId}</span>
                  </div>
                </div>

                <div className="space-y-1">
                  <label className="text-[11px] font-semibold text-muted-foreground">Access Token (Bearer):</label>
                  <div className="flex items-center justify-between gap-2 bg-background border px-3 py-2 rounded-lg font-mono text-xs">
                    <span className="truncate text-primary font-bold">{revealedCredentials.accessToken}</span>
                    <button
                      type="button"
                      onClick={async () => {
                        await navigator.clipboard.writeText(revealedCredentials.accessToken);
                        setCopiedToken(true);
                        setTimeout(() => setCopiedToken(false), 2000);
                        toast({ title: 'Copied', description: 'Access token copied to clipboard' });
                      }}
                      className="p-1.5 rounded-md hover:bg-muted text-muted-foreground hover:text-foreground shrink-0"
                    >
                      {copiedToken ? <Check className="h-4 w-4 text-emerald-600" /> : <Copy className="h-4 w-4" />}
                    </button>
                  </div>
                </div>
              </div>

              <div className="flex justify-end pt-2">
                <Button
                  size="sm"
                  onClick={() => setRevealedCredentials(null)}
                  className="font-semibold px-6"
                >
                  I Have Copied the Token
                </Button>
              </div>
            </div>
          </div>
        )}

        {/* Modal 3: Create Personal Developer Key Modal */}
        {isCreateKeyOpen && (
          <div className="fixed inset-0 z-50 flex items-center justify-center bg-black/50 backdrop-blur-xs p-4">
            <div className="w-full max-w-md bg-card rounded-2xl border p-6 space-y-4 shadow-xl">
              <div className="flex items-center gap-2 text-foreground">
                <Key className="h-5 w-5 text-primary" />
                <h3 className="text-base font-bold">Create Developer API Key</h3>
              </div>
              <p className="text-xs text-muted-foreground">
                Generate a new API key to authenticate programmatic requests to Akvo RAG.
              </p>

              <div className="space-y-1.5">
                <label className="text-xs font-semibold text-foreground">Key Name / Description *</label>
                <input
                  type="text"
                  value={newKeyName}
                  onChange={(e) => setNewKeyName(e.target.value)}
                  placeholder="e.g. Python Evaluation Script or Local CLI"
                  className="w-full h-9 px-3 text-xs rounded-xl border bg-background text-foreground outline-none focus:ring-1 focus:ring-primary"
                />
              </div>

              <div className="flex justify-end gap-2 pt-2 border-t">
                <Button variant="outline" size="sm" onClick={() => setIsCreateKeyOpen(false)} disabled={isCreatingKey}>
                  Cancel
                </Button>
                <Button size="sm" onClick={handleCreatePersonalKey} disabled={isCreatingKey} className="font-semibold">
                  {isCreatingKey ? 'Creating...' : 'Generate Key'}
                </Button>
              </div>
            </div>
          </div>
        )}

        {/* Modal 4: App Status Toggle Confirmation Modal */}
        {pendingAppToggle && (
          <div className="fixed inset-0 z-50 flex items-center justify-center bg-black/50 backdrop-blur-xs p-4">
            <div className="w-full max-w-md bg-card rounded-2xl border p-6 space-y-4 shadow-xl">
              <div className="flex items-center gap-2 text-foreground">
                {pendingAppToggle.status === 'active' ? (
                  <Ban className="h-5 w-5 text-amber-500" />
                ) : (
                  <Shield className="h-5 w-5 text-emerald-500" />
                )}
                <h3 className="text-base font-bold">
                  {pendingAppToggle.status === 'active'
                    ? `Suspend "${pendingAppToggle.app_name}"?`
                    : `Re-activate "${pendingAppToggle.app_name}"?`}
                </h3>
              </div>

              <p className="text-xs text-muted-foreground leading-relaxed">
                {pendingAppToggle.status === 'active'
                  ? 'Suspending this tenant app will immediately reject all incoming API requests (403 Forbidden) and pause webhook callbacks. You can re-activate it at any time.'
                  : 'Re-activating this tenant app will allow it to resume sending API queries and uploading documents using its existing credentials.'}
              </p>

              <div className="flex justify-end gap-2 pt-2 border-t">
                <Button variant="outline" size="sm" onClick={() => setPendingAppToggle(null)} disabled={isTogglingApp}>
                  Cancel
                </Button>
                <Button
                  size="sm"
                  onClick={confirmToggleAppStatus}
                  disabled={isTogglingApp}
                  className={`font-semibold ${
                    pendingAppToggle.status === 'active'
                      ? 'bg-amber-600 hover:bg-amber-700 text-white'
                      : 'bg-emerald-600 hover:bg-emerald-700 text-white'
                  }`}
                >
                  {isTogglingApp
                    ? 'Updating...'
                    : pendingAppToggle.status === 'active'
                    ? 'Yes, Suspend App'
                    : 'Yes, Activate App'}
                </Button>
              </div>
            </div>
          </div>
        )}

        {/* Modal 5: Personal Key Status Toggle Confirmation Modal */}
        {pendingKeyToggle && (
          <div className="fixed inset-0 z-50 flex items-center justify-center bg-black/50 backdrop-blur-xs p-4">
            <div className="w-full max-w-md bg-card rounded-2xl border p-6 space-y-4 shadow-xl">
              <div className="flex items-center gap-2 text-foreground">
                <Key className="h-5 w-5 text-primary" />
                <h3 className="text-base font-bold">
                  {pendingKeyToggle.is_active ? `Disable API Key "${pendingKeyToggle.name}"?` : `Enable API Key "${pendingKeyToggle.name}"?`}
                </h3>
              </div>

              <p className="text-xs text-muted-foreground leading-relaxed">
                {pendingKeyToggle.is_active
                  ? 'Disabling this key will cause any API requests using it to fail immediately with 401 Unauthorized.'
                  : 'Enabling this key will allow it to authenticate API requests again.'}
              </p>

              <div className="flex justify-end gap-2 pt-2 border-t">
                <Button variant="outline" size="sm" onClick={() => setPendingKeyToggle(null)}>
                  Cancel
                </Button>
                <Button size="sm" onClick={confirmTogglePersonalKey} className="font-semibold">
                  Confirm
                </Button>
              </div>
            </div>
          </div>
        )}
      </div>
    </DashboardLayout>
  );
}
