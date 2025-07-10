'use client';

import { useEffect, useState } from 'react';
import { api } from '@/lib/api';
import DashboardLayout from '@/components/layout/dashboard-layout';
import { Button } from '@/components/ui/button';

interface PromptVersion {
  id: number;
  content: string;
  version_number: number;
  is_active: boolean;
  activated_by_user_id?: number;
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
  const [status, setStatus] = useState<{ type: 'success' | 'error'; message: string } | null>(null);
  const [expandedHistories, setExpandedHistories] = useState<Record<string, boolean>>({});

  const [showModal, setShowModal] = useState(false);
  const [selectedVersion, setSelectedVersion] = useState<{
    promptName: string;
    versionId: number;
    versionNumber: number;
  } | null>(null);

  useEffect(() => {
    fetchPrompts();
  }, []);

  useEffect(() => {
    if (status) {
      const timer = setTimeout(() => setStatus(null), 4000);
      return () => clearTimeout(timer);
    }
  }, [status]);

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
      setStatus({ type: 'error', message: err.message || 'Failed to fetch prompts' });
    } finally {
      setLoading(false);
    }
  };

  const fetchPromptHistory = async (name: string) => {
    const currentlyExpanded = expandedHistories[name];
    if (currentlyExpanded) {
      // collapse
      setPromptGroups((prev) => ({
        ...prev,
        [name]: prev[name].filter((v) => v.is_active),
      }));
      setExpandedHistories((prev) => ({ ...prev, [name]: false }));
    } else {
      try {
        const detail: PromptResponse = await api.get(`/api/prompt/${name}`);
        setPromptGroups((prev) => ({
          ...prev,
          [name]: [detail.active_version!, ...detail.all_versions.filter((v) => !v.is_active)],
        }));
        setExpandedHistories((prev) => ({ ...prev, [name]: true }));
      } catch (err: any) {
        setStatus({ type: 'error', message: err.message || 'Failed to load history' });
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
      setStatus({ type: 'success', message: `Prompt updated for ${promptName}` });
      setFormState((prev) => ({ ...prev, [promptName]: { content: '', reason: '' } }));
      fetchPrompts();
    } catch (err: any) {
      setStatus({ type: 'error', message: err.message || 'Failed to update prompt' });
    }
  };

  const handleActivateVersion = async ({
    promptName,
    versionId,
    versionNumber,
  }: {
    promptName: string;
    versionId: number;
    versionNumber: number;
  }) => {
    try {
      await api.put(`/api/prompt/${promptName}/reactivate/${versionId}`);
      setStatus({
        type: 'success',
        message: `Version v${versionNumber} activated for ${promptName}`,
      });
      setShowModal(false);
      setSelectedVersion(null);
      setExpandedHistories({});
      fetchPrompts();
    } catch (err: any) {
      setStatus({ type: 'error', message: err.message || 'Failed to activate version' });
      setShowModal(false);
      setSelectedVersion(null);
    }
  };


  return (
    <DashboardLayout>
      <div className="my-10">
        <h1 className="text-3xl font-semibold mb-6 tracking-tight">Fine Tuning</h1>

        <div className="mb-10 p-4 rounded-md border border-gray-200 bg-gray-50 text-sm text-gray-700">
          <h2 className="text-lg font-semibold mb-2">💡 Prompt Types Explained</h2>
          <p className="mb-2">
            <strong>📌 Contextual Prompt:</strong> Helps the AI rewrite the user’s query using previous chat messages.
          </p>
          <p className="mb-2">
            <strong>📌 QA Prompt:</strong> Guides the AI to generate answers from the knowledge base.
          </p>
          <ul className="list-disc list-inside ml-4">
            <li><strong>Strict:</strong> Responds using only retrieved content.</li>
            <li><strong>Flexible:</strong> Allows free-form responses (used as backup).</li>
          </ul>
        </div>

        {status && (
          <div
            className={`mb-6 rounded-md p-4 text-sm transition-opacity duration-300 ${
              status.type === 'success' ? 'bg-green-100 text-green-800' : 'bg-red-100 text-red-800'
            }`}
          >
            {status.message}
          </div>
        )}

        {loading ? (
          <div className="text-gray-500 text-sm">Loading prompts...</div>
        ) : (
          Object.entries(promptGroups).map(([promptName, versions]) => (
            <div key={promptName} className="mb-10">
              <h2 className="text-lg font-medium mb-2 text-gray-900">{promptName}</h2>

              <div className="rounded-lg border border-gray-200">
                {/* Active Version */}
                {versions.length > 0 && (
                  <div className="p-4 bg-gray-50 border-b">
                    <div className="flex justify-between items-center mb-2">
                      <span className="font-semibold text-gray-800">
                        🟦 v{versions[0].version_number} <span className="text-blue-600">(Active)</span>
                      </span>
                      <span className="text-xs text-gray-500">
                        {new Date(versions[0].updated_at || versions[0].created_at).toLocaleString()}
                      </span>
                    </div>
                    <pre className="whitespace-pre-wrap text-gray-700 text-sm">{versions[0].content}</pre>
                    {versions[0].activation_reason && (
                      <p className="text-xs italic text-gray-500 mt-2">
                        Reason: {versions[0].activation_reason}
                      </p>
                    )}
                  </div>
                )}

                {/* History */}
                {versions.length > 1 && (
                  <div className="max-h-64 overflow-y-auto divide-y">
                    {/* Sticky Header */}
                    <div className="sticky top-0 bg-white px-4 py-2 text-sm font-medium text-gray-700 border-b z-10">
                      🔁 Prompt History
                    </div>

                    {versions.slice(1).map((version) => (
                      <div
                        key={version.id}
                        className="rounded-md border border-gray-200 bg-white p-4 mb-4 shadow-sm mx-5 my-5"
                      >
                        <div className="flex justify-between items-center mb-2">
                          <div className="flex items-center gap-2">
                            <span className="text-sm font-semibold text-gray-800">
                              v{version.version_number}
                            </span>
                            <span className="text-xs text-gray-500 italic">Historical Version</span>
                          </div>
                          <span className="text-xs text-gray-500">
                            {new Date(version.updated_at || version.created_at).toLocaleString()}
                          </span>
                        </div>

                        <pre className="whitespace-pre-wrap text-gray-700 text-sm mb-2">{version.content}</pre>

                        {version.activation_reason && (
                          <p className="text-xs italic text-gray-500 mb-3">
                            Reason: {version.activation_reason}
                          </p>
                        )}

                        <Button
                          size="sm"
                          variant="outline"
                          onClick={() =>
                            setSelectedVersion({ promptName, versionId: version.id, versionNumber: version.version_number }) ||
                            setShowModal(true)
                          }
                        >
                          Activate this version: v{version.version_number}
                        </Button>
                      </div>
                    ))}

                  </div>
                )}

              </div>

              <Button
                variant="link"
                size="sm"
                onClick={() => fetchPromptHistory(promptName)}
                className="mt-2"
              >
                {expandedHistories[promptName] ? 'Hide History' : 'Load History'}
              </Button>

              {/* New Version Form */}
              <div className="mt-6 space-y-2">
                <h3 className="text-sm font-medium text-gray-700">Submit New Version</h3>
                <textarea
                  rows={4}
                  placeholder="New prompt content..."
                  className="w-full rounded-md border border-gray-300 px-3 py-2 text-sm text-gray-900 bg-white placeholder:text-gray-400 focus-visible:outline-none focus-visible:ring-2 focus-visible:ring-blue-500"
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
                <input
                  type="text"
                  placeholder="Activation reason"
                  className="w-full rounded-md border border-gray-300 px-3 py-2 text-sm text-gray-900 bg-white placeholder:text-gray-400 focus-visible:outline-none focus-visible:ring-2 focus-visible:ring-blue-500"
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
                <Button
                  onClick={() => handleSubmit(promptName)}
                  size="sm"
                  className="mt-1"
                >
                  Save New Version
                </Button>
              </div>
            </div>
          ))
        )}
      </div>

      {showModal && selectedVersion && (
        <div className="fixed inset-0 z-50 flex items-center justify-center bg-black bg-opacity-50">
          <div className="bg-white rounded-lg p-6 w-full max-w-md shadow-lg">
            <h2 className="text-lg font-semibold text-gray-800 mb-4">Confirm Activation</h2>
            <p className="text-sm text-gray-700 mb-6">
              Are you sure you want to activate <span className="font-semibold">v{selectedVersion.versionNumber}</span> for prompt <span className="font-semibold">{selectedVersion.promptName}</span>?
            </p>
            <div className="flex justify-end gap-2">
              <Button
                variant="outline"
                size="sm"
                onClick={() => {
                  setShowModal(false);
                  setSelectedVersion(null);
                }}
              >
                Cancel
              </Button>
              <Button
                size="sm"
                onClick={() => handleActivateVersion({...selectedVersion})}
              >
                Confirm
              </Button>
            </div>
          </div>
        </div>
      )}

    </DashboardLayout>
  );
}
