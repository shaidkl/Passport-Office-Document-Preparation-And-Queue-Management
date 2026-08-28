/**
 * Authentication Manager for Nepal Passport Management System
 * Handles session tokens, roles, profile storage, login/logout, and page access guards.
 */

class AuthManager {
  static TOKEN_KEY = 'passport_token';
  static USER_KEY = 'passport_user';

  static isAuthenticated() {
    return !!localStorage.getItem(this.TOKEN_KEY);
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
    return localStorage.getItem(this.TOKEN_KEY);
  }

  /**
   * Perform login through /api/login/
   */
  static async login(email, password) {
    const result = await API.post('/login/', { email, password });
    if (result && result.token) {
      localStorage.setItem(this.TOKEN_KEY, result.token);
      localStorage.setItem(this.USER_KEY, JSON.stringify({
        user_id: result.user_id,
        role: result.role,
        name: result.name,
        email: result.email,
      }));
      return result;
    }
    throw new Error('Authentication failed: Missing token in response.');
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
    localStorage.removeItem(this.TOKEN_KEY);
    localStorage.removeItem(this.USER_KEY);
    if (redirect) {
      window.location.href = '/login/?msg=logged_out';
    }
  }

  /**
   * Page Auth Guard: Enforce authentication and optional required role.
   */
  static requireAuth(allowedRoles = []) {
    if (!this.isAuthenticated()) {
      const currentPath = encodeURIComponent(window.location.pathname);
      window.location.href = `/login/?next=${currentPath}`;
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
