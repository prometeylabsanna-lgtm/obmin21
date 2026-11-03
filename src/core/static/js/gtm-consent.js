/* Google Consent Mode v2: усе denied за замовчуванням, далі GTM.
   ID береться з data-gtm-id тегу <script>; без ID нічого не робимо. */
(function () {
  var script = document.currentScript;
  var id = script && script.getAttribute('data-gtm-id');
  if (!id || !/^GTM-[A-Z0-9]+$/.test(id)) return;

  window.dataLayer = window.dataLayer || [];
  function gtag() { window.dataLayer.push(arguments); }
  window.gtag = window.gtag || gtag;

  gtag('consent', 'default', {
    ad_storage: 'denied',
    ad_user_data: 'denied',
    ad_personalization: 'denied',
    analytics_storage: 'denied',
    functionality_storage: 'denied',
    personalization_storage: 'denied',
    security_storage: 'granted',
    wait_for_update: 500
  });

  window.dataLayer.push({ 'gtm.start': new Date().getTime(), event: 'gtm.js' });
  var tag = document.createElement('script');
  tag.async = true;
  tag.src = 'https://www.googletagmanager.com/gtm.js?id=' + encodeURIComponent(id);
  document.head.appendChild(tag);
})();
