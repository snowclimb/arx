(() => {
  const body = document.body;
  const base = body.dataset.base || './';
  const mobile = document.querySelector('[data-mobile-toggle]');
  const nav = document.querySelector('.main-nav');
  if (mobile && nav) mobile.addEventListener('click', () => nav.classList.toggle('open'));

  // Shared full-text archive search. The index is fetched only when search is actually used.
  const input = document.querySelector('[data-global-search]');
  const results = document.querySelector('[data-search-results]');
  const submit = document.querySelector('[data-search-submit]');
  let indexPromise = null;

  function loadIndex() {
    if (!indexPromise) {
      indexPromise = fetch(base + 'assets/search-index.json', { cache: 'force-cache' })
        .then(r => r.ok ? r.json() : [])
        .catch(() => []);
    }
    return indexPromise;
  }

  function escapeHtml(s) {
    return String(s || '').replace(/[&<>"']/g, c => ({'&':'&amp;','<':'&lt;','>':'&gt;','"':'&quot;',"'":'&#039;'}[c]));
  }
  function escapeRegExp(s) { return String(s).replace(/[.*+?^${}()|[\]\\]/g, '\\$&'); }
  function rootUrl(path) { return new URL(base + path, window.location.href).href; }
  function queryTerms(query) { return query.trim().toLowerCase().split(/\s+/).filter(Boolean); }

  function scoredSearch(items, query) {
    const q = query.trim().toLowerCase();
    const terms = queryTerms(query);
    if (!terms.length) return [];
    return items.map(item => {
      const id = String(item.id || '').toLowerCase();
      const title = String(item.title || '').toLowerCase();
      const summary = String(item.summary || '').toLowerCase();
      const category = String(item.category || '').toLowerCase();
      const type = String(item.type || '').toLowerCase();
      const status = String(item.status || '').toLowerCase();
      const text = String(item.text || '').toLowerCase();
      const hay = `${id} ${title} ${category} ${type} ${status} ${summary} ${text}`;
      if (!terms.every(term => hay.includes(term))) return null;
      let score = 0;
      if (id === q) score += 80;
      if (title === q) score += 70;
      if (title.includes(q)) score += 30;
      if (summary.includes(q)) score += 16;
      for (const term of terms) {
        if (id.includes(term)) score += 18;
        if (title.includes(term)) score += 14;
        if (category.includes(term)) score += 5;
        if (type.includes(term)) score += 4;
        if (summary.includes(term)) score += 7;
        if (text.includes(term)) score += 2;
      }
      return { item, score };
    }).filter(Boolean).sort((a,b) => b.score - a.score || String(a.item.title).localeCompare(String(b.item.title)));
  }

  function highlightText(text, terms) {
    const raw = String(text || '');
    if (!terms.length || !raw) return escapeHtml(raw);
    const re = new RegExp(`(${terms.map(escapeRegExp).join('|')})`, 'ig');
    return raw.split(re).map((part, i) => i % 2 ? `<mark>${escapeHtml(part)}</mark>` : escapeHtml(part)).join('');
  }

  function snippetFor(item, terms) {
    const raw = String(item.text || item.summary || item.title || '').replace(/\s+/g, ' ').trim();
    if (!raw) return '';
    const lower = raw.toLowerCase();
    let hit = -1;
    for (const term of terms) {
      const i = lower.indexOf(term);
      if (i !== -1 && (hit === -1 || i < hit)) hit = i;
    }
    if (hit === -1) hit = 0;
    const start = Math.max(0, hit - 105);
    const end = Math.min(raw.length, hit + 260);
    let snippet = raw.slice(start, end).trim();
    if (start > 0) snippet = `…${snippet}`;
    if (end < raw.length) snippet = `${snippet}…`;
    return highlightText(snippet, terms);
  }

  function goToSearch(query) {
    const q = String(query || '').trim();
    if (!q) return;
    window.location.href = rootUrl(`search/index.html?q=${encodeURIComponent(q)}`);
  }

  function renderDropdown(matches, query) {
    if (!results) return;
    if (!query.trim()) {
      results.classList.remove('open');
      results.innerHTML = '';
      return;
    }
    results.classList.add('open');
    if (!matches.length) {
      results.innerHTML = `<div class="search-empty">No archive pages matched “${escapeHtml(query)}”.<button class="search-all-link" type="button" data-search-all>Search anyway →</button></div>`;
      results.querySelector('[data-search-all]')?.addEventListener('click', () => goToSearch(query));
      return;
    }
    const terms = queryTerms(query);
    const top = matches.slice(0, 8);
    results.innerHTML = top.map(({item}) => {
      const label = item.id ? `${item.id} — ${item.title}` : item.title;
      return `<a class="search-result" href="${rootUrl(item.url)}"><b>${highlightText(label, terms)}</b><span>${escapeHtml(item.category || item.type || '')}${item.summary ? ` · ${escapeHtml(item.summary)}` : ''}</span></a>`;
    }).join('') + `<button class="search-view-all" type="button" data-search-all>View all ${matches.length} result${matches.length === 1 ? '' : 's'} →</button>`;
    results.querySelector('[data-search-all]')?.addEventListener('click', () => goToSearch(query));
  }

  if (input) {
    input.addEventListener('input', async () => renderDropdown(scoredSearch(await loadIndex(), input.value), input.value));
    input.addEventListener('focus', async () => {
      if (input.value.trim()) renderDropdown(scoredSearch(await loadIndex(), input.value), input.value);
    });
    input.addEventListener('keydown', e => {
      if (e.key === 'Enter') {
        e.preventDefault();
        goToSearch(input.value);
      }
      if (e.key === 'Escape') results?.classList.remove('open');
    });
    submit?.addEventListener('click', () => goToSearch(input.value));
    document.addEventListener('click', e => {
      if (!e.target.closest('.header-search')) results?.classList.remove('open');
    });
  }

  // Dedicated search results page.
  const searchPage = document.querySelector('[data-search-page]');
  if (searchPage) {
    const form = searchPage.querySelector('[data-search-page-form]');
    const pageInput = searchPage.querySelector('[data-search-page-input]');
    const pageResults = searchPage.querySelector('[data-search-page-results]');
    const summary = searchPage.querySelector('[data-search-summary]');

    async function renderSearchPage(query, updateUrl = false) {
      const q = String(query || '').trim();
      if (pageInput) pageInput.value = q;
      if (input) input.value = q;
      if (updateUrl) {
        const url = new URL(window.location.href);
        if (q) url.searchParams.set('q', q); else url.searchParams.delete('q');
        history.replaceState({}, '', url);
      }
      if (!q) {
        summary.textContent = 'Enter a search term to find matching archive pages and documents.';
        pageResults.innerHTML = '';
        return;
      }
      summary.textContent = 'Searching…';
      const matches = scoredSearch(await loadIndex(), q);
      const terms = queryTerms(q);
      summary.innerHTML = `<strong>${matches.length}</strong> result${matches.length === 1 ? '' : 's'} for “${escapeHtml(q)}”`;
      if (!matches.length) {
        pageResults.innerHTML = `<div class="search-page-empty">No pages or documents contained all of those search terms.</div>`;
        return;
      }
      pageResults.innerHTML = matches.map(({item}) => {
        const label = item.id ? `${item.id} — ${item.title}` : item.title;
        const meta = [item.category, item.type, item.status].filter(Boolean).join(' · ');
        return `<article class="full-search-result"><a href="${rootUrl(item.url)}"><h2>${highlightText(label, terms)}</h2></a><div class="full-search-meta">${escapeHtml(meta)}</div><p>${snippetFor(item, terms)}</p><a class="full-search-open" href="${rootUrl(item.url)}">Open page →</a></article>`;
      }).join('');
    }

    form?.addEventListener('submit', e => {
      e.preventDefault();
      renderSearchPage(pageInput.value, true);
    });
    const initial = new URLSearchParams(window.location.search).get('q') || '';
    renderSearchPage(initial, false);
  }

  // External document viewers resolve the current hosted file at click time.
  document.querySelectorAll('[data-google-file]').forEach(a => {
    a.addEventListener('click', e => {
      e.preventDefault();
      const abs = new URL(a.dataset.googleFile, window.location.href).href;
      window.open(`https://docs.google.com/gview?embedded=1&url=${encodeURIComponent(abs)}`, '_blank', 'noopener');
    });
  });
  document.querySelectorAll('[data-office-file]').forEach(a => {
    a.addEventListener('click', e => {
      e.preventDefault();
      const abs = new URL(a.dataset.officeFile, window.location.href).href;
      window.open(`https://view.officeapps.live.com/op/view.aspx?src=${encodeURIComponent(abs)}`, '_blank', 'noopener');
    });
  });

  // Catalogue filtering.
  const catalogue = document.querySelector('[data-catalogue]');
  if (catalogue) {
    const rows = [...catalogue.querySelectorAll('[data-doc-row]')];
    const local = document.querySelector('[data-local-search]');
    const tabs = [...document.querySelectorAll('[data-status-tab]')];
    const checks = [...document.querySelectorAll('[data-type-filter]')];
    const sort = document.querySelector('[data-sort]');
    const count = document.querySelector('[data-visible-count]');
    let status = 'all';
    function apply() {
      const q = (local?.value || '').trim().toLowerCase();
      const types = checks.filter(c => c.checked).map(c => c.value.toLowerCase());
      let visible = rows.filter(row => {
        const textOk = !q || row.dataset.search.includes(q);
        const statusOk = status === 'all' || row.dataset.status === status;
        const typeOk = !types.length || types.includes(row.dataset.type);
        return textOk && statusOk && typeOk;
      });
      rows.forEach(r => r.style.display = 'none');
      if (sort) {
        const dir = sort.value;
        visible.sort((a,b) => {
          const ad = a.dataset.date || '';
          const bd = b.dataset.date || '';
          if (dir === 'oldest') return ad.localeCompare(bd);
          if (dir === 'title') return a.dataset.title.localeCompare(b.dataset.title);
          if (dir === 'id') return a.dataset.id.localeCompare(b.dataset.id);
          return bd.localeCompare(ad);
        });
      }
      visible.forEach(r => { r.style.display = 'grid'; catalogue.appendChild(r); });
      if (count) count.textContent = visible.length;
      const empty = document.querySelector('[data-empty-state]');
      if (empty) empty.style.display = visible.length ? 'none' : 'block';
    }
    local?.addEventListener('input', apply);
    tabs.forEach(tab => tab.addEventListener('click', () => {
      status = tab.dataset.statusTab;
      tabs.forEach(t => t.classList.toggle('active', t === tab));
      apply();
    }));
    checks.forEach(c => c.addEventListener('change', apply));
    sort?.addEventListener('change', apply);
    apply();
  }
})();
