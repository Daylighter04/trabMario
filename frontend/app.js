const API_BASE = window.location.origin.includes(':8000')
    ? `${window.location.origin}/api`
    : 'http://127.0.0.1:8000/api';

if (window.Chart) {
    Chart.defaults.color = '#94a3b8';
    Chart.defaults.font.family = 'Inter, sans-serif';
    Chart.defaults.borderColor = 'rgba(255, 255, 255, 0.05)';
    Chart.defaults.plugins.tooltip.backgroundColor = '#0f0a22';
    Chart.defaults.plugins.tooltip.titleColor = '#ffffff';
    Chart.defaults.plugins.tooltip.bodyColor = '#60a5fa';
    Chart.defaults.plugins.tooltip.borderColor = '#2b1b54';
    Chart.defaults.plugins.tooltip.borderWidth = 1;
}

const AppUtils = {
    showToast(message, type = 'info') {
        let container = document.getElementById('toast-container');
        if (!container) {
            container = document.createElement('div');
            container.id = 'toast-container';
            container.className = 'fixed bottom-5 right-5 z-50 flex flex-col gap-2 pointer-events-none';
            document.body.appendChild(container);
        }

        const toast = document.createElement('div');
        const bgColors = {
            success: 'bg-[#120c2a]/95 text-blue-400 border border-blue-500/50 shadow-xl shadow-blue-950/40',
            error: 'bg-[#120c2a]/95 text-rose-400 border border-rose-500/50 shadow-xl shadow-rose-950/40',
            info: 'bg-[#120c2a]/95 text-purple-200 border border-[#2b1b54] shadow-xl shadow-purple-950/40',
        };

        toast.className = `${bgColors[type] || bgColors.info} px-4 py-3 rounded-xl text-sm font-medium transition-all duration-300 transform translate-y-2 opacity-0 pointer-events-auto flex items-center gap-2 backdrop-blur-md`;
        toast.innerHTML = `
            <span>${message}</span>
            <button class="ml-2 hover:opacity-75 focus:outline-none text-slate-400 hover:text-white" onclick="this.parentElement.remove()">✕</button>
        `;

        container.appendChild(toast);
        requestAnimationFrame(() => toast.classList.remove('translate-y-2', 'opacity-0'));

        setTimeout(() => {
            toast.classList.add('opacity-0', 'translate-y-2');
            setTimeout(() => toast.remove(), 300);
        }, 4000);
    }
};

let ratingDistChart = null;

async function initIndex() {
    await populateUserSelect();
    const userSelect = document.getElementById('select-user');
    const inputK = document.getElementById('input-k');
    const inputN = document.getElementById('input-n');

    const run = () => {
        const uId = userSelect ? parseInt(userSelect.value, 10) : 65;
        const kVal = inputK ? parseInt(inputK.value, 10) : 20;
        const nVal = inputN ? parseInt(inputN.value, 10) : 10;
        runComparison(uId, nVal, kVal);
    };

    if (userSelect) userSelect.addEventListener('change', run);
    if (inputK) inputK.addEventListener('change', run);
    if (inputN) inputN.addEventListener('change', run);

    run();
}

async function populateUserSelect() {
    const select = document.getElementById('select-user');
    if (!select) return;

    try {
        const res = await fetch(`${API_BASE}/users`);
        if (!res.ok) throw new Error();
        const data = await res.json();
        select.innerHTML = '';
        data.users.forEach(uid => {
            const opt = document.createElement('option');
            opt.value = uid;
            opt.textContent = `Usuário ${uid}`;
            if (uid === 65) opt.selected = true;
            select.appendChild(opt);
        });
    } catch {
        select.innerHTML = '';
        for (let i = 1; i <= 610; i++) {
            const opt = document.createElement('option');
            opt.value = i;
            opt.textContent = `Usuário ${i}`;
            if (i === 65) opt.selected = true;
            select.appendChild(opt);
        }
    }
}

async function runComparison(userId = 65, n = 10, k = 20) {
    const loader = document.getElementById('comparison-loader');
    if (loader) loader.classList.remove('hidden');

    try {
        const res = await fetch(`${API_BASE}/compare?user_id=${userId}&n=${n}&k=${k}`);
        if (!res.ok) throw new Error(`Status ${res.status}: ${res.statusText}`);
        const data = await res.json();

        const setVal = (id, val) => {
            const el = document.getElementById(id);
            if (el) el.textContent = val;
        };

        setVal('user-card-id', `User #${data.user_id}`);
        setVal('user-card-mean', `★ ${data.user_mean.toFixed(2)}`);
        setVal('user-card-ratings', `${data.user_total_ratings} filmes`);
        setVal('user-card-common', `${data.common_count} filmes`);

        const commonBanner = document.getElementById('common-movies-banner');
        if (commonBanner) {
            if (data.common_count > 0) {
                const titles = data.common_movies.map(m => m.title).join(', ');
                commonBanner.className = 'p-3.5 bg-gradient-to-r from-blue-900/30 to-indigo-900/30 border border-blue-500/40 rounded-xl text-xs flex items-center justify-between text-blue-300 shadow-md shadow-blue-950/20';
                commonBanner.innerHTML = `
                    <div class="flex items-center gap-2">
                        <span class="material-symbols-outlined text-[18px] text-blue-400">verified</span>
                        <span><strong>${data.common_count} Obra(s) em Comum no Top-${data.n}:</strong> ${titles}</span>
                    </div>
                    <span class="font-data-mono font-bold bg-gradient-to-r from-blue-600 to-indigo-600 text-white px-2.5 py-1 rounded-md text-[11px] shadow-sm">Consenso</span>
                `;
                commonBanner.classList.remove('hidden');
            } else {
                commonBanner.className = 'p-3.5 bg-[#120c2a] border border-[#241747] rounded-xl text-xs flex items-center justify-between text-slate-400';
                commonBanner.innerHTML = `
                    <div class="flex items-center gap-2">
                        <span class="material-symbols-outlined text-[18px] text-indigo-400">info</span>
                        <span>Nenhum filme em comum no Top-${data.n}. As abordagens exploraram perfis complementares.</span>
                    </div>
                `;
                commonBanner.classList.remove('hidden');
            }
        }

        const commonSet = new Set(data.common_movies.map(m => m.movieId));

        const tbodyUU = document.getElementById('tbody-user-user');
        if (tbodyUU) {
            tbodyUU.innerHTML = data.user_user.map((m, idx) => {
                const isCommon = commonSet.has(m.movieId);
                return `
                    <tr class="border-b border-[#221644] bg-[#120c2a]/70 hover:bg-[#191138] transition-colors text-sm ${isCommon ? 'ring-1 ring-blue-500/50 bg-[#160f33]' : ''}">
                        <td class="p-3.5 font-data-mono text-slate-400 font-bold">#${idx + 1}</td>
                        <td class="p-3.5">
                            <div class="font-bold text-white flex items-center gap-2">
                                <span>${m.title}</span>
                                ${isCommon ? '<span class="bg-gradient-to-r from-blue-500 to-indigo-500 text-white font-extrabold text-[10px] px-2 py-0.5 rounded shadow-sm" title="Em comum com Item-Item">COMUM</span>' : ''}
                            </div>
                            <div class="text-xs text-slate-400 font-data-mono mt-0.5">${m.genres}</div>
                        </td>
                        <td class="p-3.5 text-right">
                            <span class="inline-flex items-center gap-1.5 px-2.5 py-1 rounded-lg bg-[#181038] border border-[#2c1d56]">
                                <span class="text-blue-400">★</span>
                                <span class="font-data-mono font-bold text-blue-300">${m.predicted_rating.toFixed(2)}</span>
                            </span>
                        </td>
                    </tr>
                `;
            }).join('');
        }

        const tbodyII = document.getElementById('tbody-item-item');
        if (tbodyII) {
            tbodyII.innerHTML = data.item_item.map((m, idx) => {
                const isCommon = commonSet.has(m.movieId);
                return `
                    <tr class="border-b border-[#221644] bg-[#120c2a]/70 hover:bg-[#191138] transition-colors text-sm ${isCommon ? 'ring-1 ring-blue-500/50 bg-[#160f33]' : ''}">
                        <td class="p-3.5 font-data-mono text-slate-400 font-bold">#${idx + 1}</td>
                        <td class="p-3.5">
                            <div class="font-bold text-white flex items-center gap-2">
                                <span>${m.title}</span>
                                ${isCommon ? '<span class="bg-gradient-to-r from-blue-500 to-indigo-500 text-white font-extrabold text-[10px] px-2 py-0.5 rounded shadow-sm" title="Em comum com User-User">COMUM</span>' : ''}
                            </div>
                            <div class="text-xs text-slate-400 font-data-mono mt-0.5">${m.genres}</div>
                        </td>
                        <td class="p-3.5 text-center">
                            <span class="text-xs font-data-mono text-purple-200 bg-[#181038] px-2.5 py-1 rounded-lg border border-[#2c1d56]">
                                ${m.favorites_count} favs
                            </span>
                        </td>
                        <td class="p-3.5 text-right">
                            <span class="inline-flex items-center gap-1.5 px-2.5 py-1 rounded-lg bg-[#181038] border border-[#2c1d56]">
                                <span class="text-blue-400 text-xs">score</span>
                                <span class="font-data-mono font-bold text-blue-300">${m.score.toFixed(3)}</span>
                            </span>
                        </td>
                    </tr>
                `;
            }).join('');
        }
    } catch (err) {
        console.error('Erro em runComparison:', err);
        AppUtils.showToast(`Erro ao carregar comparação: ${err.message}`, 'error');
    } finally {
        if (loader) loader.classList.add('hidden');
    }
}

let currentSelectedMovieId = 1;

async function initDataset() {
    const searchInput = document.getElementById('movie-search-input');
    const suggestionsBox = document.getElementById('search-suggestions');
    const inputK = document.getElementById('k-similar-input');

    if (inputK) {
        inputK.addEventListener('change', () => {
            const kVal = parseInt(inputK.value, 10) || 10;
            loadSimilarMovies(currentSelectedMovieId, kVal);
        });
    }

    if (searchInput && suggestionsBox) {
        let timer;
        searchInput.addEventListener('input', (e) => {
            clearTimeout(timer);
            const q = e.target.value.trim();
            if (q.length < 2) {
                suggestionsBox.classList.add('hidden');
                return;
            }
            timer = setTimeout(async () => {
                try {
                    const res = await fetch(`${API_BASE}/movies?search=${encodeURIComponent(q)}&limit=8`);
                    if (!res.ok) return;
                    const data = await res.json();
                    if (data.movies.length === 0) {
                        suggestionsBox.innerHTML = '<div class="p-3 text-xs text-slate-400">Nenhum filme encontrado.</div>';
                        suggestionsBox.classList.remove('hidden');
                        return;
                    }

                    suggestionsBox.innerHTML = data.movies.map(m => `
                        <div class="p-3 hover:bg-[#1a123a] cursor-pointer border-b border-[#221644] flex justify-between items-center transition"
                            onclick="selectMovie(${m.movieId}, '${m.title.replace(/'/g, "\\'")}')">
                            <div>
                                <div class="font-bold text-white text-sm">${m.title}</div>
                                <div class="text-xs text-slate-400 font-data-mono">${m.genres}</div>
                            </div>
                            <span class="text-xs font-data-mono text-blue-400 border border-blue-500/30 bg-blue-500/10 px-2 py-0.5 rounded-md">ID ${m.movieId}</span>
                        </div>
                    `).join('');
                    suggestionsBox.classList.remove('hidden');
                } catch (err) {
                    console.error('Erro na busca:', err);
                }
            }, 250);
        });

        document.addEventListener('click', (e) => {
            if (!searchInput.contains(e.target) && !suggestionsBox.contains(e.target)) {
                suggestionsBox.classList.add('hidden');
            }
        });
    }

    loadSimilarMovies(1, 10);
}

function selectMovie(movieId, title) {
    currentSelectedMovieId = movieId;
    const searchInput = document.getElementById('movie-search-input');
    const suggestionsBox = document.getElementById('search-suggestions');
    if (searchInput) searchInput.value = title;
    if (suggestionsBox) suggestionsBox.classList.add('hidden');

    const inputK = document.getElementById('k-similar-input');
    const kVal = inputK ? parseInt(inputK.value, 10) || 10 : 10;
    loadSimilarMovies(movieId, kVal);
}

async function loadSimilarMovies(movieId = 1, k = 10) {
    const loader = document.getElementById('similar-loader');
    if (loader) loader.classList.remove('hidden');

    try {
        const res = await fetch(`${API_BASE}/recommend/similar-movies?movie_id=${movieId}&k=${k}`);
        if (!res.ok) throw new Error(`Status ${res.status}: ${res.statusText}`);
        const data = await res.json();

        const target = data.target_movie;
        const setVal = (id, val) => {
            const el = document.getElementById(id);
            if (el) el.textContent = val;
        };
        setVal('target-movie-title', target.title);
        setVal('target-movie-genres', target.genres);
        setVal('target-movie-id', `ID #${target.movieId}`);

        const tbody = document.getElementById('similar-movies-tbody');
        if (tbody) {
            tbody.innerHTML = data.similar_movies.map((m, idx) => {
                const simPercent = (m.similarity * 100).toFixed(1);
                return `
                    <tr class="border-b border-[#221644] bg-[#120c2a]/70 hover:bg-[#191138] transition-colors text-sm">
                        <td class="p-3.5 font-data-mono text-slate-400 font-bold">#${idx + 1}</td>
                        <td class="p-3.5">
                            <span class="font-bold text-white text-base hover:text-blue-400 transition">${m.title}</span>
                            <div class="text-xs text-slate-400 font-data-mono mt-0.5">ID: ${m.movieId} • ${m.genres}</div>
                        </td>
                        <td class="p-3.5 font-data-mono text-slate-400">${m.genres}</td>
                        <td class="p-3.5 text-right">
                            <div class="flex items-center justify-end gap-3">
                                <div class="w-28 bg-[#0a061b] rounded-full h-2 hidden sm:block border border-[#241747] overflow-hidden shadow-inner">
                                    <div class="bg-gradient-to-r from-blue-500 via-indigo-500 to-purple-500 h-2 rounded-full" style="width: ${simPercent}%"></div>
                                </div>
                                <span class="px-2.5 py-1 rounded-lg font-data-mono font-bold text-sm bg-[#181038] text-blue-400 border border-[#2c1d56]">
                                    ${m.similarity.toFixed(4)}
                                </span>
                            </div>
                        </td>
                    </tr>
                `;
            }).join('');
        }
    } catch (err) {
        console.error('Erro em loadSimilarMovies:', err);
        AppUtils.showToast(`Erro ao buscar similares: ${err.message}`, 'error');
    } finally {
        if (loader) loader.classList.add('hidden');
    }
}

async function initAnalytics() {
    await populateAnalyticsUserSelect();
    loadModelStats();

    const userSelect = document.getElementById('analytics-user-select');
    if (userSelect) {
        userSelect.addEventListener('change', () => {
            const uid = parseInt(userSelect.value, 10) || 65;
            loadUserNeighbors(uid, 15);
        });
    }

    loadUserNeighbors(65, 15);
}

async function populateAnalyticsUserSelect() {
    const select = document.getElementById('analytics-user-select');
    if (!select) return;

    try {
        const res = await fetch(`${API_BASE}/users`);
        if (!res.ok) return;
        const data = await res.json();
        select.innerHTML = '';
        data.users.slice(0, 100).forEach(uid => {
            const opt = document.createElement('option');
            opt.value = uid;
            opt.textContent = `User #${uid}`;
            if (uid === 65) opt.selected = true;
            select.appendChild(opt);
        });
    } catch {}
}

async function loadModelStats() {
    try {
        const res = await fetch(`${API_BASE}/stats`);
        if (!res.ok) throw new Error();
        const stats = await res.json();

        const setVal = (id, val) => {
            const el = document.getElementById(id);
            if (el) el.textContent = val;
        };

        setVal('stat-matrix-dim', `${stats.n_users} × ${stats.n_movies}`);
        setVal('stat-mem-dense', `${stats.memory_dense_mb} MB`);
        setVal('stat-mem-sparse', `${stats.memory_sparse_mb} MB`);
        setVal('stat-total-ratings', stats.total_ratings.toLocaleString('pt-BR'));
        setVal('stat-global-mean', `★ ${stats.global_mean}`);
        setVal('stat-sparsity', `${stats.sparsity_percent}%`);

        renderRatingDistChart(stats.rating_distribution);
    } catch (err) {
        console.error('Erro ao carregar estatísticas do modelo:', err);
    }
}

function renderRatingDistChart(dist) {
    const ctx = document.getElementById('chart-ratings-distribution');
    if (!ctx || !dist) return;

    if (ratingDistChart) ratingDistChart.destroy();

    ratingDistChart = new Chart(ctx, {
        type: 'bar',
        data: {
            labels: dist.map(d => `${d.rating} ★`),
            datasets: [{
                label: 'Total de Avaliações',
                data: dist.map(d => d.count),
                backgroundColor: '#3b82f6',
                hoverBackgroundColor: '#60a5fa',
                borderRadius: 6,
            }]
        },
        options: {
            responsive: true,
            maintainAspectRatio: false,
            plugins: {
                legend: { display: false },
                tooltip: {
                    callbacks: {
                        label(c) {
                            return ` ${c.parsed.y.toLocaleString('pt-BR')} avaliações`;
                        }
                    }
                }
            },
            scales: {
                x: { grid: { display: false }, ticks: { color: '#94a3b8' } },
                y: {
                    grid: { color: 'rgba(255, 255, 255, 0.05)' },
                    ticks: { color: '#94a3b8' }
                }
            }
        }
    });
}

async function loadUserNeighbors(userId = 65, k = 15) {
    const tbody = document.getElementById('user-neighbors-tbody');
    if (!tbody) return;

    try {
        const res = await fetch(`${API_BASE}/recommend/user-user?user_id=${userId}&k=${k}&n=1`);
        if (!res.ok) throw new Error();
        const data = await res.json();

        tbody.innerHTML = data.neighbors.map((n, idx) => `
            <tr class="border-b border-[#221644] bg-[#120c2a]/70 hover:bg-[#191138] transition-colors text-sm">
                <td class="p-3.5 font-data-mono text-slate-400">#${idx + 1}</td>
                <td class="p-3.5 font-bold text-white">Usuário ${n.user_id}</td>
                <td class="p-3.5 font-data-mono text-slate-400">${n.distance.toFixed(4)}</td>
                <td class="p-3.5 text-right">
                    <span class="inline-flex items-center px-2.5 py-1 rounded-lg font-data-mono font-bold text-xs bg-[#181038] text-blue-400 border border-[#2c1d56]">
                        ${n.similarity.toFixed(4)}
                    </span>
                </td>
            </tr>
        `).join('');
    } catch (err) {
        console.error('Erro ao carregar vizinhos:', err);
    }
}

document.addEventListener('DOMContentLoaded', () => {
    checkApiHealth();
    setInterval(checkApiHealth, 20000);

    if (document.getElementById('select-user')) {
        initIndex();
    } else if (document.getElementById('movie-search-input')) {
        initDataset();
    } else if (document.getElementById('chart-ratings-distribution')) {
        initAnalytics();
    }
});

async function checkApiHealth() {
    const dot = document.getElementById('api-status-dot');
    const text = document.getElementById('api-status-text');

    try {
        const res = await fetch(`${API_BASE}/health`);
        if (res.ok) {
            if (dot) dot.className = 'w-2.5 h-2.5 rounded-full bg-emerald-400 shadow-sm shadow-emerald-400/50 animate-pulse';
            if (text) text.textContent = 'MovieLens API Online';
            return;
        }
        throw new Error();
    } catch {
        if (dot) dot.className = 'w-2.5 h-2.5 rounded-full bg-rose-500 shadow-sm shadow-rose-500/50';
        if (text) text.textContent = 'API Offline';
    }
}

window.runComparison = runComparison;
window.selectMovie = selectMovie;
window.loadSimilarMovies = loadSimilarMovies;
