import { createContext, useContext, useState, type ReactNode } from "react";
import { loginUser } from "../services/api";

interface AuthUser {
  public_id: string;
  first_name: string;
  last_name: string;
  email: string;
  account_type: string;
}

interface AuthContextType {
  user: AuthUser | null;
  token: string | null;
  isAuthenticated: boolean;
  isLoading: boolean;
  login: (email: string, password: string) => Promise<void>;
  logout: () => void;
}

const AuthContext = createContext<AuthContextType | undefined>(undefined);

export function AuthProvider({ children }: { children: ReactNode }) {
  const [user, setUser] = useState<AuthUser | null>(null);
  const [token, setToken] = useState<string | null>(null);
  const [isLoading, setIsLoading] = useState(false);

  async function login(email: string, password: string) {
    setIsLoading(true);

    try {
      const response = await loginUser(email, password);

      if (
        response.user.account_type !== "STAFF" &&
        response.user.account_type !== "ADMIN"
      ) {
        throw new Error("This workspace is for authorised healthcare staff.");
      }

      setToken(response.access_token);
      setUser(response.user);
    } finally {
      setIsLoading(false);
    }
  }

  function logout() {
    setToken(null);
    setUser(null);
  }

  return (
    <AuthContext.Provider
      value={{
        user,
        token,
        isAuthenticated: Boolean(token && user),
        isLoading,
        login,
        logout,
      }}
    >
      {children}
    </AuthContext.Provider>
  );
}

export function useAuth() {
  const context = useContext(AuthContext);

  if (!context) {
    throw new Error("useAuth must be used inside AuthProvider");
  }

  return context;
}
