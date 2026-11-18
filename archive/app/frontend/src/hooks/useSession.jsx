import { createContext, useContext, useEffect, useMemo, useState } from "react";
import { authApi } from "../api/client";

const SessionContext = createContext(null);

export function SessionProvider({ children }) {
  const [session, setSession] = useState({
    loading: true,
    authenticated: false,
    user: null,
    error: "",
  });

  async function refreshSession() {
    try {
      const payload = await authApi.session();
      setSession({
        loading: false,
        authenticated: payload.authenticated,
        user: payload.user,
        error: "",
      });
      return payload;
    } catch (error) {
      setSession({
        loading: false,
        authenticated: false,
        user: null,
        error: error.message,
      });
      return null;
    }
  }

  async function login(body) {
    const payload = await authApi.login(body);
    await refreshSession();
    return payload;
  }

  async function logout() {
    await authApi.logout();
    return refreshSession();
  }

  function expireSession(errorMessage = "") {
    setSession({
      loading: false,
      authenticated: false,
      user: null,
      error: errorMessage,
    });
  }

  useEffect(() => {
    refreshSession();
  }, []);

  const value = useMemo(
    () => ({
      ...session,
      refreshSession,
      login,
      logout,
      expireSession,
    }),
    [session],
  );

  return (
    <SessionContext.Provider value={value}>{children}</SessionContext.Provider>
  );
}

export function useSession() {
  const context = useContext(SessionContext);
  if (!context) {
    throw new Error("useSession must be used within SessionProvider");
  }
  return context;
}
