'use client';

import React, { useState, useEffect, useCallback, useRef } from 'react';
import { useRouter } from 'next/navigation';
import {
  Users,
  UserCheck,
  UserX,
  Shield,
  ShieldCheck,
  Clock,
  Search,
  RefreshCw,
  AlertTriangle,
  CheckCircle2,
  XCircle,
  Mail,
  Calendar,
  Sparkles,
  User as UserIcon,
} from 'lucide-react';
import DashboardLayout from '@/components/layout/dashboard-layout';
import { Button } from '@/components/ui/button';
import { Pagination } from '@/components/ui/pagination';
import {
  Table,
  TableBody,
  TableCell,
  TableHead,
  TableHeader,
  TableRow,
} from '@/components/ui/table';
import { Tabs, TabsList, TabsTrigger, TabsContent } from '@/components/ui/tabs';
import { Switch } from '@/components/ui/switch';
import {
  Dialog,
  DialogContent,
  DialogTitle,
  DialogDescription,
  DialogHeader,
} from '@/components/ui/dialog';
import { api } from '@/lib/api';
import { useUser } from '@/contexts/userContext';
import { useToast } from '@/components/ui/use-toast';
import { formatDateTime } from '@/lib/utils';
import { InitialAvatar } from '@/components/ui/avatar';

interface UserRecord {
  id: string | number;
  email: string;
  username: string;
  is_active: boolean;
  is_superuser: boolean;
  created_at: string;
  approved_at?: string;
  approver?: {
    username: string;
    email?: string;
  };
}

export default function UsersPage() {
  const router = useRouter();
  const { user: authUser } = useUser();
  const { toast } = useToast();

  const [users, setUsers] = useState<UserRecord[]>([]);
  const [loading, setLoading] = useState<boolean>(true);
  const [page, setPage] = useState<number>(1);
  const [pageSize, setPageSize] = useState<number>(10);
  const [totalCount, setTotalCount] = useState<number>(0);
  const [selectedTab, setSelectedTab] = useState<'pending' | 'approved'>('pending');
  const [searchTerm, setSearchTerm] = useState<string>('');
  const searchTimeoutRef = useRef<NodeJS.Timeout | null>(null);

  // Modals state
  const [actionModalOpen, setActionModalOpen] = useState<boolean>(false);
  const [actionType, setActionType] = useState<'approve' | 'deactivate' | 'toggle_superuser'>('approve');
  const [selectedUser, setSelectedUser] = useState<UserRecord | null>(null);
  const [pendingSuperuserVal, setPendingSuperuserVal] = useState<boolean>(false);
  const [actionLoading, setActionLoading] = useState<boolean>(false);

  // Quick stats
  const [stats, setStats] = useState({
    pending: 0,
    approved: 0,
    superusers: 0,
  });

  const fetchUsers = useCallback(async () => {
    setLoading(true);
    try {
      const params = new URLSearchParams();
      params.append('is_active', selectedTab === 'approved' ? 'true' : 'false');
      params.append('page', page.toString());
      params.append('size', pageSize.toString());

      if (searchTerm) {
        params.append('search', searchTerm);
      }

      const { total, data: _users, size: _size } = await api.get(`/api/users?${params.toString()}`);
      setUsers(_users || []);
      setTotalCount(total || 0);
      setPageSize(_size || 10);
    } catch {
      toast({
        title: 'Error',
        description: 'Failed to retrieve users list.',
        variant: 'destructive',
      });
    } finally {
      setLoading(false);
    }
  }, [selectedTab, page, pageSize, searchTerm, toast]);

  // Load summary counts
  const fetchStats = useCallback(async () => {
    try {
      const pendingRes = await api.get('/api/users?is_active=false&page=1&size=1');
      const approvedRes = await api.get('/api/users?is_active=true&page=1&size=100');
      const superusersCount = (approvedRes?.data || []).filter((u: UserRecord) => u.is_superuser).length;

      setStats({
        pending: pendingRes?.total || 0,
        approved: approvedRes?.total || 0,
        superusers: superusersCount,
      });
    } catch {
      // Non-critical stats error
    }
  }, []);

  useEffect(() => {
    fetchUsers();
    fetchStats();
  }, [fetchUsers, fetchStats]);

  useEffect(() => {
    if (authUser && !authUser.is_superuser) {
      router.push('/dashboard');
    }
  }, [authUser, router]);

  const handleSearch = (value: string) => {
    if (searchTimeoutRef.current) {
      clearTimeout(searchTimeoutRef.current);
    }
    searchTimeoutRef.current = setTimeout(() => {
      setSearchTerm(value);
      setPage(1);
    }, 300);
  };

  const handleConfirmAction = async () => {
    if (!selectedUser) return;
    setActionLoading(true);
    try {
      if (actionType === 'approve' || actionType === 'deactivate') {
        await api.patch(`/api/users/${selectedUser.id}/toggle-active`);
        toast({
          title: actionType === 'approve' ? 'User Approved' : 'User Deactivated',
          description: `User ${selectedUser.email} has been ${
            actionType === 'approve' ? 'granted access' : 'deactivated'
          }.`,
        });
      } else if (actionType === 'toggle_superuser') {
        await api.patch(`/api/users/${selectedUser.id}/toggle-superuser`);
        toast({
          title: 'Role Updated',
          description: `User ${selectedUser.email} is ${
            pendingSuperuserVal ? 'now a Super Admin' : 'now a standard Member'
          }.`,
        });
      }
      setActionModalOpen(false);
      setSelectedUser(null);
      fetchUsers();
      fetchStats();
    } catch {
      toast({
        title: 'Action Failed',
        description: 'An error occurred while updating the user record.',
        variant: 'destructive',
      });
    } finally {
      setActionLoading(false);
    }
  };

  if (!authUser || !authUser.is_superuser) {
    return null;
  }

  return (
    <DashboardLayout>
      <div className="space-y-8 pb-12">
        {/* Header */}
        <div className="flex flex-col md:flex-row md:items-center justify-between gap-4 border-b border-border/60 pb-6">
          <div className="flex items-center gap-3">
            <div className="h-10 w-10 rounded-xl bg-gradient-to-br from-indigo-500/20 to-purple-500/20 border border-indigo-500/30 flex items-center justify-center text-indigo-400">
              <Users className="h-5 w-5" />
            </div>
            <div>
              <h1 className="text-2xl font-bold tracking-tight text-foreground flex items-center gap-2">
                User Access & Membership Portal
              </h1>
              <p className="text-sm text-muted-foreground">
                Approve incoming registration requests, manage superuser permissions, and audit platform members.
              </p>
            </div>
          </div>

          <button
            onClick={() => {
              fetchUsers();
              fetchStats();
            }}
            disabled={loading}
            className="flex items-center gap-2 px-3 py-1.5 rounded-lg bg-primary/10 hover:bg-primary/20 text-primary border border-primary/20 text-xs font-medium transition-colors self-start md:self-auto"
          >
            <RefreshCw className={`h-3.5 w-3.5 ${loading ? 'animate-spin' : ''}`} />
            Refresh
          </button>
        </div>

        {/* Quick Stats Overview */}
        <div className="grid grid-cols-1 md:grid-cols-3 gap-4">
          <div className="p-4 rounded-xl border border-border/60 bg-card/60 backdrop-blur-sm flex items-center gap-4">
            <div className="h-12 w-12 rounded-xl bg-amber-500/10 border border-amber-500/20 flex items-center justify-center text-amber-400">
              <Clock className="h-6 w-6" />
            </div>
            <div>
              <p className="text-xs text-muted-foreground uppercase font-medium tracking-wider">Pending Approvals</p>
              <div className="flex items-center gap-2 mt-0.5">
                <span className="text-xl font-bold text-foreground">{stats.pending}</span>
                {stats.pending > 0 && (
                  <span className="px-2 py-0.5 rounded-full text-[11px] font-semibold bg-amber-500/20 text-amber-400 border border-amber-500/30 animate-pulse">
                    Action Required
                  </span>
                )}
              </div>
            </div>
          </div>

          <div className="p-4 rounded-xl border border-border/60 bg-card/60 backdrop-blur-sm flex items-center gap-4">
            <div className="h-12 w-12 rounded-xl bg-emerald-500/10 border border-emerald-500/20 flex items-center justify-center text-emerald-400">
              <UserCheck className="h-6 w-6" />
            </div>
            <div>
              <p className="text-xs text-muted-foreground uppercase font-medium tracking-wider">Approved Members</p>
              <p className="text-xl font-bold text-foreground mt-0.5">{stats.approved}</p>
            </div>
          </div>

          <div className="p-4 rounded-xl border border-border/60 bg-card/60 backdrop-blur-sm flex items-center gap-4">
            <div className="h-12 w-12 rounded-xl bg-indigo-500/10 border border-indigo-500/20 flex items-center justify-center text-indigo-400">
              <ShieldCheck className="h-6 w-6" />
            </div>
            <div>
              <p className="text-xs text-muted-foreground uppercase font-medium tracking-wider">Super Administrators</p>
              <p className="text-xl font-bold text-foreground mt-0.5">{stats.superusers}</p>
            </div>
          </div>
        </div>

        {/* Tabbed User Management */}
        <Tabs
          value={selectedTab}
          onValueChange={(val) => {
            setSelectedTab(val as 'pending' | 'approved');
            setPage(1);
          }}
          className="w-full"
        >
          <div className="flex flex-col sm:flex-row sm:items-center justify-between gap-4">
            <TabsList className="grid grid-cols-2 max-w-xs">
              <TabsTrigger value="pending" className="flex items-center gap-2">
                <Clock className="h-4 w-4" />
                Pending ({stats.pending})
              </TabsTrigger>
              <TabsTrigger value="approved" className="flex items-center gap-2">
                <UserCheck className="h-4 w-4" />
                Approved ({stats.approved})
              </TabsTrigger>
            </TabsList>

            {/* Search Input */}
            <div className="relative w-full sm:w-72">
              <Search className="absolute left-3 top-1/2 -translate-y-1/2 h-4 w-4 text-muted-foreground" />
              <input
                type="text"
                placeholder="Search username or email..."
                defaultValue={searchTerm}
                onChange={(e) => handleSearch(e.target.value)}
                className="w-full pl-9 pr-4 py-2 text-xs rounded-lg border border-border/70 bg-card/80 text-foreground placeholder:text-muted-foreground focus:outline-none focus:ring-1 focus:ring-primary focus:border-primary transition-all"
              />
            </div>
          </div>

          <div className="mt-6 rounded-xl border border-border/70 bg-card/70 backdrop-blur-sm overflow-hidden shadow-sm">
            <Table>
              <TableHeader className="bg-muted/40 border-b border-border/60">
                <TableRow>
                  <TableHead className="text-xs font-semibold uppercase tracking-wider text-muted-foreground py-3.5">
                    User Details
                  </TableHead>
                  <TableHead className="text-xs font-semibold uppercase tracking-wider text-muted-foreground py-3.5">
                    Role
                  </TableHead>
                  <TableHead className="text-xs font-semibold uppercase tracking-wider text-muted-foreground py-3.5">
                    Registration & Approval
                  </TableHead>
                  <TableHead className="text-xs font-semibold uppercase tracking-wider text-muted-foreground py-3.5 text-center">
                    Super-Admin
                  </TableHead>
                  <TableHead className="text-xs font-semibold uppercase tracking-wider text-muted-foreground py-3.5 text-right">
                    Actions
                  </TableHead>
                </TableRow>
              </TableHeader>

              <TableBody className="divide-y divide-border/40 text-xs">
                {loading ? (
                  <TableRow>
                    <TableCell colSpan={5} className="text-center py-12 text-muted-foreground">
                      <div className="flex items-center justify-center gap-2">
                        <RefreshCw className="h-4 w-4 animate-spin text-primary" />
                        <span>Loading user accounts...</span>
                      </div>
                    </TableCell>
                  </TableRow>
                ) : users.length === 0 ? (
                  <TableRow>
                    <TableCell colSpan={5} className="text-center py-12 text-muted-foreground space-y-1">
                      <UserX className="h-8 w-8 mx-auto text-muted-foreground/50" />
                      <p className="font-medium text-foreground text-sm">No users found</p>
                      <p className="text-xs">
                        {selectedTab === 'pending'
                          ? 'No pending registration requests waiting for approval.'
                          : 'No approved members match your search criteria.'}
                      </p>
                    </TableCell>
                  </TableRow>
                ) : (
                  users.map((user) => {
                    const isSelf = String(user.id) === String(authUser.id);
                    return (
                      <TableRow key={user.id} className="hover:bg-muted/20 transition-colors">
                        {/* User Details */}
                        <TableCell className="py-3.5">
                          <div className="flex items-center gap-3">
                            <InitialAvatar username={user.username || user.email} />
                            <div>
                              <p className="font-semibold text-foreground text-sm flex items-center gap-1.5">
                                {user.username || user.email}
                                {isSelf && (
                                  <span className="px-1.5 py-0.5 rounded text-[10px] font-bold bg-primary/20 text-primary border border-primary/30">
                                    YOU
                                  </span>
                                )}
                              </p>
                              <p className="text-xs text-muted-foreground font-mono flex items-center gap-1">
                                <Mail className="h-3 w-3" />
                                {user.email}
                              </p>
                            </div>
                          </div>
                        </TableCell>

                        {/* Role Badge */}
                        <TableCell className="py-3.5">
                          {user.is_superuser ? (
                            <span className="inline-flex items-center gap-1 px-2.5 py-0.5 rounded-full text-xs font-semibold bg-purple-500/10 text-purple-400 border border-purple-500/20">
                              <ShieldCheck className="h-3.5 w-3.5" />
                              Super Admin
                            </span>
                          ) : (
                            <span className="inline-flex items-center gap-1 px-2.5 py-0.5 rounded-full text-xs font-medium bg-sky-500/10 text-sky-400 border border-sky-500/20">
                              <UserIcon className="h-3.5 w-3.5" />
                              Member
                            </span>
                          )}
                        </TableCell>

                        {/* Registration Date & Approver */}
                        <TableCell className="py-3.5 text-muted-foreground space-y-0.5">
                          <div className="flex items-center gap-1 text-xs">
                            <Calendar className="h-3 w-3" />
                            <span>Registered: {formatDateTime(user.created_at)}</span>
                          </div>
                          {user.approver?.username && (
                            <p className="text-[11px] text-emerald-400 font-medium">
                              Approved by {user.approver.username}
                            </p>
                          )}
                        </TableCell>

                        {/* Superuser Switch */}
                        <TableCell className="py-3.5 text-center">
                          {selectedTab === 'approved' && !isSelf ? (
                            <div className="flex justify-center">
                              <Switch
                                checked={user.is_superuser}
                                onCheckedChange={(checked) => {
                                  setSelectedUser(user);
                                  setPendingSuperuserVal(checked);
                                  setActionType('toggle_superuser');
                                  setActionModalOpen(true);
                                }}
                              />
                            </div>
                          ) : (
                            <span className="text-xs text-muted-foreground font-mono">
                              {user.is_superuser ? 'Granted' : 'Standard'}
                            </span>
                          )}
                        </TableCell>

                        {/* Actions */}
                        <TableCell className="py-3.5 text-right">
                          {!isSelf && (
                            <Button
                              size="sm"
                              variant={selectedTab === 'pending' ? 'default' : 'destructive'}
                              onClick={() => {
                                setSelectedUser(user);
                                setActionType(selectedTab === 'pending' ? 'approve' : 'deactivate');
                                setActionModalOpen(true);
                              }}
                              className="text-xs font-medium"
                            >
                              {selectedTab === 'pending' ? (
                                <>
                                  <CheckCircle2 className="h-3.5 w-3.5 mr-1" />
                                  Approve
                                </>
                              ) : (
                                <>
                                  <UserX className="h-3.5 w-3.5 mr-1" />
                                  Deactivate
                                </>
                              )}
                            </Button>
                          )}
                        </TableCell>
                      </TableRow>
                    );
                  })
                )}
              </TableBody>
            </Table>
          </div>

          {/* Pagination */}
          {totalCount > pageSize && (
            <div className="flex justify-end pt-4">
              <Pagination
                currentPage={page}
                totalPages={Math.ceil(totalCount / pageSize)}
                onPageChange={setPage}
              />
            </div>
          )}
        </Tabs>

        {/* Action Confirmation Modal */}
        <Dialog open={actionModalOpen} onOpenChange={setActionModalOpen}>
          <DialogContent className="max-w-md">
            <DialogHeader>
              <DialogTitle className="flex items-center gap-2">
                {actionType === 'approve' ? (
                  <>
                    <UserCheck className="h-5 w-5 text-emerald-400" />
                    Approve User Account
                  </>
                ) : actionType === 'deactivate' ? (
                  <>
                    <AlertTriangle className="h-5 w-5 text-rose-400" />
                    Deactivate User Account
                  </>
                ) : (
                  <>
                    <Shield className="h-5 w-5 text-purple-400" />
                    {pendingSuperuserVal ? 'Grant Super Admin Privileges' : 'Revoke Super Admin Privileges'}
                  </>
                )}
              </DialogTitle>

              <DialogDescription className="pt-2 text-sm text-muted-foreground space-y-3">
                {actionType === 'approve' && selectedUser && (
                  <>
                    <p>
                      Are you sure you want to approve{' '}
                      <strong className="text-foreground">{selectedUser.email}</strong>?
                    </p>
                    <p className="text-xs bg-emerald-500/10 text-emerald-400 border border-emerald-500/20 p-3 rounded-lg">
                      ✓ This will activate their account and grant them access to use Akvo RAG conversational features
                      and scoped knowledge bases.
                    </p>
                  </>
                )}

                {actionType === 'deactivate' && selectedUser && (
                  <>
                    <p>
                      Are you sure you want to deactivate{' '}
                      <strong className="text-foreground">{selectedUser.email}</strong>?
                    </p>
                    <p className="text-xs bg-rose-500/10 text-rose-400 border border-rose-500/20 p-3 rounded-lg">
                      ⚠️ This will immediately revoke their platform session and prevent any future sign-in attempts.
                      Their past chat history and contributions remain preserved.
                    </p>
                  </>
                )}

                {actionType === 'toggle_superuser' && selectedUser && (
                  <>
                    <p>
                      Are you sure you want to{' '}
                      <strong className="text-foreground">
                        {pendingSuperuserVal ? 'elevate' : 'demote'}
                      </strong>{' '}
                      <strong className="text-foreground">{selectedUser.email}</strong>?
                    </p>
                    <p className="text-xs bg-purple-500/10 text-purple-400 border border-purple-500/20 p-3 rounded-lg">
                      {pendingSuperuserVal
                        ? '🛡️ Super Administrators can register tenant apps, manage system prompts, grant/revoke user access, and inspect observability diagnostics.'
                        : 'Demoting this user will remove their administrative controls while preserving standard chat and knowledge base member access.'}
                    </p>
                  </>
                )}
              </DialogDescription>
            </DialogHeader>

            <div className="flex justify-end gap-2 pt-4 border-t border-border/40">
              <Button
                variant="secondary"
                disabled={actionLoading}
                onClick={() => {
                  setActionModalOpen(false);
                  setSelectedUser(null);
                }}
              >
                Cancel
              </Button>
              <Button
                variant={actionType === 'deactivate' ? 'destructive' : 'default'}
                disabled={actionLoading}
                onClick={handleConfirmAction}
              >
                {actionLoading
                  ? 'Updating...'
                  : actionType === 'approve'
                  ? 'Confirm Approval'
                  : actionType === 'deactivate'
                  ? 'Confirm Deactivation'
                  : 'Confirm Role Change'}
              </Button>
            </div>
          </DialogContent>
        </Dialog>
      </div>
    </DashboardLayout>
  );
}