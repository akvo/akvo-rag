// ...all existing imports
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

  useEffect(() => {
    fetchPrompts();
  }, []);

  const fetchPrompts = async () => {
    setLoading(true);
    try {
      const definitions: PromptResponse[] = await api.get('/api/prompt');
      console.log(definitions)
      const groups: Record<string, PromptVersion[]> = {};
      for (const def of definitions) {
        /*
          TODO ::
          currently the qa_flexible_prompt only as a backup of RAG original prompt
          and not being used, so we hide it from the UI
        */
        if (def.name === "qa_flexible_prompt") continue;
        // EOL of filter out qa_flexible_prompt
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
    try {
      const detail: PromptResponse = await api.get(`/api/prompt/${name}`);
      setPromptGroups((prev) => ({
        ...prev,
        [name]: [detail.active_version!, ...detail.all_versions.filter(v => !v.is_active)],
      }));
    } catch (err: any) {
      setStatus({ type: 'error', message: err.message || 'Failed to load history' });
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

  return (
    <DashboardLayout>
      <div className="my-10">
        <h1 className="text-3xl font-semibold mb-6 tracking-tight">Fine Tuning</h1>

        {/* Prompt Types Info Section */}
        <div className="mb-10 p-4 rounded-md border border-gray-200 bg-gray-50 text-sm text-gray-700">
          <h2 className="text-lg font-semibold mb-2">💡 Prompt Types Explained</h2>
          <p className="mb-2">
            <strong>📌 Contextual Prompt:</strong> Helps the AI rewrite the user’s query using previous chat messages (chat history).
            This makes search more accurate by adding context to follow-up questions.
          </p>
          <p className="mb-2">
            <strong>📌 QA Prompt:</strong> Guides the AI to generate the answer using retrieved knowledge base documents.
          </p>
          <ul className="list-disc list-inside ml-4">
            <li><strong>Strict:</strong> Only responds using retrieved content. (Used in production)</li>
            <li><strong>Flexible:</strong> Allows more creative or free-form responses. (Used as backup)</li>
          </ul>
        </div>

        {status && (
          <div
            className={`mb-6 rounded-md p-4 text-sm ${
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

              <div className="rounded-lg border border-gray-200 overflow-hidden divide-y">
                {versions.map((version) => (
                  <div
                    key={version.id}
                    className={`p-4 text-sm ${
                      version.is_active ? 'bg-gray-50 border-l-4 border-blue-500' : 'bg-white'
                    }`}
                  >
                    <div className="flex justify-between items-center mb-2">
                      <span className="font-semibold text-gray-800">
                        v{version.version_number} {version.is_active && <span className="text-blue-600">(Active)</span>}
                      </span>
                      <span className="text-xs text-gray-500">
                        {new Date(version.created_at).toLocaleString()}
                      </span>
                    </div>
                    <pre className="whitespace-pre-wrap text-gray-700">{version.content}</pre>
                    {version.activation_reason && (
                      <p className="text-xs italic text-gray-500 mt-2">
                        Reason: {version.activation_reason}
                      </p>
                    )}
                  </div>
                ))}
              </div>

              {versions.length === 1 && (
                <Button
                  variant="link"
                  size="sm"
                  onClick={() => fetchPromptHistory(promptName)}
                  className="mt-2"
                >
                  Load History
                </Button>
              )}

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
    </DashboardLayout>
  );
}
