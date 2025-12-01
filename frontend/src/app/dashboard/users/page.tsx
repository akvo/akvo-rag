"use client";
/**
 * Dashboard Users Page
 * This page displays a list of users for superusers.
 * Only accessible by superusers.
 * There are 2 main tabs:
 * 1. Pending Users - Users who have registered but are not yet approved.
 * 2. All Users - A list of all registered users.
 * Each user entry shows username, email, registration date, and status.
 * Superusers can approve or deactivate users from this page.
 * Only superusers can access this page; others are redirected.
 */

import { useState, useEffect, useCallback, useRef } from "react";
import { useRouter } from "next/navigation";
import DashboardLayout from "@/components/layout/dashboard-layout";
import { Button } from "@/components/ui/button";
import { Pagination } from "@/components/ui/pagination";
import {
  Table,
  TableBody,
  TableCell,
  TableHead,
  TableHeader,
  TableRow,
} from "@/components/ui/table";
import { Tabs, TabsList, TabsTrigger } from "@/components/ui/tabs";
import { api } from "@/lib/api";
import { useUser } from "@/contexts/userContext";
import { Switch } from "@/components/ui/switch";
import {
  Dialog,
  DialogTrigger,
  DialogContent,
  DialogTitle,
  DialogDescription,
  DialogHeader,
} from "@/components/ui/dialog";

const UsersPage: React.FC = () => {
  const router = useRouter();
  const { user: authUser } = useUser();
  const [users, setUsers] = useState<Array<any>>([]);
  const [loading, setLoading] = useState<boolean>(true);
  const [page, setPage] = useState<number>(1);
  const [pageSize, setPageSize] = useState<number>(10);
  const [totalCount, setTotalCount] = useState<number>(0);
  const [selectedTab, setSelectedTab] = useState<string>("pending");
  const [dialogOpen, setDialogOpen] = useState<boolean>(false);
  const [selectedUser, setSelectedUser] = useState<any>(null);
  const [searchTerm, setSearchTerm] = useState<string>("");
  const searchTimeoutRef = useRef<NodeJS.Timeout | null>(null);

  const onToggleUserActiveStatus = async (
    userId: string,
    isActive: boolean,
  ) => {
    try {
      // Make API call to toggle active status
      await api.patch(`/api/users/${userId}/toggle-active`);
      // Refresh the users list
      fetchUsers();
    } catch (error) {
      console.error("Error toggling user active status:", error);
    }
  };

  const onToggleUserSuperuserStatus = async (
    userId: string,
    isSuperuser: boolean,
  ) => {
    try {
      // Update UI optimistically
      setUsers((prevUsers) =>
        prevUsers.map((user) =>
          user.id === userId ? { ...user, is_superuser: isSuperuser } : user,
        ),
      );
      // Make API call to toggle superuser status
      await api.patch(`/api/users/${userId}/toggle-superuser`);
    } catch (error) {
      console.error("Error updating superuser status:", error);
      // Revert on error
      fetchUsers();
    }
  };

  const fetchUsers = useCallback(async () => {
    setLoading(true);
    try {
      // Build the API URL with pagination and search parameters
      const params = new URLSearchParams();

      if (selectedTab === "pending") {
        params.append("is_active", "false");
      } else {
        params.append("is_active", "true");
      }

      params.append("page", page.toString());
      params.append("size", pageSize.toString());

      if (searchTerm) {
        params.append("search", searchTerm);
      }

      const apiURL = `/api/users?${params.toString()}`;

      const {
        total,
        data: _users,
        size: _size,
      } = await api.get(apiURL);

      setUsers(_users);
      setTotalCount(total);
      setPageSize(_size);
    } catch (error) {
      console.error("Error fetching users:", error);
    } finally {
      setLoading(false);
    }
  }, [selectedTab, page, pageSize, searchTerm]);

  // Single effect to handle all fetching logic
  const prevTabRef = useRef(selectedTab);
  const prevSearchRef = useRef(searchTerm);
  const prevPageRef = useRef(page);

  useEffect(() => {
    const tabChanged = prevTabRef.current !== selectedTab;
    const searchChanged = prevSearchRef.current !== searchTerm;
    const pageChanged = prevPageRef.current !== page;

    // Update refs
    prevTabRef.current = selectedTab;
    prevSearchRef.current = searchTerm;
    prevPageRef.current = page;

    // If tab or search changed, reset to page 1 and fetch
    if (tabChanged || searchChanged) {
      if (page !== 1) {
        setPage(1);
        // Don't fetch here - let the page change trigger it
      } else {
        // Already on page 1, so fetch immediately
        fetchUsers();
      }
    }
    // If only page changed (not tab/search), fetch
    else if (pageChanged) {
      fetchUsers();
    }
  }, [selectedTab, searchTerm, page, fetchUsers]);

  useEffect(() => {
    // Redirect non-superusers to dashboard home
    if (authUser && !authUser.is_superuser) {
      router.push("/dashboard");
    }
  }, [authUser, router]);

  // Handle search with debounce
  const handleSearch = (value: string) => {
    if (searchTimeoutRef.current) {
      clearTimeout(searchTimeoutRef.current);
    }
    searchTimeoutRef.current = setTimeout(() => {
      setSearchTerm(value);
    }, 300);
  };

  if (!authUser || !authUser.is_superuser) {
    return null; // Or a loading spinner
  }

  return (
    <DashboardLayout>
      <div className="container mx-auto py-10">
        <div className="flex justify-between items-center mb-8">
          <h1 className="text-2xl font-bold">Users </h1>
        </div>

        <Tabs value={selectedTab} onValueChange={setSelectedTab}>
          <TabsList className="flex  bg-white px-0 gap-x-1 justify-start">
            <TabsTrigger
              value="pending"
              className="border border-b-0 px-4 py-2 text-sm font-medium -mb-px
                  rounded-t-md rounded-b-none
                  data-[state=active]:bg-white data-[state=active]:border-gray-300 data-[state=active]:text-primary
                  data-[state=inactive]:bg-muted data-[state=inactive]:text-muted-foreground hover:bg-white"
            >
              Pending
            </TabsTrigger>
            <TabsTrigger
              value="approved"
              className="border border-b-0 px-4 py-2 text-sm font-medium -mb-px
                  rounded-t-md rounded-b-none
                  data-[state=active]:bg-white data-[state=active]:border-gray-300 data-[state=active]:text-primary
                  data-[state=inactive]:bg-muted data-[state=inactive]:text-muted-foreground hover:bg-white"
            >
              Approved
            </TabsTrigger>
          </TabsList>
          <div className="border border-gray-300 rounded-b-md rounded-tr-md bg-white p-6 mt-0">
            {/* Filter search */}
            <div className="mb-4 flex justify-end">
              <input
                type="text"
                placeholder="Search by email or username"
                className="border border-gray-300 rounded px-4 py-2 w-64"
                onChange={(e) => handleSearch(e.target.value)}
              />
            </div>
            {/* Table for displaying users */}
            <div className="rounded-md border">
              <Table>
                <TableHeader>
                  <TableRow>
                    <TableHead>Created</TableHead>
                    <TableHead>Email</TableHead>
                    <TableHead>Username</TableHead>
                    <TableHead>Is Superuser</TableHead>
                    <TableHead>Actions</TableHead>
                  </TableRow>
                </TableHeader>
                <TableBody>
                  {loading ? (
                    <TableRow>
                      <TableCell colSpan={5} className="text-center py-8">
                        Loading...
                      </TableCell>
                    </TableRow>
                  ) : users.length === 0 ? (
                    <TableRow>
                      <TableCell colSpan={5} className="text-center py-8 text-gray-500">
                        No users found.
                      </TableCell>
                    </TableRow>
                  ) : (
                    users.map((user) => (
                      <TableRow key={user.id}>
                        <TableCell>
                          {user.created_at}
                          {user?.approver?.username && (
                            <div
                              className="text-xs text-green-600"
                              title={new Date(user.approved_at).toLocaleString(
                                "en-US",
                                {
                                  month: "long",
                                  day: "numeric",
                                  year: "numeric",
                                  hour: "numeric",
                                  minute: "numeric",
                                  hour12: true,
                                },
                              )}
                            >
                              Approved by {user.approver.username}
                            </div>
                          )}
                        </TableCell>
                        <TableCell>{user.email}</TableCell>
                        <TableCell>{user.username}</TableCell>
                        <TableCell>
                          {selectedTab === "approved" &&
                          user.id !== authUser.id ? (
                            <Switch
                              checked={user.is_superuser}
                              onCheckedChange={(checked) =>
                                onToggleUserSuperuserStatus(user.id, checked)
                              }
                            />
                          ) : user.is_superuser ? (
                            "Yes"
                          ) : (
                            "No"
                          )}
                        </TableCell>
                        <TableCell>
                          {authUser.id !== user.id && (
                            <Button
                              variant={
                                selectedTab === "pending"
                                  ? "default"
                                  : "destructive"
                              }
                              size="sm"
                              onClick={() => {
                                setSelectedUser(user);
                                setDialogOpen(true);
                              }}
                            >
                              {selectedTab === "pending"
                                ? "Approve"
                                : "Deactivate"}
                            </Button>
                          )}
                        </TableCell>
                      </TableRow>
                    ))
                  )}
                </TableBody>
              </Table>
              <Dialog open={dialogOpen} onOpenChange={setDialogOpen}>
                <DialogContent className="max-w-sm">
                  <DialogHeader>
                    <DialogTitle>
                      {selectedTab === "pending"
                        ? "Approve User"
                        : "Deactivate User"}
                    </DialogTitle>
                    <DialogDescription>
                      {selectedTab === "pending" && selectedUser && (
                        <>
                          <p>
                            Are you sure you want to{" "}
                            <b style={{ color: "green" }}>approve</b> the user{" "}
                            <strong>{selectedUser.email}</strong>?
                          </p>
                          <br />
                          <p>This will grant them access to the platform.</p>
                        </>
                      )}
                      {selectedTab === "approved" && selectedUser && (
                        <>
                          <p>
                            Are you sure you want to{" "}
                            <b style={{ color: "red" }}>deactivate</b> the user{" "}
                            <strong>{selectedUser.email}</strong>? <br />
                          </p>
                          <br />
                          <p>This will revoke their access to the platform.</p>
                        </>
                      )}
                    </DialogDescription>
                  </DialogHeader>
                  <div className="mt-4 flex justify-end gap-2">
                    <Button
                      variant="secondary"
                      onClick={() => {
                        setDialogOpen(false);
                        setSelectedUser(null);
                      }}
                    >
                      Cancel
                    </Button>
                    <Button
                      variant={
                        selectedTab === "pending" ? "default" : "destructive"
                      }
                      onClick={() => {
                        onToggleUserActiveStatus(
                          selectedUser.id,
                          selectedTab === "pending" ? true : false,
                        );
                        setSelectedUser(null);
                        setDialogOpen(false);
                      }}
                    >
                      {selectedTab === "pending" ? "Approve" : "Deactivate"}
                    </Button>
                  </div>
                </DialogContent>
              </Dialog>
            </div>
            <div className="flex justify-end mt-4">
              <Pagination
                currentPage={page}
                totalPages={Math.ceil(totalCount / pageSize)}
                onPageChange={setPage}
              />
            </div>
          </div>
        </Tabs>
      </div>
    </DashboardLayout>
  );
};

export default UsersPage;