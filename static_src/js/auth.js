const AUTH = {
  TOKEN_KEY: "access_token",
  REFRESH_KEY: "refresh_token",
  USER_KEY: "auth_user",

  init() {
    this.autoRefresh();
    this.interceptFetch();
  },

  getAccessToken() {
    return localStorage.getItem(this.TOKEN_KEY);
  },

  getRefreshToken() {
    return localStorage.getItem(this.REFRESH_KEY);
  },

  getUser() {
    try {
      return JSON.parse(localStorage.getItem(this.USER_KEY));
    } catch {
      return null;
    }
  },

  isAuthenticated() {
    return !!this.getAccessToken();
  },

  async login(username, password) {
    const resp = await fetch("/api/v1/auth/token/", {
      method: "POST",
      headers: { "Content-Type": "application/json" },
      body: JSON.stringify({ username, password }),
    });
    if (!resp.ok) {
      const err = await resp.json();
      throw new Error(err.detail || "Login failed");
    }
    const data = await resp.json();
    this.setTokens(data.access, data.refresh);
    if (data.user) {
      localStorage.setItem(this.USER_KEY, JSON.stringify(data.user));
    }
    return data;
  },

  logout() {
    const refresh = this.getRefreshToken();
    if (refresh) {
      fetch("/api/v1/auth/logout/", {
        method: "POST",
        headers: {
          "Content-Type": "application/json",
          Authorization: `Bearer ${this.getAccessToken()}`,
        },
        body: JSON.stringify({ refresh }),
      }).catch(() => {});
    }
    this.clearTokens();
    window.location.href = "/login/";
  },

  setTokens(access, refresh) {
    localStorage.setItem(this.TOKEN_KEY, access);
    localStorage.setItem(this.REFRESH_KEY, refresh);
  },

  clearTokens() {
    localStorage.removeItem(this.TOKEN_KEY);
    localStorage.removeItem(this.REFRESH_KEY);
    localStorage.removeItem(this.USER_KEY);
  },

  async refreshToken() {
    const refresh = this.getRefreshToken();
    if (!refresh) {
      this.clearTokens();
      return false;
    }
    try {
      const resp = await fetch("/api/v1/auth/token/refresh/", {
        method: "POST",
        headers: { "Content-Type": "application/json" },
        body: JSON.stringify({ refresh }),
      });
      if (!resp.ok) {
        this.clearTokens();
        return false;
      }
      const data = await resp.json();
      this.setTokens(data.access, data.refresh || refresh);
      return true;
    } catch {
      this.clearTokens();
      return false;
    }
  },

  async autoRefresh() {
    if (!this.getRefreshToken()) return;
    const exp = this._getTokenExpiry(this.getAccessToken());
    if (exp && Date.now() >= exp * 1000 - 60000) {
      await this.refreshToken();
    }
    setInterval(async () => {
      const exp = this._getTokenExpiry(this.getAccessToken());
      if (exp && Date.now() >= exp * 1000 - 60000) {
        await this.refreshToken();
      }
    }, 300000);
  },

  _getTokenExpiry(token) {
    if (!token) return null;
    try {
      const payload = JSON.parse(atob(token.split(".")[1]));
      return payload.exp || null;
    } catch {
      return null;
    }
  },

  interceptFetch() {
    const origFetch = window.fetch;
    window.fetch = async (url, options = {}) => {
      const token = this.getAccessToken();
      const skipAuth = typeof url === "string" && (
        url.includes("/api/v1/auth/token/") ||
        url.includes("/login/")
      );
      if (token && !skipAuth) {
        options.headers = {
          ...options.headers,
          Authorization: `Bearer ${token}`,
        };
      }
      let resp = await origFetch(url, options);
      if (resp.status === 401 && token && !skipAuth) {
        const refreshed = await this.refreshToken();
        if (refreshed) {
          const newToken = this.getAccessToken();
          options.headers.Authorization = `Bearer ${newToken}`;
          resp = await origFetch(url, options);
        }
      }
      return resp;
    };
  },
};

export default AUTH;
