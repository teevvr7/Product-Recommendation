/**
 * Acme Retail Semantic Recommendation Engine - Client Application
 */

const API_BASE = "/api";

// Application State
const state = {
  query: "",
  selectedCategory: "all",
  modelMode: "hybrid",
  minRating: null,
  sortBy: "similarity",
  topN: 12,
  recommendations: [],
  categories: [],
  categoryCounts: {},
  systemStats: null,
  cart: [],
  loading: false,
  routeInfo: null,
  activeView: "grid", // 'grid' | 'comparison'
  comparisonData: null,
  selectedProduct: null,
};

// DOM Elements
const el = {
  searchInput: document.getElementById("searchInput"),
  categorySelect: document.getElementById("categorySelect"),
  searchBtn: document.getElementById("searchBtn"),
  clearBtn: document.getElementById("clearBtn"),
  resultsGrid: document.getElementById("resultsGrid"),
  routingBanner: document.getElementById("routingBanner"),
  resultsCount: document.getElementById("resultsCount"),
  latencyBadge: document.getElementById("latencyBadge"),
  activeQueryDisplay: document.getElementById("activeQueryDisplay"),
  categoriesList: document.getElementById("categoriesList"),
  engineBadge: document.getElementById("engineBadge"),
  topNSlider: document.getElementById("topNSlider"),
  topNValue: document.getElementById("topNValue"),
  sortSelect: document.getElementById("sortSelect"),
  cartCount: document.getElementById("cartCount"),
  cartDrawer: document.getElementById("cartDrawer"),
  cartOverlay: document.getElementById("cartOverlay"),
  cartItemsList: document.getElementById("cartItemsList"),
  cartSubtotal: document.getElementById("cartSubtotal"),
  productModal: document.getElementById("productModal"),
  productModalContent: document.getElementById("productModalContent"),
  compareModal: document.getElementById("compareModal"),
  compareModalContent: document.getElementById("compareModalContent"),
  archModal: document.getElementById("archModal"),
  statsTotalProducts: document.getElementById("statsTotalProducts"),
  statsW2VVocab: document.getElementById("statsW2VVocab"),
  statsFTVocab: document.getElementById("statsFTVocab"),
  statsTFIDFVocab: document.getElementById("statsTFIDFVocab"),
  statsLatency: document.getElementById("statsLatency"),
  toastContainer: document.getElementById("toastContainer"),
};

// Initialize Application
document.addEventListener("DOMContentLoaded", () => {
  initApp();
  setupEventListeners();
});

async function initApp() {
  await Promise.all([fetchSystemStats(), fetchCategories()]);
  // Initial search with primary route
  setQuery("wireless mouse");
}

function setupEventListeners() {
  // Search input listeners
  el.searchInput.addEventListener("keydown", (e) => {
    if (e.key === "Enter") {
      state.query = el.searchInput.value.trim();
      executeSearch();
    }
  });

  el.searchInput.addEventListener("input", () => {
    el.clearBtn.style.display = el.searchInput.value ? "flex" : "none";
  });

  el.clearBtn.addEventListener("click", () => {
    el.searchInput.value = "";
    el.clearBtn.style.display = "none";
    el.searchInput.focus();
  });

  el.searchBtn.addEventListener("click", () => {
    state.query = el.searchInput.value.trim();
    executeSearch();
  });

  // Category select in search bar
  el.categorySelect.addEventListener("change", (e) => {
    state.selectedCategory = e.target.value;
    updateCategorySidebarActive();
    executeSearch();
  });

  // Top-N slider
  if (el.topNSlider) {
    el.topNSlider.addEventListener("input", (e) => {
      state.topN = parseInt(e.target.value, 10);
      if (el.topNValue) el.topNValue.textContent = state.topN;
      executeSearch();
    });
  }

  // Sort dropdown
  if (el.sortSelect) {
    el.sortSelect.addEventListener("change", (e) => {
      state.sortBy = e.target.value;
      executeSearch();
    });
  }

  // Global keyboard shortcuts
  document.addEventListener("keydown", (e) => {
    if ((e.key === "/" || (e.ctrlKey && e.key === "k")) && document.activeElement !== el.searchInput) {
      e.preventDefault();
      el.searchInput.focus();
      el.searchInput.select();
    } else if (e.key === "Escape") {
      closeAllModals();
      closeCart();
    }
  });
}

// Set Query from chips or presets
window.setQuery = function(text, mode = null) {
  el.searchInput.value = text;
  el.clearBtn.style.display = "flex";
  state.query = text;
  if (mode) {
    setEngineMode(mode);
  } else {
    executeSearch();
  }
};

window.setEngineMode = function(mode) {
  state.modelMode = mode;
  document.querySelectorAll(".engine-mode-btn").forEach((btn) => {
    if (btn.dataset.mode === mode) {
      btn.classList.add("bg-indigo-600", "text-white", "shadow-sm");
      btn.classList.remove("text-slate-600", "hover:bg-slate-100");
    } else {
      btn.classList.remove("bg-indigo-600", "text-white", "shadow-sm");
      btn.classList.add("text-slate-600", "hover:bg-slate-100");
    }
  });
  executeSearch();
};

window.setRatingFilter = function(minRating) {
  state.minRating = minRating;
  document.querySelectorAll(".rating-filter-btn").forEach((btn) => {
    if (parseFloat(btn.dataset.rating) === minRating || (minRating === null && btn.dataset.rating === "all")) {
      btn.classList.add("bg-amber-50", "border-amber-400", "text-amber-800", "font-semibold");
      btn.classList.remove("border-slate-200", "text-slate-600");
    } else {
      btn.classList.remove("bg-amber-50", "border-amber-400", "text-amber-800", "font-semibold");
      btn.classList.add("border-slate-200", "text-slate-600");
    }
  });
  executeSearch();
};

window.selectCategory = function(cat) {
  state.selectedCategory = cat;
  el.categorySelect.value = cat;
  updateCategorySidebarActive();
  executeSearch();
};

function updateCategorySidebarActive() {
  document.querySelectorAll(".cat-sidebar-item").forEach((item) => {
    if (item.dataset.cat.toLowerCase() === state.selectedCategory.toLowerCase()) {
      item.classList.add("bg-indigo-50", "text-indigo-700", "font-semibold");
      item.classList.remove("text-slate-600", "hover:bg-slate-100");
    } else {
      item.classList.remove("bg-indigo-50", "text-indigo-700", "font-semibold");
      item.classList.add("text-slate-600", "hover:bg-slate-100");
    }
  });
}

// API Calls
async function fetchSystemStats() {
  try {
    const res = await fetch(`${API_BASE}/system/stats`);
    if (!res.ok) return;
    const data = await res.json();
    state.systemStats = data;
    renderSystemStats(data);
  } catch (err) {
    console.error("Failed to load system stats:", err);
  }
}

async function fetchCategories() {
  try {
    const res = await fetch(`${API_BASE}/products/categories/all`);
    if (!res.ok) return;
    const data = await res.json();
    state.categories = data.categories || [];
    state.categoryCounts = data.counts || {};
    renderCategoryFilters();
  } catch (err) {
    console.error("Failed to load categories:", err);
  }
}

function renderSystemStats(data) {
  if (el.statsTotalProducts) el.statsTotalProducts.textContent = data.total_catalog_products.toLocaleString();
  if (el.statsW2VVocab) el.statsW2VVocab.textContent = data.models.primary.vocabulary_size.toLocaleString();
  if (el.statsFTVocab) el.statsFTVocab.textContent = data.models.fallback.vocabulary_size.toLocaleString();
  if (el.statsTFIDFVocab) el.statsTFIDFVocab.textContent = data.models.baseline.vocabulary_size.toLocaleString();
  if (el.statsLatency) el.statsLatency.textContent = `${data.artifacts_load_duration_seconds}s`;
}

function renderCategoryFilters() {
  // Category dropdown in navbar
  let optionsHtml = `<option value="all">All Categories</option>`;
  state.categories.forEach((cat) => {
    const count = state.categoryCounts[cat] || 0;
    optionsHtml += `<option value="${escapeHtml(cat)}">${escapeHtml(capitalize(cat))} (${count})</option>`;
  });
  el.categorySelect.innerHTML = optionsHtml;

  // Category list in sidebar
  let sidebarHtml = `
    <button onclick="selectCategory('all')" data-cat="all" class="cat-sidebar-item w-full flex items-center justify-between px-3 py-2 text-sm rounded-lg transition-colors bg-indigo-50 text-indigo-700 font-semibold">
      <span>All Products</span>
      <span class="text-xs bg-slate-200/80 px-2 py-0.5 rounded-full text-slate-700">${(state.systemStats?.total_catalog_products || 0).toLocaleString()}</span>
    </button>
  `;

  state.categories.forEach((cat) => {
    const count = state.categoryCounts[cat] || 0;
    sidebarHtml += `
      <button onclick="selectCategory('${escapeHtml(cat)}')" data-cat="${escapeHtml(cat)}" class="cat-sidebar-item w-full flex items-center justify-between px-3 py-2 text-sm rounded-lg text-slate-600 hover:bg-slate-100 transition-colors">
        <span class="truncate pr-2">${escapeHtml(capitalize(cat))}</span>
        <span class="text-xs bg-slate-200/60 px-2 py-0.5 rounded-full text-slate-500">${count.toLocaleString()}</span>
      </button>
    `;
  });
  el.categoriesList.innerHTML = sidebarHtml;
}

// Core Recommendation Execution
async function executeSearch() {
  showSkeletons();
  state.loading = true;

  const payload = {
    query: state.query || "wireless mouse",
    top_n: state.topN,
    model_mode: state.modelMode,
    category: state.selectedCategory === "all" ? null : state.selectedCategory,
    min_rating: state.minRating,
    sort_by: state.sortBy,
  };

  try {
    const res = await fetch(`${API_BASE}/recommend`, {
      method: "POST",
      headers: { "Content-Type": "application/json" },
      body: JSON.stringify(payload),
    });

    if (!res.ok) {
      throw new Error(`Recommendation failed with status ${res.status}`);
    }

    const data = await res.json();
    state.recommendations = data.recommendations || [];
    state.routeInfo = {
      query: data.query,
      cleaned_query: data.cleaned_query,
      query_tokens: data.query_tokens || [],
      model_used: data.model_used,
      model_engine: data.model_engine,
      is_fallback: data.is_fallback_triggered,
      oov_words: data.oov_words || [],
      total_results: data.total_results,
      latency_ms: data.latency_ms,
    };

    renderResults();
    renderRoutingBanner();
  } catch (err) {
    console.error("Search error:", err);
    showToast("Search failed. Check server logs.", "error");
    el.resultsGrid.innerHTML = `
      <div class="col-span-full py-12 text-center">
        <div class="inline-flex items-center justify-center w-12 h-12 rounded-full bg-rose-100 text-rose-600 mb-4">
          <svg class="w-6 h-6" fill="none" stroke="currentColor" viewBox="0 0 24 24"><path stroke-linecap="round" stroke-linejoin="round" stroke-width="2" d="M12 9v2m0 4h.01m-6.938 4h13.856c1.54 0 2.502-1.667 1.732-3L13.732 4c-.77-1.333-2.694-1.333-3.464 0L3.34 16c-.77 1.333.192 3 1.732 3z"></path></svg>
        </div>
        <h3 class="text-base font-semibold text-slate-800">Recommendation Service Unavailable</h3>
        <p class="text-sm text-slate-500 mt-1 max-w-md mx-auto">${escapeHtml(err.message)}</p>
      </div>
    `;
  } finally {
    state.loading = false;
  }
}

// Find Similar to Catalog Product
window.findSimilar = async function(catalogId, productName) {
  showSkeletons();
  el.searchInput.value = `Similar to: ${productName}`;
  state.query = productName;
  closeAllModals();

  try {
    const res = await fetch(`${API_BASE}/recommend/similar/${catalogId}?top_n=${state.topN}&model_mode=${state.modelMode}&category=${state.selectedCategory === "all" ? "" : state.selectedCategory}`);
    if (!res.ok) throw new Error("Similar query failed");

    const data = await res.json();
    state.recommendations = data.recommendations || [];
    state.routeInfo = {
      query: `Item #${catalogId}: ${productName}`,
      cleaned_query: data.cleaned_query,
      query_tokens: data.query_tokens || [],
      model_used: data.model_used,
      model_engine: data.model_engine,
      is_fallback: false,
      oov_words: [],
      total_results: data.total_results,
      latency_ms: data.latency_ms,
    };

    renderResults();
    renderRoutingBanner();
    showToast(`Showing products semantically similar to "${productName.substring(0, 30)}..."`, "info");
  } catch (err) {
    showToast("Failed to fetch similar products", "error");
  }
};

// Routing Banner Render
function renderRoutingBanner() {
  if (!state.routeInfo) return;

  const info = state.routeInfo;
  el.resultsCount.textContent = info.total_results.toLocaleString();
  el.latencyBadge.textContent = `${info.latency_ms} ms`;
  el.activeQueryDisplay.textContent = info.query;

  let bannerHtml = "";
  if (info.is_fallback) {
    bannerHtml = `
      <div class="rounded-xl border border-amber-300 bg-amber-50/80 p-4 shadow-sm transition-all animate-fadeIn">
        <div class="flex items-start gap-3">
          <div class="p-2 rounded-lg bg-amber-500 text-white shrink-0 mt-0.5 shadow-sm">
            <svg class="w-5 h-5" fill="none" stroke="currentColor" viewBox="0 0 24 24"><path stroke-linecap="round" stroke-linejoin="round" stroke-width="2" d="M13 10V3L4 14h7v7l9-11h-7z"></path></svg>
          </div>
          <div class="flex-1 min-w-0">
            <div class="flex items-center gap-2 flex-wrap">
              <span class="inline-flex items-center px-2.5 py-0.5 rounded-full text-xs font-bold bg-amber-200 text-amber-900 uppercase tracking-wide">
                Fallback Route Activated
              </span>
              <span class="text-xs font-semibold text-amber-900">FastText Subword Embedding Engine</span>
              <span class="text-xs text-amber-700 bg-amber-100/80 px-2 py-0.5 rounded">Retrieved in ${info.latency_ms}ms</span>
            </div>
            <p class="text-xs text-amber-800 mt-1.5 leading-relaxed">
              <strong>Out-Of-Vocabulary (OOV) Detected:</strong> 
              ${info.oov_words.map(w => `<code class="bg-amber-200/70 text-amber-950 px-1.5 py-0.5 rounded text-[11px] font-mono mr-1">${escapeHtml(w)}</code>`).join("")}
              Word2Vec does not contain these unseen/typo tokens. The routing engine seamlessly delegated to <strong>FastText</strong>, which extracted character n-grams (3-6 chars) to synthesize meaningful dense embeddings!
            </p>
          </div>
          <button onclick="openComparisonWithCurrent()" class="text-xs font-semibold bg-white border border-amber-300 text-amber-900 px-3 py-1.5 rounded-lg hover:bg-amber-100 transition-colors shrink-0">
            Compare Models Side-by-Side
          </button>
        </div>
      </div>
    `;
  } else {
    bannerHtml = `
      <div class="rounded-xl border border-emerald-200 bg-emerald-50/70 p-4 shadow-sm transition-all animate-fadeIn">
        <div class="flex items-start gap-3">
          <div class="p-2 rounded-lg bg-emerald-600 text-white shrink-0 mt-0.5 shadow-sm">
            <svg class="w-5 h-5" fill="none" stroke="currentColor" viewBox="0 0 24 24"><path stroke-linecap="round" stroke-linejoin="round" stroke-width="2" d="M9 12l2 2 4-4m6 2a9 9 0 11-18 0 9 9 0 0118 0z"></path></svg>
          </div>
          <div class="flex-1 min-w-0">
            <div class="flex items-center gap-2 flex-wrap">
              <span class="inline-flex items-center px-2.5 py-0.5 rounded-full text-xs font-bold bg-emerald-200 text-emerald-900 uppercase tracking-wide">
                Primary Route Active
              </span>
              <span class="text-xs font-semibold text-emerald-950">${escapeHtml(info.model_used)}</span>
              <span class="text-xs text-emerald-700 bg-emerald-100/80 px-2 py-0.5 rounded">Vector Dot Product in ${info.latency_ms}ms</span>
            </div>
            <p class="text-xs text-emerald-800 mt-1 leading-relaxed">
              Full vocabulary match confirmed. Processed tokens: 
              ${info.query_tokens.map(t => `<code class="bg-emerald-200/60 text-emerald-950 px-1.5 py-0.5 rounded text-[11px] font-mono mr-1">${escapeHtml(t)}</code>`).join("")}
              High-confidence 100D dense semantic representations retrieved via normalized cosine similarity.
            </p>
          </div>
          <button onclick="openComparisonWithCurrent()" class="text-xs font-semibold bg-white border border-emerald-300 text-emerald-900 px-3 py-1.5 rounded-lg hover:bg-emerald-100 transition-colors shrink-0">
            Compare with FastText & TF-IDF
          </button>
        </div>
      </div>
    `;
  }

  el.routingBanner.innerHTML = bannerHtml;
}

// Render Product Cards Grid
function renderResults() {
  if (!state.recommendations.length) {
    el.resultsGrid.innerHTML = `
      <div class="col-span-full py-16 text-center">
        <div class="inline-flex items-center justify-center w-14 h-14 rounded-full bg-slate-100 text-slate-400 mb-3">
          <svg class="w-6 h-6" fill="none" stroke="currentColor" viewBox="0 0 24 24"><path stroke-linecap="round" stroke-linejoin="round" stroke-width="2" d="M21 21l-6-6m2-5a7 7 0 11-14 0 7 7 0 0114 0z"></path></svg>
        </div>
        <h3 class="text-base font-semibold text-slate-800">No matching recommendations found</h3>
        <p class="text-sm text-slate-500 mt-1">Try broadening your search query or selecting a different category filter.</p>
      </div>
    `;
    return;
  }

  let html = "";
  state.recommendations.forEach((item) => {
    const matchPct = Math.round((item.similarity_score || 0) * 100);
    const scoreColorClass = matchPct >= 80 ? "match-badge-emerald" : matchPct >= 65 ? "match-badge-indigo" : "bg-slate-700";
    const routeBadgeClass = item.model_route && item.model_route.includes("FastText") ? "bg-amber-100 text-amber-900 border-amber-300" : "bg-indigo-50 text-indigo-700 border-indigo-200";

    html += `
      <div class="product-card bg-white rounded-2xl border border-slate-200/90 overflow-hidden flex flex-col justify-between group shadow-sm">
        <div>
          <!-- Thumbnail & Badges -->
          <div class="relative bg-slate-50 aspect-square overflow-hidden flex items-center justify-center p-3">
            <img 
              src="${escapeHtml(item.image)}" 
              alt="${escapeHtml(item.name)}" 
              loading="lazy" 
              class="max-h-full max-w-full object-contain group-hover:scale-105 transition-transform duration-300"
              onerror="this.onerror=null;this.src='https://images.unsplash.com/photo-1523275335684-37898b6baf30?w=500&auto=format&fit=crop&q=60';"
            />
            
            <!-- Match Score Overlay -->
            <div class="absolute top-2.5 left-2.5 ${scoreColorClass} text-white text-[11px] font-bold px-2.5 py-1 rounded-full flex items-center gap-1 shadow-md">
              <svg class="w-3 h-3" fill="currentColor" viewBox="0 0 20 20"><path fill-rule="evenodd" d="M11.3 1.046A1 1 0 0112 2v5h4a1 1 0 01.82 1.573l-7 10A1 1 0 018 18v-5H4a1 1 0 01-.82-1.573l7-10a1 1 0 011.12-.38z" clip-rule="evenodd"></path></svg>
              <span>${matchPct}% Match</span>
            </div>

            <!-- Quick Action Floating Button -->
            <button 
              onclick="openProductDetail(${item.catalog_id})" 
              title="Inspect Product & NLP Embedding" 
              class="absolute bottom-2.5 right-2.5 w-8 h-8 rounded-full bg-white/95 text-slate-700 hover:text-indigo-600 hover:bg-white shadow-md flex items-center justify-center opacity-0 group-hover:opacity-100 transition-all transform translate-y-1 group-hover:translate-y-0"
            >
              <svg class="w-4 h-4" fill="none" stroke="currentColor" viewBox="0 0 24 24"><path stroke-linecap="round" stroke-linejoin="round" stroke-width="2" d="M15 12a3 3 0 11-6 0 3 3 0 016 0z"></path><path stroke-linecap="round" stroke-linejoin="round" stroke-width="2" d="M2.458 12C3.732 7.943 7.523 5 12 5c4.478 0 8.268 2.943 9.542 7-1.274 4.057-5.064 7-9.542 7-4.477 0-8.268-2.943-9.542-7z"></path></svg>
            </button>
          </div>

          <!-- Product Details -->
          <div class="p-4">
            <!-- Category & Route Pill -->
            <div class="flex items-center justify-between gap-2 mb-2">
              <span class="text-[11px] font-semibold tracking-wider uppercase text-slate-600 truncate">
                ${escapeHtml(item.main_category)}
              </span>
              <span class="text-[10px] font-mono border px-1.5 py-0.5 rounded ${routeBadgeClass}">
                ${escapeHtml(item.model_route || "W2V")}
              </span>
            </div>

            <!-- Product Title -->
            <h4 
              onclick="openProductDetail(${item.catalog_id})"
              class="text-sm font-semibold text-slate-900 line-clamp-2 hover:text-indigo-600 cursor-pointer transition-colors leading-snug h-[2.6rem]" 
              title="${escapeHtml(item.name)}"
            >
              ${escapeHtml(item.name)}
            </h4>

            <!-- Ratings -->
            <div class="flex items-center gap-1.5 mt-2 text-xs">
              <div class="flex items-center text-amber-400">
                <svg class="w-3.5 h-3.5 fill-current" viewBox="0 0 20 20"><path d="M9.049 2.927c.3-.921 1.603-.921 1.902 0l1.07 3.292a1 1 0 00.95.69h3.462c.969 0 1.371 1.24.588 1.81l-2.8 2.034a1 1 0 00-.364 1.118l1.07 3.292c.3.921-.755 1.688-1.54 1.118l-2.8-2.034a1 1 0 00-1.175 0l-2.8 2.034c-.784.57-1.838-.197-1.539-1.118l1.07-3.292a1 1 0 00-.364-1.118L2.98 8.72c-.783-.57-.38-1.81.588-1.81h3.461a1 1 0 00.951-.69l1.07-3.292z"></path></svg>
                <span class="ml-1 font-bold text-slate-800">${item.ratings !== "N/A" ? item.ratings : "4.0"}</span>
              </div>
              <span class="text-slate-500">(${escapeHtml(item.no_of_ratings || "0")})</span>
            </div>

            <!-- Pricing -->
            <div class="flex items-baseline gap-2 mt-2.5">
              <span class="text-base font-extrabold text-slate-900">${escapeHtml(item.discount_price)}</span>
              ${item.actual_price && item.actual_price !== item.discount_price ? `<span class="text-xs text-slate-600 line-through">${escapeHtml(item.actual_price)}</span>` : ""}
            </div>
          </div>
        </div>

        <!-- Footer Actions -->
        <div class="p-4 pt-0 flex flex-col gap-2">
          <div class="grid grid-cols-2 gap-2">
            <button 
              onclick="findSimilar(${item.catalog_id}, '${escapeJsString(item.name)}')" 
              class="w-full flex items-center justify-center gap-1.5 px-2.5 py-1.5 text-xs font-semibold rounded-lg bg-indigo-50 text-indigo-700 hover:bg-indigo-100 border border-indigo-200 transition-colors"
              title="Find products semantically similar to this item"
            >
              <svg class="w-3.5 h-3.5" fill="none" stroke="currentColor" viewBox="0 0 24 24"><path stroke-linecap="round" stroke-linejoin="round" stroke-width="2" d="M19.428 15.428a2 2 0 00-1.022-.547l-2.387-.477a6 6 0 00-3.86.517l-.318.158a6 6 0 01-3.86.517L6.05 15.21a2 2 0 00-1.806.547M8 4h8l-1 1v5.172a2 2 0 00.586 1.414l5 5c1.26 1.26.367 3.414-1.415 3.414H4.828c-1.782 0-2.674-2.154-1.414-3.414l5-5A2 2 0 009 10.172V5L8 4z"></path></svg>
              <span>Similar</span>
            </button>

            <a 
              href="${escapeHtml(item.link || '#')}" 
              target="_blank" 
              rel="noopener noreferrer" 
              class="w-full flex items-center justify-center gap-1.5 px-2.5 py-1.5 text-xs font-semibold rounded-lg bg-slate-100 text-slate-700 hover:bg-slate-200 border border-slate-200 transition-colors"
            >
              <svg class="w-3.5 h-3.5" fill="none" stroke="currentColor" viewBox="0 0 24 24"><path stroke-linecap="round" stroke-linejoin="round" stroke-width="2" d="M10 6H6a2 2 0 00-2 2v10a2 2 0 002 2h10a2 2 0 002-2v-4M14 4h6m0 0v6m0-6L10 14"></path></svg>
              <span>Amazon</span>
            </a>
          </div>

          <button 
            onclick="addToCart(${item.catalog_id})" 
            class="w-full flex items-center justify-center gap-1.5 py-2 text-xs font-bold rounded-lg bg-slate-900 text-white hover:bg-indigo-600 transition-colors shadow-sm"
          >
            <svg class="w-3.5 h-3.5" fill="none" stroke="currentColor" viewBox="0 0 24 24"><path stroke-linecap="round" stroke-linejoin="round" stroke-width="2" d="M16 11V7a4 4 0 00-8 0v4M5 9h14l1 12H4L5 9z"></path></svg>
            <span>Add to Cart</span>
          </button>
        </div>
      </div>
    `;
  });

  el.resultsGrid.innerHTML = html;
}

function showSkeletons() {
  let html = "";
  for (let i = 0; i < 8; i++) {
    html += `
      <div class="bg-white rounded-2xl border border-slate-200/80 p-4 flex flex-col justify-between">
        <div>
          <div class="aspect-square rounded-xl skeleton mb-4"></div>
          <div class="h-3 w-1/3 rounded skeleton mb-2"></div>
          <div class="h-4 w-full rounded skeleton mb-1.5"></div>
          <div class="h-4 w-2/3 rounded skeleton mb-3"></div>
          <div class="h-3 w-1/2 rounded skeleton"></div>
        </div>
        <div class="mt-4 pt-4 border-t border-slate-100 flex gap-2">
          <div class="h-8 flex-1 rounded-lg skeleton"></div>
          <div class="h-8 flex-1 rounded-lg skeleton"></div>
        </div>
      </div>
    `;
  }
  el.resultsGrid.innerHTML = html;
}

// Side-by-Side Model Comparison (Notebook Cell 20)
window.openComparisonModal = async function(queryOverride = null) {
  const query = queryOverride || state.query || "wireless mouse";
  el.compareModal.classList.remove("hidden");
  el.compareModalContent.innerHTML = `
    <div class="py-16 text-center">
      <div class="inline-block animate-spin rounded-full h-8 w-8 border-4 border-indigo-600 border-t-transparent mb-3"></div>
      <p class="text-sm font-semibold text-slate-700">Evaluating TF-IDF, Word2Vec, and FastText side-by-side...</p>
    </div>
  `;

  try {
    const res = await fetch(`${API_BASE}/compare`, {
      method: "POST",
      headers: { "Content-Type": "application/json" },
      body: JSON.stringify({ query: query, top_n: 5 }),
    });

    if (!res.ok) throw new Error("Comparison failed");
    const data = await res.json();
    state.comparisonData = data;
    renderComparisonTable(data);
  } catch (err) {
    el.compareModalContent.innerHTML = `<div class="p-6 text-center text-rose-600">Failed to load comparison: ${err.message}</div>`;
  }
};

window.openComparisonWithCurrent = function() {
  openComparisonModal(state.query);
};

function renderComparisonTable(data) {
  const isOov = data.oov_words && data.oov_words.length > 0;

  let html = `
    <div class="space-y-4">
      <!-- Header query details -->
      <div class="flex items-center justify-between flex-wrap gap-2 p-3.5 rounded-xl bg-slate-50 border border-slate-200">
        <div>
          <span class="text-xs font-semibold text-slate-500 uppercase tracking-wider">Evaluation Query:</span>
          <span class="text-sm font-bold text-slate-900 ml-1">"${escapeHtml(data.query)}"</span>
          <span class="text-xs text-slate-500 ml-2">(Cleaned: <code>${escapeHtml(data.cleaned_query || data.query)}</code>)</span>
        </div>
        <div class="flex items-center gap-2">
          ${isOov ? `<span class="px-2 py-0.5 rounded text-xs font-semibold bg-amber-100 text-amber-800">⚠️ OOV Tokens: ${data.oov_words.join(", ")}</span>` : `<span class="px-2 py-0.5 rounded text-xs font-semibold bg-emerald-100 text-emerald-800">✓ In-Vocabulary Query</span>`}
          <span class="text-xs bg-slate-200 px-2 py-0.5 rounded font-mono text-slate-700">${data.latency_ms} ms</span>
        </div>
      </div>

      <!-- Quick Test Buttons in Comparison Modal -->
      <div class="flex items-center gap-2 flex-wrap text-xs">
        <span class="text-slate-500 font-semibold">Test Queries:</span>
        <button onclick="openComparisonModal('wireless mouse')" class="px-2.5 py-1 rounded-md border border-slate-300 hover:bg-slate-100 text-slate-700">Wireless Mouse (In-Vocab)</button>
        <button onclick="openComparisonModal('bluetoth wireles earphone')" class="px-2.5 py-1 rounded-md border border-amber-300 bg-amber-50 hover:bg-amber-100 text-amber-900 font-semibold">bluetoth wireles earphone (Typo Fallback)</button>
        <button onclick="openComparisonModal('cotton summer dress')" class="px-2.5 py-1 rounded-md border border-slate-300 hover:bg-slate-100 text-slate-700">Cotton Summer Dress</button>
        <button onclick="openComparisonModal('water botle')" class="px-2.5 py-1 rounded-md border border-amber-300 bg-amber-50 hover:bg-amber-100 text-amber-900 font-semibold">water botle (Typo)</button>
      </div>

      <!-- Comparative Insight Box -->
      <div class="p-3.5 rounded-xl border border-indigo-200 bg-indigo-50/70 text-xs text-indigo-900 leading-relaxed">
        <strong>Engine Evaluation Insight:</strong> ${escapeHtml(data.insights)}
      </div>

      <!-- Table View -->
      <div class="overflow-x-auto rounded-xl border border-slate-200">
        <table class="w-full text-left border-collapse text-xs">
          <thead>
            <tr class="bg-slate-100/90 text-slate-700 border-b border-slate-200 font-semibold">
              <th class="py-3 px-3 w-12 text-center">Rank</th>
              <th class="py-3 px-3 w-1/3 border-r border-slate-200">
                <div class="flex items-center justify-between">
                  <span>TF-IDF (Baseline)</span>
                  <span class="font-normal text-[10px] text-slate-500">Keyword Lexical</span>
                </div>
              </th>
              <th class="py-3 px-3 w-1/3 border-r border-slate-200">
                <div class="flex items-center justify-between">
                  <span class="text-indigo-700">Word2Vec (Primary)</span>
                  <span class="font-normal text-[10px] text-slate-500">Dense Semantic</span>
                </div>
              </th>
              <th class="py-3 px-3 w-1/3">
                <div class="flex items-center justify-between">
                  <span class="text-amber-700">FastText (Fallback)</span>
                  <span class="font-normal text-[10px] text-slate-500">Subword N-grams</span>
                </div>
              </th>
            </tr>
          </thead>
          <tbody class="divide-y divide-slate-200">
            ${data.rows.map(row => `
              <tr class="hover:bg-slate-50/60 transition-colors">
                <td class="py-3 px-3 text-center font-bold text-slate-500">${row.rank}</td>
                
                <!-- TF-IDF Column -->
                <td class="py-3 px-3 border-r border-slate-200 align-top">
                  ${renderComparisonCell(row.tfidf, "tfidf")}
                </td>

                <!-- Word2Vec Column -->
                <td class="py-3 px-3 border-r border-slate-200 align-top">
                  ${renderComparisonCell(row.word2vec, "word2vec")}
                </td>

                <!-- FastText Column -->
                <td class="py-3 px-3 align-top">
                  ${renderComparisonCell(row.fasttext, "fasttext")}
                </td>
              </tr>
            `).join("")}
          </tbody>
        </table>
      </div>
    </div>
  `;

  el.compareModalContent.innerHTML = html;
}

function renderComparisonCell(cell, engine) {
  if (!cell) {
    return `<span class="text-slate-400 italic">No match</span>`;
  }

  const scorePct = Math.round(cell.similarity_score * 100);
  const barColor = engine === "fasttext" ? "bg-amber-500" : engine === "word2vec" ? "bg-indigo-600" : "bg-slate-600";

  return `
    <div class="flex gap-2.5">
      <img 
        src="${escapeHtml(cell.image)}" 
        alt="" 
        class="w-10 h-10 object-contain rounded border border-slate-200 bg-white shrink-0 p-0.5" 
        onerror="this.onerror=null;this.src='https://images.unsplash.com/photo-1523275335684-37898b6baf30?w=500&auto=format&fit=crop&q=60';"
      />
      <div class="min-w-0 flex-1">
        <p class="font-medium text-slate-900 line-clamp-2 leading-tight" title="${escapeHtml(cell.name)}">${escapeHtml(cell.name)}</p>
        <span class="text-[10px] text-slate-500 uppercase">${escapeHtml(cell.main_category)}</span>
        
        <div class="flex items-center gap-2 mt-1.5">
          <div class="w-16 h-1.5 rounded-full bg-slate-200 overflow-hidden">
            <div class="${barColor} h-full" style="width: ${Math.min(100, Math.max(0, scorePct))}%"></div>
          </div>
          <span class="text-[11px] font-bold text-slate-700">${cell.similarity_score.toFixed(4)}</span>
        </div>
      </div>
    </div>
  `;
}

// Product Detail Modal
window.openProductDetail = async function(catalogId) {
  el.productModal.classList.remove("hidden");
  el.productModalContent.innerHTML = `
    <div class="py-16 text-center">
      <div class="inline-block animate-spin rounded-full h-8 w-8 border-4 border-indigo-600 border-t-transparent mb-3"></div>
      <p class="text-sm font-semibold text-slate-700">Loading product profile & NLP vector data...</p>
    </div>
  `;

  try {
    const res = await fetch(`${API_BASE}/products/${catalogId}`);
    if (!res.ok) throw new Error("Failed to load product detail");
    const data = await res.json();
    state.selectedProduct = data;

    let vectorHtml = "";
    if (data.vector_preview && data.vector_preview.length) {
      vectorHtml = data.vector_preview.map((v, i) => `<span class="bg-indigo-900/60 text-indigo-200 px-2 py-1 rounded font-mono text-xs">d${i}:${v}</span>`).join(" ");
    }

    el.productModalContent.innerHTML = `
      <div class="grid grid-cols-1 md:grid-cols-2 gap-6 p-2">
        <!-- Product Image -->
        <div class="bg-slate-50 rounded-2xl p-6 flex items-center justify-center border border-slate-200/80">
          <img 
            src="${escapeHtml(data.image)}" 
            alt="${escapeHtml(data.name)}" 
            class="max-h-72 max-w-full object-contain"
            onerror="this.onerror=null;this.src='https://images.unsplash.com/photo-1523275335684-37898b6baf30?w=500&auto=format&fit=crop&q=60';"
          />
        </div>

        <!-- Meta Details -->
        <div class="flex flex-col justify-between">
          <div>
            <div class="flex items-center gap-2 mb-2">
              <span class="text-xs font-semibold px-2.5 py-0.5 rounded-full bg-slate-100 text-slate-700 uppercase">
                ${escapeHtml(data.main_category)}
              </span>
              <span class="text-xs text-slate-600 font-mono">Catalog ID: #${data.catalog_id}</span>
            </div>

            <h3 class="text-lg font-bold text-slate-900 leading-snug">${escapeHtml(data.name)}</h3>

            <!-- Rating & Reviews -->
            <div class="flex items-center gap-2 mt-2.5">
              <div class="flex items-center text-amber-400">
                <svg class="w-4 h-4 fill-current" viewBox="0 0 20 20"><path d="M9.049 2.927c.3-.921 1.603-.921 1.902 0l1.07 3.292a1 1 0 00.95.69h3.462c.969 0 1.371 1.24.588 1.81l-2.8 2.034a1 1 0 00-.364 1.118l1.07 3.292c.3.921-.755 1.688-1.54 1.118l-2.8-2.034a1 1 0 00-1.175 0l-2.8 2.034c-.784.57-1.838-.197-1.539-1.118l1.07-3.292a1 1 0 00-.364-1.118L2.98 8.72c-.783-.57-.38-1.81.588-1.81h3.461a1 1 0 00.951-.69l1.07-3.292z"></path></svg>
                <span class="ml-1 text-sm font-bold text-slate-800">${data.ratings !== "N/A" ? data.ratings : "4.0"}</span>
              </div>
              <span class="text-xs text-slate-600">(${escapeHtml(data.no_of_ratings || "0")} customer reviews)</span>
            </div>

            <!-- Price -->
            <div class="flex items-baseline gap-3 mt-4">
              <span class="text-2xl font-black text-slate-900">${escapeHtml(data.discount_price)}</span>
              ${data.actual_price && data.actual_price !== data.discount_price ? `<span class="text-sm text-slate-600 line-through">${escapeHtml(data.actual_price)}</span>` : ""}
            </div>

            <!-- NLP Diagnostics Section -->
            <div class="mt-6 p-4 rounded-xl bg-slate-900 text-slate-200 text-xs space-y-2">
              <div class="flex items-center justify-between text-slate-400 font-semibold border-b border-slate-800 pb-2">
                <span>NLP Preprocessing & Embeddings</span>
                <span class="text-[10px] bg-indigo-500/30 text-indigo-300 px-2 py-0.5 rounded font-mono">100 Dimensions</span>
              </div>
              <div>
                <span class="text-slate-400">Cleaned Lemmatized Corpus:</span>
                <p class="font-mono text-emerald-400 mt-0.5 break-words">${escapeHtml(data.cleaned_text || "N/A")}</p>
              </div>
              <div>
                <span class="text-slate-400">Dense Vector Sample (First 5 dims):</span>
                <div class="flex flex-wrap gap-1.5 mt-1">${vectorHtml}</div>
              </div>
            </div>
          </div>

          <!-- Buttons -->
          <div class="flex gap-3 mt-6">
            <button 
              onclick="findSimilar(${data.catalog_id}, '${escapeJsString(data.name)}')" 
              class="flex-1 py-2.5 px-4 rounded-xl bg-indigo-600 hover:bg-indigo-700 text-white font-bold text-xs flex items-center justify-center gap-2 shadow-md transition-all"
            >
              <svg class="w-4 h-4" fill="none" stroke="currentColor" viewBox="0 0 24 24"><path stroke-linecap="round" stroke-linejoin="round" stroke-width="2" d="M19.428 15.428a2 2 0 00-1.022-.547l-2.387-.477a6 6 0 00-3.86.517l-.318.158a6 6 0 01-3.86.517L6.05 15.21a2 2 0 00-1.806.547M8 4h8l-1 1v5.172a2 2 0 00.586 1.414l5 5c1.26 1.26.367 3.414-1.415 3.414H4.828c-1.782 0-2.674-2.154-1.414-3.414l5-5A2 2 0 009 10.172V5L8 4z"></path></svg>
              <span>Recommend Similar Products</span>
            </button>

            <a 
              href="${escapeHtml(data.link || '#')}" 
              target="_blank" 
              rel="noopener noreferrer" 
              class="py-2.5 px-4 rounded-xl bg-slate-100 hover:bg-slate-200 text-slate-800 font-bold text-xs flex items-center justify-center gap-1.5 border border-slate-200 transition-colors"
            >
              <svg class="w-4 h-4" fill="none" stroke="currentColor" viewBox="0 0 24 24"><path stroke-linecap="round" stroke-linejoin="round" stroke-width="2" d="M10 6H6a2 2 0 00-2 2v10a2 2 0 002 2h10a2 2 0 002-2v-4M14 4h6m0 0v6m0-6L10 14"></path></svg>
              <span>Amazon Page</span>
            </a>
          </div>
        </div>
      </div>
    `;
  } catch (err) {
    el.productModalContent.innerHTML = `<div class="p-6 text-center text-rose-600">Error loading product: ${err.message}</div>`;
  }
};

// Architecture & Assessment Modal
window.openArchitectureModal = function() {
  el.archModal.classList.remove("hidden");
};

// Cart Functionality
window.addToCart = function(catalogId) {
  const prod = state.recommendations.find(p => p.catalog_id === catalogId) || state.selectedProduct;
  if (!prod) return;

  const existing = state.cart.find(c => c.product.catalog_id === catalogId);
  if (existing) {
    existing.quantity += 1;
  } else {
    state.cart.push({ product: prod, quantity: 1 });
  }

  updateCartUI();
  showToast(`Added "${prod.name.substring(0, 24)}..." to cart!`, "success");
};

window.removeFromCart = function(catalogId) {
  state.cart = state.cart.filter(c => c.product.catalog_id !== catalogId);
  updateCartUI();
};

window.toggleCart = function() {
  el.cartDrawer.classList.toggle("translate-x-full");
  el.cartOverlay.classList.toggle("hidden");
};

window.closeCart = function() {
  el.cartDrawer.classList.add("translate-x-full");
  el.cartOverlay.classList.add("hidden");
};

function updateCartUI() {
  const totalCount = state.cart.reduce((sum, item) => sum + item.quantity, 0);
  el.cartCount.textContent = totalCount;
  el.cartCount.style.display = totalCount > 0 ? "flex" : "none";

  if (!state.cart.length) {
    el.cartItemsList.innerHTML = `
      <div class="py-12 text-center text-slate-400">
        <svg class="w-12 h-12 mx-auto stroke-current opacity-40 mb-2" fill="none" viewBox="0 0 24 24"><path stroke-linecap="round" stroke-linejoin="round" stroke-width="2" d="M16 11V7a4 4 0 00-8 0v4M5 9h14l1 12H4L5 9z"></path></svg>
        <p class="text-sm font-semibold">Your cart is empty</p>
        <p class="text-xs text-slate-500 mt-1">Discover products using semantic vector search!</p>
      </div>
    `;
    el.cartSubtotal.textContent = "₹0";
    return;
  }

  let totalNum = 0;
  let html = "";
  state.cart.forEach(item => {
    const rawPrice = item.product.discount_price ? item.product.discount_price.replace(/[^\d.]/g, "") : "0";
    const numPrice = parseFloat(rawPrice) || 0;
    totalNum += numPrice * item.quantity;

    html += `
      <div class="flex items-center gap-3 p-3 rounded-xl bg-slate-50 border border-slate-200">
        <img 
          src="${escapeHtml(item.product.image)}" 
          alt="" 
          class="w-12 h-12 object-contain rounded bg-white border border-slate-200 p-1 shrink-0" 
          onerror="this.onerror=null;this.src='https://images.unsplash.com/photo-1523275335684-37898b6baf30?w=500&auto=format&fit=crop&q=60';"
        />
        <div class="min-w-0 flex-1">
          <p class="text-xs font-semibold text-slate-900 line-clamp-1">${escapeHtml(item.product.name)}</p>
          <div class="flex items-center justify-between mt-1 text-xs">
            <span class="font-extrabold text-slate-900">${escapeHtml(item.product.discount_price)} × ${item.quantity}</span>
            <button onclick="removeFromCart(${item.product.catalog_id})" class="text-rose-500 hover:text-rose-700 text-xs font-semibold">Remove</button>
          </div>
        </div>
      </div>
    `;
  });

  el.cartItemsList.innerHTML = html;
  el.cartSubtotal.textContent = `₹${totalNum.toLocaleString()}`;
}

window.checkoutCart = function() {
  if (!state.cart.length) return;
  showToast("Order simulated! Acme Retail Express shipping initiated.", "success");
  state.cart = [];
  updateCartUI();
  closeCart();
};

// Modal Helpers
window.closeAllModals = function() {
  el.productModal.classList.add("hidden");
  el.compareModal.classList.add("hidden");
  el.archModal.classList.add("hidden");
};

// Toast Notifications
function showToast(message, type = "info") {
  const toast = document.createElement("div");
  const bgClass = type === "success" ? "bg-slate-900 text-emerald-400 border-emerald-500/40" : type === "error" ? "bg-rose-900 text-rose-100 border-rose-500/40" : "bg-slate-900 text-white border-slate-700";

  toast.className = `toast max-w-sm px-4 py-3 rounded-xl shadow-xl border text-xs font-semibold flex items-center gap-2 ${bgClass}`;
  toast.innerHTML = `
    <span>${escapeHtml(message)}</span>
  `;

  el.toastContainer.appendChild(toast);
  setTimeout(() => {
    toast.style.opacity = "0";
    toast.style.transform = "translateY(10px)";
    toast.style.transition = "all 0.3s ease";
    setTimeout(() => toast.remove(), 300);
  }, 3500);
}

// Security & Sanitization Helpers
function escapeHtml(str) {
  if (!str) return "";
  return String(str)
    .replace(/&/g, "&amp;")
    .replace(/</g, "&lt;")
    .replace(/>/g, "&gt;")
    .replace(/"/g, "&quot;")
    .replace(/'/g, "&#039;");
}

function escapeJsString(str) {
  if (!str) return "";
  return String(str).replace(/'/g, "\\'").replace(/"/g, '\\"');
}

function capitalize(str) {
  if (!str) return "";
  return str.charAt(0).toUpperCase() + str.slice(1);
}
