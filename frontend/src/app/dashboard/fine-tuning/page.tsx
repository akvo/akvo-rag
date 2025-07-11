'use client';

import { useEffect, useState } from 'react';
import { api } from '@/lib/api';
import DashboardLayout from '@/components/layout/dashboard-layout';
import { Button } from '@/components/ui/button';
import { Input } from '@/components/ui/input';
import { Label } from '@/components/ui/label';
import { Dialog, DialogTrigger, DialogContent, DialogHeader, DialogTitle, DialogFooter } from '@/components/ui/dialog';
import { Accordion, AccordionItem, AccordionTrigger, AccordionContent } from '@/components/ui/accordion';
import { useToast } from '@/components/ui/use-toast';
import { Divider } from '@/components/ui/divider';
import { Tabs, TabsList, TabsTrigger, TabsContent } from '@/components/ui/tabs';

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

export default function FineTuningPage() {
  const [promptGroups, setPromptGroups] = useState<Record<string, PromptVersion[]>>({});
  const [loading, setLoading] = useState(false);
  const [formState, setFormState] = useState<Record<string, { content: string; reason: string }>>({});
  const [expandedHistories, setExpandedHistories] = useState<Record<string, boolean>>({});
  const [noHistoryAvailable, setNoHistoryAvailable] = useState<Record<string, boolean>>({});
  const [selectedVersion, setSelectedVersion] = useState<{
    promptName: string;
    versionId: number;
    versionNumber: number;
  } | null>(null);
  const [reactivationReason, setReactivationReason] = useState('');
  const [selectedTab, setSelectedTab] = useState<string>('');
  const { toast } = useToast();

  useEffect(() => {
    fetchPrompts();
  }, []);

  useEffect(() => {
    if (Object.keys(promptGroups).length > 0 && !selectedTab) {
      setSelectedTab(Object.keys(promptGroups)[0]);
    }
  }, [promptGroups]);

  const fetchPrompts = async () => {
    setLoading(true);
    try {
      const definitions: PromptResponse[] = await api.get('/api/prompt');
      const groups: Record<string, PromptVersion[]> = {};
      for (const def of definitions) {
        if (def.name === 'qa_flexible_prompt') continue;
        if (!def.active_version) continue;
        groups[def.name] = [def.active_version];
      }
      setPromptGroups(groups);
    } catch (err: any) {
      toast({ title: 'Error', description: err.message || 'Failed to fetch prompts', variant: 'destructive' });
    } finally {
      setLoading(false);
    }
  };

  const fetchPromptHistory = async (name: string) => {
    const currentlyExpanded = expandedHistories[name];
    if (currentlyExpanded) {
      setPromptGroups((prev) => ({
        ...prev,
        [name]: prev[name].filter((v) => v.is_active),
      }));
      setExpandedHistories((prev) => ({ ...prev, [name]: false }));
      setNoHistoryAvailable((prev) => ({ ...prev, [name]: false }));
    } else {
      try {
        const detail: PromptResponse = await api.get(`/api/prompt/${name}`);
        const history = detail.all_versions.filter((v) => !v.is_active);
        setPromptGroups((prev) => ({
          ...prev,
          [name]: [detail.active_version!, ...history],
        }));
        setExpandedHistories((prev) => ({ ...prev, [name]: true }));
        setNoHistoryAvailable((prev) => ({ ...prev, [name]: history.length === 0 }));
      } catch (err: any) {
        toast({ title: 'Error', description: err.message || 'Failed to load history', variant: 'destructive' });
      }
    }
  };

  const handleSubmit = async (promptName: string) => {
    const { content, reason } = formState[promptName] || {};
    if (!content) return;

    try {
      await api.put(`/api/prompt/${promptName}`, {
        content,
        activation_reason: reason,
      });
      toast({ title: 'Success', description: `Prompt updated for ${promptName}` });
      setFormState((prev) => ({ ...prev, [promptName]: { content: '', reason: '' } }));
      fetchPrompts();
    } catch (err: any) {
      toast({ title: 'Error', description: err.message || 'Failed to update prompt', variant: 'destructive' });
    }
  };

  const handleActivateVersion = async () => {
    if (!selectedVersion) return;
    const { promptName, versionId, versionNumber } = selectedVersion;
    try {
      await api.put(`/api/prompt/${promptName}/reactivate/${versionId}`, {
        reactivation_reason: reactivationReason,
      });
      toast({ title: 'Success', description: `Version v${versionNumber} activated for ${promptName}` });
      setSelectedVersion(null);
      setReactivationReason('');
      setExpandedHistories({});
      fetchPrompts();
    } catch (err: any) {
      toast({ title: 'Error', description: err.message || 'Failed to activate version', variant: 'destructive' });
    }
  };

  return (
    <DashboardLayout>
      <div className="my-10">
        <h1 className="text-3xl font-semibold mb-6 tracking-tight">Fine Tuning</h1>

        <div className="mb-10 p-4 rounded-md border bg-muted text-sm">
          <h2 className="text-lg font-semibold mb-2">💡 Prompt Types Explained</h2>
          <p><strong>📌 Contextual Prompt:</strong> Helps the AI rewrite the user’s query using previous chat messages.</p>
          <p><strong>📌 QA Prompt:</strong> Guides the AI to generate answers from the knowledge base.</p>
          <ul className="list-disc list-inside ml-4">
            <li><strong>Strict:</strong> Responds using only retrieved content.</li>
            <li><strong>Flexible:</strong> Allows free-form responses (used as backup).</li>
          </ul>
        </div>

        <Tabs value={selectedTab} onValueChange={setSelectedTab}>
          <TabsList className="flex  bg-white px-0 gap-x-1 justify-start">
            {Object.keys(promptGroups).map((promptName) => (
              <TabsTrigger
                key={promptName}
                value={promptName}
                className="border border-b-0 px-4 py-2 text-sm font-medium -mb-px
                  rounded-t-md rounded-b-none
                  data-[state=active]:bg-white data-[state=active]:border-gray-300 data-[state=active]:text-primary
                  data-[state=inactive]:bg-muted data-[state=inactive]:text-muted-foreground hover:bg-white"
              >
                {promptName}
              </TabsTrigger>
            ))}
          </TabsList>

          {Object.entries(promptGroups).map(([promptName, versions]) => (
            <TabsContent key={promptName} value={promptName} className="border border-gray-300 rounded-b-md rounded-tr-md bg-white p-6 mt-0">
              {loading ? (
                <p className="text-sm text-muted-foreground">Loading prompts...</p>
              ) : (
                <div className="mb-12">
                  <h2 className="text-lg font-medium mb-2 text-gray-900">{promptName}</h2>

                  <div className="rounded-lg border">
                    <div className="p-4 bg-gray-50 border-b">
                      <div className="flex justify-between items-center mb-2">
                        <span className="font-semibold text-gray-800">
                          🟦 v{versions[0].version_number} <span className="text-blue-600">(Active)</span>
                        </span>
                        <span className="text-xs text-gray-500">
                          {new Date(versions[0].updated_at || versions[0].created_at).toLocaleString()}
                        </span>
                      </div>
                      <pre className="whitespace-pre-wrap text-sm text-gray-700">{versions[0].content}</pre>
                      {versions[0].activation_reason && (
                        <p className="text-xs italic text-muted-foreground mt-2">Reason: {versions[0].activation_reason}</p>
                      )}
                      {versions[0].activated_by_user && (
                        <div>
                          <Divider className="my-2" />
                          <p className="text-xs italic text-muted-foreground">
                            Activated by: {versions[0].activated_by_user.email}
                          </p>
                        </div>
                      )}
                    </div>

                    <Accordion
                      type="single"
                      collapsible
                      value={expandedHistories[promptName] ? 'history' : undefined}
                      onValueChange={(value) => {
                        if (value === 'history') {
                          fetchPromptHistory(promptName);
                        } else {
                          setPromptGroups((prev) => ({
                            ...prev,
                            [promptName]: prev[promptName].filter((v) => v.is_active),
                          }));
                          setExpandedHistories((prev) => ({ ...prev, [promptName]: false }));
                          setNoHistoryAvailable((prev) => ({ ...prev, [promptName]: false }));
                        }
                      }}
                    >
                      <AccordionItem value="history">
                        <AccordionTrigger className="px-4 text-sm font-medium">
                          🔁 {expandedHistories[promptName] ? 'Hide History' : 'Load History'}
                        </AccordionTrigger>

                        {expandedHistories[promptName] && (
                          <AccordionContent className="space-y-4 px-4 py-2 max-h-96 overflow-y-auto">
                            {versions.slice(1).map((version) => (
                              <div key={version.id} className="rounded-md border bg-white p-4 shadow-sm">
                                <div className="flex justify-between mb-1">
                                  <span className="text-sm font-semibold">v{version.version_number}</span>
                                  <span className="text-xs text-muted-foreground">
                                    {new Date(version.updated_at || version.created_at).toLocaleString()}
                                  </span>
                                </div>
                                <pre className="whitespace-pre-wrap text-sm mb-2">{version.content}</pre>
                                {version.activation_reason && (
                                  <p className="text-xs italic text-muted-foreground mb-2">
                                    Reason: {version.activation_reason}
                                  </p>
                                )}
                                {version.activated_by_user && (
                                  <div className="mb-6">
                                    <Divider className="my-2" />
                                    <p className="text-xs italic text-muted-foreground">
                                      Created by: {version.activated_by_user.email}
                                    </p>
                                  </div>
                                )}

                                <Dialog>
                                  <DialogTrigger asChild>
                                    <Button
                                      size="sm"
                                      variant="outline"
                                      onClick={() =>
                                        setSelectedVersion({
                                          promptName,
                                          versionId: version.id,
                                          versionNumber: version.version_number,
                                        })
                                      }
                                    >
                                      Activate this version: v{version.version_number}
                                    </Button>
                                  </DialogTrigger>
                                  {selectedVersion?.versionId === version.id && (
                                    <DialogContent>
                                      <DialogHeader>
                                        <DialogTitle>Confirm Activation</DialogTitle>
                                      </DialogHeader>
                                      <p className="text-sm">
                                        Are you sure you want to activate version <strong>v{version.version_number}</strong> for prompt <strong>{promptName}</strong>?
                                      </p>
                                      <Label htmlFor="reactivation-reason" className="mt-4">Reactivation Reason</Label>
                                      <Input
                                        id="reactivation-reason"
                                        placeholder="e.g., rollback due to bug"
                                        value={reactivationReason}
                                        onChange={(e) => setReactivationReason(e.target.value)}
                                      />
                                      <DialogFooter className="mt-4">
                                        <Button variant="outline" onClick={() => setSelectedVersion(null)}>Cancel</Button>
                                        <Button onClick={handleActivateVersion}>Confirm</Button>
                                      </DialogFooter>
                                    </DialogContent>
                                  )}
                                </Dialog>
                              </div>
                            ))}
                            {noHistoryAvailable[promptName] && (
                              <p className="text-sm italic text-muted-foreground">No history available.</p>
                            )}
                          </AccordionContent>
                        )}
                      </AccordionItem>
                    </Accordion>
                  </div>

                  <Divider className="my-4" />

                  <div className="space-y-2">
                    <h3 className="text-sm font-medium text-gray-700">Submit New Version</h3>
                    <textarea
                      rows={4}
                      className="flex min-h-[80px] w-full rounded-md border border-input bg-background px-3 py-2 text-sm ring-offset-background placeholder:text-muted-foreground focus-visible:outline-none focus-visible:ring-2 focus-visible:ring-ring focus-visible:ring-offset-2 disabled:cursor-not-allowed disabled:opacity-50"
                      placeholder="New prompt content..."
                      value={formState[promptName]?.content || ''}
                      onChange={(e) =>
                        setFormState((prev) => ({
                          ...prev,
                          [promptName]: {
                            ...prev[promptName],
                            content: e.target.value,
                          },
                        }))
                      }
                    />
                    <Label htmlFor={`reason-${promptName}`}>Activation Reason</Label>
                    <Input
                      id={`reason-${promptName}`}
                      placeholder="Activation reason"
                      value={formState[promptName]?.reason || ''}
                      onChange={(e) =>
                        setFormState((prev) => ({
                          ...prev,
                          [promptName]: {
                            ...prev[promptName],
                            reason: e.target.value,
                          },
                        }))
                      }
                    />
                    <Button onClick={() => handleSubmit(promptName)} size="sm">
                      Save New Version
                    </Button>
                  </div>
                </div>
              )}
            </TabsContent>
          ))}
        </Tabs>
      </div>
    </DashboardLayout>
  );
}
