"use client";

import React, { createContext, useContext, useEffect, useState } from "react";
import { api, ApiError } from "@/lib/api";

// Sesuaikan tipe User dengan yang kamu punya
type User = {
  id: number;
  email: string;
  username: string;
  is_active: boolean;
  is_superuser: boolean;
  created_at: string;
  updated_at: string;
};

type UserContextType = {
  user: User | null;
  loading: boolean;
  error: string | null;
  setUser: (user: User | null) => void;
};

const UserContext = createContext<UserContextType>({
  user: null,
  loading: true,
  error: null,
  setUser: () => {},
});

export const UserProvider = ({ children }: { children: React.ReactNode }) => {
  const [user, setUser] = useState<User | null>(null);
  const [loading, setLoading] = useState(true);
  const [error, setError] = useState<string | null>(null);

  useEffect(() => {
    const token = localStorage.getItem("token");

    if (!token) {
      setLoading(false);
      return;  // Tidak perlu melakukan fetch jika tidak ada token
    }

    const fetchUser = async () => {
      try {
        const data = await api.get("/api/auth/me");
        if (data && JSON.stringify(data) !== JSON.stringify(user)) {
          setUser(data); // Hanya update jika data berubah
        }
      } catch (err) {
        setUser(null);
        setError(err instanceof ApiError ? err.message : "Unknown error occurred");
      } finally {
        setLoading(false);
      }
    };

    fetchUser();
  }, []);

  return (
    <UserContext.Provider value={{ user, loading, error, setUser }}>
      {children}
    </UserContext.Provider>
  );
};

export const useUser = () => useContext(UserContext);
