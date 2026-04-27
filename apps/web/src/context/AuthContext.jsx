import axios from "axios";
import {
    createContext,
    useCallback,
    useContext,
    useEffect,
    useMemo,
    useRef,
    useState,
} from "react";

const API_BASE_URL = import.meta.env.VITE_API_BASE_URL || "/api/v1";
const apiClient = axios.create({
  baseURL: API_BASE_URL,
  withCredentials: true,
});

const AuthContext = createContext(null);

export function AuthProvider({ children }) {
  const [user, setUser] = useState(null);
  const [accessToken, setAccessToken] = useState(null);
  const [isLoading, setIsLoading] = useState(true);

  const refreshPromiseRef = useRef(null);

  const isAuthenticated = Boolean(user && accessToken);

  const refreshToken = useCallback(async () => {
    if (!refreshPromiseRef.current) {
      refreshPromiseRef.current = axios
        .post(
          `${API_BASE_URL}/auth/refresh`,
          {},
          {
            withCredentials: true,
          },
        )
        .then((response) => {
          const newAccessToken = response?.data?.data?.access_token || null;
          setAccessToken(newAccessToken);
          return newAccessToken;
        })
        .catch((error) => {
          setAccessToken(null);
          setUser(null);
          throw error;
        })
        .finally(() => {
          refreshPromiseRef.current = null;
        });
    }

    return refreshPromiseRef.current;
  }, []);

  const login = useCallback(async (email, password, rememberMe = false) => {
    const response = await apiClient.post("/auth/login", {
      email,
      password,
      remember_me: rememberMe,
    });
    const payload = response?.data || {};

    if (!payload.success) {
      throw new Error(payload.message || "Login failed");
    }

    setUser(payload?.data?.user || null);
    setAccessToken(payload?.data?.access_token || null);

    return payload;
  }, []);

  const register = useCallback(async (data) => {
    const response = await apiClient.post("/auth/register", data);
    const payload = response?.data || {};

    if (!payload.success) {
      throw new Error(payload.message || "Registration failed");
    }

    return payload;
  }, []);

  const logout = useCallback(async () => {
    try {
      await apiClient.post("/auth/logout", {});
    } finally {
      setUser(null);
      setAccessToken(null);
    }
  }, []);

  useEffect(() => {
    const requestInterceptor = apiClient.interceptors.request.use(
      (config) => {
        if (accessToken) {
          config.headers.Authorization = `Bearer ${accessToken}`;
        }
        return config;
      },
      (error) => Promise.reject(error),
    );

    const responseInterceptor = apiClient.interceptors.response.use(
      (response) => response,
      async (error) => {
        const originalRequest = error?.config;

        if (error?.response?.status === 401 && originalRequest && !originalRequest._retry) {
          originalRequest._retry = true;

          try {
            const newToken = await refreshToken();
            if (newToken) {
              originalRequest.headers = {
                ...originalRequest.headers,
                Authorization: `Bearer ${newToken}`,
              };
              return apiClient(originalRequest);
            }
          } catch (refreshError) {
            setUser(null);
            setAccessToken(null);
            return Promise.reject(refreshError);
          }
        }

        return Promise.reject(error);
      },
    );

    return () => {
      apiClient.interceptors.request.eject(requestInterceptor);
      apiClient.interceptors.response.eject(responseInterceptor);
    };
  }, [accessToken, refreshToken]);

  useEffect(() => {
    const initializeAuth = async () => {
      try {
        await refreshToken();
      } catch {
      } finally {
        setIsLoading(false);
      }
    };

    initializeAuth();
  }, [refreshToken]);

  const value = useMemo(
    () => ({
      user,
      accessToken,
      isAuthenticated,
      isLoading,
      login,
      logout,
      register,
      refreshToken,
      setUser,
      apiClient,
    }),
    [
      user,
      accessToken,
      isAuthenticated,
      isLoading,
      login,
      logout,
      register,
      refreshToken,
    ],
  );

  return <AuthContext.Provider value={value}>{children}</AuthContext.Provider>;
}

export function useAuth() {
  const context = useContext(AuthContext);
  if (!context) {
    throw new Error("useAuth must be used within an AuthProvider");
  }
  return context;
}
