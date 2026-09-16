/**
 * Centralized API Client Layer for Nepal Passport Management System
 * Handles authentication headers, error catching, multipart uploads, and JSON serialization.
 */

// Resolve API base URL: always use relative /api when hosted by Django, or current origin
const API_BASE_URL = (typeof window !== 'undefined' && window.location && window.location.origin && !window.location.origin.startsWith('file'))
  ? `${window.location.origin}/api`
  : '/api';

class ApiClient {
  static translateMessage(message, fallback = '') {
    const text = message || fallback;
    return (typeof I18n !== 'undefined' && I18n.translateError)
      ? I18n.translateError(text)
      : text;
  }

  static getCsrfToken() {
    const cookie = document.cookie.split('; ').find(row => row.startsWith('csrftoken='));
    return cookie ? decodeURIComponent(cookie.split('=').slice(1).join('=')) : null;
  }

  /**
   * Core request dispatcher
   */
  static async request(endpoint, options = {}) {
    const url = endpoint.startsWith('http') ? endpoint : `${API_BASE_URL}${endpoint.startsWith('/') ? '' : '/'}${endpoint}`;
    const headers = {
      Accept: 'application/json',
      ...options.headers,
    };
    const method = (options.method || 'GET').toUpperCase();
    if (!['GET', 'HEAD', 'OPTIONS', 'TRACE'].includes(method) && !headers['X-CSRFToken']) {
      const csrfToken = this.getCsrfToken();
      if (csrfToken) headers['X-CSRFToken'] = csrfToken;
    }

    // Set JSON content-type only if body is a plain object and NOT FormData
    let body = options.body;
    if (body && !(body instanceof FormData) && typeof body === 'object') {
      headers['Content-Type'] = 'application/json';
      body = JSON.stringify(body);
    }

    try {
      const response = await fetch(url, {
        method,
        headers,
        body,
        credentials: 'same-origin',
      });

      // Handle 401 Unauthorized - token invalid or expired
      if (response.status === 401) {
        if (typeof Auth !== 'undefined' && Auth.isAuthenticated()) {
          console.warn('Session expired or unauthorized. Logging out.');
          const loginUrl = Auth.loginUrlForRole(Auth.getRole());
          Auth.logout(false);
          if (!window.location.pathname.includes('/login')) {
            window.location.href = `${loginUrl}?msg=session_expired`;
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
      console.error(`API Error [${method} ${url}]:`, err.message);
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

  static async getBlob(endpoint) {
    const url = endpoint.startsWith('http') ? endpoint : `${API_BASE_URL}${endpoint.startsWith('/') ? '' : '/'}${endpoint}`;
    const headers = { Accept: '*/*' };

    const response = await fetch(url, { method: 'GET', headers, credentials: 'same-origin' });
    if (response.status === 401) {
      if (typeof Auth !== 'undefined') Auth.logout(false);
      throw new Error('Your session has expired. Please sign in again.');
    }
    if (!response.ok) {
      const data = await response.json().catch(() => null);
      throw new Error((data && (data.error || data.detail)) || `Request failed with status ${response.status}`);
    }
    return response.blob();
  }

  static async getBlobUrl(endpoint) {
    const blob = await this.getBlob(endpoint);
    return URL.createObjectURL(blob);
  }

  static async openFile(endpoint) {
    // Open synchronously so browsers treat this as part of the user's click.
    // Passing "noopener" to window.open can return null even after creating a
    // tab, which previously left that tab blank and redirected the dashboard.
    const popup = window.open('about:blank', '_blank');
    if (!popup) {
      const error = new Error('The document tab was blocked. Allow pop-ups for this site and try again.');
      alert(this.translateMessage(error.message));
      throw error;
    }

    popup.opener = null;
    const loadingMessage = (typeof I18n !== 'undefined') ? I18n.t('loading_document', 'Loading document...') : 'Loading document...';
    popup.document.title = loadingMessage;
    popup.document.body.textContent = loadingMessage;
    try {
      const objectUrl = await this.getBlobUrl(endpoint);
      popup.location.replace(objectUrl);
      window.setTimeout(() => URL.revokeObjectURL(objectUrl), 60000);
    } catch (error) {
      popup.close();
      alert(this.translateMessage(error.message, 'Unable to open the file.'));
      throw error;
    }
  }

  static async downloadFile(endpoint, filename) {
    try {
      const objectUrl = await this.getBlobUrl(endpoint);
      const link = document.createElement('a');
      link.href = objectUrl;
      link.download = filename || 'download';
      document.body.appendChild(link);
      link.click();
      link.remove();
      window.setTimeout(() => URL.revokeObjectURL(objectUrl), 60000);
    } catch (error) {
      alert(this.translateMessage(error.message, 'Unable to download the file.'));
      throw error;
    }
  }
}

// Global exposure
window.API = ApiClient;
