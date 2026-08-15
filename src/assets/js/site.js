(() => {
  const body = document.body;
  const base = body.dataset.base || './';
  const mobile = document.querySelector('[data-mobile-toggle]');
  const nav = document.querySelector('.main-nav');
  if (mobile && nav) mobile.addEventListener('click', () => nav.classList.toggle('open'));

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
        if (status.includes(term)) score += 3;
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
    if (!query.trim()) { results.classList.remove('open'); results.innerHTML = ''; return; }
    results.classList.add('open');
    if (!matches.length) {
      results.innerHTML = `<div class="search-empty">No archive pages matched “${escapeHtml(query)}”.<button class="search-all-link" type="button" data-search-all>Search anyway →</button></div>`;
      results.querySelector('[data-search-all]')?.addEventListener('click', () => goToSearch(query));
      return;
    }
    const terms = queryTerms(query);
    results.innerHTML = matches.slice(0,8).map(({item}) => {
      const label = item.id ? `${item.id} — ${item.title}` : item.title;
      const meta = [item.type, item.status].filter(Boolean).join(' · ');
      return `<a class="search-result" href="${rootUrl(item.url)}"><b>${highlightText(label, terms)}</b><span>${escapeHtml(meta || item.category || '')}${item.summary ? ` · ${escapeHtml(item.summary)}` : ''}</span></a>`;
    }).join('') + `<button class="search-view-all" type="button" data-search-all>View all ${matches.length} result${matches.length === 1 ? '' : 's'} →</button>`;
    results.querySelector('[data-search-all]')?.addEventListener('click', () => goToSearch(query));
  }

  if (input) {
    input.addEventListener('input', async () => renderDropdown(scoredSearch(await loadIndex(), input.value), input.value));
    input.addEventListener('focus', async () => { if (input.value.trim()) renderDropdown(scoredSearch(await loadIndex(), input.value), input.value); });
    input.addEventListener('keydown', e => {
      if (e.key === 'Enter') { e.preventDefault(); goToSearch(input.value); }
      if (e.key === 'Escape') results?.classList.remove('open');
    });
    submit?.addEventListener('click', () => goToSearch(input.value));
    document.addEventListener('click', e => { if (!e.target.closest('.header-search')) results?.classList.remove('open'); });
  }

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
      if (!q) { summary.textContent = 'Enter a search term to find matching archive pages and documents.'; pageResults.innerHTML = ''; return; }
      summary.textContent = 'Searching…';
      const matches = scoredSearch(await loadIndex(), q);
      const terms = queryTerms(q);
      summary.innerHTML = `<strong>${matches.length}</strong> result${matches.length === 1 ? '' : 's'} for “${escapeHtml(q)}”`;
      if (!matches.length) { pageResults.innerHTML = '<div class="search-page-empty">No pages or documents contained all of those search terms.</div>'; return; }
      pageResults.innerHTML = matches.map(({item}) => {
        const label = item.id ? `${item.id} — ${item.title}` : item.title;
        const meta = [item.category, item.type, item.status].filter(Boolean).join(' · ');
        return `<article class="full-search-result"><a href="${rootUrl(item.url)}"><h2>${highlightText(label, terms)}</h2></a><div class="full-search-meta">${escapeHtml(meta)}</div><p>${snippetFor(item, terms)}</p><a class="full-search-open" href="${rootUrl(item.url)}">Open page →</a></article>`;
      }).join('');
    }
    form?.addEventListener('submit', e => { e.preventDefault(); renderSearchPage(pageInput.value, true); });
    renderSearchPage(new URLSearchParams(window.location.search).get('q') || '', false);
  }

  document.querySelectorAll('[data-google-file]').forEach(a => {
    a.addEventListener('click', e => {
      e.preventDefault();
      const abs = new URL(a.dataset.googleFile, window.location.href).href;
      window.open(`https://docs.google.com/gview?embedded=1&url=${encodeURIComponent(abs)}`, '_blank', 'noopener');
    });
  });

  // One master archive catalogue. Home-page buttons pre-apply filters through URL parameters.
  const catalogue = document.querySelector('[data-catalogue]');
  if (catalogue) {
    const rows = [...catalogue.querySelectorAll('[data-doc-row]')];
    const local = document.querySelector('[data-local-search]');
    const typeChecks = [...document.querySelectorAll('[data-type-filter]')];
    const statusChecks = [...document.querySelectorAll('[data-status-filter]')];
    const year = document.querySelector('[data-year-filter]');
    const sort = document.querySelector('[data-sort]');
    const count = document.querySelector('[data-visible-count]');
    const activeBar = document.querySelector('[data-active-filters]');
    const empty = document.querySelector('[data-empty-state]');

    function paramsToChecks() {
      const params = new URLSearchParams(window.location.search);
      const types = params.getAll('type').map(v => v.toLowerCase());
      const statuses = params.getAll('status').map(v => v.toLowerCase());
      typeChecks.forEach(c => c.checked = types.includes(c.value.toLowerCase()));
      statusChecks.forEach(c => c.checked = statuses.includes(c.value.toLowerCase()));
      if (year) year.value = params.get('year') || '';
      if (local) local.value = params.get('q') || '';
    }
    function selected(checks) { return checks.filter(c => c.checked).map(c => c.value); }
    function updateUrl() {
      const url = new URL(window.location.href);
      url.search = '';
      selected(typeChecks).forEach(v => url.searchParams.append('type', v));
      selected(statusChecks).forEach(v => url.searchParams.append('status', v));
      if (year?.value) url.searchParams.set('year', year.value);
      if (local?.value.trim()) url.searchParams.set('q', local.value.trim());
      history.replaceState({}, '', url);
    }
    function removeFilter(kind, value) {
      if (kind === 'type') typeChecks.find(c => c.value === value)?.click();
      if (kind === 'status') statusChecks.find(c => c.value === value)?.click();
      if (kind === 'year' && year) { year.value = ''; apply(); }
      if (kind === 'q' && local) { local.value = ''; apply(); }
    }
    function renderActiveFilters() {
      if (!activeBar) return;
      const chips = [];
      selected(typeChecks).forEach(v => chips.push(['type', v]));
      selected(statusChecks).forEach(v => chips.push(['status', v]));
      if (year?.value) chips.push(['year', year.value]);
      if (local?.value.trim()) chips.push(['q', `Search: ${local.value.trim()}`]);
      if (!chips.length) {
        activeBar.innerHTML = '<span class="filter-context">Showing all archive records.</span>';
        return;
      }
      activeBar.innerHTML = '<span class="filter-context">Active filters:</span>' + chips.map(([kind,label]) => `<button type="button" class="filter-chip" data-remove-filter="${escapeHtml(kind)}" data-remove-value="${escapeHtml(kind === 'q' ? label.replace(/^Search: /,'') : label)}">${escapeHtml(label)} <b>×</b></button>`).join('') + '<button type="button" class="clear-filters" data-clear-filters>Clear all</button>';
      activeBar.querySelectorAll('[data-remove-filter]').forEach(btn => btn.addEventListener('click', () => removeFilter(btn.dataset.removeFilter, btn.dataset.removeValue)));
      activeBar.querySelector('[data-clear-filters]')?.addEventListener('click', () => {
        typeChecks.forEach(c => c.checked = false);
        statusChecks.forEach(c => c.checked = false);
        if (year) year.value = '';
        if (local) local.value = '';
        apply();
      });
    }
    function apply() {
      const q = (local?.value || '').trim().toLowerCase();
      const types = selected(typeChecks).map(v => v.toLowerCase());
      const statuses = selected(statusChecks).map(v => v.toLowerCase());
      const yr = year?.value || '';
      let visible = rows.filter(row => {
        const textOk = !q || row.dataset.search.includes(q);
        const typeOk = !types.length || types.includes(row.dataset.type);
        const statusOk = !statuses.length || statuses.includes(row.dataset.status);
        const yearOk = !yr || row.dataset.year === yr;
        return textOk && typeOk && statusOk && yearOk;
      });
      if (sort) {
        const mode = sort.value;
        visible.sort((a,b) => {
          const ad = a.dataset.date || '', bd = b.dataset.date || '';
          if (mode === 'oldest') return ad.localeCompare(bd);
          if (mode === 'title') return a.dataset.title.localeCompare(b.dataset.title);
          if (mode === 'id') return a.dataset.id.localeCompare(b.dataset.id);
          return bd.localeCompare(ad);
        });
      }
      rows.forEach(r => r.style.display = 'none');
      visible.forEach(r => { r.style.display = 'grid'; catalogue.appendChild(r); });
      if (count) count.textContent = visible.length;
      if (empty) empty.style.display = visible.length ? 'none' : 'block';
      renderActiveFilters();
      updateUrl();
    }
    paramsToChecks();
    local?.addEventListener('input', apply);
    typeChecks.forEach(c => c.addEventListener('change', apply));
    statusChecks.forEach(c => c.addEventListener('change', apply));
    year?.addEventListener('change', apply);
    sort?.addEventListener('change', apply);
    apply();
  }

  // Swap between current and previous PDF versions without leaving the document record.
  const frame = document.querySelector('[data-viewer-frame]');
  const versionButtons = [...document.querySelectorAll('[data-version-select]')];
  const note = document.querySelector('[data-version-note]');
  const pdfOpen = document.querySelector('[data-pdf-open]');
  const pdfDownload = document.querySelector('[data-pdf-download]');
  const google = document.querySelector('[data-google-file]');
  if (frame && versionButtons.length) {
    function selectVersion(btn, updateUrl = true) {
      const file = btn.dataset.versionFile;
      if (!file) return;
      frame.src = `${file}#view=FitH`;
      versionButtons.forEach(b => b.classList.toggle('active', b === btn));
      if (pdfOpen) pdfOpen.href = file;
      if (pdfDownload) pdfDownload.href = file;
      if (google) google.dataset.googleFile = file;
      const current = btn.dataset.versionKey === 'current';
      if (note) {
        note.style.display = current ? 'none' : 'flex';
        note.innerHTML = current ? '' : `<strong>Viewing previous version:</strong><span>${escapeHtml(btn.dataset.versionLabel || 'Previous version')}</span>`;
      }
      if (updateUrl) {
        const url = new URL(window.location.href);
        if (current) url.searchParams.delete('version'); else url.searchParams.set('version', btn.dataset.versionKey || 'previous');
        history.replaceState({}, '', url);
      }
    }
    versionButtons.forEach(btn => btn.addEventListener('click', () => selectVersion(btn, true)));
    const wanted = new URLSearchParams(window.location.search).get('version');
    if (wanted) {
      const target = versionButtons.find(b => b.dataset.versionKey === wanted);
      if (target) selectVersion(target, false);
    }
  }
})();
