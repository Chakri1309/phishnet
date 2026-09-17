// PhishNet frontend · Neura hero-12 motion port + scanner logic
let featChart, modelChart, impChart, currentMetric = 'accuracy';
let lastBulk = [], lastResult = null;
const HIST_KEY = 'phishnet_history';
const REDUCED = matchMedia('(prefers-reduced-motion: reduce)').matches;
Chart.defaults.font.family = 'Inter, sans-serif';
Chart.defaults.color = 'rgba(255,255,255,.6)';

/* ---------- toasts ---------- */
function toast(msg, kind){
  const box = document.getElementById('toasts');
  const t = document.createElement('div');
  t.className = 'toast' + (kind ? ' ' + kind : '');
  t.textContent = msg;
  box.appendChild(t);
  setTimeout(() => { t.style.opacity = '0'; t.style.transition = 'opacity .4s'; }, 3400);
  setTimeout(() => t.remove(), 3900);
}

/* ---------- seeded rand ---------- */
function mulberry(seed){
  let a = seed >>> 0;
  return function(){
    a |= 0; a = (a + 0x6D2B79F5) | 0;
    let t = Math.imul(a ^ (a >>> 15), 1 | a);
    t = (t + Math.imul(t ^ (t >>> 7), 61 | t)) ^ t;
    return ((t ^ (t >>> 14)) >>> 0) / 4294967296;
  };
}

/* ---------- starburst (Neura StarBurst port: 140 twinkling stars fanning from top-center) ---------- */
(function starburst(){
  const cv = document.getElementById('starburst');
  if(!cv || REDUCED) return;
  const ctx = cv.getContext('2d');
  let W, H, stars = [], visible = true, seed = 7;
  function size(){
    const r = cv.parentElement.getBoundingClientRect();
    const dpr = Math.min(2, devicePixelRatio || 1);
    W = cv.width = r.width * dpr; H = cv.height = r.height * dpr;
    const rnd = mulberry(seed);
    const maxR = H * .8;
    stars = Array.from({length: 140}, () => {
      const a = Math.PI * rnd();                    // downward fan
      const d = Math.pow(rnd(), 1.4) * maxR + H * .02;
      return { x: W * .5 + Math.cos(a) * d, y: Math.sin(a) * d * .9,
        r: (.6 + rnd() * 1.5) * dpr, ph: rnd() * 6.28,
        sp: 1.5 + rnd() * 2.5, a0: .35 + rnd() * .5 };
    });
  }
  size(); addEventListener('resize', size);
  new IntersectionObserver(es => visible = es[0].isIntersecting).observe(cv);
  (function frame(t){
    requestAnimationFrame(frame);
    if(!visible || document.hidden) return;
    ctx.clearRect(0, 0, W, H);
    for(const s of stars){
      const tw = .5 + .5 * Math.sin(t * .001 * s.sp + s.ph);
      ctx.fillStyle = `rgba(232,212,255,${(s.a0 * tw * .8).toFixed(3)})`;
      ctx.beginPath(); ctx.arc(s.x, s.y, s.r, 0, 7); ctx.fill();
    }
  })(0);
})();

/* ---------- stardust (gentle rising particles along the bottom glow) ---------- */
(function stardust(){
  const cv = document.getElementById('stardust');
  if(!cv || REDUCED) return;
  const ctx = cv.getContext('2d');
  let W, H, ps = [], visible = true;
  function size(){
    const r = cv.parentElement.getBoundingClientRect();
    const dpr = Math.min(2, devicePixelRatio || 1);
    W = cv.width = r.width * dpr; H = cv.height = Math.max(2, r.height * dpr);
    const rnd = mulberry(21);
    ps = Array.from({length: Math.floor(r.width / 14)}, () => ({
      x: rnd() * W, y: rnd() * H, r: (.5 + rnd()) * dpr,
      vy: -(.12 + rnd() * .3) * dpr, ph: rnd() * 6.28, a: .25 + rnd() * .45 }));
  }
  size(); addEventListener('resize', size);
  new IntersectionObserver(es => visible = es[0].isIntersecting).observe(cv);
  (function frame(t){
    requestAnimationFrame(frame);
    if(!visible || document.hidden) return;
    ctx.clearRect(0, 0, W, H);
    ctx.fillStyle = '#fff';
    for(const p of ps){
      p.y += p.vy;
      if(p.y < -4){ p.y = H + 4; }
      ctx.globalAlpha = p.a * (.6 + .4 * Math.sin(t * .002 + p.ph));
      ctx.beginPath(); ctx.arc(p.x, p.y, p.r, 0, 7); ctx.fill();
    }
    ctx.globalAlpha = 1;
  })(0);
})();

/* ---------- electric bolt (Neura ElectricLine, simplified: 3 flickering strands) ---------- */
(function bolt(){
  const cv = document.getElementById('bolt');
  if(!cv) return;
  const ctx = cv.getContext('2d');
  // gentle 13-point spine, [along 0..1, across -1..1]
  const SPINE = [[0,-.06],[.06,.05],[.1,-.12],[.15,.1],[.2,-.2],[.35,.18],[.52,-.22],[.6,.2],[.7,-.14],[.8,.12],[.87,-.1],[.94,.04],[1,0]];
  function size(){
    const r = cv.getBoundingClientRect();
    const dpr = Math.min(2, devicePixelRatio || 1);
    cv.width = Math.max(2, r.width * dpr); cv.height = Math.max(2, r.height * dpr);
  }
  size(); addEventListener('resize', size);
  function stroke(pts, w, style, blur){
    ctx.strokeStyle = style; ctx.lineWidth = Math.max(.6, w);
    ctx.shadowColor = style; ctx.shadowBlur = blur;
    ctx.beginPath();
    pts.forEach(([x, y], i) => i ? ctx.lineTo(x, y) : ctx.moveTo(x, y));
    ctx.stroke(); ctx.shadowBlur = 0;
  }
  let seed = 4981;
  function draw(){
    const W = cv.width, H = cv.height;
    if(!W || !H) return;
    ctx.clearRect(0, 0, W, H);
    ctx.globalCompositeOperation = 'lighter';
    ctx.globalAlpha = .72 + Math.random() * .28;   // lightning flicker
    for(let s = 0; s < 3; s++){
      const rnd = mulberry(seed + s * 101);
      const spread = (s - 1) * W * .05;
      const pts = SPINE.map(([a, c]) => [
        W * .5 + spread + c * W * .3 + (rnd() - .5) * W * .16, a * H ]);
      stroke(pts, W * .085, 'rgba(211,98,255,.30)', 22);  // diffuse beam
      stroke(pts, W * .04, 'rgba(226,112,255,.5)', 9);
      stroke(pts, Math.max(1, W * .009), 'rgba(255,255,255,.9)', 0); // white core
    }
    ctx.globalAlpha = 1;
    ctx.globalCompositeOperation = 'source-over';
  }
  draw();
  if(!REDUCED) setInterval(() => { seed = (seed * 9301 + 49297) % 233280; if(!document.hidden) draw(); }, 150);
})();

/* ---------- rolling headline (Neura RollingLetters port) ---------- */
function buildRoll(el){
  const nodes = [...el.childNodes];
  el.innerHTML = '';
  let n = 0;
  nodes.forEach(node => {
    if(node.nodeType === 3){
      [...node.textContent].forEach(ch => {
        if(ch === '\n') return;
        const m = document.createElement('span'); m.className = 'rl-mask';
        const c = document.createElement('span'); c.className = 'rl-ch';
        c.textContent = (ch === ' ') ? ' ' : ch;
        c.style.transitionDelay = (n++ * 22) + 'ms';
        m.appendChild(c); el.appendChild(m);
      });
    } else if(node.nodeName === 'BR'){ el.appendChild(document.createElement('br')); }
  });
  return n;
}

/* ---------- hero orchestration: visual → nav → headline → content ---------- */
(function intro(){
  const hero = document.querySelector('.n-hero');
  const title = document.querySelector('[data-roll]');
  const chars = title ? buildRoll(title) : 0;
  if(REDUCED){ hero.classList.add('instant'); title?.classList.add('rl-on'); return; }
  let advanced = false;
  const toNav = () => {
    if(advanced) return; advanced = true;
    hero.classList.add('go-nav');
    setTimeout(() => {
      hero.classList.add('go-headline');
      title?.classList.add('rl-on');
      setTimeout(() => hero.classList.add('go-content'), chars * 22 + 450);
    }, 420);
  };
  const imgs = [...hero.querySelectorAll('.n-visual img')];
  Promise.all(imgs.map(im => new Promise(res => {
    if(im.complete && im.naturalWidth) return res();
    im.onload = im.onerror = res;
  }))).then(() => requestAnimationFrame(() => requestAnimationFrame(toNav)));
  setTimeout(toNav, 1800); // never block the UI on assets
})();

/* ---------- mobile menu ---------- */
(function menu(){
  const btn = document.getElementById('menuBtn'), m = document.getElementById('mobileMenu');
  btn.addEventListener('click', () => {
    const open = m.classList.toggle('hidden');
    btn.setAttribute('aria-expanded', String(!open));
  });
  m.querySelectorAll('a').forEach(a => a.addEventListener('click', () => {
    m.classList.add('hidden'); btn.setAttribute('aria-expanded', 'false');
  }));
})();

/* ---------- rotating placeholder ---------- */
(function placeholder(){
  const el = document.getElementById('urlInput');
  const samples = ['http://paypal-secure-confirm.tinyurl.com@192.168.1.10/login',
    'https://www.your-bank.com/signin', 'http://free-iphone-winner-https-secure.tk@bit.ly/prize'];
  let si = 0, ci = 0, del = false;
  (function tick(){
    if(document.activeElement === el || el.value){ setTimeout(tick, 1500); return; }
    const s = samples[si];
    el.setAttribute('placeholder', (del ? s.slice(0, --ci) : s.slice(0, ++ci)) + '▍');
    if(!del && ci === s.length){ del = true; setTimeout(tick, 1700); return; }
    if(del && ci === 0){ del = false; si = (si + 1) % samples.length; }
    setTimeout(tick, del ? 12 : 30);
  })();
})();

/* ---------- eased counters ---------- */
document.querySelectorAll('[data-count]').forEach(el => {
  const target = parseFloat(el.dataset.count);
  const dec = parseInt(el.dataset.dec ?? (target <= 100 ? 1 : 0), 10);
  const t0 = performance.now(), dur = 1500;
  (function tick(t){
    const p = Math.min((t - t0) / dur, 1);
    const e = 1 - Math.pow(2, -10 * p);
    const v = target * (p === 1 ? 1 : e);
    el.textContent = target >= 1000 ? Math.round(v).toLocaleString('en-US') : v.toFixed(dec);
    if(p < 1) requestAnimationFrame(tick);
  })(t0);
});

/* ---------- scrollspy + reveals ---------- */
(function spy(){
  const links = [...document.querySelectorAll('.n-links a')];
  const map = new Map(links.map(a => [a.getAttribute('href').slice(1), a]));
  const io = new IntersectionObserver(es => es.forEach(e => {
    if(e.isIntersecting){
      links.forEach(a => a.classList.remove('active'));
      map.get(e.target.id)?.classList.add('active');
    }
  }), {rootMargin:'-40% 0px -55% 0px'});
  map.forEach((_, id) => { const s = document.getElementById(id); if(s) io.observe(s); });
})();
(function reveals(){
  const io = new IntersectionObserver(es => es.forEach(e => {
    if(e.isIntersecting){ e.target.classList.add('in'); io.unobserve(e.target); }
  }), {threshold:.1, rootMargin:'0px 0px -6% 0px'});
  document.querySelectorAll('.reveal').forEach(el => io.observe(el));
})();

/* ================= scanner ================= */
function demo(u){ document.getElementById('urlInput').value = u; scanUrl(); }
document.getElementById('urlInput').addEventListener('keydown', e => { if(e.key === 'Enter') scanUrl(); });

async function scanUrl(){
  const url = document.getElementById('urlInput').value.trim();
  if(!url){ document.getElementById('urlInput').focus(); toast('Paste a URL first — or try one of the examples.'); return; }
  const btn = document.getElementById('scanBtn');
  btn.disabled = true;
  document.getElementById('loader').classList.remove('hidden');
  document.getElementById('result').classList.add('hidden');
  try{
    const r = await fetch('/api/predict', {method:'POST', headers:{'Content-Type':'application/json'}, body:JSON.stringify({url})});
    const d = await r.json();
    if(d.error) throw new Error(d.error);
    lastResult = d;
    renderResult(d); saveHistory(d);
  }catch(e){ toast('Scan failed: ' + e.message, 'err'); }
  finally{
    document.getElementById('loader').classList.add('hidden');
    btn.disabled = false;
  }
}

function renderResult(d){
  document.getElementById('result').classList.remove('hidden');
  document.getElementById('result').scrollIntoView({behavior: REDUCED ? 'auto' : 'smooth', block:'nearest'});
  const arc = document.getElementById('gaugeArc'), txt = document.getElementById('gaugeText');
  requestAnimationFrame(() => { arc.style.strokeDashoffset = 251 - (251 * d.risk_score / 100); });
  arc.style.stroke = d.level === 'danger' ? '#f26d7d' : (d.level === 'warning' ? '#f5b544' : '#3ecf8e');
  const t0 = performance.now(), dur = 1100;
  (function count(t){
    const p = Math.min((t - t0) / dur, 1), e = 1 - Math.pow(2, -10 * p);
    txt.textContent = Math.round(d.risk_score * (p === 1 ? 1 : e)) + '%';
    if(p < 1) requestAnimationFrame(count);
  })(t0);
  const b = document.getElementById('verdictBadge');
  b.className = 'verdict ' + d.level;
  b.textContent = d.verdict === 'PHISHING' ? 'Phishing — do not enter any credentials'
    : (d.verdict === 'SUSPICIOUS' ? 'Suspicious — proceed with caution' : 'Legitimate — no phishing signs found');
  document.getElementById('resultUrl').textContent = d.url + `  ·  ${d.model}`;
  document.getElementById('cPhish').textContent = d.counts.phishy + ' phishy';
  document.getElementById('cSusp').textContent = d.counts.suspicious + ' unclear';
  document.getElementById('cLegit').textContent = d.counts.legit + ' clean';
  document.getElementById('pPhish').textContent = (d.phish_prob * 100).toFixed(1) + '%';
  document.getElementById('pLegit').textContent = (d.legit_prob * 100).toFixed(1) + '%';
  requestAnimationFrame(() => {
    document.getElementById('bPhish').style.width = (d.phish_prob * 100) + '%';
    document.getElementById('bLegit').style.width = (d.legit_prob * 100) + '%';
  });
  const sl = document.getElementById('signalList'); sl.innerHTML = '';
  if(!d.top_signals.length) sl.innerHTML = '<li class="ok"><span class="sig-tag">Clean</span><b>No phishy signals</b><small>All 30 checks came back clean.</small></li>';
  d.top_signals.forEach(s => {
    const li = document.createElement('li');
    li.innerHTML = `<span class="sig-tag">Phishy · ${s.value}</span><b></b><small></small>`;
    li.querySelector('b').textContent = s.feature;
    li.querySelector('small').textContent = s.explanation;
    sl.appendChild(li);
  });
  const ft = document.getElementById('featTable'); ft.innerHTML = '';
  d.features.forEach(f => {
    const row = document.createElement('div'); row.className = 'feat-row';
    const code = document.createElement('code'); code.textContent = f.feature;
    const sm = document.createElement('small'); sm.textContent = f.explanation;
    const pill = document.createElement('span');
    pill.className = 'pillv ' + (f.value === -1 ? 'p' : (f.value === 0 ? 's' : 'l'));
    pill.textContent = `${f.value} · ${f.label}`;
    row.append(code, sm, pill); ft.appendChild(row);
  });
  if(featChart) featChart.destroy();
  featChart = new Chart(document.getElementById('featChart'), {type:'bar',
    data:{labels:d.features.map(f => f.feature), datasets:[{data:d.features.map(f => f.value),
      backgroundColor:d.features.map(f => f.value === -1 ? '#f26d7d' : (f.value === 0 ? '#f5b544' : '#3ecf8e')),
      borderRadius:4, borderSkipped:false}]},
    options:{indexAxis:'y', animation:{duration:700, easing:'easeOutQuart'},
      plugins:{legend:{display:false}, tooltip:{callbacks:{label:c => ` ${c.raw === -1 ? 'Phishy' : (c.raw === 0 ? 'Unclear' : 'Clean')} (${c.raw})`}}},
      scales:{x:{min:-1.5, max:1.5, grid:{color:'rgba(255,255,255,.07)'}}, y:{ticks:{font:{size:9, family:'JetBrains Mono, monospace'}}}}}});
  document.getElementById('adviceBox').innerHTML = d.level === 'safe'
    ? `<p><b>Looks clean — stay in the habit:</b></p><ul><li>Still glance at the domain spelling before signing in.</li><li>Reach banks and payment sites via bookmarks, not links.</li><li>Keep two-factor authentication on everywhere it matters.</li></ul>`
    : `<p><b>${d.level === 'danger' ? 'High risk. Recommended steps:' : 'Worth a second look:'}</b></p><ul><li>Do not enter passwords, one-time codes, or card details.</li><li>Close the tab and type the official address yourself.</li><li>Report it to your IT/security team or national phishing hotline.</li><li>Already submitted something? Change that password now and enable 2FA.</li></ul>`;
}

function tab(e, name){
  document.querySelectorAll('.tab').forEach(t => t.classList.remove('active'));
  e.target.classList.add('active');
  ['signals','allfeat','advice'].forEach(n => document.getElementById('tab-' + n).classList.toggle('hidden', n !== name));
}

function copyReport(){
  if(!lastResult){ toast('Run a scan first.'); return; }
  const d = lastResult;
  const lines = [`PhishNet report — ${d.url}`, `Verdict: ${d.verdict} (risk ${d.risk_score}%) · model: ${d.model}`,
    `Signals: ${d.counts.phishy} phishy, ${d.counts.suspicious} unclear, ${d.counts.legit} clean`,
    ...(d.top_signals.length ? ['Key signals:'] : ['No phishy signals.']),
    ...d.top_signals.map(s => ` - ${s.feature} (${s.value}): ${s.explanation}`)];
  const done = () => toast('Report copied to clipboard.', 'ok');
  if(navigator.clipboard?.writeText) navigator.clipboard.writeText(lines.join('\n')).then(done, () => toast('Copy failed in this browser.', 'err'));
  else {
    const ta = document.createElement('textarea');
    ta.value = lines.join('\n'); document.body.appendChild(ta); ta.select();
    try{ document.execCommand('copy'); done(); }catch{ toast('Copy failed in this browser.', 'err'); }
    ta.remove();
  }
}

/* ================= model arena ================= */
function drawModels(){
  const names = Object.keys(METRICS.models);
  const vals = names.map(n => METRICS.models[n][currentMetric] * 100);
  if(modelChart) modelChart.destroy();
  modelChart = new Chart(document.getElementById('modelChart'), {type:'bar',
    data:{labels:names, datasets:[{label:currentMetric + ' (%)', data:vals,
      backgroundColor:names.map(n => n === METRICS.best_model ? '#ffffff' : 'rgba(255,255,255,.26)'),
      hoverBackgroundColor:'#e8d4ff', borderRadius:7, borderSkipped:false}]},
    options:{animation:{duration:700, easing:'easeOutQuart'}, plugins:{legend:{display:false}},
      scales:{y:{min:80, max:100, ticks:{callback:v => v + '%'}, grid:{color:'rgba(255,255,255,.07)'}},
        x:{ticks:{font:{size:9}}, grid:{display:false}}}}});
  const box = document.getElementById('modelCards'); box.innerHTML = '';
  [...names].sort((a,b) => METRICS.models[b][currentMetric] - METRICS.models[a][currentMetric]).forEach((n, i) => {
    const m = METRICS.models[n];
    const div = document.createElement('div');
    div.className = 'mcard' + (n === METRICS.best_model ? ' best' : '');
    div.innerHTML = `<span><b></b><br><small></small></span>`;
    div.querySelector('b').textContent = (n === METRICS.best_model ? '★ ' : '') + n;
    div.querySelector('small').textContent = `${i === 0 ? '1st' : (i + 1) + 'th'} · acc ${m.accuracy} · prec ${m.precision} · rec ${m.recall} · F1 ${m.f1}`;
    const badge = document.createElement('span');
    badge.className = 'badge ' + (m[currentMetric] > .95 ? 'safe' : (m[currentMetric] > .9 ? 'warning' : 'danger'));
    badge.textContent = (m[currentMetric] * 100).toFixed(2) + '%';
    div.appendChild(badge); box.appendChild(div);
  });
  const cm = METRICS.models[METRICS.best_model].confusion_matrix;
  document.getElementById('cmBox').innerHTML = `<div class="tn">TN<br>${cm[0][0]}</div><div class="fp">FP<br>${cm[0][1]}</div><div class="fn">FN<br>${cm[1][0]}</div><div class="tp">TP<br>${cm[1][1]}</div>
    <small>TN = legit, correctly cleared · TP = phish, correctly caught · FP = false alarm · FN = missed phish</small>`;
}
document.querySelectorAll('.mt').forEach(b => b.onclick = () => {
  document.querySelectorAll('.mt').forEach(x => x.classList.remove('active'));
  b.classList.add('active'); currentMetric = b.dataset.m; drawModels();
});
drawModels();

impChart = new Chart(document.getElementById('impChart'), {type:'bar',
  data:{labels:IMPORTANCE.map(i => i.feature), datasets:[{data:IMPORTANCE.map(i => i.importance),
    backgroundColor:'rgba(201,139,255,.8)', hoverBackgroundColor:'#e8d4ff', borderRadius:5, borderSkipped:false}]},
  options:{indexAxis:'y', animation:{duration:700, easing:'easeOutQuart'}, plugins:{legend:{display:false}},
    scales:{x:{grid:{color:'rgba(255,255,255,.07)'}}, y:{ticks:{font:{size:10, family:'JetBrains Mono, monospace'}}}}}});

/* ================= bulk ================= */
async function bulkCheck(){
  const urls = document.getElementById('bulkInput').value.split('\n').map(s => s.trim()).filter(Boolean).slice(0, 20);
  if(!urls.length){ toast('Paste at least one URL — one per line.'); return; }
  const box = document.getElementById('bulkResults'); box.innerHTML = '<p class="muted">Scanning…</p>';
  try{
    const r = await fetch('/api/batch', {method:'POST', headers:{'Content-Type':'application/json'}, body:JSON.stringify({urls})});
    const d = await r.json(); lastBulk = d.results || [];
    box.innerHTML = '<table><tr><th>URL</th><th>Verdict</th><th>Risk</th></tr>' + lastBulk.map(() =>
      `<tr><td style="word-break:break-all;font-family:JetBrains Mono,monospace;font-size:.78rem"></td><td></td><td></td></tr>`
    ).join('') + '</table>';
    [...box.querySelectorAll('tr')].slice(1).forEach((tr, i) => {
      const x = lastBulk[i], tds = tr.querySelectorAll('td');
      tds[0].textContent = x.url;
      tds[1].innerHTML = ''; const sp = document.createElement('span');
      sp.className = 'badge ' + x.level; sp.textContent = x.verdict; tds[1].appendChild(sp);
      tds[2].textContent = x.risk_score + '%';
    });
  }catch(e){ box.innerHTML = ''; toast('Bulk check failed: ' + e.message, 'err'); }
}
function downloadCSV(){
  if(!lastBulk.length){ toast('Run a bulk check first.'); return; }
  const csv = 'url,verdict,risk_score,phish_prob\n' + lastBulk.map(x => `"${x.url.replace(/"/g, '""')}",${x.verdict},${x.risk_score},${x.phish_prob}`).join('\n');
  const a = document.createElement('a');
  a.href = URL.createObjectURL(new Blob([csv], {type:'text/csv'}));
  a.download = 'phishnet_results.csv'; a.click();
  URL.revokeObjectURL(a.href);
  toast(`Downloaded ${lastBulk.length} results.`, 'ok');
}

/* ================= history ================= */
function saveHistory(d){
  const h = JSON.parse(localStorage.getItem(HIST_KEY) || '[]');
  h.unshift({url:d.url, verdict:d.verdict, level:d.level, risk:d.risk_score, t:new Date().toLocaleString()});
  localStorage.setItem(HIST_KEY, JSON.stringify(h.slice(0, 15))); showHistory();
}
function showHistory(){
  const h = JSON.parse(localStorage.getItem(HIST_KEY) || '[]');
  const box = document.getElementById('historyList');
  box.innerHTML = '';
  if(!h.length){ box.innerHTML = '<p class="muted">No scans yet — results will appear here.</p>'; return; }
  h.forEach(x => {
    const row = document.createElement('div'); row.className = 'hrow';
    const badge = document.createElement('span'); badge.className = 'badge ' + x.level; badge.textContent = x.verdict;
    const u = document.createElement('span'); u.className = 'u'; u.textContent = x.url;
    const meta = document.createElement('span'); meta.textContent = `${x.risk}% · ${x.t}`;
    row.append(badge, u, meta); box.appendChild(row);
  });
}
function clearHistory(){ localStorage.removeItem(HIST_KEY); showHistory(); toast('Logbook cleared.'); }
showHistory();

/* ================= quiz ================= */
const QUIZ = [
 {q:'Which of these URLs would you trust the least?', opts:['https://www.paypal.com/signin','http://paypal-secure-confirm.tinyurl.com@192.168.1.10/login','https://accounts.google.com/signin'], a:1, why:'The middle one stacks four tricks: a raw IP host, an @ that hides the real destination, a shortener, and a dashed lookalike domain.'},
 {q:'A login page loads over http:// instead of https://. What is the safe move?', opts:['Log in quickly before the page expires','Close it — never type credentials into an unencrypted page','Fine, as long as the logo looks right'], a:1, why:'Without HTTPS your credentials travel in cleartext — and logos take seconds to copy.'},
 {q:'“Dear customer, your account will be closed! Verify now at http://bit.ly/2xYz.” What is this?', opts:['A genuine urgent notice','A textbook phish: urgency, generic greeting, masked link','Harmless if your antivirus is on'], a:1, why:'Pressure plus a hidden destination is the classic combination. Real providers name you and host their own links.'}];
let qi = 0, qscore = 0;
function renderQuiz(){
  const box = document.getElementById('quizBox');
  if(qi >= QUIZ.length){
    const verdict = qscore === 3 ? 'Excellent — a careful eye.' : (qscore === 2 ? 'Solid — one more look at the misses.' : 'A good start — the scanner above will train your instincts.');
    box.innerHTML = '';
    const h = document.createElement('h3'); h.textContent = `You scored ${qscore} out of ${QUIZ.length}. ${verdict}`;
    const btn = document.createElement('button'); btn.className = 'btn-primary'; btn.textContent = 'Try again'; btn.onclick = () => { qi = 0; qscore = 0; renderQuiz(); };
    box.append(h, btn); return;
  }
  const q = QUIZ[qi];
  box.innerHTML = '<div class="quiz-q"><span class="q"></span><div class="opts"></div><p class="quiz-meta"></p></div>';
  box.querySelector('.q').textContent = `Q${qi + 1}. ${q.q}`;
  box.querySelector('.quiz-meta').textContent = `Question ${qi + 1} of ${QUIZ.length} · Score ${qscore}`;
  const opts = box.querySelector('.opts');
  q.opts.forEach((o, i) => {
    const b = document.createElement('button'); b.textContent = o; b.onclick = () => answer(i); opts.appendChild(b);
  });
}
function answer(i){
  const q = QUIZ[qi]; const ok = i === q.a; if(ok) qscore++;
  const box = document.getElementById('quizBox');
  box.innerHTML = '<div class="quiz-q"><span class="q"></span><p class="muted"></p></div>';
  box.querySelector('.q').textContent = ok ? 'Correct.' : 'Not quite.';
  box.querySelector('.muted').textContent = q.why;
  const btn = document.createElement('button'); btn.className = 'btn-primary'; btn.style.marginTop = '.7rem';
  btn.textContent = qi + 1 >= QUIZ.length ? 'See my score' : 'Next question';
  btn.onclick = () => { qi++; renderQuiz(); };
  box.querySelector('.quiz-q').appendChild(btn);
}
renderQuiz();
