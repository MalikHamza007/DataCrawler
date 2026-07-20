(function () {
  function payload() {
    return {
      seed_url: document.getElementById("enrichment-url").value.trim(),
      crawl_mode: document.getElementById("enrichment-mode").value,
      max_pages: Number(document.getElementById("enrichment-max-pages").value),
      use_playwright_fallback: document.getElementById("enrichment-playwright").checked
    };
  }

  async function preview() {
    const output = document.getElementById("enrichment-preview");
    try {
      output.textContent = JSON.stringify(await AlduorApi.previewWebsite(payload()), null, 2);
    } catch (error) {
      output.textContent = error.message;
    }
    output.style.display = "block";
  }

  async function submit(event) {
    event.preventDefault();
    try {
      const job = await AlduorApi.createWebsiteJob(payload());
      window.AlduorApp.notify(`Website enrichment job #${job.id} was queued.`, "success");
      await AlduorJobs.loadJobs();
    } catch (error) {
      window.AlduorApp.notify(error.message, "error");
    }
  }

  document.getElementById("preview-enrichment").addEventListener("click", preview);
  document.getElementById("enrichment-form").addEventListener("submit", submit);
})();
