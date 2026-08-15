(() => {
  const body = document.body;
  const base = body.dataset.base || './';
  const mobile = document.querySelector('[data-mobile-toggle]');
  const nav = document.querySelector('.main-nav');
  if (mobile && nav) mobile.addEventListener('click', () => nav.classList.toggle('open'));

  // Global archive search.
  const input = document.querySelector('[data-global-search]');
  const results = document.querySelector('[data-search-results]');
  let indexPromise = null;
  function loadIndex() {
    if (!indexPromise) indexPromise = fetch(base + 'assets/search-index.json').then(r => r.json()).catch(() => []);
    return indexPromise;
  }
  function escapeHtml(s) {
    return String(s || '').replace(/[&<>"']/g, c => ({'&':'&amp;','<':'&lt;','>':'&gt;','"':'&quot;',"'":'&#039;'}[c]));
  }
  function rootUrl(path) { return new URL(base + path, window.location.href).href; }
  function search(items, query) {
    const q = query.trim().toLowerCase();
    if (!q) return [];
    const terms = q.split(/\s+/).filter(Boolean);
    return items.map(item => {
      const hay = `${item.id} ${item.title} ${item.category} ${item.type} ${item.status} ${item.summary} ${item.text || ''}`.toLowerCase();
      let score = 0;
      for (const term of terms) {
        if (String(item.id).toLowerCase().includes(term)) score += 10;
        if (String(item.title).toLowerCase().includes(term)) score += 8;
        if (String(item.summary).toLowerCase().includes(term)) score += 4;
        if (hay.includes(term)) score += 1;
      }
      return { item, score };
    }).filter(x => x.score >= terms.length).sort((a,b) => b.score - a.score).slice(0,8).map(x => x.item);
  }
  function renderResults(items, query) {
    if (!results) return;
    if (!query.trim()) { results.classList.remove('open'); results.innerHTML=''; return; }
    results.classList.add('open');
    if (!items.length) {
      results.innerHTML = `<div class="search-empty">No archive records matched “${escapeHtml(query)}”.</div>`;
      return;
    }
    results.innerHTML = items.map(item => `<a class="search-result" href="${rootUrl(item.url)}"><b>${escapeHtml(item.id)} — ${escapeHtml(item.title)}</b><span>${escapeHtml(item.summary || item.type || item.category)}</span></a>`).join('');
  }
  if (input) {
    input.addEventListener('input', async () => renderResults(search(await loadIndex(), input.value), input.value));
    input.addEventListener('focus', async () => { if (input.value.trim()) renderResults(search(await loadIndex(), input.value), input.value); });
    input.addEventListener('keydown', e => {
      if (e.key === 'Enter') {
        const first = results?.querySelector('a');
        if (first) window.location.href = first.href;
      }
      if (e.key === 'Escape') results?.classList.remove('open');
    });
    document.addEventListener('click', e => {
      if (!e.target.closest('.header-search')) results?.classList.remove('open');
    });
  }

  // External document viewers resolve the current hosted file at click time.
  document.querySelectorAll('[data-google-file]').forEach(a => {
    a.addEventListener('click', e => {
      e.preventDefault();
      const raw = a.dataset.googleFile;
      const abs = new URL(raw, window.location.href).href;
      window.open(`https://docs.google.com/gview?embedded=1&url=${encodeURIComponent(abs)}`, '_blank', 'noopener');
    });
  });
  document.querySelectorAll('[data-office-file]').forEach(a => {
    a.addEventListener('click', e => {
      e.preventDefault();
      const raw = a.dataset.officeFile;
      const abs = new URL(raw, window.location.href).href;
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
