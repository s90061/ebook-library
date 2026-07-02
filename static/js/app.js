/* === E-Book Library - Main App === */

const API = {
    async getBooks(status, search) {
        const params = new URLSearchParams();
        if (status) params.set('status', status);
        if (search) params.set('search', search);
        const res = await fetch(`/api/books?${params}`);
        return res.json();
    },
    async getBook(id) {
        const res = await fetch(`/api/books/${id}`);
        return res.json();
    },
    async createBook(data) {
        const res = await fetch('/api/books', {
            method: 'POST',
            headers: { 'Content-Type': 'application/json' },
            body: JSON.stringify(data)
        });
        return res.json();
    },
    async updateBook(id, data) {
        const res = await fetch(`/api/books/${id}`, {
            method: 'PUT',
            headers: { 'Content-Type': 'application/json' },
            body: JSON.stringify(data)
        });
        return res.json();
    },
    async deleteBook(id) {
        return fetch(`/api/books/${id}`, { method: 'DELETE' }).then(r => r.json());
    },
    async addPlatform(bookId, platform) {
        const res = await fetch(`/api/books/${bookId}/platforms`, {
            method: 'POST',
            headers: { 'Content-Type': 'application/json' },
            body: JSON.stringify(platform)
        });
        return res.json();
    }
};

// ======== State ========
let allBooks = [];
let currentBookId = null;
let platformRowCount = 1;

// ======== Render Grid ========
function getPlatformChipHTML(platforms) {
    return platforms.map(p => {
        const name = p.platform_name || '其他';
        const cls = ['Readmoo','HyRead','Kobo','Google'].includes(name) ? name : 'default';
        return `<span class="platform-chip ${cls}">${name}</span>`;
    }).join('');
}

function getStatusBadgeHTML(status) {
    const labels = { Wishlist: '欲讀', Reading: '閱讀中', Completed: '完讀' };
    return `<span class="status-badge ${status}">${labels[status] || status}</span>`;
}

function getStarsHTML(rating, interactive = false) {
    let html = '<div class="star-rating">';
    for (let i = 1; i <= 5; i++) {
        const cls = i <= rating ? 'star active' : 'star';
        if (interactive) {
            html += `<span class="${cls}" data-s="${i}" onclick="setRating(${i})">★</span>`;
        } else {
            html += `<span class="${cls}">★</span>`;
        }
    }
    html += '</div>';
    return html;
}

function renderBooks(books) {
    const grid = document.getElementById('bookGrid');
    const isEmpty = books.length === 0;

    if (isEmpty) {
        grid.innerHTML = `
            <div class="empty-state">
                <div class="icon">📖</div>
                <p>還沒有任何書籍</p>
                <p class="sub">點擊右上角「+ 新增」來加入第一本書</p>
            </div>`;
        return;
    }

    grid.innerHTML = books.map(b => `
        <div class="book-card" onclick="openDetail(${b.id})">
            <div class="cover">
                ${b.cover_url
                    ? `<img src="${b.cover_url}" alt="${b.title}" loading="lazy">`
                    : `<span class="no-cover">📕</span>`
                }
                ${getStatusBadgeHTML(b.status)}
            </div>
            <div class="card-body">
                <div class="card-title">${b.title}</div>
                ${b.author ? `<div class="card-author">${b.author}</div>` : ''}
                <div class="card-platforms">
                    ${b.platforms ? getPlatformChipHTML(b.platforms) : ''}
                </div>
            </div>
        </div>
    `).join('');
}

async function loadBooks() {
    const status = document.getElementById('statusFilter').value;
    const search = document.getElementById('searchInput').value.trim();
    const result = await API.getBooks(status, search || undefined);
    allBooks = result.books || [];
    renderBooks(allBooks);
}

// ======== Detail Drawer ========
async function openDetail(bookId) {
    currentBookId = bookId;
    const book = await API.getBook(bookId);

    document.getElementById('drawerOverlay').classList.add('active');
    const drawer = document.getElementById('detailDrawer');
    drawer.classList.add('open');

    const body = document.getElementById('drawerBody');
    const platforms = book.platforms || [];

    body.innerHTML = `
        <div class="detail-cover">
            ${book.cover_url
                ? `<img src="${book.cover_url}" alt="${book.title}">`
                : `<div class="no-cover">📕</div>`
            }
        </div>

        <div class="detail-title">${book.title}</div>
        ${book.subtitle ? `<div class="detail-subtitle">${book.subtitle}</div>` : ''}
        ${book.author ? `<div class="detail-author">👤 ${book.author}</div>` : ''}

        <div class="status-selector">
            ${['Wishlist','Reading','Completed'].map(s => {
                const labels = {Wishlist:'欲讀',Reading:'閱讀中',Completed:'完讀'};
                return `<button class="status-btn ${s === book.status ? 'active' : ''} ${s}" 
                        onclick="changeStatus(${bookId}, '${s}')">${labels[s]}</button>`;
            }).join('')}
        </div>

        ${getStarsHTML(book.rating, true)}

        <div class="detail-meta">
            ${book.publisher ? `<div class="meta-item"><div class="label">出版社</div><div class="value">${book.publisher}</div></div>` : ''}
            ${book.year ? `<div class="meta-item"><div class="label">出版年份</div><div class="value">${book.year}</div></div>` : ''}
            ${book.isbn ? `<div class="meta-item"><div class="label">ISBN</div><div class="value">${book.isbn}</div></div>` : ''}
            ${book.tags ? `<div class="meta-item"><div class="label">標籤</div><div class="value">${book.tags}</div></div>` : ''}
            ${book.date_added ? `<div class="meta-item"><div class="label">新增日期</div><div class="value">${new Date(book.date_added).toLocaleDateString()}</div></div>` : ''}
        </div>

        <div class="detail-section-title">📌 平台連結</div>
        <div class="platform-list">
            ${platforms.length > 0
                ? platforms.map(p => `
                    <div class="platform-item">
                        <div>
                            <div class="p-name">${p.platform_name}</div>
                            ${p.price ? `<div class="p-price">NT$ ${p.price}</div>` : ''}
                        </div>
                        <a href="${p.url}" target="_blank" class="p-link">前往閱讀 →</a>
                    </div>
                `).join('')
                : '<div style="color:var(--text-muted);font-size:14px;">尚未新增平台連結</div>'
            }
        </div>

        <div class="detail-note">
            <label>個人筆記</label>
            <textarea id="noteInput" placeholder="記錄你的想法..." onchange="saveNote(${bookId}, this.value)">${book.note || ''}</textarea>
        </div>

        <div class="detail-actions">
            <button class="btn btn-outline" onclick="deleteBook(${bookId})" style="color:#e57373;border-color:#e57373;">刪除</button>
        </div>
    `;
}

function closeDetail() {
    document.getElementById('drawerOverlay').classList.remove('active');
    document.getElementById('detailDrawer').classList.remove('open');
    currentBookId = null;
}

async function changeStatus(bookId, status) {
    await API.updateBook(bookId, { status });
    loadBooks();
    openDetail(bookId); // Refresh drawer
}

let pendingRating = null;
async function setRating(rating) {
    if (!currentBookId) return;
    pendingRating = rating;
    await API.updateBook(currentBookId, { rating });
    // Update stars visually
    document.querySelectorAll('.star-rating .star').forEach((el, i) => {
        el.classList.toggle('active', i < rating);
    });
}

async function saveNote(bookId, note) {
    await API.updateBook(bookId, { note });
}

async function deleteBook(bookId) {
    if (!confirm('確定要刪除此書籍？')) return;
    await API.deleteBook(bookId);
    closeDetail();
    loadBooks();
}

// ======== Add Book Modal ========
document.getElementById('addBookBtn').onclick = () => {
    document.getElementById('addOverlay').classList.add('active');
    document.getElementById('addDrawer').classList.add('open');
    platformRowCount = 1;
};

function closeAddDrawer() {
    document.getElementById('addOverlay').classList.remove('active');
    document.getElementById('addDrawer').classList.remove('open');
    document.getElementById('addForm').reset();
    // Reset platform rows
    document.getElementById('platformInputs').innerHTML = `
        <div class="platform-item" style="padding:0;background:transparent;border:none;margin-bottom:8px;gap:6px;flex-wrap:wrap;">
            <select id="platName0" style="background:var(--bg-secondary);border:1px solid var(--border);border-radius:6px;color:var(--text-primary);padding:8px;font-size:13px;flex:1;min-width:100px;">
                <option value="">選擇平台</option>
                <option value="Readmoo">Readmoo</option>
                <option value="HyRead">HyRead</option>
                <option value="Kobo">Kobo</option>
                <option value="Google">Google Play</option>
                <option value="其他">其他</option>
            </select>
            <input type="url" id="platUrl0" placeholder="書籍網址" style="flex:2;min-width:150px;background:var(--bg-secondary);border:1px solid var(--border);border-radius:6px;color:var(--text-primary);padding:8px;font-size:13px;outline:none;">
            <button type="button" class="btn-outline" style="padding:6px 12px;font-size:12px;" onclick="addPlatformRow()">+</button>
        </div>
    `;
}

function addPlatformRow() {
    const container = document.getElementById('platformInputs');
    const idx = platformRowCount++;
    const row = document.createElement('div');
    row.className = 'platform-item';
    row.style.cssText = 'padding:0;background:transparent;border:none;margin-bottom:8px;gap:6px;flex-wrap:wrap;';
    row.innerHTML = `
        <select id="platName${idx}" style="background:var(--bg-secondary);border:1px solid var(--border);border-radius:6px;color:var(--text-primary);padding:8px;font-size:13px;flex:1;min-width:100px;">
            <option value="">選擇平台</option>
            <option value="Readmoo">Readmoo</option>
            <option value="HyRead">HyRead</option>
            <option value="Kobo">Kobo</option>
            <option value="Google">Google Play</option>
            <option value="其他">其他</option>
        </select>
        <input type="url" id="platUrl${idx}" placeholder="書籍網址" style="flex:2;min-width:150px;background:var(--bg-secondary);border:1px solid var(--border);border-radius:6px;color:var(--text-primary);padding:8px;font-size:13px;outline:none;">
        <button type="button" style="background:none;border:none;color:#e57373;font-size:18px;cursor:pointer;padding:4px 8px;" onclick="this.parentElement.remove()">✕</button>
    `;
    container.appendChild(row);
}

async function submitNewBook() {
    const title = document.getElementById('addTitle').value.trim();
    if (!title) { alert('請填寫書名'); return; }

    const platforms = [];
    // Collect all platform rows
    const container = document.getElementById('platformInputs');
    const selects = container.querySelectorAll('select');
    const urls = container.querySelectorAll('input[type="url"]');
    for (let i = 0; i < selects.length; i++) {
        const name = selects[i].value;
        const url = urls[i].value.trim();
        if (name && url) {
            platforms.push({ platform_name: name, url });
        }
    }

    const data = {
        title,
        subtitle: document.getElementById('addSubtitle').value.trim() || null,
        author: document.getElementById('addAuthor').value.trim() || null,
        publisher: document.getElementById('addPublisher').value.trim() || null,
        isbn: document.getElementById('addIsbn').value.trim() || null,
        cover_url: document.getElementById('addCover').value.trim() || null,
        tags: document.getElementById('addTags').value.trim() || null,
        platforms: platforms.length > 0 ? platforms : null
    };

    try {
        const result = await API.createBook(data);
        if (result.success) {
            closeAddDrawer();
            loadBooks();
        } else {
            alert('新增失敗：' + (result.detail || '未知錯誤'));
        }
    } catch (e) {
        alert('新增失敗：' + e.message);
    }
}

// ======== Event Listeners ========
document.getElementById('statusFilter').onchange = loadBooks;
document.getElementById('searchInput').oninput = debounce(loadBooks, 300);
document.getElementById('closeDrawer').onclick = closeDetail;
document.getElementById('drawerOverlay').onclick = closeDetail;
document.getElementById('closeAddDrawer').onclick = closeAddDrawer;
document.getElementById('addOverlay').onclick = closeAddDrawer;

function debounce(fn, delay) {
    let timer;
    return (...args) => {
        clearTimeout(timer);
        timer = setTimeout(() => fn(...args), delay);
    };
}

// ======== Init ========
loadBooks();