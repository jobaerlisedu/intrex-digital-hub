/**
 * Intrex ERP SPA — Main Entry Point (Vite)
 *
 * Imports the SPA router and re-initializes dynamic components
 * after each content swap.
 */
import AUTH from './auth.js';
import './spa-router.js';

AUTH.init();

// Re-initialize after SPA content swap
document.addEventListener('spa:content-updated', () => {
  // Re-run dropdown toggles for sidebar
  document.querySelectorAll('.nav-item-dropdown .dropdown-toggle').forEach((el) => {
    el.addEventListener('click', function (e) {
      e.preventDefault();
      const targetId = this.getAttribute('onclick')?.match(/'([^']+)'/)?.[1];
      if (targetId && typeof toggleDropdown === 'function') {
        toggleDropdown(e, targetId);
      }
    });
  });

  // Re-run pagination init
  if (typeof initPagination === 'function') {
    initPagination();
  }

  // Re-run search filtering
  if (typeof initSearchFilter === 'function') {
    initSearchFilter();
  }
});
