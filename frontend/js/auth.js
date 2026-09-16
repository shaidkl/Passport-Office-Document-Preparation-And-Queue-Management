/**
 * Authentication Manager for Nepal Passport Management System
 * Handles secure cookie sessions, roles, profile storage, login/logout, and page access guards.
 */

class AuthManager {
  static USER_KEY = 'passport_user';
  static profilePhotoObjectUrl = null;

  static isAuthenticated() {
    return !!this.getUser();
  }

  static getUser() {
    try {
      const data = localStorage.getItem(this.USER_KEY);
      return data ? JSON.parse(data) : null;
    } catch {
      return null;
    }
  }

  static getRole() {
    const user = this.getUser();
    return user ? user.role : null;
  }

  static getToken() {
    return null;
  }

  static loginUrlForRole(role) {
    if (role === 'staff') return '/staff/login/';
    if (role === 'administrator') return '/admin-portal/login/';
    return '/login/';
  }

  static async loadVerifiedProfilePhoto(user = this.getUser()) {
    const role = user ? user.role : null;
    if (!user || !user.user_id || !['citizen', 'applicant'].includes(role)) return;

    try {
      const response = await fetch(`/api/applicants/${user.user_id}/profile-photo/`, {
        headers: {
          // DRF negotiates the request before the FileResponse is returned.
          // Accept any response here, then enforce an image content type below.
          'Accept': '*/*'
        },
        credentials: 'same-origin'
      });
      if (!response.ok) return;

      const contentType = response.headers.get('content-type') || '';
      if (!contentType.startsWith('image/')) return;

      const photoBlob = await response.blob();
      const photoUrl = URL.createObjectURL(photoBlob);
      if (this.profilePhotoObjectUrl) {
        URL.revokeObjectURL(this.profilePhotoObjectUrl);
      }
      this.profilePhotoObjectUrl = photoUrl;

      document.querySelectorAll('.auth-user-avatar').forEach(element => {
        element.textContent = '';
        element.setAttribute('aria-label', `${user.name || 'Citizen'} verified profile photo`);
        element.classList.add('has-profile-photo');
        element.style.backgroundImage = `url("${photoUrl}")`;
      });
      return true;
    } catch (error) {
      console.warn('Verified profile photo could not be loaded.', error);
      return false;
    }
  }

  /**
   * Perform login through /api/login/
   * Supports email or username identifier.
   */
  static storeAuthenticatedUser(result) {
    localStorage.removeItem('passport_token');
    localStorage.setItem(this.USER_KEY, JSON.stringify({
      user_id: result.user_id,
      role: result.role,
      name: result.name,
      username: result.username || null,
      email: result.email,
      department: result.department || null,
      designation: result.designation || null,
    }));
  }

  static async login(identifier, password, portalRole = null, rememberMe = false) {
    const result = await API.post('/login/', {
      email: identifier,
      username: identifier,
      password: password,
      remember_me: rememberMe,
      ...(portalRole ? { portal_role: portalRole } : {})
    });
    if (result && result.mfa_required) return result;
    if (result && result.user_id) {
      this.storeAuthenticatedUser(result);
      return result;
    }
    throw new Error('Authentication failed: Missing account details in response.');
  }

  static async completeMfa(challengeId, code) {
    const result = await API.post('/login/mfa/verify/', {
      challenge_id: challengeId,
      code,
    });
    if (result && result.user_id) {
      this.storeAuthenticatedUser(result);
      return result;
    }
    throw new Error('Authentication failed: Missing account details in response.');
  }

  /**
   * Perform registration through /api/register/
   */
  static async register(userData) {
    return await API.post('/register/', userData);
  }

  /**
   * Log out and clear state
   */
  static logout(redirect = true) {
    const role = this.getRole();
    const csrfToken = (typeof API !== 'undefined') ? API.getCsrfToken() : null;
    fetch('/api/logout/', {
      method: 'POST',
      headers: {
        Accept: 'application/json',
        ...(csrfToken ? { 'X-CSRFToken': csrfToken } : {}),
      },
      credentials: 'same-origin',
      keepalive: true,
    }).catch(() => {});
    localStorage.removeItem('passport_token');
    localStorage.removeItem(this.USER_KEY);
    if (redirect) {
      const loginUrl = this.loginUrlForRole(role);
      window.location.href = `${loginUrl}?msg=logged_out`;
    }
  }

  /**
   * Page Auth Guard: Enforce authentication and optional required role.
   */
  static requireAuth(allowedRoles = []) {
    if (!this.isAuthenticated()) {
      const currentPath = encodeURIComponent(window.location.pathname);
      const requiredRole = window.location.pathname.startsWith('/admin-portal/')
        ? 'administrator'
        : window.location.pathname.startsWith('/staff/')
          ? 'staff'
          : allowedRoles.length === 1
            ? allowedRoles[0]
            : null;
      const loginUrl = this.loginUrlForRole(requiredRole);
      window.location.href = `${loginUrl}?next=${currentPath}`;
      return false;
    }

    const currentRole = this.getRole();
    if (allowedRoles.length > 0 && !allowedRoles.includes(currentRole)) {
      console.warn(`Unauthorized role: ${currentRole}. Allowed:`, allowedRoles);
      // Redirect to user's appropriate portal
      if (currentRole === 'citizen' || currentRole === 'applicant') {
        window.location.href = '/applicant/dashboard/';
      } else if (currentRole === 'staff') {
        window.location.href = '/staff/dashboard/';
      } else if (currentRole === 'administrator') {
        window.location.href = '/admin-portal/dashboard/';
      } else {
        window.location.href = '/';
      }
      return false;
    }

    return true;
  }

  /**
   * Sync Header UI state (show Login/Register vs Profile/Logout)
   */
  static syncHeaderUI() {
    const isAuth = this.isAuthenticated();
    const user = this.getUser();

    const authGuestElements = document.querySelectorAll('.auth-guest-only');
    const authUserElements = document.querySelectorAll('.auth-user-only');
    const userNameElements = document.querySelectorAll('.auth-user-name');
    const userRoleElements = document.querySelectorAll('.auth-user-role');
    const userAvatarElements = document.querySelectorAll('.auth-user-avatar');

    if (isAuth && user) {
      authGuestElements.forEach(el => el.style.display = 'none');
      authUserElements.forEach(el => el.style.display = 'flex');
      userNameElements.forEach(el => el.textContent = user.name || 'User');
      userRoleElements.forEach(el => el.textContent = (user.role || '').toUpperCase());
      userAvatarElements.forEach(el => {
        const initials = (user.name || 'U').split(' ').map(n => n[0]).join('').substring(0, 2).toUpperCase();
        el.textContent = initials;
      });
      this.loadVerifiedProfilePhoto(user);

      // Update portal link if present
      const portalLink = document.getElementById('header-portal-link');
      if (portalLink) {
        if (user.role === 'staff') {
          portalLink.href = '/staff/dashboard/';
          portalLink.textContent = 'Staff Portal';
        } else if (user.role === 'administrator') {
          portalLink.href = '/admin-portal/dashboard/';
          portalLink.textContent = 'Admin Portal';
        } else {
          portalLink.href = '/applicant/dashboard/';
          portalLink.textContent = 'Citizen Portal';
        }
      }
    } else {
      authGuestElements.forEach(el => el.style.display = 'flex');
      authUserElements.forEach(el => el.style.display = 'none');
    }
  }
}

// Global exposure
window.Auth = AuthManager;

// Sync header when DOM is loaded
document.addEventListener('DOMContentLoaded', () => {
  AuthManager.syncHeaderUI();
});
