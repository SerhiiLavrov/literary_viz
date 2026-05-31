const fileInput = document.getElementById('fileInput');
const uploadArea = document.getElementById('uploadArea');
const results = document.getElementById('results');
const tabContent = document.getElementById('tabContent');

let currentData = null;
let currentTab = 'emotion';

uploadArea.addEventListener('dragover', (e) => {
    e.preventDefault();
    uploadArea.style.borderColor = '#a78bfa';
});

uploadArea.addEventListener('dragleave', () => {
    uploadArea.style.borderColor = '#333';
});

uploadArea.addEventListener('drop', (e) => {
    e.preventDefault();
    uploadArea.style.borderColor = '#333';
    const file = e.dataTransfer.files[0];
    if (file && file.name.endsWith('.pdf')) uploadFile(file);
});

fileInput.addEventListener('change', () => {
    if (fileInput.files[0]) uploadFile(fileInput.files[0]);
});

function showLoading(msg) {
    results.style.display = 'block';
    tabContent.innerHTML = `
        <div class="loading">
            <div class="spinner"></div>
            <p>${msg}</p>
        </div>`;
}

function uploadFile(file) {
    const formData = new FormData();
    formData.append('file', file);
    showLoading('Uploading file...');

    fetch('/upload', { method: 'POST', body: formData })
        .then(r => r.json())
        .then(data => {
            if (data.success) {
                showLoading('Analyzing text... this may take a few minutes');
                return fetch('/analyze', {
                    method: 'POST',
                    headers: { 'Content-Type': 'application/json' },
                    body: JSON.stringify({ filename: data.filename })
                });
            } else {
                throw new Error(data.error);
            }
        })
        .then(r => r.json())
        .then(data => {
            if (data.error) throw new Error(data.error);
            currentData = data;
            showMetadata(data);
            showTab(currentTab);
        })
        .catch(err => {
            tabContent.innerHTML = `<div class="loading"><p>Error: ${err.message}</p></div>`;
        });
}

function showMetadata(data) {
    const existing = document.getElementById('metadataCard');
    if (existing) existing.remove();

    const card = document.createElement('div');
    card.id = 'metadataCard';
    card.style.cssText = `
        background: #16162a;
        border: 1px solid #2a2a45;
        border-radius: 16px;
        padding: 24px 28px;
        margin-bottom: 32px;
        display: grid;
        grid-template-columns: 1fr 1fr;
        gap: 20px;
    `;

    card.innerHTML = `
        <div>
            <div style="color:#666; font-size:12px; margin-bottom:4px; text-transform:uppercase; letter-spacing:1px;">Title</div>
            <div style="display:flex; align-items:center; gap:8px;">
                <span id="metaTitle" style="color:#e0e0e0; font-size:1.2rem; font-weight:500;">${data.title}</span>
                <button onclick="editMeta('title')" style="background:none; border:none; color:#555; cursor:pointer; font-size:12px;">Edit</button>
            </div>
        </div>
        <div>
            <div style="color:#666; font-size:12px; margin-bottom:4px; text-transform:uppercase; letter-spacing:1px;">Author</div>
            <div style="display:flex; align-items:center; gap:8px;">
                <span id="metaAuthor" style="color:#e0e0e0; font-size:1rem;">${data.author}</span>
                <button onclick="editMeta('author')" style="background:none; border:none; color:#555; cursor:pointer; font-size:12px;">Edit</button>
            </div>
        </div>
        <div>
            <div style="color:#666; font-size:12px; margin-bottom:4px; text-transform:uppercase; letter-spacing:1px;">Genre</div>
            <div style="display:flex; align-items:center; gap:8px;">
                <span id="metaGenre" style="color:#a78bfa; font-size:0.95rem;">${data.genre}</span>
                <button onclick="editMeta('genre')" style="background:none; border:none; color:#555; cursor:pointer; font-size:12px;">Edit</button>
            </div>
        </div>
        <div>
            <div style="color:#666; font-size:12px; margin-bottom:4px; text-transform:uppercase; letter-spacing:1px;">Sentences</div>
            <span style="color:#e0e0e0; font-size:0.95rem;">${data.sentence_count || data.sentences.length}</span>
        </div>
        <div style="grid-column: 1 / -1;">
            <div style="color:#666; font-size:12px; margin-bottom:8px; text-transform:uppercase; letter-spacing:1px;">Summary</div>
            <p id="metaSummary" style="color:#aaa; font-size:0.9rem; line-height:1.6;">${data.summary}</p>
        </div>
    `;

    const resultsDiv = document.getElementById('results');
    resultsDiv.style.display = 'block';
    resultsDiv.insertBefore(card, resultsDiv.firstChild);
}

function editMeta(field) {
    const el = document.getElementById('meta' + field.charAt(0).toUpperCase() + field.slice(1));
    const current = el.textContent;
    const input = document.createElement('input');
    input.value = current;
    input.style.cssText = `
        background: #0f0f1a;
        border: 1px solid #a78bfa;
        border-radius: 6px;
        color: #e0e0e0;
        padding: 4px 8px;
        font-size: inherit;
        width: 200px;
    `;
    input.onblur = () => {
        el.textContent = input.value;
        currentData[field] = input.value;
        input.replaceWith(el);
    };
    input.onkeydown = (e) => {
        if (e.key === 'Enter') input.blur();
    };
    el.replaceWith(input);
    input.focus();
}

document.querySelectorAll('.tab').forEach(tab => {
    tab.addEventListener('click', () => {
        document.querySelectorAll('.tab').forEach(t => t.classList.remove('active'));
        tab.classList.add('active');
        currentTab = tab.dataset.tab;
        if (currentData) showTab(currentTab);
    });
});

function showTab(tab) {
    switch (tab) {
        case 'emotion': showEmotion(); break;
        case 'tension': showTension(); break;
        case 'characters': showCharacters(); break;
        case 'rhythm': showRhythm(); break;
        case 'punctuation': showPunctuation(); break;
        case 'map': showMap(); break;
    }
}

function showEmotion() {
    const labels = currentData.parts.map(p => `Part ${p.part}`);
    const values = currentData.valence;

    tabContent.innerHTML = `
        <h3 style="margin-bottom:16px; color:#ccc;">Emotional Valence</h3>
        <p style="color:#666; font-size:13px; margin-bottom:20px;">
            Hover over a point to see dominant emotion
        </p>
        <div style="position:relative; width:100%; height:300px;">
            <canvas id="emotionChart"></canvas>
        </div>
        <div id="emotionTooltip" style="margin-top:16px; padding:12px 16px; 
            background:#1e1e35; border-radius:8px; border:1px solid #333;
            font-size:13px; color:#aaa; min-height:50px;">
            Hover over a point to see the fragment
        </div>`;

    setTimeout(() => {
        const ctx = document.getElementById('emotionChart').getContext('2d');
        new Chart(ctx, {
            type: 'line',
            data: {
                labels,
                datasets: [{
                    data: values,
                    borderColor: '#a78bfa',
                    backgroundColor: 'rgba(167,139,250,0.1)',
                    pointBackgroundColor: values.map(v => v > 0 ? '#4ade80' : '#f87171'),
                    pointRadius: 6,
                    pointHoverRadius: 9,
                    tension: 0.4,
                    fill: true,
                    borderWidth: 2
                }]
            },
            options: {
                responsive: true,
                maintainAspectRatio: false,
                plugins: {
                    legend: { display: false },
                    tooltip: { enabled: false }
                },
                scales: {
                    y: {
                        grid: { color: 'rgba(255,255,255,0.05)' },
                        ticks: { color: '#666' }
                    },
                    x: {
                        grid: { display: false },
                        ticks: { color: '#666', maxRotation: 45, minRotation: 45 }
                    },
                },
                onHover: (e, elements) => {
                    if (elements.length > 0) {
                        const i = elements[0].index;
                        const val = values[i].toFixed(2);
                        const color = values[i] > 0 ? '#4ade80' : '#f87171';
                        const emotion = currentData.parts[i].dominant_emotion;
                        const dist = currentData.parts[i].emotion_dist;

                        const neutral = (dist.neutral * 100).toFixed(0);
                        const topEmotions = Object.entries(dist)
                            .filter(([k]) => k !== 'neutral')
                            .sort((a, b) => b[1] - a[1])
                            .slice(0, 3)
                            .map(([k, v]) => `${k}: ${(v * 100).toFixed(0)}%`)
                            .join(' | ');

                        document.getElementById('emotionTooltip').innerHTML = `
                            <span style="color:#ccc; font-weight:500">Part ${i + 1}</span>
                            &nbsp; valence: <span style="color:${color}">${val}</span>
                            &nbsp; dominant: <span style="color:#a78bfa">${emotion}</span><br>
                            <span style="color:#888; margin-top:4px; display:block">${topEmotions}</span>
                            <span style="color:#555; font-size:12px;">neutral background: ${neutral}%</span>`;
                    }
                }
            }
        });
    }, 100);
}

function showTension() {
    const labels = currentData.parts.map(p => `Part ${p.part}`);
    const values = currentData.tension;
    const maxIdx = values.indexOf(Math.max(...values));
    const peakPart = currentData.parts[maxIdx];

    tabContent.innerHTML = `
        <h3 style="margin-bottom:16px; color:#ccc;">Narrative Tension</h3>
        <div style="position:relative; width:100%; height:300px;">
            <canvas id="tensionChart"></canvas>
        </div>
        <div id="tensionTooltip" style="margin-top:12px; padding:12px 16px;
            background:#1e1e35; border-radius:8px; border:1px solid #333;
            font-size:13px; color:#aaa; min-height:50px;">
            Hover over a point to see tension components
        </div>
        <div style="margin-top:16px; padding:16px;
            background:#1a1a2e; border-radius:12px; border:1px solid #2a2a45;">
            <div style="color:#f87171; font-size:13px; font-weight:500; margin-bottom:8px;">
                Peak — Part ${peakPart.part} (sentences ${peakPart.sent_range})
            </div>
            <div style="color:#888; font-size:13px; line-height:1.6;">
                "${peakPart.sentences.join(' ')}"
            </div>
        </div>`;

    setTimeout(() => {
        const ctx = document.getElementById('tensionChart').getContext('2d');
        new Chart(ctx, {
            type: 'line',
            data: {
                labels,
                datasets: [{
                    data: values,
                    borderColor: '#f87171',
                    backgroundColor: 'rgba(248,113,113,0.1)',
                    pointBackgroundColor: values.map((v, i) => i === maxIdx ? '#f87171' : 'rgba(248,113,113,0.5)'),
                    pointRadius: values.map((v, i) => i === maxIdx ? 9 : 5),
                    tension: 0.4,
                    fill: true,
                    borderWidth: 2
                }]
            },
            options: {
                responsive: true,
                maintainAspectRatio: false,
                plugins: { legend: { display: false }, tooltip: { enabled: false } },
                scales: {
                    y: {
                        min: 0, max: 10,
                        grid: { color: 'rgba(255,255,255,0.05)' },
                        ticks: { color: '#666' }
                    },
                    x: {
                        grid: { display: false },
                        ticks: { color: '#666', maxRotation: 45, minRotation: 45 }
                    },
                },
                onHover: (e, elements) => {
                    if (elements.length > 0) {
                        const i = elements[0].index;
                        const part = currentData.parts[i];
                        const tension = values[i].toFixed(1);
                        const shiftPct = part.turn * 100;
                        const shiftLabel = shiftPct < 20 ? '↔ stable' : shiftPct < 40 ? '↑ mood shift' : '⚡ sharp turn';
                        const shiftColor = shiftPct < 20 ? '#888' : shiftPct < 40 ? '#fbbf24' : '#f87171';
                        document.getElementById('tensionTooltip').innerHTML = `
                            <span style="color:#ccc; font-weight:500">Part ${i + 1}</span>
                            &nbsp; tension: <span style="color:#f87171">${tension}/10</span><br>
                            <span style="color:#888">dominant: ${part.dominant_emotion}
                            &nbsp;|&nbsp; <span style="color:${shiftColor}">${shiftLabel}</span>
                            &nbsp;|&nbsp; conflict: ${(part.spike * 100).toFixed(0)}%</span>`;
                    }
                }
            }
        });
    }, 100);
}

function showCharacters() {
    const chars = currentData.characters;
    const focus = currentData.character_focus;
    const parts = currentData.parts.map(p => `Part ${p.part}`);

    // Приоритет: сначала люди, потом животные, роли только если мало людей
    const people = chars.people || [];
    const animals = chars.animals || [];
    const roles = chars.roles || [];
    const allChars = people.length >= 6 
        ? [...people, ...animals]
        : [...people, ...animals, ...roles];

    if (allChars.length === 0) {
        tabContent.innerHTML = '<div class="loading"><p>No characters found</p></div>';
        return;
    }

    // Сортируем по суммарным упоминаниям — топ-6 самых важных
    const ranked = allChars
        .filter(name => focus[name])
        .map(name => ({
            name,
            total: focus[name].reduce((a, b) => a + b, 0)
        }))
        .sort((a, b) => b.total - a.total)
        .slice(0, 6)
        .map(x => x.name);

    const colors = ['#a78bfa', '#60a5fa', '#4ade80', '#f87171', '#fbbf24', '#34d399'];

    tabContent.innerHTML = `
        <h3 style="margin-bottom:16px; color:#ccc;">Character Focus</h3>
        <div style="position:relative; width:100%; height:300px;">
            <canvas id="charChart"></canvas>
        </div>`;

    setTimeout(() => {
        const ctx = document.getElementById('charChart').getContext('2d');
        new Chart(ctx, {
            type: 'line',
            data: {
                labels: parts,
                datasets: ranked.map((name, i) => ({
                    label: name,
                    data: focus[name] || [],
                    borderColor: colors[i % colors.length],
                    backgroundColor: 'transparent',
                    pointRadius: 4,
                    tension: 0.4,
                    borderWidth: 2
                }))
            },
            options: {
                responsive: true,
                maintainAspectRatio: false,
                plugins: {
                    legend: {
                        display: true,
                        labels: { color: '#888', boxWidth: 12 }
                    }
                },
                scales: {
                    y: {
                        grid: { color: 'rgba(255,255,255,0.05)' },
                        ticks: { color: '#666', maxRotation: 45, minRotation: 45 }
                    },
                    x: {
                        grid: { display: false },
                        ticks: { color: '#666', maxRotation: 45, minRotation: 45 }
                    }
                }
            }
        });
    }, 100);
}

function showRhythm() {
    const lengths = currentData.structure.sentence_lengths;
    const canvas = document.createElement('canvas');
    canvas.width = 800;
    canvas.height = 500;
    canvas.style.width = '100%';
    canvas.style.display = 'block';

    tabContent.innerHTML = `
        <h3 style="margin-bottom:16px; color:#ccc;">Sentence Rhythm</h3>
        <p style="color:#666; font-size:13px; margin-bottom:20px;">
            Each line is a sentence. Length = number of words. Turns 90° at the end.
        </p>`;
    tabContent.appendChild(canvas);

    const ctx = canvas.getContext('2d');
    const w = canvas.width;
    const h = canvas.height;
    ctx.fillStyle = '#0f0f1a';
    ctx.fillRect(0, 0, w, h);

    const sample = lengths;
    const dirs = [[1, 0], [0, 1], [-1, 0], [0, -1]];

    function simulate(scale) {
        let x = 0, y = 0, dir = 0;
        let minX = 0, maxX = 0, minY = 0, maxY = 0;
        sample.forEach(len => {
            x += dirs[dir][0] * len * scale;
            y += dirs[dir][1] * len * scale;
            minX = Math.min(minX, x); maxX = Math.max(maxX, x);
            minY = Math.min(minY, y); maxY = Math.max(maxY, y);
            dir = (dir + 1) % 4;
        });
        return { minX, maxX, minY, maxY };
    }

    let scale = 6;
    for (let i = 0; i < 20; i++) {
        const { minX, maxX, minY, maxY } = simulate(scale);
        const fw = maxX - minX, fh = maxY - minY;
        const ratioW = (w * 0.85) / fw, ratioH = (h * 0.85) / fh;
        const ratio = Math.min(ratioW, ratioH);
        scale *= ratio;
        if (Math.abs(ratio - 1) < 0.01) break;
    }

    const { minX, maxX, minY, maxY } = simulate(scale);
    const offsetX = w / 2 - (minX + maxX) / 2;
    const offsetY = h / 2 - (minY + maxY) / 2;
    const maxLen = Math.max(...sample);

    let x = offsetX, y = offsetY, dir = 0;
    sample.forEach((len, i) => {
        const pct = Math.min(len / maxLen, 1);
        const r = Math.round(100 + pct * 155);
        const b = Math.round(250 - pct * 100);
        ctx.strokeStyle = `rgba(${r}, 100, ${b}, 0.85)`;
        ctx.lineWidth = 1.5;
        ctx.beginPath();
        ctx.moveTo(x, y);
        x += dirs[dir][0] * len * scale;
        y += dirs[dir][1] * len * scale;
        ctx.lineTo(x, y);
        ctx.stroke();
        dir = (dir + 1) % 4;
    });
    // Начальная точка — зелёная
    ctx.beginPath();
    ctx.arc(offsetX, offsetY, 5, 0, Math.PI * 2);
    ctx.fillStyle = '#4ade80';
    ctx.fill();

    // Конечная точка — красная
    ctx.beginPath();
    ctx.arc(x, y, 5, 0, Math.PI * 2);
    ctx.fillStyle = '#f87171';
    ctx.fill();
}

function showPunctuation() {
    const punct = currentData.structure.punctuation;
    const colorMap = {
        '.': '#ffffff',
        ',': '#60a5fa',
        '!': '#ef4444',
        '?': '#fbbf24',
        ';': '#60a5fa',
        ':': '#c084fc',
        '"': '#4ade80',
        '\u201c': '#4ade80',
        '\u201d': '#4ade80',
        '—': '#fb923c',
        '(': '#888',
        ')': '#888'
    };

    const html = punct.split('').map(ch => {
        const color = colorMap[ch] || '#444';
        return `<span style="color:${color}; font-size:18px; margin:2px;">${ch}</span>`;
    }).join('');

    tabContent.innerHTML = `
        <h3 style="margin-bottom:16px; color:#ccc;">Punctuation Pattern</h3>
        <p style="color:#666; font-size:13px; margin-bottom:16px;">
            Text without words — only punctuation marks
        </p>
        <div style="background:#0a0a14; border-radius:12px; padding:20px; 
            font-family:monospace; line-height:2.5; word-break:break-all; 
            border:1px solid #222;">
            ${html}
        </div>`;
}

function showMap() {
    const locations = currentData.locations;

    if (!locations || locations.length === 0) {
        tabContent.innerHTML = '<div class="loading"><p>No locations found in this text</p></div>';
        return;
    }

    const locationList = locations.slice(0, 20).map(loc =>
        `<div style="padding:8px 12px; background:#1e1e35; border-radius:6px; 
            border:1px solid #333; font-size:14px; color:#ccc;">${loc}</div>`
    ).join('');

    tabContent.innerHTML = `
        <h3 style="margin-bottom:16px; color:#ccc;">Locations</h3>
        <p style="color:#666; font-size:13px; margin-bottom:16px;">
            Places mentioned in the text
        </p>
        <div style="display:flex; flex-wrap:wrap; gap:8px;">
            ${locationList}
        </div>`;
}
function showLibrary() {
    document.getElementById('libraryModal').style.display = 'block';
    loadLibrary();
}

function closeLibrary() {
    document.getElementById('libraryModal').style.display = 'none';
}

function loadLibrary(query = '') {
    const url = query ? `/library?q=${encodeURIComponent(query)}` : '/library';
    fetch(url)
        .then(r => r.json())
        .then(books => renderLibrary(books));
}

function searchLibrary() {
    const query = document.getElementById('librarySearch').value;
    loadLibrary(query);
}

function renderLibrary(books) {
    const list = document.getElementById('libraryList');
    if (books.length === 0) {
        list.innerHTML = '<p style="color:#666; text-align:center;">No books found</p>';
        return;
    }
    list.innerHTML = books.map(book => {
        const isSelected = compareId1 === book.id;
        const safeTitle = book.title.replace(/'/g, "\\'");
        return `
        <div style="padding:16px; background:${isSelected ? '#1a1a3a' : '#0f0f1a'}; border-radius:10px;
            border:1px solid ${isSelected ? '#a78bfa' : '#222'}; margin-bottom:12px;
            display:flex; justify-content:space-between; align-items:center;">
            <div style="cursor:pointer; flex:1;" onclick="loadFromLibrary(${book.id})">
                <div style="color:#e0e0e0; font-weight:500; margin-bottom:4px;">${book.title}</div>
                <div style="color:#666; font-size:13px;">${book.author} · ${book.genre} · ${book.sentence_count} sentences</div>
                <div style="color:#555; font-size:12px; margin-top:4px;">${book.summary ? book.summary.slice(0, 100) + '...' : ''}</div>
            </div>
            <div style="display:flex; flex-direction:column; align-items:flex-end; gap:8px; margin-left:16px;">
                <div style="color:#a78bfa; font-size:12px;">${new Date(book.analyzed_at).toLocaleDateString()}</div>
                <button onclick="selectForCompare(${book.id}, '${safeTitle}')" style="background:${isSelected ? '#a78bfa' : '#1e1e35'}; border:1px solid ${isSelected ? '#a78bfa' : '#2a2a45'}; color:${isSelected ? '#000' : '#60a5fa'}; padding:4px 10px; border-radius:6px; cursor:pointer; font-size:12px;">${isSelected ? '✓ Selected' : 'Compare'}</button>
            </div>
        </div>`
    }).join('');
}

let compareId1 = null;
let compareTitle1 = null;

function selectForCompare(id, title) {
    if (!compareId1) {
        compareId1 = id;
        compareTitle1 = title;
        document.getElementById('librarySearch').placeholder = `Comparing "${title}" with... pick second book`;
        loadLibrary();
    } else if (compareId1 === id) {
        compareId1 = null;
        compareTitle1 = null;
        document.getElementById('librarySearch').placeholder = 'Search by title or author...';
        loadLibrary();
    } else {
        window.location.href = `/compare?id1=${compareId1}&id2=${id}`;
    }
}


function loadFromLibrary(bookId) {
    closeLibrary();
    showLoading('Loading from library...');
    fetch(`/library/${bookId}`)
        .then(r => r.json())
        .then(data => {
            if (data.error) throw new Error(data.error);
            currentData = data;
            showMetadata(data);
            showTab(currentTab);
        })
        .catch(err => {
            tabContent.innerHTML = `<div class="loading"><p>Error: ${err.message}</p></div>`;
        });
}