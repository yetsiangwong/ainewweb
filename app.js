const state = {
  issues: [],
  activeIssue: null,
  activeCategory: "All",
};

const $ = (selector) => document.querySelector(selector);

async function loadNews() {
  const response = await fetch("data/news.json", { cache: "no-store" });
  if (!response.ok) throw new Error(`Failed to load news data: ${response.status}`);
  const data = await response.json();
  state.issues = data.issues || [];
  state.activeIssue = state.issues[0];
  renderSite(data.site || {});
  renderIssue();
  startCanvas();
}

function renderSite(site) {
  const stories = state.issues.flatMap((issue) => issue.stories || []);
  $("#issue-count").textContent = state.issues.length;
  $("#story-count").textContent = stories.length;
  $("#latest-date").textContent = state.activeIssue?.date || "--";
  $("#last-updated").textContent = site.lastUpdated ? `Last updated ${site.lastUpdated}` : "";
}

function renderIssue() {
  const issue = state.activeIssue;
  if (!issue) return;

  $("#issue-title").textContent = `${issue.date} · Global AI News Brief`;
  $("#issue-status").textContent = issue.status || "";

  const highlights = issue.highlights || [];
  $("#highlight-grid").innerHTML = highlights
    .map((item, index) => `<article class="highlight-card"><strong>0${index + 1}</strong><p>${escapeHtml(item)}</p></article>`)
    .join("");

  const tickerItems = [...highlights, ...highlights];
  $("#ticker-track").innerHTML = tickerItems.map((item) => `<span>${escapeHtml(item)}</span>`).join("");

  const categories = ["All", ...new Set((issue.stories || []).map((story) => story.category))];
  $("#filters").innerHTML = categories
    .map((category) => `<button class="filter-button ${category === state.activeCategory ? "active" : ""}" data-category="${escapeHtml(category)}">${escapeHtml(category)}</button>`)
    .join("");

  $("#filters").querySelectorAll("button").forEach((button) => {
    button.addEventListener("click", () => {
      state.activeCategory = button.dataset.category;
      renderIssue();
    });
  });

  const stories = (issue.stories || []).filter((story) => state.activeCategory === "All" || story.category === state.activeCategory);
  $("#story-grid").innerHTML = stories
    .map((story) => `
      <article class="story-card">
        <span class="category">${escapeHtml(story.category)}</span>
        <h3>${escapeHtml(story.title)}</h3>
        <p>${escapeHtml(story.summary)}</p>
        <p class="why"><strong>Why it matters:</strong> ${escapeHtml(story.whyItMatters)}</p>
        <a class="source-link" href="${escapeAttribute(story.source)}" target="_blank" rel="noopener">Open source</a>
      </article>
    `)
    .join("");

  $("#short-list").innerHTML = (issue.discordShort || []).map((item) => `<li>${escapeHtml(item)}</li>`).join("");

  $("#archive-list").innerHTML = state.issues
    .map((archiveIssue) => `
      <article class="archive-card">
        <p class="eyebrow">${escapeHtml(archiveIssue.label || "Archive")}</p>
        <h3>${escapeHtml(archiveIssue.date)} · ${archiveIssue.stories?.length || 0} stories</h3>
        <p>${escapeHtml((archiveIssue.highlights || [])[0] || archiveIssue.status || "")}</p>
        <button class="button secondary" data-date="${escapeAttribute(archiveIssue.date)}">Load briefing</button>
      </article>
    `)
    .join("");

  $("#archive-list").querySelectorAll("button").forEach((button) => {
    button.addEventListener("click", () => {
      state.activeIssue = state.issues.find((issueItem) => issueItem.date === button.dataset.date) || state.issues[0];
      state.activeCategory = "All";
      renderIssue();
      $("#briefing").scrollIntoView({ behavior: "smooth" });
    });
  });
}

function startCanvas() {
  const canvas = $("#signal-canvas");
  const context = canvas.getContext("2d");
  const points = Array.from({ length: 84 }, () => ({ x: Math.random(), y: Math.random(), vx: (Math.random() - 0.5) * 0.0007, vy: (Math.random() - 0.5) * 0.0007 }));

  function resize() {
    canvas.width = window.innerWidth * window.devicePixelRatio;
    canvas.height = window.innerHeight * window.devicePixelRatio;
  }

  function frame() {
    context.clearRect(0, 0, canvas.width, canvas.height);
    context.lineWidth = 1 * window.devicePixelRatio;

    points.forEach((point) => {
      point.x += point.vx;
      point.y += point.vy;
      if (point.x < 0 || point.x > 1) point.vx *= -1;
      if (point.y < 0 || point.y > 1) point.vy *= -1;
    });

    for (let i = 0; i < points.length; i += 1) {
      for (let j = i + 1; j < points.length; j += 1) {
        const a = points[i];
        const b = points[j];
        const dx = (a.x - b.x) * canvas.width;
        const dy = (a.y - b.y) * canvas.height;
        const distance = Math.sqrt(dx * dx + dy * dy);
        if (distance < 150 * window.devicePixelRatio) {
          context.strokeStyle = `rgba(69, 215, 255, ${0.16 - distance / (150 * window.devicePixelRatio) * 0.13})`;
          context.beginPath();
          context.moveTo(a.x * canvas.width, a.y * canvas.height);
          context.lineTo(b.x * canvas.width, b.y * canvas.height);
          context.stroke();
        }
      }
    }

    context.fillStyle = "rgba(114, 242, 184, 0.6)";
    points.forEach((point) => {
      context.beginPath();
      context.arc(point.x * canvas.width, point.y * canvas.height, 1.6 * window.devicePixelRatio, 0, Math.PI * 2);
      context.fill();
    });

    requestAnimationFrame(frame);
  }

  resize();
  window.addEventListener("resize", resize);
  frame();
}

function escapeHtml(value) {
  return String(value || "")
    .replaceAll("&", "&amp;")
    .replaceAll("<", "&lt;")
    .replaceAll(">", "&gt;")
    .replaceAll('"', "&quot;")
    .replaceAll("'", "&#039;");
}

function escapeAttribute(value) {
  return escapeHtml(value).replaceAll("`", "&#096;");
}

loadNews().catch((error) => {
  document.body.innerHTML = `<main class="section"><h1>Unable to load briefing</h1><p>${escapeHtml(error.message)}</p></main>`;
});
