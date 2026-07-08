/**
 * Intrex ERP SPA Router
 *
 * Intercepts navigation clicks, fetches page content via AJAX,
 * swaps the content area, and updates browser history — all
 * without a full page reload.
 */

const SPA = {
  // CSS selector for the content container
  contentSelector: '#spa-content',
  // CSS selector to ignore (e.g., external links, logout, etc.)
  ignoreSelector: '[data-spa-ignore], [target="_blank"], a[href^="http"], a[href^="//"], a[href^="#"], a[href^="mailto:"], a[href^="tel:"]',
  // Currently active URL path
  currentPath: window.location.pathname + window.location.search,
  // Whether a navigation is in progress
  navigating: false,
  // Cache of fetched pages
  cache: new Map(),
  // Prefetch timeout handle
  prefetchTimer: null,
};

/**
 * Checks if a link should be intercepted by the SPA router.
 */
SPA.shouldIntercept = function (link) {
  if (!link || link.closest(this.ignoreSelector)) return false;
  if (link.matches(this.ignoreSelector)) return false;
  if (link.hasAttribute('download')) return false;
  if (link.getAttribute('rel') === 'external') return false;

  const url = new URL(link.href, window.location.origin);
  // Same origin check
  if (url.origin !== window.location.origin) return false;
  // Skip if it's the same page
  if (url.pathname + url.search === this.currentPath) return false;
  // Skip if it's not an ERP path (only intercept /erp/ and module paths)
  if (!url.pathname.startsWith('/erp/') &&
      !['/hrm/', '/inventory/', '/investment/', '/billing/', '/solutions/', '/training/', '/users/'].some(p => url.pathname.startsWith(p))) {
    return false;
  }
  return true;
};

/**
 * Parses the HTML response and extracts the content block.
 */
SPA.extractContent = function (html) {
  const parser = new DOMParser();
  const doc = parser.parseFromString(html, 'text/html');
  const content = doc.querySelector(this.contentSelector);
  const title = doc.querySelector('title')?.textContent || 'Intrex ERP';
  const extraCSS = doc.querySelector('style[data-spa-style]')?.outerHTML || '';
  const extraJS = doc.querySelector('script[data-spa-script]')?.textContent || '';

  return { content, title, extraCSS, extraJS, doc };
};

/**
 * Loads a page via fetch.
 */
SPA.fetchPage = async function (url, useCache = true) {
  const cacheKey = url;

  if (useCache && this.cache.has(cacheKey)) {
    return this.cache.get(cacheKey);
  }

  const response = await fetch(url, {
    headers: {
      'X-SPA-Fragment': 'true',
      'X-Requested-With': 'XMLHttpRequest',
    },
  });

  if (!response.ok) {
    throw new Error(`Page fetch failed: ${response.status}`);
  }

  const html = await response.text();
  const result = this.extractContent(html);

  // Cache for later use (max 50 entries)
  if (this.cache.size > 50) {
    const firstKey = this.cache.keys().next().value;
    this.cache.delete(firstKey);
  }
  this.cache.set(cacheKey, result);

  return result;
};

/**
 * Renders content into the page.
 */
SPA.renderContent = async function (url, pushState = true) {
  if (this.navigating) return;
  this.navigating = true;

  const contentEl = document.querySelector(this.contentSelector);
  if (!contentEl) {
    // Fallback: full page load
    window.location.href = url;
    this.navigating = false;
    return;
  }

  // Show loading indicator
  this.showLoading(true);

  try {
    const page = await this.fetchPage(url, true);

    if (!page.content) {
      throw new Error('Content block not found in response');
    }

    // Fade out
    contentEl.style.opacity = '0';
    contentEl.style.transform = 'translateY(8px)';
    contentEl.style.transition = 'opacity 0.15s ease, transform 0.15s ease';

    await new Promise((r) => setTimeout(r, 120));

    // Swap content using DOM node replacement (safe, preserves event listeners on ancestors)
    contentEl.replaceChildren(...page.content.childNodes);

    // Update title
    if (page.title) {
      document.title = page.title;
    }

    // Inject page-specific CSS if provided
    const existingStyle = document.getElementById('spa-page-style');
    if (existingStyle) existingStyle.remove();
    if (page.extraCSS) {
      const styleTag = document.createElement('style');
      styleTag.id = 'spa-page-style';
      styleTag.setAttribute('data-spa-style', '');
      styleTag.textContent = page.extraCSS;
      document.head.appendChild(styleTag);
    }

    // Update URL
    const newPath = url.split('?')[0];
    const search = url.includes('?') ? '?' + url.split('?')[1] : '';
    if (pushState) {
      window.history.pushState({ path: newPath + search }, '', newPath + search);
      this.currentPath = newPath + search;
    }

    // Fade in
    contentEl.style.opacity = '1';
    contentEl.style.transform = 'translateY(0)';

    // Re-run page-specific scripts
    if (page.extraJS) {
      console.warn('[SPA] extraJS is deprecated and will not execute.');
    }

    // Update sidebar active states
    this.updateSidebarActive(newPath + search);

    // Re-initialize dynamic components
    this.reinitializeComponents();

    // Scroll to top for main navigation, preserve for same-page
    window.scrollTo({ top: 0, behavior: 'smooth' });

  } catch (err) {
    console.error('SPA navigation error:', err);
    // Fallback: full page load
    window.location.href = url;
  } finally {
    this.showLoading(false);
    this.navigating = false;
  }
};

/**
 * Re-initializes components after content swap (tooltips, etc.)
 */
SPA.reinitializeComponents = function () {
  // Dispatch custom event for other scripts to hook into
  document.dispatchEvent(new CustomEvent('spa:content-updated'));
};

/**
 * Updates sidebar link active states based on current URL.
 */
SPA.updateSidebarActive = function (path) {
  document.querySelectorAll('.sidebar .nav-link, .sidebar .submenu-link').forEach((link) => {
    const href = link.getAttribute('href');
    if (!href || href === '#') return;

    // Match start of path to handle nested routes
    const isActive = path.startsWith(href.split('?')[0]);
    link.classList.toggle('active', isActive);
  });

  // Update dropdown open states
  document.querySelectorAll('.nav-item-dropdown').forEach((item) => {
    const hasActive = item.querySelector('.submenu-link.active') !== null;
    const submenu = item.querySelector('.submenu-links');
    item.classList.toggle('active', hasActive);
    item.classList.toggle('open', hasActive);
    if (submenu) submenu.classList.toggle('show', hasActive);
  });
};

/**
 * Toggles the loading indicator.
 */
SPA.showLoading = function (visible) {
  let loader = document.getElementById('spa-loader');
  if (visible) {
    if (!loader) {
      loader = document.createElement('div');
      loader.id = 'spa-loader';
      loader.innerHTML = '<div></div>';
      document.body.appendChild(loader);
    }
    loader.style.display = '';
  } else {
    if (loader) loader.style.display = 'none';
  }
};

/**
 * Prefetches a page on hover for instant navigation.
 */
SPA.prefetch = function (link) {
  if (!link || !this.shouldIntercept(link)) return;

  const url = link.href;
  if (this.cache.has(url)) return;

  clearTimeout(this.prefetchTimer);
  this.prefetchTimer = setTimeout(() => {
    this.fetchPage(url, false).catch(() => {});
  }, 150);
};

/**
 * Initializes the SPA router.
 */
SPA.init = function () {
  // ======= Intercept all clicks on anchor tags =======
  document.addEventListener('click', (e) => {
    const link = e.target.closest('a');
    if (!link) return;
    if (!this.shouldIntercept(link)) return;

    e.preventDefault();
    this.renderContent(link.href, true);
  }, true); // Use capture to intercept early

  // ======= Handle browser back/forward =======
  window.addEventListener('popstate', (e) => {
    if (e.state && e.state.path) {
      this.renderContent(e.state.path, false);
    }
  });

  // ======= Prefetch on hover =======
  document.addEventListener('mouseover', (e) => {
    const link = e.target.closest('a');
    if (link) this.prefetch(link);
  }, true);

  // ======= Re-bind after content swap =======
  document.addEventListener('spa:content-updated', () => {
    // Re-run any specific ERP initializations
    if (typeof toggleDropdown === 'function') {
      document.querySelectorAll('.dropdown-toggle').forEach((el) => {
        // Re-attach dropdown toggles if needed
      });
    }
    // Re-init sidebar active states
    const currentPath = window.location.pathname;
    document.querySelectorAll('.sidebar .nav-link, .sidebar .submenu-link').forEach((link) => {
      const href = link.getAttribute('href');
      if (href && href !== '#' && currentPath.startsWith(href)) {
        link.classList.add('active');
      } else {
        link.classList.remove('active');
      }
    });
  });

  // ======= Listen for SPA-navigate custom events (for programmatic nav) =======
  document.addEventListener('spa:navigate', (e) => {
    if (e.detail && e.detail.url) {
      this.renderContent(e.detail.url, true);
    }
  });

  console.log('[SPA Router] initialized');
};

// Auto-initialize
if (document.readyState === 'loading') {
  document.addEventListener('DOMContentLoaded', () => SPA.init());
} else {
  SPA.init();
}

// Expose for debugging
window.SPA = SPA;
