// ===== JOURNEY STEP DATA =====
const stepData = {
  buyer: [
    { icon:'📄', title:'Tender Digital Twin', body:'Your document becomes a structured object: 25 requirements extracted, each with type, value, unit, and the standard it references. Every clause is individually trackable.', tags:['ui','kg'], label:'LIVE URL', href:'http://localhost:3000/tenders', linkText:'localhost:3000/tenders →' },
    { icon:'🧮', title:'Formal Contradiction Proof', body:'Clause 4.2 says YS ≥ 500 MPa. Clause 7.2 says YS ≤ 480 MPa. Z3 returns UNSAT — a mathematical proof of impossibility, not a warning. The exact conflicting clauses are highlighted.', tags:['z3'], label:'RESULT', value:'UNSAT — 2 clauses impossible', valueClass:'fail' },
    { icon:'🧹', title:'Tender Linting Report', body:'38 deterministic rules: undefined test method, missing make-in-India clause, wrong IS edition, vague tolerance, and more. Each finding has a stable ID and an auto-generated fix in standard government phrasing.', tags:['ui'], label:'READINESS GATE', value:'BLOCKED — 34 findings', valueClass:'fail' },
    { icon:'🏪', title:'Market Restriction Analysis', body:'"Carbon ≤ 0.18%" leaves only 1 of 12 licensed manufacturers. Relax to the IS limit → restores 6. This is GFR Rule 144 evidence, generated automatically per clause.', tags:['kg'], label:'MANUFACTURERS LEFT', value:'1 of 12', valueClass:'warn' },
    { icon:'🪄', title:'Tender Studio', body:'Type or speak one sentence: "6,000 LED bulbs for District Hospital". The Studio asks 4 clarifying questions, pulls the right IS + QCO + BEE ratings from the knowledge graph, renders the draft, and the compiler says READY.', tags:['kg','ui'], label:'STUDIO', href:'http://localhost:3000/studio', linkText:'localhost:3000/studio →' },
  ],
  bidder: [
    { icon:'🔍', title:'Multilingual Standards Search', body:'"स्प्लिट एयर कंडीशनर" → IS 1391 (Part 2). Kannada "ಸೀಲಿಂಗ್ ಫ್ಯಾನ್" → IS 374. No LLM translation. An offline phonetic transliteration engine handles 7 Indian languages.', tags:['ocr','kg'], label:'SEARCH', href:'http://localhost:3000/recommend', linkText:'localhost:3000/recommend →' },
    { icon:'📝', title:'Smart Bid Form — Auto-Fill', body:'The bid form is generated from the canonical tender. Drop a scanned NABL test report — PP-OCRv6 reads it at 97% accuracy and fills the values automatically. No manual re-entry.', tags:['ocr','ui'], label:'OCR ACCURACY', value:'97% on NABL scans', valueClass:'pass' },
    { icon:'📊', title:'Live Match Index', body:'Every clause in the tender is matched against your evidence. Green = covered. Red = knock-out. The index tells you not just what is missing, but exactly what document to add and which clause to quote.', tags:['ui','kg'], label:'SAMPLE SCORE', value:'Match: 92% — 1 knock-out', valueClass:'warn' },
    { icon:'🛂', title:'W3C Compliance Passport', body:'A Verifiable Credential signed with Ed25519. Change one value — the signature fails. Verifiable offline by scanning the QR code. Aligns with the EU Digital Product Passport vision.', tags:['vc'], label:'PASSPORT', href:'http://localhost:3000/passport/2cb3a24af919', linkText:'View demo passport →' },
  ],
  ai: [
    { icon:'🤖', title:'MCP Server Integration', body:'Three tools: lint_tender, check_contradictions, resolve_standard. Any MCP-capable AI (Claude Desktop, IDE agents, GeM copilots) can call them. The AI converses — SpecSure proves.', tags:['ui','z3'], label:'MCP ENDPOINT', value:'stdio or HTTP/SSE', valueClass:'pass' },
    { icon:'📡', title:'REST API — 60+ Endpoints', body:'Full Swagger docs at /docs. Every pipeline step is individually callable. Use from Python, Node, curl, or any HTTP client. Response includes document-level provenance on every result.', tags:['ui'], label:'API DOCS', href:'http://localhost:8000/docs', linkText:'localhost:8000/docs →' },
    { icon:'🔌', title:'Browser Extension (Manifest V3)', body:'Install once. Every GeM bid listing gets annotated: standard name, edition, amendments, certification status. Select text on any .gov.in page → "Find Indian Standards" in the context menu.', tags:['ui','kg'], label:'PLATFORMS', value:'GeM · CPPP · any .gov.in', valueClass:'pass' },
  ],
  lifecycle: [
    { icon:'🪄', title:'Intent → Verified Tender', body:'One sentence → Tender Studio → knowledge graph lookup → clause draft → compiler self-check → READY. The whole loop runs in under 30 seconds.', tags:['kg','ui','z3'], label:'STUDIO', href:'http://localhost:3000/studio', linkText:'localhost:3000/studio →' },
    { icon:'📋', title:'Publish → Contractors Bid', body:'Published tender appears on the contractor marketplace. Smart bid form auto-fills from uploaded documents. Real-time Match Index shows compliance before submission.', tags:['ui','ocr'], label:'MARKETPLACE', href:'http://localhost:3000/contractor', linkText:'localhost:3000/contractor →' },
    { icon:'⚖️', title:'Evaluation → Award', body:'Financial bids are re-hashed against ledger commitments. L1 determined → Make in India 20% preference applied → MSE 15% margin + 25% share → Award letter generated as PDF.', tags:['ui'], label:'OFFICER DASHBOARD', href:'http://localhost:3000/officer', linkText:'localhost:3000/officer →' },
    { icon:'📡', title:'Regulatory Radar', body:'When any BIS standard, amendment, or QCO changes, every published tender referencing it is re-validated automatically via reverse traversal of the normative reference graph.', tags:['kg','z3'], label:'RADAR', href:'http://localhost:3000/radar', linkText:'localhost:3000/radar →' },
    { icon:'🔗', title:'Tamper-Evident Audit Ledger', body:'Every compile, review, bid, and award is hash-chained with SHA-256. Document hash + KB snapshot hash + engine version. One click verifies the entire chain, front to back, reproducibly.', tags:['vc','ui'], label:'LEDGER', href:'http://localhost:3000/ledger', linkText:'localhost:3000/ledger →' },
  ]
};

// ===== TAG LABELS =====
const tagLabel = { z3:'Z3 Solver', kg:'Knowledge Graph', vc:'W3C VC', ui:'Live UI', ocr:'OCR / NLP' };

function renderPreview(role, idx) {
  const d = stepData[role][idx];
  const preEl = document.getElementById('preview-' + role);
  if (!preEl || !d) return;
  const tags = (d.tags || []).map(t => `<span class="jp-tag ${t}">${tagLabel[t] || t}</span>`).join('');
  let resultHtml = '';
  if (d.href) {
    resultHtml = `<a href="${d.href}" target="_blank">${d.linkText}</a>`;
  } else {
    const cls = d.valueClass || '';
    resultHtml = `<span class="${cls}">${d.value}</span>`;
  }
  preEl.innerHTML = `
    <div class="jp-icon">${d.icon}</div>
    <div class="jp-title">${d.title}</div>
    <div class="jp-body">${d.body}</div>
    <div class="jp-tags">${tags}</div>
    <div class="jp-result"><div class="jpr-label">${d.label}</div><div class="jpr-value">${resultHtml}</div></div>
  `;
}

// ===== TAB SWITCHING =====
function showJourney(btn, role) {
  document.querySelectorAll('.journey-panel').forEach(p => p.classList.remove('active'));
  document.querySelectorAll('.jnav-btn').forEach(b => b.classList.remove('active'));
  document.getElementById('j-' + role).classList.add('active');
  btn.classList.add('active');
  // reset first step
  const panel = document.getElementById('j-' + role);
  panel.querySelectorAll('.jstep').forEach((s, i) => s.classList.toggle('active', i === 0));
  renderPreview(role, 0);
}

function setStep(el, role, idx) {
  el.closest('.journey-panel').querySelectorAll('.jstep').forEach(s => s.classList.remove('active'));
  el.classList.add('active');
  renderPreview(role, idx);
}

function activateRole(role) {
  const btn = document.querySelector(`.jnav-btn[onclick*="'${role}'"]`);
  if (btn) { showJourney(btn, role); }
  setTimeout(() => document.getElementById('journeys').scrollIntoView({ behavior:'smooth', block:'start' }), 50);
}

// ===== INIT PREVIEWS =====
renderPreview('buyer', 0);
renderPreview('bidder', 0);
renderPreview('ai', 0);
renderPreview('lifecycle', 0);

// ===== SCROLL ANIMATIONS =====
const io = new IntersectionObserver(entries => {
  entries.forEach(e => { if (e.isIntersecting) { e.target.classList.add('visible'); io.unobserve(e.target); } });
}, { threshold: 0.08 });
document.querySelectorAll('.flow-step,.flow-card,.stat-box,.proof-card,.tech-item,.problem-list li,.role-card,.solution-box,.jstep').forEach(el => {
  el.classList.add('anim'); io.observe(el);
});

// ===== HERO ANIM =====
document.querySelectorAll('.hero .anim').forEach(el => {
  setTimeout(() => el.classList.add('visible'), 200);
});

// ===== NAV HIGHLIGHT =====
const secEls = document.querySelectorAll('section[id]');
const navAs = document.querySelectorAll('.nav-links a');
const navEl = document.querySelector('.nav');
window.addEventListener('scroll', () => {
  let cur = '';
  secEls.forEach(s => { if (window.scrollY >= s.offsetTop - 80) cur = s.id; });
  navAs.forEach(a => a.classList.toggle('active', a.getAttribute('href') === '#' + cur));
  navEl.style.background = window.scrollY > 80 ? 'rgba(11,29,58,0.97)' : 'rgba(11,29,58,0.9)';
}, { passive: true });

// ===== SMOOTH SCROLL =====
document.querySelectorAll('a[href^="#"]').forEach(a => {
  a.addEventListener('click', e => {
    const t = document.querySelector(a.getAttribute('href'));
    if (t) { e.preventDefault(); t.scrollIntoView({ behavior:'smooth', block:'start' }); }
  });
});

// ===== STEP COLOUR CLASSES =====
// These need to be in CSS but also injected for dynamic content
const styleEl = document.createElement('style');
styleEl.textContent = `
  .fail { color: #F87171; }
  .pass { color: #34D399; }
  .warn { color: #FBBF24; }
  .jpr-value a { color: #fff; text-decoration: none; }
  .jpr-value a:hover { color: var(--amber-lt, #FBBF24); }
`;
document.head.appendChild(styleEl);
