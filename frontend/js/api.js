/**
 * Centralized API Client Layer for Nepal Passport Management System
 * Handles authentication headers, error catching, multipart uploads, and JSON serialization.
 */

// Resolve API base URL: always use relative /api when hosted by Django, or current origin
const API_BASE_URL = (typeof window !== 'undefined' && window.location && window.location.origin && !window.location.origin.startsWith('file'))
  ? `${window.location.origin}/api`
  : '/api';

class ApiClient {
  /**
   * Get the stored Bearer token
   */
  static getToken() {
    return localStorage.getItem('passport_token') || null;
  }

  /**
   * Core request dispatcher
   */
  static async request(endpoint, options = {}) {
    const url = endpoint.startsWith('http') ? endpoint : `${API_BASE_URL}${endpoint.startsWith('/') ? '' : '/'}${endpoint}`;
    const token = this.getToken();

    const headers = {
      Accept: 'application/json',
      ...options.headers,
    };

    // If there is an active session token and no custom Authorization header, attach Bearer
    if (token && !headers['Authorization']) {
      headers['Authorization'] = `Bearer ${token}`;
    }

    // Set JSON content-type only if body is a plain object and NOT FormData
    let body = options.body;
    if (body && !(body instanceof FormData) && typeof body === 'object') {
      headers['Content-Type'] = 'application/json';
      body = JSON.stringify(body);
    }

    try {
      const response = await fetch(url, {
        method: options.method || 'GET',
        headers,
        body,
      });

      // Handle 401 Unauthorized - token invalid or expired
      if (response.status === 401) {
        if (typeof Auth !== 'undefined' && Auth.isAuthenticated()) {
          console.warn('Session expired or unauthorized. Logging out.');
          Auth.logout(false);
          if (!window.location.pathname.includes('/login')) {
            window.location.href = '/login/?msg=session_expired';
          }
        }
      }

      // 204 No Content
      if (response.status === 204) {
        return { success: true, data: null };
      }

      const data = await response.json().catch(() => null);

      if (!response.ok) {
        let errorMessage = `Request failed with status ${response.status}`;
        if (data) {
          if (typeof data.error === 'string') errorMessage = data.error;
          else if (typeof data.detail === 'string') errorMessage = data.detail;
          else if (typeof data.message === 'string') errorMessage = data.message;
          else if (typeof data === 'object') {
            // DRF field validation error dictionary
            const firstKey = Object.keys(data)[0];
            const firstVal = data[firstKey];
            if (Array.isArray(firstVal)) {
              errorMessage = `${firstKey}: ${firstVal[0]}`;
            } else if (typeof firstVal === 'string') {
              errorMessage = `${firstKey}: ${firstVal}`;
            } else {
              errorMessage = JSON.stringify(data);
            }
          }
        }
        const error = new Error(errorMessage);
        error.status = response.status;
        error.data = data;
        throw error;
      }

      return data;
    } catch (err) {
      console.error(`API Error [${options.method || 'GET'} ${url}]:`, err.message);
      throw err;
    }
  }

  static get(endpoint, params = {}) {
    let url = endpoint;
    const query = new URLSearchParams();
    Object.entries(params).forEach(([key, val]) => {
      if (val !== undefined && val !== null && val !== '') {
        query.append(key, val);
      }
    });
    const queryString = query.toString();
    if (queryString) {
      url += (url.includes('?') ? '&' : '?') + queryString;
    }
    return this.request(url, { method: 'GET' });
  }

  static post(endpoint, data = {}) {
    return this.request(endpoint, { method: 'POST', body: data });
  }

  static put(endpoint, data = {}) {
    return this.request(endpoint, { method: 'PUT', body: data });
  }

  static patch(endpoint, data = {}) {
    return this.request(endpoint, { method: 'PATCH', body: data });
  }

  static delete(endpoint) {
    return this.request(endpoint, { method: 'DELETE' });
  }

  static upload(endpoint, formData) {
    return this.request(endpoint, {
      method: 'POST',
      body: formData,
    });
  }
}

// Global exposure
window.API = ApiClient;
