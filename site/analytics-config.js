/* Public analytics endpoint only. Keep all admin credentials out of GitHub.
   Counts are aggregate and no cookies or visitor IDs are used.
   Full IPs for technical security are stored separately on the Cloudflare Worker.
   Same Worker as Portfolio and BORS (see Portfoliopage/analytics/README.md).
   Switch off: set endpoint to "" and rebuild the site (python -m transparenz build-site). */
window.JB_ANALYTICS_CONFIG = Object.freeze({
  endpoint: "https://jonas-portfolio-analytics.jonas-bader-analytics.workers.dev/collect"
});
