/* ============================================================
   EXPIRYCARE — app.js
   Frontend prototype: HTML + CSS + vanilla JavaScript.
   Data lives in the browser's localStorage (no backend yet).
   Later: replace the functions in the STORAGE section with
   Flask API calls (fetch) and Firebase/Firestore.
   v2: premium UI layer added (icons, toasts, nav, dashboard
   widgets, inventory UX, live preview). Core logic is unchanged.
   ============================================================ */

// ======================================
// STORAGE  (only this section touches localStorage)
// ======================================

function getProducts() {
    const saved = localStorage.getItem("products");
    if (!saved) {
        return [];
    }
    return JSON.parse(saved);
}

function saveProducts(products) {
    localStorage.setItem("products", JSON.stringify(products));
}

function getProductById(id) {
    const products = getProducts();
    for (let i = 0; i < products.length; i++) {
        if (products[i].id === id) {
            return products[i];
        }
    }
    return null;
}

function getUsers() {
    const saved = localStorage.getItem("users");
    if (!saved) {
        return [];
    }
    return JSON.parse(saved);
}

function saveUsers(users) {
    localStorage.setItem("users", JSON.stringify(users));
}

// "Remember me" ticked -> localStorage. Not ticked -> sessionStorage
// (forgotten when the browser tab is closed).
function getCurrentUser() {
    const saved = localStorage.getItem("currentUser") || sessionStorage.getItem("currentUser");
    if (!saved) {
        return null;
    }
    return JSON.parse(saved);
}

function saveCurrentUser(user, remember) {
    const text = JSON.stringify(user);
    if (remember === undefined) {
        // keep it wherever it already is (used by the profile page)
        remember = localStorage.getItem("currentUser") !== null;
    }
    localStorage.removeItem("currentUser");
    sessionStorage.removeItem("currentUser");
    if (remember) {
        localStorage.setItem("currentUser", text);
    } else {
        sessionStorage.setItem("currentUser", text);
    }
}

function clearCurrentUser() {
    localStorage.removeItem("currentUser");
    sessionStorage.removeItem("currentUser");
}

function getSettings() {
    const saved = localStorage.getItem("settings");
    const defaults = { alertThresholds: [3], defaultSort: "expiry-date" };
    if (!saved) {
        return defaults;
    }
    return Object.assign(defaults, JSON.parse(saved));
}

function saveSettings(settings) {
    localStorage.setItem("settings", JSON.stringify(settings));
}

// A message to show on the NEXT page (e.g. after a redirect)
function setFlashMessage(message, type) {
    sessionStorage.setItem("flash", JSON.stringify({ message: message, type: type }));
}

function showFlashMessage() {
    const saved = sessionStorage.getItem("flash");
    if (saved) {
        sessionStorage.removeItem("flash");
        const flash = JSON.parse(saved);
        showToast(flash.message, flash.type);
    }
}

// ======================================
// USER / AUTHENTICATION  (prototype only — passwords are NOT secure here)
// ======================================

const PROTECTED_PAGES = [
    "page-dashboard", "page-inventory", "page-add-product", "page-product-details",
    "page-edit-product", "page-alerts", "page-healthcare-guidance", "page-profile"
];

function checkLogin(pageId) {
    if (PROTECTED_PAGES.indexOf(pageId) !== -1 && !getCurrentUser()) {
        window.location.href = "login.html";
        return false;
    }
    return true;
}

function showCurrentUserName() {
    const user = getCurrentUser();
    if (!user) {
        return;
    }
    const nameEl = document.getElementById("current-user-name");
    if (nameEl) {
        nameEl.textContent = user.name;
    }
    const avatar = document.querySelector(".user-avatar");
    if (avatar) {
        avatar.textContent = user.name.charAt(0).toUpperCase();
    }
}

function setupLogout() {
    const links = document.querySelectorAll(".logout-link");
    links.forEach(function (link) {
        link.addEventListener("click", function () {
            clearCurrentUser();           // products stay saved
            setFlashMessage("You have been logged out.", "info");
        });
    });
}

function isValidEmail(email) {
    return /^[^\s@]+@[^\s@]+\.[^\s@]+$/.test(email);
}

// ======================================
// EXPIRY CALCULATIONS  (one place, used by every page)
// ======================================

const SOON_LIMIT_DAYS = 30;     // 30 days or fewer = Expiring Soon
const CATEGORY_NAMES = {
    "grocery": "Grocery",
    "medicine": "Medicine",
    "personal-care": "Personal Care",
    "other": "Other"
};

function parseDate(text) {
    const parts = text.split("-");
    return new Date(Number(parts[0]), Number(parts[1]) - 1, Number(parts[2]));
}

function getToday() {
    const now = new Date();
    return new Date(now.getFullYear(), now.getMonth(), now.getDate());
}

function toInputDate(date) {
    const m = String(date.getMonth() + 1).padStart(2, "0");
    const d = String(date.getDate()).padStart(2, "0");
    return date.getFullYear() + "-" + m + "-" + d;
}

function getDaysFromDate(expiryText) {
    const msPerDay = 24 * 60 * 60 * 1000;
    return Math.round((parseDate(expiryText) - getToday()) / msPerDay);
}

function getDaysRemaining(product) {
    if (!product || !product.expiryDate) return null;
    return getDaysFromDate(product.expiryDate);
}

function getStatusFromDays(days) {
    if (days < 0) {
        return "expired";
    }
    if (days <= SOON_LIMIT_DAYS) {
        return "expiring-soon";
    }
    return "active";
}

function getStatus(product) {
    if (!product || !product.name || product.name === "Unidentified Product") return "unidentified";
    if (!product.expiryDate) return product.trackingStatus || "expiry-unknown";
    if (product.expirySource === "estimated") return "estimated-expiry";
    return getStatusFromDays(getDaysRemaining(product));
}

function getStatusLabel(status) {
    const extra = { "unidentified": "Unidentified Product", "expiry-unknown": "Expiry Unknown", "needs-verification": "Needs Verification", "estimated-expiry": "Estimated Expiry" };
    if (extra[status]) return extra[status];
    if (status === "expired") {
        return "Expired";
    }
    if (status === "expiring-soon") {
        return "Expiring Soon";
    }
    return "Active";
}

function getStatusClass(status) {
    if (["unidentified", "expiry-unknown", "needs-verification", "estimated-expiry"].includes(status)) return "status-badge-expiring";
    if (status === "expired") {
        return "status-badge-expired";
    }
    if (status === "expiring-soon") {
        return "status-badge-expiring";
    }
    return "status-badge-active";
}

function pluralDays(n) {
    return n === 1 ? "1 day" : n + " days";
}

// "Expires in 3 days" / "Expired 2 days ago"
function describeDays(days) {
    if (days < 0) {
        return "Expired " + pluralDays(Math.abs(days)) + " ago";
    }
    if (days === 0) {
        return "Expires today";
    }
    return "Expires in " + pluralDays(days);
}

function formatDate(text) {
    if (!text) return "Unknown";
    const date = parseDate(text);
    if (Number.isNaN(date.getTime())) return "Unknown";
    return date.toLocaleDateString("en-IN", { day: "numeric", month: "short", year: "numeric" });
}

function getCategoryName(value) {
    return CATEGORY_NAMES[value] || "Other";
}

// The biggest ticked reminder window (7, 3 or 1 day). Used on the Alerts page.
function getAlertWindow() {
    const list = getSettings().alertThresholds;
    if (!list || list.length === 0) {
        return 7;
    }
    return Math.max.apply(null, list.map(Number));
}

function sortByExpiry(products) {
    return products.slice().sort(function (a, b) {
        return getDaysRemaining(a) - getDaysRemaining(b);
    });
}

function countByStatus(products) {
    const counts = { active: 0, "expiring-soon": 0, expired: 0, "expiry-unknown": 0, "estimated-expiry": 0, "needs-verification": 0, unidentified: 0 };
    products.forEach(function (p) { const status = getStatus(p); if (Object.prototype.hasOwnProperty.call(counts, status)) counts[status]++; });
    return counts;
}


// ======================================
// ICONS  (inline SVG sprite, no icon library needed)
// ======================================

const ICON_PATHS = {
    logo: '<path d="M12 2.5l8 3v6c0 5.2-3.4 8.7-8 10-4.6-1.3-8-4.8-8-10v-6l8-3z"/><path d="M12 7.5V12l3 2"/>',
    grid: '<rect x="3" y="3" width="7" height="7" rx="1.5"/><rect x="14" y="3" width="7" height="7" rx="1.5"/><rect x="3" y="14" width="7" height="7" rx="1.5"/><rect x="14" y="14" width="7" height="7" rx="1.5"/>',
    box: '<path d="M21 8l-9-5-9 5 9 5 9-5z"/><path d="M3 8v8l9 5 9-5V8M12 13v8"/>',
    plus: '<path d="M12 5v14M5 12h14"/>',
    bell: '<path d="M6 8a6 6 0 1112 0c0 7 3 8 3 8H3s3-1 3-8M10 20a2 2 0 004 0"/>',
    heart: '<path d="M12 21s-8-5.2-8-11a4.5 4.5 0 018-2.8A4.5 4.5 0 0120 10c0 5.8-8 11-8 11z"/>',
    user: '<circle cx="12" cy="8" r="4"/><path d="M4 21c0-4 4-6 8-6s8 2 8 6"/>',
    check: '<circle cx="12" cy="12" r="9"/><path d="M8 12.5l2.7 2.7L16 9.5"/>',
    clock: '<circle cx="12" cy="12" r="9"/><path d="M12 7v5l3 2"/>',
    alert: '<path d="M12 3l10 18H2L12 3z"/><path d="M12 10v5M12 18v.01"/>',
    xcircle: '<circle cx="12" cy="12" r="9"/><path d="M9 9l6 6M15 9l-6 6"/>',
    pill: '<rect x="2.5" y="8.5" width="19" height="7" rx="3.5" transform="rotate(-45 12 12)"/><path d="M8.5 8.5l7 7"/>',
    food: '<path d="M12 8c-2-2-7-1-7 5 0 4 3 8 5 8 1 0 1.5-.5 2-.5s1 .5 2 .5c2 0 5-4 5-8 0-6-5-7-7-5z"/><path d="M12 8c0-2 1-4 3-5"/>',
    droplet: '<path d="M12 3s7 7 7 12a7 7 0 01-14 0c0-5 7-12 7-12z"/>',
    thermo: '<path d="M14 14V5a2 2 0 00-4 0v9a4 4 0 104 0z"/>',
    search: '<circle cx="11" cy="11" r="7"/><path d="M20 20l-4-4"/>',
    x: '<path d="M6 6l12 12M18 6L6 18"/>',
    menu: '<path d="M4 7h16M4 12h16M4 17h16"/>',
    arrow: '<path d="M5 12h14M13 6l6 6-6 6"/>',
    trash: '<path d="M4 7h16M9 7V4h6v3M6 7l1 13h10l1-13"/>',
    edit: '<path d="M4 20h4L19 9l-4-4L4 16v4zM13 7l4 4"/>',
    eye: '<path d="M2 12s4-7 10-7 10 7 10 7-4 7-10 7S2 12 2 12z"/><circle cx="12" cy="12" r="3"/>',
    calendar: '<rect x="3" y="5" width="18" height="16" rx="2"/><path d="M3 10h18M8 3v4M16 3v4"/>',
    info: '<circle cx="12" cy="12" r="9"/><path d="M12 11v5M12 8v.01"/>',
    shield: '<path d="M12 3l8 3v6c0 5-3.5 8-8 9-4.5-1-8-4-8-9V6l8-3z"/><path d="M9 12l2 2 4-4"/>',
    logout: '<path d="M9 4H5a2 2 0 00-2 2v12a2 2 0 002 2h4M16 8l4 4-4 4M20 12H9"/>'
};

// Puts every icon in one hidden <svg>; pages use <svg><use href="#i-name"/></svg>
function injectIconSprite() {
    if (document.getElementById("icon-sprite")) {
        return;
    }
    let html = '<svg id="icon-sprite" width="0" height="0" style="position:absolute" aria-hidden="true" focusable="false">';
    Object.keys(ICON_PATHS).forEach(function (name) {
        html += '<symbol id="i-' + name + '" viewBox="0 0 24 24">' + ICON_PATHS[name] + '</symbol>';
    });
    document.body.insertAdjacentHTML("afterbegin", html + "</svg>");
}

function icon(name, extraClass) {
    return '<svg class="i ' + (extraClass || "") + '" aria-hidden="true" focusable="false"><use href="#i-' + name + '"/></svg>';
}

function productIcon(category) {
    const map = { medicine: "pill", grocery: "food", "personal-care": "droplet", other: "box" };
    return icon(map[category] || "box");
}

// ======================================
// COMMON UI HELPERS
// ======================================

const prefersReducedMotion = window.matchMedia("(prefers-reduced-motion: reduce)").matches;

// Stops text typed by users from being treated as HTML
function esc(text) {
    const div = document.createElement("div");
    div.textContent = text === undefined || text === null ? "" : String(text);
    return div.innerHTML;
}

function setText(id, text) {
    const el = document.getElementById(id);
    if (el) {
        el.textContent = text;
    }
}

function setupPasswordToggle(buttonId, inputId) {
    const button = document.getElementById(buttonId);
    const input = document.getElementById(inputId);
    if (!button || !input) {
        return;
    }
    button.addEventListener("click", function () {
        const showing = input.type === "text";
        input.type = showing ? "password" : "text";
        button.textContent = showing ? "Show" : "Hide";
        button.setAttribute("aria-pressed", showing ? "false" : "true");
    });
}

function setFieldError(inputId, message) {
    const errorEl = document.getElementById(inputId + "-error");
    const input = document.getElementById(inputId);
    if (errorEl) {
        errorEl.textContent = message;
    }
    if (input) {
        if (message) {
            input.setAttribute("aria-invalid", "true");
        } else {
            input.removeAttribute("aria-invalid");
        }
    }
}

function showFormError(boxId, message) {
    const box = document.getElementById(boxId);
    if (!box) {
        return;
    }
    box.textContent = message;
    box.hidden = !message;
}

function focusFirstError(form) {
    const bad = form.querySelector("[aria-invalid='true']");
    if (bad) {
        bad.focus();
    }
}

function animateNumber(element, target) {
    if (prefersReducedMotion || target === 0) {
        element.textContent = target;
        return;
    }
    const duration = 700;
    const start = performance.now();
    function step(now) {
        const progress = Math.min((now - start) / duration, 1);
        element.textContent = Math.round(target * progress);
        if (progress < 1) {
            requestAnimationFrame(step);
        }
    }
    requestAnimationFrame(step);
}

// Scroll reveal: elements fade in when they enter the screen
function setupScrollReveal() {
    const selector = ".reveal-item, .summary-card, .dashboard-priority, .dashboard-secondary, .insights-section, " +
        ".quick-actions, .healthcare-tip, .alert-group, .alert-preferences, .settings-section, .guidance-topic, " +
        ".profile-card, .form-group, .inventory-controls, .pd-identity, .cta-inner, .disclaimer-note, .guidance-cta";
    const items = document.querySelectorAll(selector);

    if (prefersReducedMotion || !("IntersectionObserver" in window)) {
        return;   // leave everything visible
    }
    const observer = new IntersectionObserver(function (entries) {
        entries.forEach(function (entry) {
            if (entry.isIntersecting) {
                entry.target.classList.add("is-visible");
                observer.unobserve(entry.target);
            }
        });
    }, { threshold: 0.1 });

    items.forEach(function (item, index) {
        item.classList.add("reveal");
        item.style.transitionDelay = (index % 4) * 70 + "ms";
        observer.observe(item);
    });
}

// Landing hero: heading, text, buttons appear one after another
// Small helper: gives each child a staggered entrance delay (CSS does the animation)
function stagger(container) {
    if (!container) {
        return;
    }
    Array.prototype.forEach.call(container.children, function (child, i) {
        child.style.animationDelay = Math.min(i, 8) * 40 + "ms";
    });
}

// Make sure the correct nav link has aria-current="page"
function setActiveNav() {
    const file = window.location.pathname.split("/").pop() || "index.html";
    const links = document.querySelectorAll(".app-nav a, .public-nav a");
    links.forEach(function (link) {
        const target = link.getAttribute("href");
        if (target === file && !link.classList.contains("btn")) {
            link.setAttribute("aria-current", "page");
        }
    });
}

// ======================================
// TOAST NOTIFICATIONS
// ======================================

const TOAST_TITLES = { success: "Success", error: "Something went wrong", warning: "Heads up", info: "Notice" };
const TOAST_ICONS = { success: "check", error: "xcircle", warning: "alert", info: "info" };

function showToast(message, type) {
    type = TOAST_ICONS[type] ? type : "info";
    let container = document.getElementById("toast-container");
    if (!container) {
        container = document.createElement("div");
        container.id = "toast-container";
        container.className = "toast-container";
        container.setAttribute("aria-live", "polite");
        document.body.appendChild(container);
    }
    const toast = document.createElement("div");
    toast.className = "toast toast-" + type;
    toast.setAttribute("role", type === "error" ? "alert" : "status");
    toast.innerHTML =
        '<span class="toast-icon">' + icon(TOAST_ICONS[type]) + '</span>' +
        '<div class="toast-body"><span class="toast-title">' + TOAST_TITLES[type] + '</span>' +
        '<span class="toast-text">' + esc(message) + '</span></div>' +
        '<button type="button" class="toast-close" aria-label="Dismiss notification">' + icon("x", "i-sm") + '</button>' +
        '<span class="toast-bar"></span>';
    container.appendChild(toast);

    let timer = null;
    function dismiss() {
        clearTimeout(timer);
        toast.classList.add("toast-hide");
        setTimeout(function () { toast.remove(); }, prefersReducedMotion ? 0 : 250);
    }
    toast.querySelector(".toast-close").addEventListener("click", dismiss);
    timer = setTimeout(dismiss, 3500);
}

// ======================================
// MODALS  (delete confirmation)
// ======================================

let modalOpener = null;   // the button that opened the modal (to return focus)

// The details page already has this modal. Other pages get one created.
function getDeleteModal() {
    let modal = document.getElementById("delete-confirm-modal");
    if (modal) {
        return modal;
    }
    modal = document.createElement("div");
    modal.className = "modal";
    modal.id = "delete-confirm-modal";
    modal.setAttribute("role", "alertdialog");
    modal.setAttribute("aria-labelledby", "delete-confirm-heading");
    modal.setAttribute("aria-describedby", "delete-confirm-text");
    modal.hidden = true;
    modal.innerHTML =
        '<div class="modal-content">' +
        '<span class="modal-icon">' + icon("alert") + '</span>' +
        '<h2 id="delete-confirm-heading">Delete this product?</h2>' +
        '<p id="delete-confirm-text">This action cannot be undone.</p>' +
        '<div class="form-actions">' +
        '<button type="button" class="btn btn-secondary" id="delete-cancel-button">Cancel</button>' +
        '<button type="button" class="btn btn-solid-danger" id="delete-confirm-button">' + icon("trash") + ' Delete</button>' +
        '</div></div>';
    document.body.appendChild(modal);
    return modal;
}

function closeDeleteModal() {
    const modal = getDeleteModal();
    modal.hidden = true;
    if (modalOpener) {
        modalOpener.focus();
    }
}

// Opens the modal; runs onConfirm() if the user clicks Delete
function openDeleteModal(product, onConfirm) {
    const modal = getDeleteModal();
    modalOpener = document.activeElement;
    setText("delete-confirm-text", "“" + product.name + "” will be removed from your inventory. This action cannot be undone.");

    // replace the button to remove old click listeners
    const oldButton = document.getElementById("delete-confirm-button");
    const confirmButton = oldButton.cloneNode(true);
    oldButton.parentNode.replaceChild(confirmButton, oldButton);
    confirmButton.addEventListener("click", function () {
        modal.hidden = true;
        onConfirm();
    });

    document.getElementById("delete-cancel-button").onclick = closeDeleteModal;
    modal.onclick = function (event) {
        if (event.target === modal) {      // clicked the dark area outside
            closeDeleteModal();
        }
    };
    modal.hidden = false;
    document.getElementById("delete-cancel-button").focus();
}

document.addEventListener("keydown", function (event) {
    const modal = document.getElementById("delete-confirm-modal");
    if (event.key === "Escape" && modal && !modal.hidden) {
        closeDeleteModal();
    }
});

function deleteProduct(id) {
    const remaining = getProducts().filter(function (p) {
        return p.id !== id;
    });
    saveProducts(remaining);
}

// ======================================
// DEMO DATA
// ======================================

function makeDemoProducts() {
    const today = getToday();
    function inDays(n) {
        const d = new Date(today.getFullYear(), today.getMonth(), today.getDate() + n);
        return toInputDate(d);
    }
    // name, category, quantity, days until expiry
    const rows = [
        ["Paracetamol 500mg", "medicine", 1, 3],
        ["Cough Syrup", "medicine", 1, -5],
        ["Vitamin C Tablets", "medicine", 2, 210],
        ["Antiseptic Solution", "medicine", 1, 14],
        ["Milk (1 litre)", "grocery", 2, 2],
        ["Packaged Noodles", "grocery", 6, 120],
        ["Brown Bread", "grocery", 1, -2],
        ["Face Cream", "personal-care", 1, 20],
        ["Sunscreen SPF 50", "personal-care", 1, 75],
        ["First-Aid Bandages", "other", 3, 400]
    ];
    const list = [];
    rows.forEach(function (row, index) {
        list.push({
            id: "product_" + (Date.now() + index),
            name: row[0],
            category: row[1],
            quantity: row[2],
            notes: "Demo record — example data.",
            purchaseDate: inDays(-60),
            expiryDate: inDays(row[3]),
            batchNumber: "",
            createdAt: Date.now() + index,
            isDemo: true
        });
    });
    return list;
}

function loadDemoData() {
    if (getProducts().length > 0) {
        showToast("Demo data is only loaded when the inventory is empty.", "warning");
        return false;
    }
    saveProducts(makeDemoProducts());
    showToast("Demo products loaded. These are example records.", "success");
    return true;
}

// Adds a "Load demo data" button inside an empty-state box
function addDemoButton(containerId, afterLoad) {
    const box = document.getElementById(containerId);
    if (!box || box.querySelector(".demo-data-button")) {
        return;
    }
    const button = document.createElement("button");
    button.type = "button";
    button.className = "btn btn-secondary demo-data-button";
    button.textContent = "Load demo data";
    button.addEventListener("click", function () {
        if (loadDemoData()) {
            afterLoad();
        }
    });
    box.appendChild(button);
}

// ======================================
// DASHBOARD
// ======================================

// One row used on the dashboard and the alerts page
function renderAlertItem(product, kind, recommendation) {
    const days = getDaysRemaining(product);
    const chip = days < 0 ? "is-expired" : (kind === "expiring" ? "is-expiring" : "");
    return '<li class="alert-item alert-item-' + kind + '" data-product-id="' + esc(product.id) + '">' +
        '<div class="alert-item-main"><span class="cat-icon">' + productIcon(product.category) + '</span>' +
        '<div class="alert-item-info">' +
        '<p class="alert-product-name">' + esc(product.name) + '</p>' +
        '<p class="alert-product-meta">' + getCategoryName(product.category) + ' · ' +
        '<span class="days-chip ' + chip + '">' + describeDays(days) + '</span></p>' +
        (recommendation ? '<p class="alert-recommendation">' + esc(recommendation) + '</p>' : '') +
        '</div></div>' +
        '<a href="product-details.html?id=' + encodeURIComponent(product.id) + '" class="btn btn-secondary btn-small" ' +
        'aria-label="View ' + esc(product.name) + '">View</a></li>';
}

function fillList(listId, emptyId, products, kind) {
    const list = document.getElementById(listId);
    const empty = document.getElementById(emptyId);
    list.innerHTML = products.map(function (p) { return renderAlertItem(p, kind); }).join("");
    stagger(list);
    list.hidden = products.length === 0;
    empty.hidden = products.length !== 0;
}

function getGreeting() {
    const hour = new Date().getHours();
    if (hour < 12) {
        return "Good morning";
    }
    if (hour < 17) {
        return "Good afternoon";
    }
    return "Good evening";
}


// Upcoming-expiry timeline built from real product dates
function renderTimeline(products) {
    const buckets = [
        { label: "Today", dot: "expired", test: function (d) { return d === 0; } },
        { label: "Tomorrow", dot: "expiring", test: function (d) { return d === 1; } },
        { label: "2–7 days", dot: "expiring", test: function (d) { return d >= 2 && d <= 7; } },
        { label: "8–30 days", dot: "active", test: function (d) { return d >= 8 && d <= 30; } },
        { label: "Later", dot: "active", test: function (d) { return d > 30; } }
    ];
    const upcoming = sortByExpiry(products).filter(function (p) { const days = getDaysRemaining(p); return days !== null && days >= 0; });
    let html = "";
    buckets.forEach(function (b) {
        const items = upcoming.filter(function (p) { return b.test(getDaysRemaining(p)); });
        let chips = items.slice(0, 4).map(function (p) {
            return '<a class="tl-chip" href="product-details.html?id=' + encodeURIComponent(p.id) + '">' + esc(p.name) + '</a>';
        }).join("");
        if (items.length > 4) {
            chips += '<a class="tl-chip" href="inventory.html">+' + (items.length - 4) + ' more</a>';
        }
        if (items.length === 0) {
            chips = '<span class="tl-none">Nothing expiring</span>';
        }
        html += '<li class="tl-row"><div class="tl-label"><span class="dot dot-' + b.dot + '"></span>' + b.label +
            ' <small>' + items.length + '</small></div><div class="tl-items">' + chips + '</div></li>';
    });
    document.getElementById("expiry-timeline").innerHTML = html;
}

// Active / Expiring / Expired as one stacked bar
function renderStatusBar(counts) {
    const bar = document.getElementById("status-bar");
    const parts = [["stack-ok", counts.active], ["stack-soon", counts["expiring-soon"]], ["stack-bad", counts.expired]];
    bar.innerHTML = parts.filter(function (p) { return p[1] > 0; }).map(function (p) {
        return '<i class="' + p[0] + '" style="flex:' + p[1] + '"></i>';
    }).join("");
    bar.setAttribute("aria-label", counts.active + " active, " + counts["expiring-soon"] + " expiring soon, " + counts.expired + " expired");
}

function renderDashboard() {
    const products = getProducts();
    const counts = countByStatus(products);
    const hasProducts = products.length > 0;

    // greeting + date
    const user = getCurrentUser();
    const heading = document.getElementById("greeting-heading");
    heading.firstChild.textContent = getGreeting() + ", ";
    setText("dashboard-user-name", user.name.split(" ")[0]);
    setText("dashboard-date-context", new Date().toLocaleDateString("en-US",
        { weekday: "long", year: "numeric", month: "long", day: "numeric" }));

    // counters
    animateNumber(document.getElementById("summary-total"), products.length);
    animateNumber(document.getElementById("summary-active"), counts.active);
    animateNumber(document.getElementById("summary-expiring"), counts["expiring-soon"]);
    animateNumber(document.getElementById("summary-expired"), counts.expired);
    setText("verified-expiry-count", products.filter(function (p) { return !!p.expiryDate && ["user-confirmed", "label/user-confirmed"].includes(p.expirySource); }).length);
    setText("estimated-expiry-count", counts["estimated-expiry"] || 0);
    setText("needs-verification-count", (counts["needs-verification"] || 0) + (counts.unidentified || 0) + products.filter(function (p) { return !!p.expiryDate && !p.expirySource; }).length);
    setText("expiry-unknown-count", counts["expiry-unknown"] || 0);

    // show the empty state or the real sections
    document.getElementById("dashboard-empty-state").hidden = hasProducts;
    document.querySelectorAll(".dashboard-grid, .dashboard-priority, .dashboard-secondary, .healthcare-tip, .insights-section")
        .forEach(function (section) {
            section.hidden = !hasProducts;
        });
    addDemoButton("dashboard-empty-state", renderDashboard);
    if (!hasProducts) {
        return;
    }

    const sorted = sortByExpiry(products);
    const expired = sorted.filter(function (p) { return getStatus(p) === "expired"; });
    const soon = sorted.filter(function (p) { return getStatus(p) === "expiring-soon"; });

    fillList("urgent-product-list", "urgent-empty-state", expired, "expired");
    fillList("expiring-soon-list", "expiring-soon-empty-state", soon, "expiring");

    setText("active-count", counts.active);
    setText("active-count-note", counts.active + " products have a recorded expiry more than " + SOON_LIMIT_DAYS + " days away; this is not a safety assessment.");

    // recently added: newest first, show 5
    const recent = products.slice().sort(function (a, b) {
        return (b.createdAt || 0) - (a.createdAt || 0);
    }).slice(0, 5);
    const recentList = document.getElementById("recent-product-list");
    recentList.innerHTML = recent.map(function (p) {
        const status = getStatus(p);
        return '<li class="recent-item" data-product-id="' + esc(p.id) + '">' +
            '<a class="recent-product-name" href="product-details.html?id=' + encodeURIComponent(p.id) + '">' + esc(p.name) + '</a>' +
            '<span class="recent-product-meta"><span class="dot dot-' + (status === "expiring-soon" ? "expiring" : status) + '"></span>' +
            getStatusLabel(status) + '</span></li>';
    }).join("");
    stagger(recentList);
    renderTimeline(products);
    renderStatusBar(counts);
    document.getElementById("recent-empty-state").hidden = true;

    renderInsights(products, counts);
}

// Smart Insights: simple rules on real data (this is NOT AI)
// Smart Insights: simple rules on real data (this is NOT AI)
function renderInsights(products, counts) {
    const section = document.getElementById("smart-insights");
    if (!section) {
        return;
    }
    const total = products.length;
    const healthPercent = Math.round((counts.active / total) * 100);
    const windowDays = getAlertWindow();
    const needAttention = products.filter(function (p) {
        const d = getDaysRemaining(p);
        return d !== null && d >= 0 && d <= windowDays;
    }).length;
    const within30 = products.filter(function (p) {
        const d = getDaysRemaining(p);
        return d !== null && d >= 0 && d <= SOON_LIMIT_DAYS;
    });

    // category counts (all products) and category counts of products expiring within 30 days
    const categoryCounts = {};
    const soonByCategory = {};
    products.forEach(function (p) {
        categoryCounts[p.category] = (categoryCounts[p.category] || 0) + 1;
    });
    within30.forEach(function (p) {
        soonByCategory[p.category] = (soonByCategory[p.category] || 0) + 1;
    });
    let topCategory = null;
    Object.keys(soonByCategory).forEach(function (key) {
        if (topCategory === null || soonByCategory[key] > soonByCategory[topCategory]) {
            topCategory = key;
        }
    });

    // headline = the single most important rule that applies
    let headline = "Nothing needs urgent attention right now.";
    if (counts.expired > 0) {
        headline = counts.expired + (counts.expired === 1 ? " product has" : " products have") + " already expired. Review them first.";
    } else if (needAttention > 0) {
        headline = needAttention + (needAttention === 1 ? " product expires" : " products expire") + " within your " + pluralDays(windowDays) + " reminder window.";
    } else if (within30.length > 0) {
        headline = within30.length + (within30.length === 1 ? " product is" : " products are") + " approaching expiry this month.";
    }

    const notes = [];
    notes.push("You are tracking " + total + (total === 1 ? " product." : " products."));
    if (topCategory) {
        notes.push(getCategoryName(topCategory) + " has the most upcoming expiries (" + soonByCategory[topCategory] + " within " + SOON_LIMIT_DAYS + " days).");
    }
    if (categoryCounts.medicine) {
        notes.push("Medicines are " + Math.round((categoryCounts.medicine / total) * 100) + "% of your inventory.");
    }
    const noteHtml = notes.map(function (t) { return "<li>" + esc(t) + "</li>"; }).join("");

    let categoryHtml = "";
    Object.keys(CATEGORY_NAMES).forEach(function (key) {
        const n = categoryCounts[key] || 0;
        if (n > 0) {
            categoryHtml += '<div class="category-row"><span>' + CATEGORY_NAMES[key] + '</span>' +
                '<div class="mini-bar"><div class="mini-bar-fill" style="width:' + Math.round((n / total) * 100) + '%"></div></div>' +
                '<span>' + n + '</span></div>';
        }
    });

    section.innerHTML =
        '<div class="insight-head"><h2 id="insights-heading">Smart Insight</h2>' +
        '<span class="rule-tag" title="Simple rules on your saved data. Not AI.">Rule-based</span></div>' +
        '<div class="insight-main"><div class="ring" style="--p:' + healthPercent + '" role="img" ' +
        'aria-label="' + healthPercent + ' percent of products have more than ' + SOON_LIMIT_DAYS + ' days left"><span>' + healthPercent + '%</span></div>' +
        '<p class="insight-headline">' + esc(headline) + '</p></div>' +
        '<ul class="insight-list">' + noteHtml + '</ul>' +
        '<h3 class="visually-hidden">By category</h3>' + categoryHtml;
}

function initDashboard() {
    renderDashboard();
}

// ======================================
// INVENTORY
// ======================================

const PAGE_SIZE = 10;
let currentPage = 1;
let inventoryProducts = [];    // the products after filtering (used for pagination)

let inventorySearchTerm = "";

// Wraps the matching part of a text in <mark> (text is escaped first)
function highlight(text, term) {
    const plain = String(text);
    const i = term ? plain.toLowerCase().indexOf(term) : -1;
    if (i < 0) {
        return esc(plain);
    }
    return esc(plain.slice(0, i)) + "<mark>" + esc(plain.slice(i, i + term.length)) + "</mark>" + esc(plain.slice(i + term.length));
}

function shortDays(days) {
    if (days < 0) {
        return pluralDays(Math.abs(days)) + " overdue";
    }
    return days === 0 ? "Today" : pluralDays(days);
}

function getProductImage(product) {
    const name = String(product.name || "").toLowerCase();
    const category = String(product.category || "").toLowerCase();
    if (/milk|dairy|yogurt|curd|cheese|butter/.test(name)) {
        return { src: "https://images.unsplash.com/photo-1563636619-e9143da7973b?auto=format&fit=crop&w=180&h=180&q=80", alt: "Milk and dairy product" };
    }
    if (/cream|cosmetic|makeup|lipstick|serum|sunscreen|shampoo|lotion|skincare|moistur/.test(name) || /personal.?care|cosmetic|beauty/.test(category)) {
        return { src: "https://images.unsplash.com/photo-1608248543803-ba4f8c70ae0b?auto=format&fit=crop&w=180&h=180&q=80", alt: "Personal-care product" };
    }
    if (/tablet|medicine|medicin|paracetamol|syrup|capsule|vitamin|antacid|ointment/.test(name) || /medicine|pharma|health/.test(category)) {
        return { src: "https://images.unsplash.com/photo-1584308666744-24d5c474f2ae?auto=format&fit=crop&w=180&h=180&q=80", alt: "Medicine packaging" };
    }
    if (/bread|snack|biscuit|rice|flour|cereal|juice|coffee|tea|grocery|pasta|sauce|food/.test(name) || /grocery|food|beverage/.test(category)) {
        return { src: "https://images.unsplash.com/photo-1542838132-92c53300491e?auto=format&fit=crop&w=180&h=180&q=80", alt: "Fresh grocery products" };
    }
    if (/clean|detergent|dishwash|surface|disinfect/.test(name) || /household|cleaning/.test(category)) {
        return { src: "https://images.unsplash.com/photo-1585421514738-01798e348b17?auto=format&fit=crop&w=180&h=180&q=80", alt: "Household care product" };
    }
    return { src: "https://images.unsplash.com/photo-1542838132-92c53300491e?auto=format&fit=crop&w=180&h=180&q=80", alt: "Everyday product" };
}

function renderProductRow(product) {
    const status = getStatus(product);
    const days = getDaysRemaining(product);
    const id = encodeURIComponent(product.id);
    const term = inventorySearchTerm;
    const chip = status === "expired" ? "is-expired" : (status === "expiring-soon" ? "is-expiring" : "");
    return '<tr class="product-row" data-product-id="' + esc(product.id) + '" data-status="' + status + '">' +
        '<td data-label="Product"><div class="product-cell"><img class="product-thumb" src="' + getProductImage(product).src + '" alt="" loading="lazy" onerror="this.hidden=true"><div class="product-cell-copy">' +
        '<a href="product-details.html?id=' + id + '">' + highlight(product.name, term) + '</a>' +
        (product.batchNumber ? '<small>Batch ' + highlight(product.batchNumber, term) + '</small>' : '') + '</div></div></td>' +
        '<td data-label="Category">' + highlight(getCategoryName(product.category), term) + '</td>' +
        '<td data-label="Qty">' + esc(product.quantity) + '</td>' +
        '<td data-label="Expiry date">' + (product.expiryDate ? formatDate(product.expiryDate) : (product.reviewReminderDate ? "Unknown · review " + formatDate(product.reviewReminderDate) : "Unknown")) + '</td>' +
        '<td data-label="Days left"><span class="days-chip ' + chip + '">' + (days === null ? "Review needed" : shortDays(days)) + '</span></td>' +
        '<td data-label="Status"><span class="status-badge ' + getStatusClass(status) + '">' + getStatusLabel(status) + '</span></td>' +
        '<td class="table-actions">' +
        '<a href="product-details.html?id=' + id + '" class="icon-btn" title="View" aria-label="View ' + esc(product.name) + '">' + icon("eye") + '</a>' +
        '<a href="edit-product.html?id=' + id + '" class="icon-btn" title="Edit" aria-label="Edit ' + esc(product.name) + '">' + icon("edit") + '</a>' +
        '<button type="button" class="icon-btn icon-btn-danger" title="Delete" data-action="delete-product" aria-label="Delete ' + esc(product.name) + '">' + icon("trash") + '</button>' +
        '</td></tr>';
}

function getFilteredProducts() {
    const search = document.getElementById("search-products").value.trim().toLowerCase();
    inventorySearchTerm = search;
    const category = document.querySelector("input[name='category']:checked").value;
    const checkedStatuses = [];
    document.querySelectorAll("input[name='status']:checked").forEach(function (box) {
        checkedStatuses.push(box.value);
    });
    const sortValue = document.getElementById("sort-products").value;

    let result = getProducts().filter(function (p) {
        const text = (p.name + " " + getCategoryName(p.category) + " " + (p.batchNumber || "")).toLowerCase();
        if (search && text.indexOf(search) === -1) {
            return false;
        }
        if (category !== "all" && p.category !== category) {
            return false;
        }
        // no status ticked = show all statuses
        if (checkedStatuses.length > 0 && checkedStatuses.indexOf(getStatus(p)) === -1) {
            return false;
        }
        return true;
    });

    if (sortValue === "name") {
        result.sort(function (a, b) { return a.name.localeCompare(b.name); });
    } else if (sortValue === "recently-added") {
        result.sort(function (a, b) { return (b.createdAt || 0) - (a.createdAt || 0); });
    } else {
        result = sortByExpiry(result);
    }
    return result;
}

function renderInventory() {
    const allCount = getProducts().length;
    inventoryProducts = getFilteredProducts();

    const totalPages = Math.max(1, Math.ceil(inventoryProducts.length / PAGE_SIZE));
    if (currentPage > totalPages) {
        currentPage = totalPages;
    }
    const pageItems = inventoryProducts.slice((currentPage - 1) * PAGE_SIZE, currentPage * PAGE_SIZE);

    const body = document.getElementById("inventory-table-body");
    body.innerHTML = pageItems.map(renderProductRow).join("");

    // table / empty states
    document.getElementById("inventory-table").hidden = inventoryProducts.length === 0;
    document.getElementById("inventory-empty-state").hidden = allCount !== 0;
    document.getElementById("inventory-search-empty-state").hidden = !(allCount > 0 && inventoryProducts.length === 0);
    document.getElementById("inventory-pagination").hidden = inventoryProducts.length === 0;

    // active filters: search, category, status
    const activeCount = (inventorySearchTerm ? 1 : 0) +
        (document.querySelector("input[name='category']:checked").value !== "all" ? 1 : 0) +
        document.querySelectorAll("input[name='status']:checked").length;
    document.getElementById("search-clear").hidden = !inventorySearchTerm;
    document.getElementById("clear-filters").hidden = activeCount === 0;
    setText("inventory-result-count", "Showing " + inventoryProducts.length + " of " + allCount +
        (allCount === 1 ? " product" : " products") + (activeCount ? " · " + activeCount + (activeCount === 1 ? " filter" : " filters") + " active" : ""));
    setText("pagination-status", "Page " + currentPage + " of " + totalPages);
    document.getElementById("pagination-prev").disabled = currentPage <= 1;
    document.getElementById("pagination-next").disabled = currentPage >= totalPages;
}

function initInventory() {
    // result count line (created here, not in the HTML)
    const count = document.createElement("p");
    count.id = "inventory-result-count";
    count.className = "result-count";
    count.setAttribute("aria-live", "polite");
    const controls = document.querySelector(".inventory-controls");
    controls.parentNode.insertBefore(count, controls.nextSibling);

    // start values: saved default sort, then URL parameters (?status=active&sort=recent)
    const sortSelect = document.getElementById("sort-products");
    sortSelect.value = getSettings().defaultSort;
    const params = new URLSearchParams(window.location.search);
    if (params.get("sort") === "recent") {
        sortSelect.value = "recently-added";
    }
    if (params.get("status")) {
        const box = document.querySelector("input[name='status'][value='" + params.get("status") + "']");
        if (box) {
            box.checked = true;
        }
    }

    const form = document.getElementById("inventory-filter-form");
    form.addEventListener("submit", function (event) {
        event.preventDefault();
    });
    // any change in the form re-draws the table from page 1
    form.addEventListener("input", function () {
        currentPage = 1;
        renderInventory();
    });

    document.getElementById("pagination-prev").addEventListener("click", function () {
        currentPage--;
        renderInventory();
    });
    document.getElementById("pagination-next").addEventListener("click", function () {
        currentPage++;
        renderInventory();
    });

    // delete buttons are created dynamically, so listen on the table body
    document.getElementById("inventory-table-body").addEventListener("click", function (event) {
        const button = event.target.closest("[data-action='delete-product']");
        if (!button) {
            return;
        }
        const id = button.closest("tr").getAttribute("data-product-id");
        const product = getProductById(id);
        openDeleteModal(product, function () {
            deleteProduct(id);
            showToast("Product deleted.", "success");
            renderInventory();
        });
    });

    // clear buttons
    function resetFilters() {
        const sortValue = sortSelect.value;      // keep the chosen sort order
        form.reset();
        sortSelect.value = sortValue;
        currentPage = 1;
        renderInventory();
    }
    document.getElementById("search-clear").addEventListener("click", function () {
        const box = document.getElementById("search-products");
        box.value = "";
        box.focus();
        currentPage = 1;
        renderInventory();
    });
    document.getElementById("clear-filters").addEventListener("click", resetFilters);
    document.getElementById("empty-clear-filters").addEventListener("click", resetFilters);

    addDemoButton("inventory-empty-state", renderInventory);
    renderInventory();
    const tbody = document.getElementById("inventory-table-body");
    tbody.classList.add("animate-in");     // row entrance only on the first draw
    setTimeout(function () { tbody.classList.remove("animate-in"); }, 600);
}

// ======================================
// ADD PRODUCT  (also uses shared form code for EDIT)
// ======================================

const ADD_IDS = {
    name: "product-name", category: "product-category", quantity: "product-quantity",
    notes: "product-notes", purchase: "purchase-date", expiry: "expiry-date", batch: "product-batch-number"
};
const EDIT_IDS = {
    name: "edit-product-name", category: "edit-product-category", quantity: "edit-product-quantity",
    notes: "edit-product-notes", purchase: "edit-purchase-date", expiry: "edit-expiry-date", batch: "edit-product-batch-number"
};

// Checks the form. Returns true if everything is valid.
function validateProductForm(ids) {
    let ok = true;
    function check(key, message, isBad) {
        const input = document.getElementById(ids[key]);
        if (isBad(input.value.trim())) {
            setFieldError(ids[key], message);
            ok = false;
        } else {
            setFieldError(ids[key], "");
        }
    }
    // Add flow accepts unknown identity/category; edit flow keeps the original validation.
    if (ids === ADD_IDS) {
        const name = document.getElementById(ids.name).value.trim();
        const category = document.getElementById(ids.category).value;
        setFieldError(ids.name, ""); setFieldError(ids.category, "");
        if (!name) document.getElementById(ids.name).value = "Unidentified Product";
        if (!category) document.getElementById(ids.category).value = "other";
    } else {
        check("name", "Please enter the product name.", function (v) { return v === ""; });
        check("category", "Please choose a category.", function (v) { return v === ""; });
    }
    check("quantity", "Quantity must be a whole number of 1 or more.", function (v) {
        return v === "" || Number(v) < 1 || !Number.isInteger(Number(v));
    });
    // Purchase and expiry dates are optional when the user cannot verify them.
    setFieldError(ids.purchase, ""); setFieldError(ids.expiry, "");

    // expiry must not be before purchase
    const purchase = document.getElementById(ids.purchase).value;
    const expiry = document.getElementById(ids.expiry).value;
    if (purchase && expiry && expiry < purchase) {
        setFieldError(ids.expiry, "Expiry date cannot be before the purchase date.");
        ok = false;
    }
    return ok;
}

// Small coloured message under the expiry date field
// Live expiry preview: small message under the date field + the side panel
function setupExpiryPreview(ids) {
    const expiryInput = document.getElementById(ids.expiry);
    const preview = document.createElement("p");
    preview.className = "expiry-preview";
    preview.setAttribute("aria-live", "polite");
    expiryInput.parentNode.insertBefore(preview, document.getElementById(ids.expiry + "-error"));
    const panel = document.getElementById("expiry-panel");
    const PANEL_ICONS = { empty: "calendar", active: "check", "expiring-soon": "clock", expired: "xcircle" };

    function updatePanel(state, title, text, number, unit) {
        if (!panel) {
            return;
        }
        panel.setAttribute("data-state", state);
        panel.querySelector("#expiry-panel-icon use").setAttribute("href", "#i-" + PANEL_ICONS[state]);
        setText("expiry-panel-title", title);
        setText("expiry-panel-text", text);
        setText("expiry-panel-days", number);
        panel.querySelector(".expiry-panel-days span").textContent = unit;
    }

    function update() {
        if (!expiryInput.value) {
            preview.innerHTML = "";
            updatePanel("empty", "Expiry date unknown", "You can save without a date and set a separate review reminder.", "—", "expiry not established");
            return;
        }
        const days = getDaysFromDate(expiryInput.value);
        const status = getStatusFromDays(days);
        let text;
        if (status === "active") {
            text = "Recorded expiry is " + pluralDays(days) + " away; this is not a safety assessment.";
        } else if (status === "expiring-soon") {
            text = "Recorded expiry is near — " + pluralDays(days) + " remaining.";
        } else {
            text = "This product has already expired (" + pluralDays(Math.abs(days)) + " ago)";
        }
        preview.innerHTML = '<span class="status-badge ' + getStatusClass(status) + '">' + getStatusLabel(status) + '</span> ' + esc(text);
        updatePanel(status, getStatusLabel(status), describeDays(days),
            days < 0 ? Math.abs(days) : days, days < 0 ? "days overdue" : (days === 1 ? "day remaining" : "days remaining"));
    }
    expiryInput.addEventListener("input", update);
    update();
}

function initAddProduct() {
    const form = document.getElementById("add-product-form");
    setupExpiryPreview(ADD_IDS);

    form.addEventListener("reset", function () {
        showFormError("add-product-form-error", "");
        Object.keys(ADD_IDS).forEach(function (key) {
            setFieldError(ADD_IDS[key], "");
        });
        setTimeout(function () {
            document.getElementById(ADD_IDS.expiry).dispatchEvent(new Event("input"));
        }, 0);
    });

    form.addEventListener("submit", function (event) {
        event.preventDefault();
        showFormError("add-product-form-error", "");
        if (!validateProductForm(ADD_IDS)) {
            showFormError("add-product-form-error", "Please fix the highlighted fields.");
            focusFirstError(form);
            return;
        }
        const products = getProducts();
        const enteredExpiryDate = document.getElementById(ADD_IDS.expiry).value;
        const manufacturingDate = document.getElementById("manufacturing-date").value;
        const shelfLifeDays = Number(document.getElementById("verified-shelf-life-days").value);
        const shelfLifeSource = document.getElementById("shelf-life-source").value.trim();
        let estimatedExpiryDate = "";
        if (!enteredExpiryDate && manufacturingDate && shelfLifeDays > 0 && Number.isInteger(shelfLifeDays) && shelfLifeSource) {
            const estimatedDate = parseDate(manufacturingDate);
            estimatedDate.setDate(estimatedDate.getDate() + shelfLifeDays);
            estimatedExpiryDate = toInputDate(estimatedDate);
        }
        const savedExpiryDate = enteredExpiryDate || estimatedExpiryDate;
        products.push({
            id: "product_" + Date.now(),
            name: document.getElementById(ADD_IDS.name).value.trim() || "Unidentified Product",
            category: document.getElementById(ADD_IDS.category).value || "other",
            quantity: Number(document.getElementById(ADD_IDS.quantity).value),
            notes: document.getElementById(ADD_IDS.notes).value.trim(),
            purchaseDate: document.getElementById(ADD_IDS.purchase).value,
            batchNumber: document.getElementById(ADD_IDS.batch).value.trim(),
            manufacturingDate: manufacturingDate,
            verifiedShelfLifeDays: estimatedExpiryDate ? shelfLifeDays : null,
            shelfLifeSource: estimatedExpiryDate ? shelfLifeSource : "",
            barcode: document.getElementById("barcode-manual").value.trim(),
            expiryDate: savedExpiryDate,
            expirySource: enteredExpiryDate ? "user-confirmed" : (estimatedExpiryDate ? "estimated" : "unknown"),
            trackingStatus: (!document.getElementById(ADD_IDS.name).value.trim() || document.getElementById(ADD_IDS.name).value.trim() === "Unidentified Product") ? "unidentified" : (estimatedExpiryDate ? "estimated-expiry" : (!savedExpiryDate ? "expiry-unknown" : "verified-expiry")),
            reviewReminderDate: savedExpiryDate ? "" : toInputDate(new Date(Date.now() + Number(document.getElementById("review-interval").value) * 86400000)),
            evidence: { name: (!document.getElementById(ADD_IDS.name).value.trim() || document.getElementById(ADD_IDS.name).value.trim() === "Unidentified Product") ? "not-found" : scannerIdentitySource, expiry: enteredExpiryDate ? "user-confirmed" : (estimatedExpiryDate ? "estimated from manufacturing date + entered shelf life; verify source and conditions" : "unknown"), shelfLifeSource: shelfLifeSource || "not-provided", barcode: document.getElementById("barcode-manual").value.trim() ? "lookup-input; identity source recorded separately" : "not-provided" },
            createdAt: Date.now()
        });
        saveProducts(products);
        setFlashMessage("Product saved. Tracking status: " + getStatusLabel(getStatus(products[products.length - 1])) + ".", "success");
        window.location.href = "inventory.html";
    });
}

// ======================================
// PRODUCT DETAILS
// ======================================

function getIdFromUrl() {
    return new URLSearchParams(window.location.search).get("id");
}

// If the product is missing, go back to the inventory
function loadProductOrLeave() {
    const product = getProductById(getIdFromUrl());
    if (!product) {
        setFlashMessage("That product could not be found.", "error");
        window.location.href = "inventory.html";
        return null;
    }
    return product;
}

function getSafetyText(status) {
    if (status === "expired") {
        return "This product is past its expiry date. Check the packaging for disposal instructions and do not use it. " +
            "This is general information, not medical advice.";
    }
    if (status === "expiring-soon") {
        return "This product is close to its expiry date. Plan to use or replace it soon, and check the packaging for any " +
            "signs of damage. This is general information, not medical advice.";
    }
    return "Check the packaging for any physical signs of degradation even before the listed expiry date. " +
        "This is general information, not medical advice.";
}

// Big status number, progress bar, icon and batch (the dominant part of the page)
function showProductStatusPanel(product, days) {
    document.getElementById("product-details-icon").innerHTML = productIcon(product.category);
    setText("product-details-batch", product.batchNumber || "—");
    setText("pd-days-number", days === 0 ? "0" : Math.abs(days));
    setText("pd-days-label", days < 0 ? "days overdue" : (days === 0 ? "expires today" : (days === 1 ? "day remaining" : "days remaining")));

    // how much of the shelf life (purchase -> expiry) has passed
    const msPerDay = 24 * 60 * 60 * 1000;
    if (!product.expiryDate || !product.purchaseDate) {
        document.querySelector("#pd-progress i").style.width = "0%";
        setText("pd-progress-text", "Progress is unavailable until purchase and expiry dates are known.");
        return;
    }
    const total = Math.round((parseDate(product.expiryDate) - parseDate(product.purchaseDate)) / msPerDay);
    const used = Math.round((getToday() - parseDate(product.purchaseDate)) / msPerDay);
    if (total > 0) {
        const percent = Math.max(0, Math.min(100, Math.round((used / total) * 100)));
        document.querySelector("#pd-progress i").style.width = percent + "%";
        setText("pd-progress-text", percent + "% of the time between purchase and expiry has passed.");
    }
}

function initProductDetails() {
    const product = loadProductOrLeave();
    if (!product) {
        return;
    }
    const days = getDaysRemaining(product);
    const status = getStatus(product);

    document.getElementById("product-details").setAttribute("data-product-id", product.id);
    document.getElementById("product-details").setAttribute("data-status", status);
    showProductStatusPanel(product, days);
    document.title = product.name + " — ExpiryCare";
    setText("breadcrumb-product-name", product.name);
    setText("product-details-name", product.name);
    const productPhoto = document.getElementById("product-details-photo");
    if (productPhoto) {
        const image = getProductImage(product);
        productPhoto.src = image.src.replace("w=180&h=180", "w=520&h=520");
        productPhoto.alt = image.alt + " for " + product.name;
        productPhoto.hidden = false;
        productPhoto.onerror = function () { this.hidden = true; };
    }
    setText("product-details-category", getCategoryName(product.category));
    setText("product-details-quantity", product.quantity);
    setText("product-details-purchase-date", formatDate(product.purchaseDate));
    setText("product-details-expiry-date", formatDate(product.expiryDate));
    setText("product-details-notes", product.notes || "—");
    setText("product-safety-text", getSafetyText(status));
    setText("evidence-expiry-status", product.expiryDate ? (product.expirySource === "estimated" ? "Estimated — check assumptions" : "Recorded expiry date; verify against packaging") : "Unknown — no expiry date recorded");
    setText("evidence-source", product.evidence && product.evidence.expiry ? product.evidence.expiry : (product.expirySource || "Legacy product record; source not recorded"));
    if (product.shelfLifeSource) setText("evidence-source", (document.getElementById("evidence-source").textContent || "") + "; shelf-life source: " + product.shelfLifeSource);
    setText("evidence-missing", [!product.name || product.name === "Unidentified Product" ? "product identity" : "", !product.purchaseDate ? "purchase date" : "", !product.expiryDate ? "expiry date" : "", !product.batchNumber ? "batch/lot number" : ""].filter(Boolean).join(", ") || "No required fields flagged; packaging should still be checked.");

    const badge = document.getElementById("product-details-status");
    badge.textContent = getStatusLabel(status);
    badge.className = "status-badge " + getStatusClass(status);

    if (days === null) {
        setText("product-details-days-remaining", product.reviewReminderDate ? "Review by " + formatDate(product.reviewReminderDate) + " (not an expiry date)" : "Expiry unknown — verify packaging");
        setText("pd-days-number", "—"); setText("pd-days-label", "expiry not established");
        setText("pd-progress-text", "No expiry calculation is possible without a verified date.");
    } else if (days < 0) {
        setText("product-details-days-remaining", "Expired " + pluralDays(Math.abs(days)) + " ago");
    } else if (days === 0) {
        setText("product-details-days-remaining", "Expires today");
    } else {
        setText("product-details-days-remaining", pluralDays(days) + " remaining");
    }

    document.querySelector("a[href='edit-product.html']").href = "edit-product.html?id=" + encodeURIComponent(product.id);

    document.getElementById("delete-product-button").addEventListener("click", function () {
        openDeleteModal(product, function () {
            deleteProduct(product.id);
            setFlashMessage("Product deleted.", "success");
            window.location.href = "inventory.html";
        });
    });
}

// ======================================
// EDIT PRODUCT
// ======================================

function initEditProduct() {
    const product = loadProductOrLeave();
    if (!product) {
        return;
    }
    const form = document.getElementById("edit-product-form");
    form.setAttribute("data-product-id", product.id);

    document.getElementById(EDIT_IDS.name).value = product.name;
    document.getElementById(EDIT_IDS.category).value = product.category;
    document.getElementById(EDIT_IDS.quantity).value = product.quantity;
    document.getElementById(EDIT_IDS.notes).value = product.notes || "";
    document.getElementById(EDIT_IDS.purchase).value = product.purchaseDate;
    document.getElementById(EDIT_IDS.expiry).value = product.expiryDate;
    document.getElementById(EDIT_IDS.batch).value = product.batchNumber || "";

    const detailsUrl = "product-details.html?id=" + encodeURIComponent(product.id);
    document.querySelectorAll("a[href='product-details.html']").forEach(function (link) {
        link.href = detailsUrl;
    });
    setupExpiryPreview(EDIT_IDS);

    form.addEventListener("submit", function (event) {
        event.preventDefault();
        showFormError("edit-product-form-error", "");
        if (!validateProductForm(EDIT_IDS)) {
            showFormError("edit-product-form-error", "Please fix the highlighted fields.");
            focusFirstError(form);
            return;
        }
        const products = getProducts();
        for (let i = 0; i < products.length; i++) {
            if (products[i].id === product.id) {
                products[i].name = document.getElementById(EDIT_IDS.name).value.trim();
                products[i].category = document.getElementById(EDIT_IDS.category).value;
                products[i].quantity = Number(document.getElementById(EDIT_IDS.quantity).value);
                products[i].notes = document.getElementById(EDIT_IDS.notes).value.trim();
                products[i].purchaseDate = document.getElementById(EDIT_IDS.purchase).value;
                products[i].expiryDate = document.getElementById(EDIT_IDS.expiry).value;
                products[i].batchNumber = document.getElementById(EDIT_IDS.batch).value.trim();
                products[i].trackingStatus = !products[i].expiryDate ? (products[i].name === "Unidentified Product" ? "unidentified" : "expiry-unknown") : "verified-expiry";
                products[i].expirySource = products[i].expiryDate ? "user-confirmed" : "unknown";
                products[i].evidence = products[i].evidence || {};
                products[i].evidence.expiry = products[i].expiryDate ? "user-confirmed" : "unknown";
            }
        }
        saveProducts(products);
        setFlashMessage("Product updated successfully.", "success");
        window.location.href = detailsUrl;
    });

    document.querySelector("[data-action='delete-product']").addEventListener("click", function () {
        openDeleteModal(product, function () {
            deleteProduct(product.id);
            setFlashMessage("Product deleted.", "success");
            window.location.href = "inventory.html";
        });
    });
}

// ======================================
// ALERTS
// ======================================

function renderAlertGroup(sectionId, emptyId, products, kind, recommendation) {
    const list = document.querySelector("#" + sectionId + " .alert-list");
    list.innerHTML = products.map(function (p) {
        return renderAlertItem(p, kind, recommendation);
    }).join("");
    stagger(list);
    list.hidden = products.length === 0;
    document.getElementById(emptyId).hidden = products.length !== 0;
    setText(sectionId + "-count", products.length);
}

function renderAlerts() {
    const windowDays = getAlertWindow();
    const sorted = sortByExpiry(getProducts());

    // Expired: past date. Expiring Soon: inside the reminder window.
    // Upcoming: still "Expiring Soon" status but outside the window (up to 30 days).
    const expired = sorted.filter(function (p) { const d = getDaysRemaining(p); return d !== null && d < 0; });
    const soon = sorted.filter(function (p) {
        const d = getDaysRemaining(p);
        return d !== null && d >= 0 && d <= windowDays;
    });
    const upcoming = sorted.filter(function (p) {
        const d = getDaysRemaining(p);
        return d !== null && d > windowDays && d <= SOON_LIMIT_DAYS;
    });

    renderAlertGroup("expired", "expired-empty-state", expired, "expired",
        "Recommended: Dispose of safely and remove from inventory.");
    renderAlertGroup("expiring-soon", "expiring-soon-empty-state", soon, "expiring",
        "Recommended: Use soon or plan a replacement.");
    renderAlertGroup("upcoming", "upcoming-empty-state", upcoming, "upcoming", "");

    const nothing = expired.length + soon.length + upcoming.length === 0;
    document.getElementById("alerts-empty-state").hidden = !nothing;
    document.getElementById("expired").hidden = nothing;
    document.getElementById("expiring-soon").hidden = nothing;
    document.getElementById("upcoming").hidden = nothing;
    if (nothing && getProducts().length === 0) {
        document.querySelector("#alerts-empty-state p").textContent = "You have no products yet. Add one to start getting alerts.";
    }
}

// Tick the saved reminder boxes and save when the form is submitted.
function setupThresholdForm(formId, afterSave) {
    const form = document.getElementById(formId);
    const saved = getSettings().alertThresholds.map(String);
    form.querySelectorAll("input[name='alert_threshold']").forEach(function (box) {
        box.checked = saved.indexOf(box.value) !== -1;
    });
    form.addEventListener("submit", function (event) {
        event.preventDefault();
        const chosen = [];
        form.querySelectorAll("input[name='alert_threshold']:checked").forEach(function (box) {
            chosen.push(Number(box.value));
        });
        const settings = getSettings();
        settings.alertThresholds = chosen;
        saveSettings(settings);
        showToast(chosen.length ? "Alert preferences saved." : "No reminder ticked — using 7 days by default.",
            chosen.length ? "success" : "warning");
        if (afterSave) {
            afterSave();
        }
    });
}

function initAlerts() {
    renderAlerts();
    setupThresholdForm("alert-preferences-form", renderAlerts);
}

// ======================================
// PROFILE / SETTINGS
// ======================================

// Left-hand account card on the profile page
function updateProfileCard() {
    const user = getCurrentUser();
    setText("profile-avatar", user.name.charAt(0).toUpperCase());
    setText("profile-card-name", user.name);
    setText("profile-card-email", user.email);
    setText("profile-product-count", getProducts().length);
}

function initProfile() {
    const user = getCurrentUser();
    document.getElementById("profile-name").value = user.name;
    document.getElementById("profile-email").value = user.email;
    updateProfileCard();

    document.getElementById("profile-form").addEventListener("submit", function (event) {
        event.preventDefault();
        const name = document.getElementById("profile-name").value.trim();
        const email = document.getElementById("profile-email").value.trim().toLowerCase();
        if (name === "" || !isValidEmail(email)) {
            showToast("Please enter a name and a valid email.", "error");
            return;
        }
        // email must not belong to a different account
        const users = getUsers();
        for (let i = 0; i < users.length; i++) {
            if (users[i].id !== user.id && users[i].email === email) {
                showToast("That email is already used by another account.", "error");
                return;
            }
        }
        for (let i = 0; i < users.length; i++) {
            if (users[i].id === user.id) {
                users[i].name = name;
                users[i].email = email;
            }
        }
        saveUsers(users);
        user.name = name;
        user.email = email;
        saveCurrentUser(user);
        showCurrentUserName();
        updateProfileCard();
        showToast("Profile updated.", "success");
    });

    setupThresholdForm("notification-preferences-form");

    const sortSelect = document.getElementById("default-inventory-sort");
    sortSelect.value = getSettings().defaultSort;
    document.getElementById("app-preferences-form").addEventListener("submit", function (event) {
        event.preventDefault();
        const settings = getSettings();
        settings.defaultSort = sortSelect.value;
        saveSettings(settings);
        showToast("Application preferences saved.", "success");
    });
}

// ======================================
// GUIDANCE PAGE
// ======================================

// Each topic shows its first sentence; the rest opens with "Read more"
function initGuidance() {
    document.querySelectorAll(".guidance-topic").forEach(function (topic) {
        const para = topic.querySelector("p");
        const sentences = para.textContent.trim().split(/(?<=[.!?])\s+/);
        if (sentences.length < 2) {
            return;
        }
        para.className = "lead-line";
        para.textContent = sentences[0];
        const more = document.createElement("div");
        more.className = "guidance-more";
        more.hidden = true;
        more.innerHTML = "<p>" + esc(sentences.slice(1).join(" ")) + "</p>";
        const button = document.createElement("button");
        button.type = "button";
        button.className = "more-toggle";
        button.setAttribute("aria-expanded", "false");
        button.textContent = "Read more";
        button.addEventListener("click", function () {
            const open = more.hidden;
            more.hidden = !open;
            button.setAttribute("aria-expanded", String(open));
            button.textContent = open ? "Show less" : "Read more";
        });
        para.after(more);
        more.after(button);
    });
}

// ======================================
// PUBLIC PAGES: REGISTER / LOGIN / FORGOT PASSWORD
// ======================================

// Password strength meter (length + mix of character types)
function setupPasswordStrength() {
    const input = document.getElementById("register-password");
    const bar = document.querySelector("#register-strength i");
    const label = document.getElementById("register-strength-label");
    input.addEventListener("input", function () {
        const v = input.value;
        let score = 0;
        if (v.length >= 8) { score++; }
        if (/[a-z]/.test(v) && /[A-Z]/.test(v)) { score++; }
        if (/\d/.test(v)) { score++; }
        if (/[^A-Za-z0-9]/.test(v) || v.length >= 12) { score++; }
        if (v === "") { score = 0; }
        const names = ["", "Weak", "Fair", "Good", "Strong"];
        const colors = ["", "#d2483c", "#d99a1c", "#5b8fc4", "#2e9e6a"];
        bar.style.width = score * 25 + "%";
        bar.style.background = colors[score] || "";
        label.textContent = names[score];
    });
}

// Shows a small spinner on the submit button just before leaving the page
function setSubmitLoading(form) {
    const button = form.querySelector("button[type='submit']");
    if (button) {
        button.classList.add("is-loading");
    }
}

function initRegister() {
    setupPasswordToggle("register-password-toggle", "register-password");
    setupPasswordStrength();
    setupPasswordToggle("register-confirm-password-toggle", "register-confirm-password");
    const form = document.getElementById("register-form");

    form.addEventListener("submit", function (event) {
        event.preventDefault();
        const name = document.getElementById("register-name").value.trim();
        const email = document.getElementById("register-email").value.trim().toLowerCase();
        const password = document.getElementById("register-password").value;
        const confirm = document.getElementById("register-confirm-password").value;
        const agreed = document.getElementById("register-terms").checked;
        let ok = true;

        function problem(id, message) {
            setFieldError(id, message);
            if (message) {
                ok = false;
            }
        }
        problem("register-name", name.length < 2 ? "Please enter your full name." : "");
        problem("register-email", isValidEmail(email) ? "" : "Please enter a valid email address.");
        problem("register-password", password.length < 8 ? "Password must be at least 8 characters." : "");
        problem("register-confirm-password", confirm !== password ? "Passwords do not match." : "");
        problem("register-terms", agreed ? "" : "You must agree to continue.");

        const users = getUsers();
        if (isValidEmail(email) && users.some(function (u) { return u.email === email; })) {
            problem("register-email", "An account with this email already exists.");
        }
        if (!ok) {
            showFormError("register-form-error", "Please fix the highlighted fields.");
            focusFirstError(form);
            return;
        }
        showFormError("register-form-error", "");
        users.push({ id: "user_" + Date.now(), name: name, email: email, password: password });
        saveUsers(users);
        setSubmitLoading(form);
        setFlashMessage("Account created. Please log in.", "success");
        window.location.href = "login.html";
    });
}

function initLogin() {
    setupPasswordToggle("login-password-toggle", "login-password");
    const form = document.getElementById("login-form");

    form.addEventListener("submit", function (event) {
        event.preventDefault();
        const email = document.getElementById("login-email").value.trim().toLowerCase();
        const password = document.getElementById("login-password").value;
        const remember = document.getElementById("login-remember").checked;

        setFieldError("login-email", isValidEmail(email) ? "" : "Please enter a valid email address.");
        setFieldError("login-password", password === "" ? "Please enter your password." : "");
        showFormError("login-form-error", "");
        if (!isValidEmail(email) || password === "") {
            focusFirstError(form);
            return;
        }
        const user = getUsers().find(function (u) {
            return u.email === email && u.password === password;
        });
        if (!user) {
            showFormError("login-form-error", "Incorrect email or password. Please try again.");
            return;
        }
        saveCurrentUser({ id: user.id, name: user.name, email: user.email }, remember);
        setSubmitLoading(form);
        setFlashMessage("Login successful. Welcome, " + user.name.split(" ")[0] + "!", "success");
        window.location.href = "dashboard.html";
    });
}

function initForgotPassword() {
    const form = document.getElementById("forgot-password-form");
    form.addEventListener("submit", function (event) {
        event.preventDefault();
        const email = document.getElementById("forgot-password-email").value.trim();
        if (!isValidEmail(email)) {
            setFieldError("forgot-password-email", "Please enter a valid email address.");
            return;
        }
        setFieldError("forgot-password-email", "");
        // Prototype only: no email is really sent. Show a clear prototype success state.
        setText("forgot-password-success-text", "Password reset instructions would be sent to " + email + ".");
        document.getElementById("forgot-password-panel").hidden = true;
        document.getElementById("forgot-password-success").hidden = false;
    });
}


// ======================================
// RESPONSIVE INTERACTIONS (mobile menu, sticky header, page transitions)
// ======================================

function setupNavigation() {
    const toggle = document.getElementById("nav-toggle");
    const panel = document.getElementById("nav-panel");
    const header = document.querySelector(".site-header, .app-header");

    function setOpen(open) {
        panel.classList.toggle("is-open", open);
        toggle.setAttribute("aria-expanded", String(open));
        toggle.setAttribute("aria-label", open ? "Close menu" : "Open menu");
    }
    if (toggle && panel) {
        toggle.addEventListener("click", function (event) {
            event.stopPropagation();
            setOpen(!panel.classList.contains("is-open"));
        });
        document.addEventListener("click", function (event) {
            if (!panel.contains(event.target)) {
                setOpen(false);
            }
        });
        document.addEventListener("keydown", function (event) {
            if (event.key === "Escape" && panel.classList.contains("is-open")) {
                setOpen(false);
                toggle.focus();
            }
        });
        window.addEventListener("resize", function () {
            if (window.innerWidth > 1020) {
                setOpen(false);
            }
        });
    }
    if (header) {
        const onScroll = function () {
            header.classList.toggle("is-scrolled", window.scrollY > 8);
        };
        window.addEventListener("scroll", onScroll, { passive: true });
        onScroll();
    }
}

// Quick fade-out before following an internal link (about 0.1 seconds)
function setupPageTransitions() {
    document.addEventListener("click", function (event) {
        if (prefersReducedMotion || event.defaultPrevented || event.button !== 0 ||
            event.metaKey || event.ctrlKey || event.shiftKey || event.altKey) {
            return;
        }
        const link = event.target.closest("a[href]");
        if (!link || link.target === "_blank" || link.hasAttribute("download")) {
            return;
        }
        const href = link.getAttribute("href");
        if (!href || href.charAt(0) === "#" || /^(https?:|mailto:|tel:)/.test(href)) {
            return;
        }
        event.preventDefault();
        document.body.classList.add("is-leaving");
        setTimeout(function () { window.location.href = link.href; }, 110);
    });
    window.addEventListener("pageshow", function () {
        document.body.classList.remove("is-leaving");
    });
}

// ======================================
// LANDING + ABOUT
// ======================================

// The hero preview uses the app's own demo data, so every number is calculated, not invented.
function initLanding() {
    const demo = makeDemoProducts();
    const counts = countByStatus(demo);
    const health = Math.round((counts.active / demo.length) * 100);
    setText("lp-total", demo.length);
    setText("lp-active", counts.active);
    setText("lp-soon", counts["expiring-soon"]);
    setText("lp-expired", counts.expired);
    setText("lp-health", health + "%");
    document.getElementById("lp-ring").style.setProperty("--p", health);
    setText("lt-total", demo.length);
    setText("lt-active", counts.active);
    setText("lt-soon", counts["expiring-soon"]);
    setText("lt-expired", counts.expired);

    const sorted = sortByExpiry(demo);
    const firstExpired = sorted.filter(function (p) { return getStatus(p) === "expired"; })[0];
    const soon = sorted.filter(function (p) { return getStatus(p) === "expiring-soon"; });
    const shown = [firstExpired, soon[0], soon[1], soon[2]].filter(Boolean);
    document.getElementById("lp-list").innerHTML = shown.map(function (p) {
        const s = getStatus(p);
        return '<li><div><b>' + esc(p.name) + '</b><small>' + getCategoryName(p.category) + ' · ' + describeDays(getDaysRemaining(p)) + '</small></div>' +
            '<span class="status-badge ' + getStatusClass(s) + '">' + getStatusLabel(s) + '</span></li>';
    }).join("");
    if (soon[0]) {
        setText("lp-alert-title", soon[0].name);
        setText("lp-alert-text", describeDays(getDaysRemaining(soon[0])));
    }

    // soft pointer movement on the preview (skipped when reduced motion is on)
    const visual = document.getElementById("hero-visual");
    if (!prefersReducedMotion && visual && window.matchMedia("(hover: hover)").matches) {
        visual.addEventListener("mousemove", function (event) {
            const box = visual.getBoundingClientRect();
            visual.style.setProperty("--rx", ((event.clientX - box.left) / box.width - 0.5).toFixed(3));
            visual.style.setProperty("--ry", ((event.clientY - box.top) / box.height - 0.5).toFixed(3));
        });
        visual.addEventListener("mouseleave", function () {
            visual.style.setProperty("--rx", 0);
            visual.style.setProperty("--ry", 0);
        });
    }

    // if someone is already logged in, point the header at the app
    if (getCurrentUser()) {
        const actions = document.querySelector(".auth-actions");
        actions.innerHTML = '<a href="dashboard.html" class="btn btn-primary">Open Dashboard ' + icon("arrow") + '</a>';
    }
}

function initAbout() {
    const steps = document.querySelectorAll(".about-step");
    steps.forEach(function (step) {
        step.addEventListener("click", function () {
            steps.forEach(function (s) { s.classList.remove("is-active"); });
            step.classList.add("is-active");
        });
    });
}

// ======================================
// EXPIRYCARE INTELLIGENCE SERVICES
// ======================================
// Use same-origin API when Flask serves the frontend. When using a separate local
// static server (e.g. VS Code Live Server), route API requests to Flask on port 5000.
// For a separately deployed frontend, define window.EXPIRYCARE_API_BASE before app.js.
const EXPIRYCARE_API = {
    baseUrl: (window.EXPIRYCARE_API_BASE || (function () {
        const host = window.location.hostname;
        const port = window.location.port;
        if (window.location.protocol === "file:") return "http://127.0.0.1:5000/api";
        if ((host === "localhost" || host === "127.0.0.1") && ["5500", "5501", "8000", "8080"].includes(port)) return "http://127.0.0.1:5000/api";
        return window.location.origin + "/api";
    })()), timeoutMs: 20000
};
let scannerIdentitySource = "user-entered";

async function lookupFoodBarcode(code) {
    if (!/^\d{8,14}$/.test(code)) throw new Error("Enter a valid 8–14 digit barcode.");
    const response = await fetch("https://world.openfoodfacts.org/api/v2/product/" + encodeURIComponent(code) + ".json?fields=product_name,brands,categories,quantity,code");
    if (!response.ok) throw new Error("The product database is unavailable. You can enter details manually.");
    const data = await response.json();
    if (data.status !== 1 || !data.product) throw new Error("No matching food product was found. Try the label or manual entry.");
    return data.product;
}

async function callExpiryCareApi(path, body) {
    const controller = new AbortController();
    const timeout = setTimeout(function () { controller.abort(); }, EXPIRYCARE_API.timeoutMs);
    try {
        const response = await fetch(EXPIRYCARE_API.baseUrl + path, { method: "POST", headers: { "Content-Type": "application/json" }, body: JSON.stringify(body), signal: controller.signal });
        if (!response.ok) throw new Error("Service returned HTTP " + response.status + ". Check that the Flask service is running and configured.");
        return await response.json();
    } finally { clearTimeout(timeout); }
}

function initIntelligenceScanner() {
    const message = document.getElementById("scanner-message");
    if (!message) return;
    const barcode = document.getElementById("barcode-manual");
    const video = document.getElementById("barcode-video");
    let stream = null, scanTimer = null;
    function say(text) { message.textContent = text; }
    function applyBarcodeProduct(product, code) {
        if (product.product_name) { document.getElementById("product-name").value = product.product_name; scannerIdentitySource = "product-database: Open Food Facts"; }
        if (product.brands) document.getElementById("product-notes").value = (document.getElementById("product-notes").value + " Brand: " + product.brands).trim();
        const cat = (product.categories || "").toLowerCase();
        if (cat.includes("food") || cat.includes("beverage") || cat.includes("snack")) document.getElementById("product-category").value = "grocery";
        barcode.value = code;
        say("Database match loaded. Review and correct all fields; barcode lookup does not supply or verify expiry dates.");
    }
    document.getElementById("lookup-barcode").addEventListener("click", async function () {
        const code = barcode.value.trim(); if (!code) { say("Enter a barcode first."); return; }
        say("Looking up supported food-product database…");
        try { const product = await lookupFoodBarcode(code); applyBarcodeProduct(product, code); }
        catch (error) { say(error.message || "Lookup failed. Please enter details manually."); }
    });
    document.getElementById("start-barcode-scan").addEventListener("click", async function () {
        if (!("BarcodeDetector" in window) || !navigator.mediaDevices || !navigator.mediaDevices.getUserMedia) { say("Live scanning is not supported in this browser. Enter the barcode manually or upload a label photo."); return; }
        try {
            stream = await navigator.mediaDevices.getUserMedia({ video: { facingMode: "environment" } }); video.srcObject = stream; video.hidden = false; await video.play();
            const detector = new BarcodeDetector({ formats: ["ean_13", "ean_8", "upc_a", "upc_e", "code_128"] });
            document.getElementById("start-barcode-scan").disabled = true; document.getElementById("stop-barcode-scan").disabled = false;
            const scan = async function () { if (!stream) return; try { const codes = await detector.detect(video); if (codes.length) { barcode.value = codes[0].rawValue; document.getElementById("lookup-barcode").click(); stop(); return; } } catch (_) {} scanTimer = requestAnimationFrame(scan); };
            scan(); say("Camera is active. Hold the barcode steady in view.");
        } catch (_) { say("Camera permission was denied or the camera is unavailable. Enter the barcode manually."); }
    });
    function stop() { if (scanTimer) cancelAnimationFrame(scanTimer); if (stream) stream.getTracks().forEach(function (track) { track.stop(); }); stream = null; video.hidden = true; document.getElementById("start-barcode-scan").disabled = false; document.getElementById("stop-barcode-scan").disabled = true; }
    document.getElementById("stop-barcode-scan").addEventListener("click", stop);
    const fileInput = document.getElementById("label-image"), preview = document.getElementById("label-preview");
    fileInput.addEventListener("change", function () {
        const file = fileInput.files && fileInput.files[0]; if (!file) return;
        if (!file.type.startsWith("image/") || file.size > 8 * 1024 * 1024) { fileInput.value = ""; say("Choose an image under 8 MB. No image was uploaded."); return; }
        preview.src = URL.createObjectURL(file); preview.hidden = false; say("Image ready. Label OCR/AI needs the Flask endpoint; no analysis has been claimed yet.");
    });
    document.getElementById("analyze-label").addEventListener("click", async function () {
        const file = fileInput.files && fileInput.files[0]; if (!file) { say("Choose a product or label photo first."); return; }
        say("Sending image to configured label-analysis service…");
        try {
            const imageData = await new Promise(function (resolve, reject) {
                const reader = new FileReader(); reader.onload = function () { resolve(reader.result); }; reader.onerror = function () { reject(new Error("The image could not be read.")); }; reader.readAsDataURL(file);
            });
            const result = await callExpiryCareApi("/products/analyze-label", { imageName: file.name, imageType: file.type, imageData: imageData });
            if (result.name) { document.getElementById("product-name").value = result.name; scannerIdentitySource = "AI suggestion; requires user verification"; }
            if (result.manufacturingDate) document.getElementById("manufacturing-date").value = result.manufacturingDate;
            if (result.expiryDate) document.getElementById("expiry-date").value = result.expiryDate;
            if (result.batchNumber) document.getElementById("product-batch-number").value = result.batchNumber;
            say("Service returned suggestions. Verify every field against the actual label before saving.");
        } catch (error) { say("Label scan could not complete: " + error.message + " You can still enter details manually."); }
    });
}

function initGuidanceChatbot() {
    const form = document.getElementById("guidance-chat-form"); if (!form) return;
    const input = document.getElementById("guidance-chat-input"), log = document.getElementById("guidance-chat-log"), send = form.querySelector("button[type='submit']");
    form.addEventListener("submit", async function (event) {
        event.preventDefault(); const question = input.value.trim(); if (!question) return;
        const userLine = document.createElement("p"); userLine.className = "chat-message chat-user"; userLine.textContent = "You: " + question; log.appendChild(userLine); input.value = ""; send.disabled = true;
        const status = document.createElement("p"); status.className = "chat-message"; status.setAttribute("role", "status"); status.textContent = "Checking ExpiryCare guidance…"; log.appendChild(status);
        try { const data = await callExpiryCareApi("/guidance/chat", { message: question }); status.textContent = (data.mode === "offline_knowledge_base" ? "ExpiryCare guidance (offline knowledge base): " : "ExpiryCare guidance: ") + (data.reply || "The service returned no answer.") + (data.disclaimer ? " — " + data.disclaimer : ""); }
        catch (error) { status.textContent = "Guidance service is unreachable. Check that the Flask backend is running. Do not assume an unidentified item is safe; consult a pharmacist about medicines. Detail: " + error.message; }
        send.disabled = false; input.focus();
    });
}

// ======================================
// PAGE INITIALIZATION
// ======================================

document.addEventListener("DOMContentLoaded", function () {
    const page = document.body.id;

    if (!checkLogin(page)) {
        return;
    }
    injectIconSprite();
    document.body.classList.add("page-ready");
    setupNavigation();
    setupPageTransitions();
    setActiveNav();
    showCurrentUserName();
    setupLogout();

    if (page === "page-landing") {
        initLanding();
    } else if (page === "page-about") {
        initAbout();
    } else if (page === "page-register") {
        initRegister();
    } else if (page === "page-login") {
        initLogin();
    } else if (page === "page-forgot-password") {
        initForgotPassword();
    } else if (page === "page-dashboard") {
        initDashboard();
    } else if (page === "page-inventory") {
        initInventory();
    } else if (page === "page-add-product") {
        initAddProduct();
        initIntelligenceScanner();
    } else if (page === "page-product-details") {
        initProductDetails();
    } else if (page === "page-edit-product") {
        initEditProduct();
    } else if (page === "page-alerts") {
        initAlerts();
    } else if (page === "page-healthcare-guidance") {
        initGuidance();
        initGuidanceChatbot();
    } else if (page === "page-profile") {
        initProfile();
    }

    setupScrollReveal();
    showFlashMessage();
});
