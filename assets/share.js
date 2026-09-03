(function () {
  'use strict';
  const cleanTitle = () => document.title.replace(/｜いまいくら.*$/, '').trim();
  const pageUrl = () => document.querySelector('link[rel="canonical"]')?.href || location.href.split('#')[0];
  const track = (method) => {
    if (typeof window.gtag === 'function') {
      window.gtag('event', 'share', { method, content_type: 'article', item_id: location.pathname });
    }
  };
  async function copyUrl(button) {
    const url = pageUrl();
    try {
      await navigator.clipboard.writeText(url);
    } catch (_) {
      const area = document.createElement('textarea');
      area.value = url;
      area.setAttribute('readonly', '');
      area.style.position = 'fixed';
      area.style.opacity = '0';
      document.body.appendChild(area);
      area.select();
      document.execCommand('copy');
      area.remove();
    }
    const status = button.closest('[data-share-box]')?.querySelector('[data-share-status]');
    if (status) {
      status.textContent = 'URLをコピーしました。';
      window.setTimeout(() => { status.textContent = ''; }, 2500);
    }
    track('copy');
  }
  document.addEventListener('click', async (event) => {
    const button = event.target.closest('[data-share]');
    if (!button) return;
    const method = button.dataset.share;
    const title = cleanTitle();
    const url = pageUrl();
    if (method === 'native') {
      event.preventDefault();
      if (navigator.share) {
        try { await navigator.share({ title, text: title, url }); track('native'); } catch (_) {}
      } else {
        await copyUrl(button);
      }
    } else if (method === 'copy') {
      event.preventDefault();
      await copyUrl(button);
    } else if (method === 'x') {
      button.href = 'https://twitter.com/intent/tweet?text=' + encodeURIComponent(title) + '&url=' + encodeURIComponent(url);
      track('x');
    } else if (method === 'line') {
      button.href = 'https://social-plugins.line.me/lineit/share?url=' + encodeURIComponent(url);
      track('line');
    }
  });
})();
