const MotionController = (() => {
  'use strict';

  /* ──────── Internal state ─────────────────── */
  let _prefersReduced = false;
  let _isMobile = false;
  let _observers = [];
  let _initialized = false;

  /* ──────── Helpers ─────────────────────── */
  function clamp(v, lo, hi) { return Math.max(lo, Math.min(hi, v)); }
  function lerp(a, b, t)    { return a + (b - a) * t; }
  function easeOutCubic(t)  { return 1 - Math.pow(1 - t, 3); }
  function easeOutElastic(t) {
    const c4 = (2 * Math.PI) / 3;
    return t === 0 ? 0 : t === 1 ? 1 :
      Math.pow(2, -10 * t) * Math.sin((t * 10 - 0.75) * c4) + 1;
  }
  function themeColor(varName, fallback) {
    const v = getComputedStyle(document.documentElement).getPropertyValue(varName).trim();
    return v || fallback;
  }

  /* ──────── Theme Persistence ─────────────────── */
  function initTheme() {
    const html  = document.documentElement;
    const saved = localStorage.getItem('theme');
    if (saved) {
      html.setAttribute('data-theme', saved);
    } else {
      const prefersDark = window.matchMedia('(prefers-color-scheme: dark)').matches;
      html.setAttribute('data-theme', prefersDark ? 'dark' : 'light');
    }

    function setTheme(isDark) {
      const theme = isDark ? 'dark' : 'light';
      html.setAttribute('data-theme', theme);
      localStorage.setItem('theme', theme);

      const moon = document.getElementById('themeIconMoon');
      const sun = document.getElementById('themeIconSun');
      if (moon && sun) {
        moon.style.display = isDark ? 'inline-block' : 'none';
        sun.style.display  = isDark ? 'none' : 'inline-block';
      }

      // Legacy support for <img>-based toggles, if any template still uses one
      const moonSrc = '/static/images/icons/moon.svg';
      const sunSrc  = '/static/images/icons/sun.svg';
      const iconSrc  = isDark ? moonSrc : sunSrc;
      document.querySelectorAll('[data-theme-icon]').forEach(img => { img.src = iconSrc; });

      _triggerThemeReveal();
    }

    const isDark = html.getAttribute('data-theme') !== 'light';
    const moon = document.getElementById('themeIconMoon');
    const sun = document.getElementById('themeIconSun');
    if (moon && sun) {
      moon.style.display = isDark ? 'inline-block' : 'none';
      sun.style.display  = isDark ? 'none' : 'inline-block';
    }

    function _triggerThemeReveal() {
      if (_prefersReduced) return;
      const reveal = document.getElementById('lmThemeReveal');
      if (!reveal) return;
      reveal.classList.remove('lm-reveal-active');
      void reveal.offsetWidth; // force reflow so the next class-add re-triggers the transition
      reveal.classList.add('lm-reveal-active');
      setTimeout(() => reveal.classList.remove('lm-reveal-active'), 700);
    }

    function toggleTheme() {
      const isDark = html.getAttribute('data-theme') !== 'dark';
      setTheme(isDark);
    }

    // Single binding site for every [data-action="toggle-theme"] button on
    // the page (desktop icon + mobile menu button both use this attribute).
    document.querySelectorAll('[data-action="toggle-theme"]').forEach(btn => {
      if (btn.dataset.themeInit) return;
      btn.dataset.themeInit = '1';
      btn.addEventListener('click', toggleTheme);
    });
  }

  /* ──────── Scroll Reveal (reveal-liquid, fade-up, stagger) */
  function initScrollReveal() {
    const items = document.querySelectorAll(
      '[data-motion="reveal-liquid"], [data-motion="fade-up"], [data-motion="stagger"]'
    );
    if (items.length) {
      const obs = new IntersectionObserver((entries) => {
        entries.forEach(e => {
          if (e.isIntersecting) {
            const delay = e.target.getAttribute('data-motion-delay');
            if (delay) e.target.style.transitionDelay = delay;
            e.target.classList.add('lm-visible');
            obs.unobserve(e.target);
          }
        });
      }, { threshold: 0.08 });
      items.forEach(el => obs.observe(el));
      _observers.push(obs);
    }

    // Backward-compat with the old .animate-on-scroll class
    const legacy = document.querySelectorAll('.animate-on-scroll:not(.visible)');
    if (legacy.length) {
      const legacyObs = new IntersectionObserver((entries) => {
        entries.forEach(e => {
          if (e.isIntersecting) {
            e.target.classList.add('visible');
            legacyObs.unobserve(e.target);
          }
        });
      }, { threshold: 0.08 });
      legacy.forEach(el => legacyObs.observe(el));
      _observers.push(legacyObs);
    }
  }

  /* ──────── Stat Count-Up with Liquid Fill ──── */
  function initCounters() {
    const items = document.querySelectorAll('[data-motion="count-up"]');
    if (!items.length) {
      _initLegacyCounters();
      return;
    }

    const obs = new IntersectionObserver((entries) => {
      entries.forEach(e => {
        if (!e.isIntersecting) return;
        _runCounter(e.target);
        obs.unobserve(e.target);
      });
    }, { threshold: 0.5 });

    items.forEach(el => obs.observe(el));
    _observers.push(obs);
  }

  function _initLegacyCounters() {
    const obs = new IntersectionObserver((entries) => {
      entries.forEach(e => {
        if (!e.isIntersecting) return;
        const numEl = e.target.querySelector('.stat-num');
        if (!numEl) return;
        const target = parseInt(e.target.dataset.count, 10) || 0;
        _animateNumber(numEl, 0, target, 1200, easeOutCubic);
        const iconWrap = e.target.querySelector('.stat-icon-wrap');
        if (iconWrap) {
          iconWrap.style.transition = `transform 0.4s var(--ease-liquid), box-shadow 0.6s var(--ease-liquid)`;
          iconWrap.style.transform = 'scale(1.15)';
          iconWrap.style.boxShadow = `0 0 18px color-mix(in srgb, var(--c, var(--brand-accent)) 40%, transparent)`;
          setTimeout(() => {
            iconWrap.style.transform = 'scale(1)';
            iconWrap.style.boxShadow = '';
          }, 600);
        }
        e.target.classList.add('lm-counted');
        obs.unobserve(e.target);
      });
    }, { threshold: 0.5 });

    document.querySelectorAll('.stat-item[data-count]').forEach(el => obs.observe(el));
    _observers.push(obs);
  }

  function _runCounter(el) {
    const numEl = el.querySelector('.lm-count-num, .stat-num, [data-count-display]');
    if (!numEl) return;
    const target = parseInt(el.dataset.count, 10) || 0;
    const fill = el.querySelector('.lm-count-fill');
    const colorKey = el.dataset.motionColor || 'default';
    const color = (typeof ICON_COLORS !== 'undefined' && typeof iconColor === 'function') ? iconColor(colorKey) : '#7C3AED';

    if (fill) fill.style.background = color;

    _animateNumber(numEl, 0, target, 1200, easeOutCubic, () => {
      el.classList.add('lm-counted');
    });
  }

  function _animateNumber(el, from, to, duration, easeFn, onComplete) {
    if (_prefersReduced) { el.textContent = to; if (onComplete) onComplete(); return; }
    const start = performance.now();
    function step(now) {
      const progress = clamp((now - start) / duration, 0, 1);
      el.textContent  = Math.round(easeFn(progress) * (to - from) + from);
      if (progress < 1) {
        requestAnimationFrame(step);
      } else {
        el.textContent = to;
        if (onComplete) onComplete();
      }
    }
    requestAnimationFrame(step);
  }

  /* ─────── Progress bars ────────────────────── */
  function initProgressBars() {
    const bars = document.querySelectorAll('[data-motion="progress-liquid"]');
    if (!bars.length) return;

    const obs = new IntersectionObserver((entries) => {
      entries.forEach(e => {
        if (!e.isIntersecting) return;
        const el = e.target;
        const value = parseFloat(el.dataset.value) || 0;
        const track = el.querySelector('.lm-progress-track');
        if (track) track.style.width = value + '%';
        obs.unobserve(el);
      });
    }, { threshold: 0.3 });

    bars.forEach(el => obs.observe(el));
    _observers.push(obs);
  }

  /* ──────── Button Liquid Ripple ────────────── */
  function initRipple() {
    document.querySelectorAll('.lm-ripple-host, .btn').forEach(btn => {
      if (btn.dataset.rippleInit) return;
      btn.dataset.rippleInit = '1';
      btn.addEventListener('pointerdown', e => {
        if (_prefersReduced) return;
        const rect = btn.getBoundingClientRect();
        const size = Math.max(rect.width, rect.height) * 2;
        const ripple = document.createElement('span');
        ripple.className = 'lm-ripple';
        ripple.style.cssText = `
          width: ${size}px; height: ${size}px;
          left: ${e.clientX - rect.left - size / 2}px;
          top:  ${e.clientY - rect.top  - size / 2}px;
        `;
        btn.appendChild(ripple);
        ripple.addEventListener('animationend', () => ripple.remove());
      });
      if (!btn.classList.contains('lm-ripple-host')) {
        btn.classList.add('lm-ripple-host');
      }
    });
  }

  /* ──────── Page Wipe Transition ────────────── */
  function initPageWipe() {
    const wipe = document.getElementById('lmPageWipe');
    if (!wipe || _prefersReduced) return;

    document.querySelectorAll('[data-motion="page-wipe"]').forEach(el => {
      if (el.dataset.wipeInit) return;
      el.dataset.wipeInit = '1';
      el.addEventListener('click', e => {
        const href = el.getAttribute('href');
        if (!href || href.startsWith('#') || href.startsWith('javascript')) return;
        e.preventDefault();
        wipe.classList.add('lm-wipe-active');
        setTimeout(() => { window.location.href = href; }, 300);
      });
    });
  }

  /* ──────── Card Tilt ────────────────────────── */
  function initTilt() {
    if (_isMobile || _prefersReduced) return;
    const selector = '.project-card, .dashboard-card, .research-card, .insight-card, .explore-card, .cert-card, .outcome-card';
    document.querySelectorAll(selector).forEach(card => {
      if (card.dataset.tiltInit) return;
      card.dataset.tiltInit = '1';

      card.addEventListener('mousemove', e => {
        const rect = card.getBoundingClientRect();
        const x = (e.clientX - rect.left) / rect.width  - 0.5;
        const y = (e.clientY - rect.top)  / rect.height - 0.5;
        card.style.transform = `translateY(-6px) rotateX(${-y * 6}deg) rotateY(${x * 6}deg)`;
      });
      card.addEventListener('mouseenter', () => {
        card.style.transition = 'transform 0.1s ease';
      });
      card.addEventListener('mouseleave', () => {
        card.style.transform  = '';
        card.style.transition = 'transform 0.5s var(--ease-liquid)';
      });
    });
  }

  /* ────────Magnetic buttons ─────────────────── */
  function initMagnetic() {
    if (_prefersReduced) return;
    document.querySelectorAll('.magnetic').forEach(btn => {
      if (btn.dataset.magneticInit) return;
      btn.dataset.magneticInit = '1';
      let raf = null;
      btn.addEventListener('mousemove', e => {
        const rect = btn.getBoundingClientRect();
        const x = e.clientX - rect.left - rect.width / 2;
        const y = e.clientY - rect.top - rect.height / 2;
        if (raf) cancelAnimationFrame(raf);
        raf = requestAnimationFrame(() => {
          btn.style.transform = `translate(${x * 0.18}px, ${y * 0.3}px)`;
        });
      });
      btn.addEventListener('mouseleave', () => {
        if (raf) cancelAnimationFrame(raf);
        btn.style.transform = 'translate(0, 0)';
      });
    });
  }

  /* ─────── Navbar (scroll shadow, mobile menu, active link) ── */
  function initNavbar() {
    const navbar       = document.getElementById('navbar');
    const hamburger    = document.getElementById('hamburger');
    const mobileMenu   = document.getElementById('mobileMenu');
    const backdrop     = document.getElementById('menuBackdrop');
    const navLinksList = document.getElementById('navLinks');
    const navIndicator = document.getElementById('navIndicator');
    if (!navbar) return;

    window.addEventListener('scroll', () => {
      navbar.classList.toggle('scrolled', window.scrollY > 20);
    }, { passive: true });

    if (hamburger && mobileMenu) {
      const closeMobileMenu = () => {
        mobileMenu.classList.remove('open');
        hamburger.classList.remove('open');
        hamburger.setAttribute('aria-expanded', 'false');
        if (backdrop) backdrop.classList.remove('open');
        document.body.classList.remove('lm-menu-open');
      };
      const openMobileMenu = () => {
        mobileMenu.classList.add('open');
        hamburger.classList.add('open');
        hamburger.setAttribute('aria-expanded', 'true');
        if (backdrop) backdrop.classList.add('open');
        document.body.classList.add('lm-menu-open');
        if (!_prefersReduced) {
          const firstLink = mobileMenu.querySelector('.nav-link');
          if (firstLink) setTimeout(() => firstLink.focus(), 320);
        }
      };

      hamburger.addEventListener('click', () => {
        const isOpen = mobileMenu.classList.contains('open');
        isOpen ? closeMobileMenu() : openMobileMenu();
      });
      document.querySelectorAll('.mobile-nav-links .nav-link').forEach(l => {
        l.addEventListener('click', closeMobileMenu);
      });
      if (backdrop) backdrop.addEventListener('click', closeMobileMenu);
      document.addEventListener('click', e => {
        if (mobileMenu.classList.contains('open') && !navbar.contains(e.target)) closeMobileMenu();
      });
      document.addEventListener('keydown', e => {
        if (e.key === 'Escape' && mobileMenu.classList.contains('open')) {
          closeMobileMenu();
          hamburger.focus();
        }
      });
      // Rotating a tablet or resizing past the breakpoint used to leave
      // the menu stuck open with no way to close it.
      let resizeTimer;
      window.addEventListener('resize', () => {
        clearTimeout(resizeTimer);
        resizeTimer = setTimeout(() => {
          if (window.innerWidth > 900) closeMobileMenu();
        }, 150);
      }, { passive: true });
    }

    // Active link (desktop + mobile share the .nav-link class)
    const currentPath = window.location.pathname;
    let activeDesktopLink = null;
    document.querySelectorAll('.nav-link').forEach(l => {
      const href = l.getAttribute('href');
      if (!href) return;
      const isActive = href !== '/' ? currentPath.startsWith(href) : currentPath === '/';
      l.classList.toggle('active', isActive);
      if (isActive && navLinksList && navLinksList.contains(l)) activeDesktopLink = l;
    });

    // Sliding indicator under the active/hovered desktop link
    if (navLinksList && navIndicator) {
      const placeIndicator = (el) => {
        if (!el) { navIndicator.classList.remove('active'); return; }
        const linkRect = el.getBoundingClientRect();
        const listRect = navLinksList.getBoundingClientRect();
        navIndicator.style.width = linkRect.width + 'px';
        navIndicator.style.transform = `translateX(${linkRect.left - listRect.left}px)`;
        navIndicator.classList.add('active');
      };
      navLinksList.querySelectorAll('.nav-link').forEach(link => {
        link.addEventListener('mouseenter', () => placeIndicator(link));
      });
      navLinksList.addEventListener('mouseleave', () => placeIndicator(activeDesktopLink));
      if (document.readyState === 'complete') {
        placeIndicator(activeDesktopLink);
      } else {
        window.addEventListener('load', () => placeIndicator(activeDesktopLink));
      }
    }
  }

  /* ──────── Search ────────────── */
  function initSearch() {
    const btn     = document.getElementById('searchBtn');
    const overlay = document.getElementById('searchOverlay');
    const close   = document.getElementById('searchClose');
    const input   = document.getElementById('searchInput');
    const results = document.getElementById('searchResults');
    if (!btn || !overlay) return;

    let currentMatches = [];
    let activeIndex = -1;
    let fetchToken = 0; // guards against a slow, older request overwriting a newer one

    btn.addEventListener('click', () => {
      overlay.classList.add('open');
      input && input.focus();
    });
    close && close.addEventListener('click', closeSearch);
    document.addEventListener('keydown', e => {
      if (e.key === 'Escape' && overlay.classList.contains('open')) closeSearch();
    });
    document.addEventListener('click', e => {
      if (overlay.classList.contains('open') && !overlay.contains(e.target) && e.target !== btn && !btn.contains(e.target)) {
        closeSearch();
      }
    });

    function closeSearch() {
      overlay.classList.remove('open');
      if (input) { input.value = ''; input.setAttribute('aria-expanded', 'false'); }
      currentMatches = [];
      activeIndex = -1;
      renderResults([]);
    }

    let debounceTimer;
    input && input.addEventListener('input', () => {
      clearTimeout(debounceTimer);
      debounceTimer = setTimeout(runSearch, 220);
    });

    input && input.addEventListener('keydown', e => {
      if (!currentMatches.length) return;
      if (e.key === 'ArrowDown') { e.preventDefault(); moveActive(1); }
      else if (e.key === 'ArrowUp') { e.preventDefault(); moveActive(-1); }
      else if (e.key === 'Enter') {
        e.preventDefault();
        const target = currentMatches[activeIndex] || currentMatches[0];
        if (target && target.url) window.location.href = target.url;
      }
    });

    function moveActive(delta) {
      if (!results) return;
      activeIndex = (activeIndex + delta + currentMatches.length) % currentMatches.length;
      Array.prototype.forEach.call(results.children, (el, i) => el.classList.toggle('lm-active', i === activeIndex));
      const activeEl = results.children[activeIndex];
      if (activeEl) activeEl.scrollIntoView({ block: 'nearest' });
    }

    function runSearch() {
      const q = input.value.trim();
      input.setAttribute('aria-expanded', q ? 'true' : 'false');

      if (q.length < 2) {
        currentMatches = [];
        activeIndex = -1;
        renderResults([]);
        return;
      }

      const scope = document.body.dataset.searchScope || 'all';
      const token = ++fetchToken;
      fetch(`/search/?q=${encodeURIComponent(q)}&scope=${encodeURIComponent(scope)}`)
        .then(res => res.json())
        .then(data => {
          if (token !== fetchToken) return; // a newer keystroke already superseded this
          currentMatches = (data.results || []).map(item => ({
            title: item.title, type: item.type, url: item.url, excerpt: item.meta,
          }));
          activeIndex = -1;
          renderResults(currentMatches, q);
        })
        .catch(() => {
          if (token !== fetchToken) return;
          currentMatches = [];
          renderResults([]);
        });
    }

    function escapeHtml(str) {
      const div = document.createElement('div');
      div.textContent = str == null ? '' : String(str);
      return div.innerHTML;
    }

    function highlight(safeText, q) {
      if (!q) return safeText;
      const idx = safeText.toLowerCase().indexOf(q.toLowerCase());
      if (idx === -1) return safeText;
      return safeText.slice(0, idx) + '<mark>' + safeText.slice(idx, idx + q.length) + '</mark>' + safeText.slice(idx + q.length);
    }

    function renderResults(matches, q) {
      if (!results) return;
      results.innerHTML = '';

      if (!matches.length) {
        if (input && input.value.trim() && index.length) {
          const li = document.createElement('li');
          li.className = 'search-empty-state';
          li.textContent = `No results for "${input.value.trim()}"`;
          results.appendChild(li);
          results.classList.add('has-content');
        } else {
          results.classList.remove('has-content');
        }
        return;
      }

      results.classList.add('has-content');
      matches.forEach(item => {
        const li = document.createElement('li');
        li.className = 'search-result-item';
        li.setAttribute('role', 'option');
        const typeKey = (item.type || '').toLowerCase();
        const color = (typeof ICON_COLORS !== 'undefined' && typeof iconColor === 'function') ? iconColor(typeKey) : '';
        if (color) li.style.setProperty('--result-color', color);

        const iconEl = document.createElement('span');
        iconEl.className = 'search-result-icon';
        if (item.image) {
          const img = document.createElement('img');
          img.src = item.image; img.alt = ''; img.loading = 'lazy';
          iconEl.appendChild(img);
        } else {
          iconEl.textContent = (item.title || '?').trim().charAt(0).toUpperCase();
        }

        const textEl = document.createElement('span');
        textEl.className = 'search-result-text';
        const titleEl = document.createElement('span');
        titleEl.className = 'search-result-title';
        titleEl.innerHTML = highlight(escapeHtml(item.title || ''), q || '');
        const metaEl = document.createElement('span');
        metaEl.className = 'search-result-meta';
        metaEl.textContent = [item.type, item.excerpt].filter(Boolean).join(' · ');
        textEl.appendChild(titleEl);
        textEl.appendChild(metaEl);

        li.appendChild(iconEl);
        li.appendChild(textEl);
        li.addEventListener('click', () => { if (item.url) window.location.href = item.url; });
        results.appendChild(li);
      });
    }

    function resetFilter() {
      document.querySelectorAll('.project-card, .insight-card, .research-card, .dashboard-card').forEach(card => {
        card.style.opacity = ''; card.style.transform = '';
      });
    }
  }

  /* ──────── Typing Effect ───────────────────── */
  function initTyping() {
    const el = document.getElementById('typedText');
    if (!el || _prefersReduced) return;
    const words   = ['Insights.', 'Intelligence.', 'Decisions.', 'Innovation.', 'Value.'];
    let wIdx = 0, cIdx = 0, deleting = false;

    function tick() {
      const word = words[wIdx];
      if (!deleting) {
        el.textContent = word.slice(0, ++cIdx);
        if (cIdx === word.length) { deleting = true; setTimeout(tick, 2000); return; }
      } else {
        el.textContent = word.slice(0, --cIdx);
        if (cIdx === 0) { deleting = false; wIdx = (wIdx + 1) % words.length; }
      }
      setTimeout(tick, deleting ? 55 : 95);
    }
    tick();
  }

  /* ────────  Network canvases (hero + section connectors) ─── */
  function initNetworkCanvases() {
    if (_prefersReduced) return;
    const canvases = document.querySelectorAll('#particleCanvas, [data-motion-network]');
    if (!canvases.length) return;

    canvases.forEach(canvas => {
      if (canvas.dataset.networkInit) return;
      canvas.dataset.networkInit = '1';

      const ctx = canvas.getContext('2d');
      const COUNT     = parseInt(canvas.dataset.density, 10) || (_isMobile ? 35 : 80);
      const GLITTER   = _isMobile ? 16 : 45;
      const COLORS    = [
        themeColor('--brand-accent', '#7c3aed'),
        themeColor('--brand-blue', '#3b5bfd'),
        themeColor('--brand-emerald', '#10b981'),
      ];
      const GLITTER_C = [
        themeColor('--brand-accent-light', '#a78bfa'),
        themeColor('--brand-cyan', '#60a5fa'),
        themeColor('--brand-emerald', '#34d399'),
        themeColor('--brand-amber', '#fbbf24'),
        themeColor('--brand-pink', '#f472b6'),
      ];
      const lineColor = themeColor('--brand-accent', '#7c3aed');

      let W, H, particles, glitters, rafId, isVisible = true;
      const mouse = { x: -999, y: -999 };

      function resize() {
        W = canvas.width  = canvas.offsetWidth;
        H = canvas.height = canvas.offsetHeight;
      }
      function mk() {
        particles = Array.from({ length: COUNT }, () => ({
          x: Math.random() * W, y: Math.random() * H,
          r: Math.random() * 1.8 + 0.4,
          dx: (Math.random() - 0.5) * 0.5,
          dy: (Math.random() - 0.5) * 0.5,
          opacity: Math.random() * 0.55 + 0.1,
          color: COLORS[Math.floor(Math.random() * COLORS.length)],
        }));
        glitters = Array.from({ length: GLITTER }, () => ({
          x: Math.random() * W, y: Math.random() * H,
          size: Math.random() * 3 + 1,
          life: Math.random() * Math.PI * 2,
          speed: Math.random() * 0.04 + 0.01,
          maxSize: Math.random() * 4 + 2,
          color: GLITTER_C[Math.floor(Math.random() * GLITTER_C.length)],
        }));
      }
      function draw() {
        ctx.clearRect(0, 0, W, H);
        for (let i = 0; i < particles.length; i++) {
          for (let j = i + 1; j < particles.length; j++) {
            const d = Math.hypot(particles[i].x - particles[j].x, particles[i].y - particles[j].y);
            if (d < 120) {
              ctx.beginPath();
              ctx.moveTo(particles[i].x, particles[i].y);
              ctx.lineTo(particles[j].x, particles[j].y);
              ctx.strokeStyle = lineColor;
              ctx.globalAlpha = 0.12 * (1 - d / 120);
              ctx.lineWidth = 0.6;
              ctx.stroke();
              ctx.globalAlpha = 1;
            }
          }
        }
        particles.forEach(p => {
          ctx.beginPath();
          ctx.arc(p.x, p.y, p.r, 0, Math.PI * 2);
          ctx.fillStyle = p.color;
          ctx.globalAlpha = p.opacity;
          ctx.fill();
          ctx.globalAlpha = 1;
          const dx = mouse.x - p.x, dy = mouse.y - p.y;
          if (Math.hypot(dx, dy) < 120) { p.x -= dx * 0.02; p.y -= dy * 0.02; }
          p.x += p.dx; p.y += p.dy;
          if (p.x < 0 || p.x > W) p.dx *= -1;
          if (p.y < 0 || p.y > H) p.dy *= -1;
        });
        glitters.forEach(g => {
          g.life += g.speed;
          const pulse   = (Math.sin(g.life) + 1) / 2;
          const size    = g.size + pulse * g.maxSize;
          const opacity = pulse * 0.85;
          if (opacity > 0.05) {
            ctx.save();
            ctx.globalAlpha = opacity * 0.5;
            const grd = ctx.createRadialGradient(g.x, g.y, 0, g.x, g.y, size * 2.5);
            grd.addColorStop(0, g.color);
            grd.addColorStop(1, 'transparent');
            ctx.fillStyle = grd;
            ctx.beginPath();
            ctx.arc(g.x, g.y, size * 2.5, 0, Math.PI * 2);
            ctx.fill();
            ctx.restore();
            ctx.save();
            ctx.globalAlpha = opacity;
            ctx.strokeStyle = g.color;
            ctx.lineWidth = 1;
            ctx.beginPath();
            ctx.moveTo(g.x - size, g.y); ctx.lineTo(g.x + size, g.y);
            ctx.moveTo(g.x, g.y - size); ctx.lineTo(g.x, g.y + size);
            ctx.stroke();
            ctx.restore();
          }
        });
        ctx.globalAlpha = 1;
        if (isVisible) rafId = requestAnimationFrame(draw);
      }

      resize(); mk(); draw();
      window.addEventListener('resize', () => { resize(); mk(); }, { passive: true });
      canvas.addEventListener('mousemove', e => {
        const rect = canvas.getBoundingClientRect();
        mouse.x = e.clientX - rect.left;
        mouse.y = e.clientY - rect.top;
      }, { passive: true });

      const io = new IntersectionObserver(entries => {
        entries.forEach(entry => {
          isVisible = entry.isIntersecting && !document.hidden;
          if (isVisible) { cancelAnimationFrame(rafId); rafId = requestAnimationFrame(draw); }
          else cancelAnimationFrame(rafId);
        });
      }, { threshold: 0 });
      io.observe(canvas);
      _observers.push(io);

      document.addEventListener('visibilitychange', () => {
        if (document.hidden) { cancelAnimationFrame(rafId); }
        else if (isVisible) { rafId = requestAnimationFrame(draw); }
      });
    });
  }

  /* ──  Smooth Scroll ─── */
  function initSmoothScroll() {
    document.querySelectorAll('a[href^="#"]').forEach(a => {
      if (a.dataset.smoothInit) return;
      a.dataset.smoothInit = '1';
      a.addEventListener('click', e => {
        const href = a.getAttribute('href');
        if (href === '#') return;
        const target = document.querySelector(href);
        if (target) { e.preventDefault(); target.scrollIntoView({ behavior: 'smooth', block: 'start' }); }
      });
    });
  }

  /* ──── Icon color application ────── */
  function applyIconColors() {
    if (typeof ICON_COLORS === 'undefined' || typeof iconColor !== 'function') return;
    document.querySelectorAll('[data-icon-category]').forEach(el => {
      const key   = el.dataset.iconCategory;
      const color = iconColor(key);
      el.style.setProperty('--icon-color', color);
    });
    document.querySelectorAll('.lm-icon--colored').forEach(icon => {
      const color = getComputedStyle(icon).getPropertyValue('--icon-color').trim();
      if (color) icon.style.color = color;
    });
  }

  /* ────────  Download Toast ──────────────── */
  function initDownloadToast() {
    document.querySelectorAll('a[download]').forEach(a => {
      if (a.dataset.toastInit) return;
      a.dataset.toastInit = '1';
      a.addEventListener('click', () => {
        // Fire server-side tracking ping if a track URL is provided
        const trackUrl = a.dataset.trackUrl;
        if (trackUrl) {
          fetch(trackUrl, { method: 'GET', keepalive: true }).catch(() => {});
        }

        if (_prefersReduced) return;
        let toast = document.getElementById('lmDownloadToast');
        const label = a.dataset.downloadLabel || 'File';
        if (!toast) {
          toast = document.createElement('div');
          toast.id = 'lmDownloadToast';
          toast.className = 'lm-download-toast';
          document.body.appendChild(toast);
        }
        toast.innerHTML = `
          <div class="lm-toast-progress" id="lmToastProgress"></div>
          <div>
            <div style="font-weight:600;margin-bottom:2px">Downloading ${label}</div>
            <div style="font-size:0.8rem;color:var(--text-dim)">Preparing secure PDF...</div>
          </div>
        `;

        const progress = document.getElementById('lmToastProgress');
        progress.classList.remove('lm-toast-done');

        void toast.offsetWidth;
        toast.classList.add('lm-toast-visible');

        setTimeout(() => {
          progress.classList.add('lm-toast-done');
          toast.querySelector('div > div:nth-child(2)').textContent = 'Download Complete ✓';
          setTimeout(() => { toast.classList.remove('lm-toast-visible'); }, 3000);
        }, 1500);
      });
    });
  }

  /* ────── Subscribe Form ────────────────────── */
  const EMAIL_RE = /^[^\s@]+@[^\s@]+\.[a-zA-Z]{2,}$/;

  function _validateEmail(value) {
    const v = (value || '').trim();
    if (!v) return 'Enter your email to subscribe.';
    if (!EMAIL_RE.test(v)) return 'Enter a valid email address (e.g. name@example.com).';
    return null;
  }

  function initSubscribeForm() {
    document.querySelectorAll('form[action*="subscribe"]').forEach(form => {
      if (form.dataset.subscribeInit) return;
      form.dataset.subscribeInit = '1';

      const input = form.querySelector('input[type="email"], .subscribe-input');
      const error = form.querySelector('.field-error');
      const btn   = form.querySelector('button[type="submit"]');
      const originalBtnHTML = btn ? btn.innerHTML : '';

      function showError(msg) {
        if (input) { input.classList.add('lm-invalid'); input.classList.remove('lm-valid'); }
        if (error) { error.textContent = msg; error.classList.add('visible'); }
      }
      function clearError() {
        if (input) input.classList.remove('lm-invalid');
        if (error) error.classList.remove('visible');
      }

      input && input.addEventListener('input', () => {
        if (!input.value.trim()) { clearError(); return; }
        const msg = _validateEmail(input.value);
        if (msg) { showError(msg); } else { clearError(); input.classList.add('lm-valid'); }
      });

      form.addEventListener('submit', e => {
        const msg = input ? _validateEmail(input.value) : null;
        if (msg) {
          e.preventDefault();
          showError(msg);
          input && input.focus();
          return;
        }
        clearError();
        if (btn && !_prefersReduced) {
          btn.innerHTML = `<span class="lm-subscribe-ok">
            <svg width="16" height="16" viewBox="0 0 24 24" fill="none" stroke="currentColor" stroke-width="3" stroke-linecap="round" stroke-linejoin="round"><polyline points="20 6 9 17 4 12"></polyline></svg>
            Done
          </span>`;
          btn.style.width = btn.offsetWidth + 'px';
          btn.classList.add('lm-success');
          setTimeout(() => {
            btn.innerHTML = originalBtnHTML;
            btn.classList.remove('lm-success');
            btn.style.width = '';
          }, 9000);
        }
      });
    });
  }

  /* ──────── Liquid Blob Background ──────────── */
  function initLiquidBlobs() {
    if (_prefersReduced) return;
    if (document.querySelector('.lm-goo-host')) return;

    const host = document.createElement('div');
    host.className = 'lm-goo-host';
    host.setAttribute('aria-hidden', 'true');
    document.body.insertBefore(host, document.body.firstChild);

    const palette = ['var(--orb-1)', 'var(--orb-2)', 'var(--orb-3)', 'var(--orb-4)'];
    const count = _isMobile ? 3 : 5;

    for (let i = 0; i < count; i++) {
      const blob = document.createElement('div');
      blob.className = 'liquid-blob';
      const size     = _isMobile ? (180 + Math.random() * 140) : (280 + Math.random() * 260);
      const top      = Math.random() * 85;
      const left     = Math.random() * 85;
      const duration = 16 + Math.random() * 12;
      const delay    = -(Math.random() * duration);
      blob.style.cssText = `width:${size}px;height:${size}px;top:${top}%;left:${left}%;` +
        `background:${palette[i % palette.length]};` +
        `animation:lm-orb-drift ${duration}s ease-in-out infinite ${delay}s;`;
      host.appendChild(blob);
    }
  }

  /* ──────── First-time-visitor "best on desktop" notice ────── */
  const DESKTOP_NOTICE_KEY = 'lm_desktop_notice_seen';

  function initDesktopNotice() {
    const notice = document.getElementById('lmDesktopNotice');
    if (!notice || !_isMobile) return;

    let seen;
    try { seen = localStorage.getItem(DESKTOP_NOTICE_KEY); } catch (e) { seen = null; }
    if (seen) return;

    const closeBtn = document.getElementById('lmDesktopNoticeClose');

    function dismiss() {
      notice.classList.remove('lm-visible');
      notice.classList.add('lm-leaving');
      setTimeout(() => notice.remove(), 450);
    }

    setTimeout(() => {
      notice.classList.add('lm-visible');
      // Mark as seen once shown, not only on dismiss — otherwise
      // navigating to another page before the auto-hide fires would
      // show it again on every page of the first visit.
      try { localStorage.setItem(DESKTOP_NOTICE_KEY, '1'); } catch (e) { /* ignore */ }
    }, 900);

    setTimeout(dismiss, 9000);
    closeBtn && closeBtn.addEventListener('click', dismiss);
  }

  /* ────────Public API ──────────── */
  function init() {
    // Guards against the script (or MotionController.init()) ever running
    // twice on the same page — a common source of animations/counters/toasts
    // silently double-firing or a feature "working, then breaking".
    if (_initialized) return;
    _initialized = true;

    _prefersReduced = window.matchMedia('(prefers-reduced-motion: reduce)').matches;
    _isMobile       = window.innerWidth <= 768;

    initTheme();
    initNavbar();
    initLiquidBlobs();
    initScrollReveal();
    initCounters();
    initProgressBars();
    initRipple();
    initMagnetic();
    initPageWipe();
    initSearch();
    initTyping();
    initNetworkCanvases();
    initSmoothScroll();
    applyIconColors();
    initDownloadToast();
    initSubscribeForm();
    initDesktopNotice();
    setTimeout(initTilt, 300);
  }

  function refresh() {
    if (!_initialized) { init(); return; }
    initScrollReveal();
    initCounters();
    initProgressBars();
    initRipple();
    initMagnetic();
    initPageWipe();
    applyIconColors();
    initSubscribeForm();
    initTilt();
  }

  return { init, refresh, initTilt, initRipple, initMagnetic, applyIconColors };
})();

document.addEventListener('DOMContentLoaded', () => MotionController.init());