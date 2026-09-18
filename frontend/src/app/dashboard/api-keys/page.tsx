"use client";

import { useState, useEffect } from "react";
import { Plus, Copy, Check, List, Info } from "lucide-react";
import { useRouter } from "next/navigation";
import DashboardLayout from "@/components/layout/dashboard-layout";
import { Button } from "@/components/ui/button";
import {
  Dialog,
  DialogContent,
  DialogDescription,
  DialogFooter,
  DialogHeader,
  DialogTitle,
  DialogTrigger,
} from "@/components/ui/dialog";
import { Input } from "@/components/ui/input";
import { Label } from "@/components/ui/label";
import { Switch } from "@/components/ui/switch";
import {
  Table,
  TableBody,
  TableCell,
  TableHead,
  TableHeader,
  TableRow,
} from "@/components/ui/table";
import { useToast } from "@/components/ui/use-toast";
import { api } from "@/lib/api";

export interface APIKey {
  id: number;
  name: string;
  key: string;
  is_active: boolean;
  last_used_at: string | null;
  created_at: string;
  updated_at: string;
}

export interface APIKeyCreate {
  name: string;
  is_active?: boolean;
}

export interface APIKeyUpdate {
  name?: string;
  is_active?: boolean;
}

export default function APIKeysPage() {
  const [apiKeys, setApiKeys] = useState<APIKey[]>([]);
  const [isLoading, setIsLoading] = useState(true);
  const [isCreating, setIsCreating] = useState(false);
  const [newKeyName, setNewKeyName] = useState("");
  const [isDialogOpen, setIsDialogOpen] = useState(false);
  const [isAPIListDialogOpen, setIsAPIListDialogOpen] = useState(false);
  const [copiedId, setCopiedId] = useState<number | null>(null);
  const { toast } = useToast();
  const router = useRouter();

  // Fetch API keys list
  const fetchAPIKeys = async () => {
    try {
      const data = await api.get("/api/api-keys");
      setApiKeys(data);
    } catch (error) {
      toast({
        title: "Error",
        description: "Failed to fetch API keys",
        variant: "destructive",
      });
    } finally {
      setIsLoading(false);
    }
  };

  useEffect(() => {
    fetchAPIKeys();
  }, []);

  // Create new API key
  const createAPIKey = async () => {
    if (!newKeyName.trim()) {
      toast({
        title: "Error",
        description: "Please enter a name for the API key",
        variant: "destructive",
      });
      return;
    }

    setIsCreating(true);
    try {
      const data = await api.post("/api/api-keys", {
        name: newKeyName,
        is_active: true,
      });

      setApiKeys([...apiKeys, data]);
      setNewKeyName("");
      setIsDialogOpen(false);
      toast({
        title: "Success",
        description: "API key created successfully",
      });
    } catch (error) {
      toast({
        title: "Error",
        description: "Failed to create API key",
        variant: "destructive",
      });
    } finally {
      setIsCreating(false);
    }
  };

  // Delete API key
  const deleteAPIKey = async (id: number) => {
    try {
      const response = await api.delete(`/api/api-keys/${id}`);

      if (!response.ok) throw new Error("Failed to delete API key");

      setApiKeys(apiKeys.filter((key) => key.id !== id));
      toast({
        title: "Success",
        description: "API key deleted successfully",
      });
    } catch (error) {
      toast({
        title: "Error",
        description: "Failed to delete API key",
        variant: "destructive",
      });
    }
  };

  // Update API key status
  const toggleAPIKeyStatus = async (id: number, currentStatus: boolean) => {
    try {
      const response = await api.put(`/api/api-keys/${id}`, {
        is_active: !currentStatus,
      });

      setApiKeys(
        apiKeys.map((key) =>
          key.id === id ? { ...key, is_active: !currentStatus } : key
        )
      );

      toast({
        title: "Success",
        description: "API key status updated successfully",
      });
    } catch (error) {
      toast({
        title: "Error",
        description: "Failed to update API key",
        variant: "destructive",
      });
    }
  };

  // Copy API key to clipboard
  const copyAPIKey = async (id: number, key: string) => {
    try {
      await navigator.clipboard.writeText(key);
      setCopiedId(id);
      setTimeout(() => {
        setCopiedId(null);
      }, 3000);
      toast({
        title: "Success",
        description: "API key copied to clipboard",
      });
    } catch (error) {
      toast({
        title: "Error",
        description: "Failed to copy API key",
        variant: "destructive",
      });
    }
  };

  return (
    <DashboardLayout>
      <div className="container mx-auto py-10 space-y-6">
        <div className="flex justify-between items-center">
          <div>
            <h1 className="text-2xl font-bold">API Keys</h1>
            <p className="text-sm text-muted-foreground mt-1">
              Personal API keys for direct programmatic access and querying knowledge bases.
            </p>
          </div>
          <div className="flex gap-4">
            <Dialog
              open={isAPIListDialogOpen}
              onOpenChange={setIsAPIListDialogOpen}
            >
              <DialogTrigger asChild>
                <Button variant="outline">
                  <List className="mr-2 h-4 w-4" />
                  API List
                </Button>
              </DialogTrigger>
              <DialogContent>
                <DialogHeader>
                  <DialogTitle>Available API Endpoints</DialogTitle>
                  <DialogDescription>
                    List of available API endpoints for personal API keys.
                  </DialogDescription>
                </DialogHeader>
                <div className="mt-4 space-y-6">
                  <div className="border rounded-lg p-6 bg-slate-50">
                    <div className="flex items-center justify-between mb-4">
                      <h3 className="text-lg font-semibold">
                        Knowledge Base Query
                      </h3>
                      <span className="px-2 py-0.5 rounded text-xs bg-amber-100 text-amber-800 border border-amber-200">
                        In Progress (Under Migration)
                      </span>
                    </div>
                    <div className="space-y-4">
                      <div>
                        <h4 className="text-sm font-medium text-slate-700 mb-2">
                          Method
                        </h4>
                        <code className="block p-3 bg-white border rounded-md text-sm font-mono text-[#03AD8C] font-semibold">
                          GET
                        </code>
                      </div>

                      <div>
                        <h4 className="text-sm font-medium text-slate-700 mb-2">
                          Endpoint
                        </h4>
                        <code className="block p-3 bg-white border rounded-md text-sm font-mono">
                          /openapi/knowledge/{"{id}"}/query
                        </code>
                      </div>

                      <div>
                        <h4 className="text-sm font-medium text-slate-700 mb-2">
                          Query Parameters
                        </h4>
                        <div className="bg-white border rounded-md p-3 space-y-2">
                          <div className="grid grid-cols-3 text-sm">
                            <div className="font-mono text-[#03AD8C]">query</div>
                            <div className="col-span-2">
                              Your search query string
                            </div>
                          </div>
                          <div className="grid grid-cols-3 text-sm">
                            <div className="font-mono text-[#03AD8C]">top_k</div>
                            <div className="col-span-2">
                              Number of results to return (optional, default: 3)
                            </div>
                          </div>
                        </div>
                      </div>

                      <div>
                        <h4 className="text-sm font-medium text-slate-700 mb-2">
                          Headers
                        </h4>
                        <div className="bg-white border rounded-md p-3 grid grid-cols-3 text-sm">
                          <div className="font-mono text-[#03AD8C]">
                            X-API-Key
                          </div>
                          <div className="col-span-2">your_api_key</div>
                        </div>
                      </div>
                    </div>
                  </div>
                </div>
              </DialogContent>
            </Dialog>

            <Dialog open={isDialogOpen} onOpenChange={setIsDialogOpen}>
              <DialogTrigger asChild>
                <Button>
                  <Plus className="mr-2 h-4 w-4" />
                  Create API Key
                </Button>
              </DialogTrigger>
              <DialogContent>
                <DialogHeader>
                  <DialogTitle>Create New API Key</DialogTitle>
                  <DialogDescription>
                    Create a new personal API key to access the API programmatically.
                  </DialogDescription>
                </DialogHeader>
                <div className="grid gap-4 py-4">
                  <div className="grid gap-2">
                    <Label htmlFor="name">Name</Label>
                    <Input
                      id="name"
                      value={newKeyName}
                      onChange={(e) => setNewKeyName(e.target.value)}
                      placeholder="Enter API key name"
                    />
                  </div>
                </div>
                <DialogFooter>
                  <Button
                    onClick={createAPIKey}
                    disabled={isCreating || !newKeyName.trim()}
                  >
                    {isCreating ? "Creating..." : "Create"}
                  </Button>
                </DialogFooter>
              </DialogContent>
            </Dialog>
          </div>
        </div>

        {/* Description & Usage Callout */}
        <div className="rounded-lg border bg-muted/40 p-4 text-sm text-muted-foreground space-y-3">
          <div className="flex items-center gap-2 font-medium text-foreground">
            <Info className="h-4 w-4 text-[#03AD8C]" />
            <span>About Personal API Keys</span>
          </div>
          <p>
            Personal API keys are designed to authenticate programmatic requests to query knowledge bases directly using your user account.
          </p>

          <div className="text-xs text-amber-800 dark:text-amber-300 bg-amber-50 dark:bg-amber-950/30 border border-amber-200 dark:border-amber-900 rounded p-3 space-y-1">
            <p className="font-semibold">⚠️ Feature Status:</p>
            <p>
              The OpenAPI query endpoint using personal API keys is <strong>currently under active development and does not work yet</strong>. API key generation and management work, but querying endpoints will be enabled in a future release.
            </p>
          </div>

          <div className="text-xs space-y-1.5 bg-background/80 rounded border p-3">
            <p className="font-semibold text-foreground">How it will work once enabled:</p>
            <p>
              Pass your generated key in the <code className="font-mono text-[#03AD8C] font-semibold">X-API-Key</code> HTTP request header to query a knowledge base:
            </p>
            <code className="block p-2.5 bg-muted rounded font-mono text-xs text-foreground mt-1 overflow-x-auto">
              curl -X GET &quot;http://localhost:8000/openapi/knowledge/1/query?query=What+is+Akvo+RAG&amp;top_k=3&quot; \<br />
              &nbsp;&nbsp;-H &quot;X-API-Key: sk_your_api_key_here&quot;
            </code>
          </div>
        </div>

        <div className="rounded-md border">
          <Table>
            <TableHeader>
              <TableRow>
                <TableHead>Name</TableHead>
                <TableHead>API Key</TableHead>
                <TableHead>Status</TableHead>
                <TableHead>Created</TableHead>
                <TableHead>Last Used</TableHead>
                <TableHead>Actions</TableHead>
              </TableRow>
            </TableHeader>
            <TableBody>
              {apiKeys.map((apiKey) => (
                <TableRow key={apiKey.id}>
                  <TableCell>{apiKey.name}</TableCell>
                  <TableCell className="flex items-center gap-2">
                    <code className="relative rounded bg-muted px-[0.3rem] py-[0.2rem] font-mono text-sm">
                      {apiKey.key}
                    </code>
                    <Button
                      variant="ghost"
                      size="icon"
                      onClick={() => copyAPIKey(apiKey.id, apiKey.key)}
                    >
                      {copiedId === apiKey.id ? (
                        <Check className="h-4 w-4" />
                      ) : (
                        <Copy className="h-4 w-4" />
                      )}
                    </Button>
                  </TableCell>
                  <TableCell>
                    <Switch
                      checked={apiKey.is_active}
                      onCheckedChange={() =>
                        toggleAPIKeyStatus(apiKey.id, apiKey.is_active)
                      }
                    />
                  </TableCell>
                  <TableCell>
                    {new Date(apiKey.created_at).toLocaleDateString()}
                  </TableCell>
                  <TableCell>
                    {apiKey.last_used_at
                      ? new Date(apiKey.last_used_at).toLocaleDateString()
                      : "Never"}
                  </TableCell>
                  <TableCell>
                    <Button
                      variant="destructive"
                      size="sm"
                      onClick={() => deleteAPIKey(apiKey.id)}
                    >
                      Delete
                    </Button>
                  </TableCell>
                </TableRow>
              ))}
            </TableBody>
          </Table>
        </div>
      </div>
    </DashboardLayout>
  );
}
