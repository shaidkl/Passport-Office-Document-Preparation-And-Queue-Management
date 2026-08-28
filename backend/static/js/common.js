/**
 * Common UI Utilities and Helpers for Nepal Passport Management System
 */

const UI = {
  /**
   * Display a floating toast notification
   * @param {string} message 
   * @param {'success'|'error'|'warning'|'info'} type 
   * @param {number} duration 
   */
  showToast(message, type = 'info', duration = 4000) {
    let container = document.getElementById('global-toast-container');
    if (!container) {
      container = document.createElement('div');
      container.id = 'global-toast-container';
      container.className = 'toast-container';
      document.body.appendChild(container);
    }

    const toast = document.createElement('div');
    toast.className = `toast toast-${type}`;

    let iconName = 'info';
    if (type === 'success') iconName = 'check_circle';
    if (type === 'error') iconName = 'error';
    if (type === 'warning') iconName = 'warning';

    toast.innerHTML = `
      <span class="material-symbols-outlined text-${type}">${iconName}</span>
      <div style="flex: 1; font-size: 0.875rem;">${message}</div>
      <button type="button" style="background:none; border:none; color:var(--outline); cursor:pointer;" onclick="this.parentElement.remove()">
        <span class="material-symbols-outlined" style="font-size: 1.125rem;">close</span>
      </button>
    `;

    container.appendChild(toast);

    setTimeout(() => {
      if (toast.parentElement) {
        toast.style.opacity = '0';
        toast.style.transform = 'translateX(100%)';
        toast.style.transition = 'all 0.3s ease';
        setTimeout(() => toast.remove(), 300);
      }
    }, duration);
  },

  /**
   * Show full-screen loading spinner
   */
  showLoading(text = 'Processing, please wait...') {
    let overlay = document.getElementById('global-loading-overlay');
    if (!overlay) {
      overlay = document.createElement('div');
      overlay.id = 'global-loading-overlay';
      overlay.className = 'loading-overlay';
      overlay.innerHTML = `
        <div class="spinner"></div>
        <p id="loading-text" style="font-weight: 600; color: var(--primary); font-size: 0.9375rem;">${text}</p>
      `;
      document.body.appendChild(overlay);
    } else {
      const label = overlay.querySelector('#loading-text');
      if (label) label.textContent = text;
    }
    overlay.classList.add('active');
  },

  /**
   * Hide full-screen loading spinner
   */
  hideLoading() {
    const overlay = document.getElementById('global-loading-overlay');
    if (overlay) {
      overlay.classList.remove('active');
    }
  },

  /**
   * Open Modal dialog
   */
  openModal(modalId) {
    const modal = document.getElementById(modalId);
    if (modal) {
      modal.classList.add('show');
      document.body.style.overflow = 'hidden';
    }
  },

  /**
   * Close Modal dialog
   */
  closeModal(modalId) {
    const modal = document.getElementById(modalId);
    if (modal) {
      modal.classList.remove('show');
      document.body.style.overflow = '';
    }
  },

  /**
   * Toggle Mobile Drawer
   */
  toggleMobileNav(open = null) {
    const drawer = document.getElementById('mobile-drawer');
    const overlay = document.getElementById('mobile-drawer-overlay');
    if (!drawer || !overlay) return;

    const isOpen = open !== null ? open : !drawer.classList.contains('open');
    if (isOpen) {
      drawer.classList.add('open');
      overlay.classList.add('active');
      document.body.style.overflow = 'hidden';
    } else {
      drawer.classList.remove('open');
      overlay.classList.remove('active');
      document.body.style.overflow = '';
    }
  },

  /**
   * Format ISO Date string to human readable
   */
  formatDate(dateString) {
    if (!dateString) return 'N/A';
    try {
      const date = new Date(dateString);
      return date.toLocaleDateString('en-US', {
        year: 'numeric',
        month: 'short',
        day: 'numeric',
      });
    } catch {
      return dateString;
    }
  },

  /**
   * Format ISO Date string to human readable Date & Time
   */
  formatDateTime(dateString) {
    if (!dateString) return 'N/A';
    try {
      const date = new Date(dateString);
      return date.toLocaleString('en-US', {
        year: 'numeric',
        month: 'short',
        day: 'numeric',
        hour: '2-digit',
        minute: '2-digit',
      });
    } catch {
      return dateString;
    }
  },

  /**
   * Render appropriate status badge HTML
   */
  renderStatusBadge(status) {
    const s = (status || '').toLowerCase();
    let badgeClass = 'badge-pending';
    if (s.includes('review')) badgeClass = 'badge-review';
    else if (s.includes('approv') || s.includes('verifi')) badgeClass = 'badge-approved';
    else if (s.includes('reject')) badgeClass = 'badge-rejected';
    else if (s.includes('complet')) badgeClass = 'badge-completed';
    else if (s.includes('wait')) badgeClass = 'badge-waiting';
    else if (s.includes('serv') || s.includes('call')) badgeClass = 'badge-serving';
    else if (s.includes('active')) badgeClass = 'badge-active';
    else if (s.includes('inactive')) badgeClass = 'badge-inactive';

    return `<span class="badge ${badgeClass}">${status || 'Unknown'}</span>`;
  }
};

window.UI = UI;
