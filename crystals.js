/* MirrorMirage: эффекты сайта (кристаллы, меню-бургер, проявление блоков).
   Один файл без библиотек. Если он не загрузился, сайт работает как обычно. */
(function () {
  'use strict';

  /* ---------- Меню-бургер на телефоне ----------
     Кнопка переключает класс open у шапки и атрибут aria-expanded.
     Меню закрывают: Esc, клик по ссылке, расширение окна до компьютерной ширины. */
  function initMenu() {
    var header = document.querySelector('header.site');
    var button = header && header.querySelector('.menu-toggle');
    var nav = document.getElementById('site-nav');
    if (!header || !button || !nav) return;

    function setOpen(open) {
      header.classList.toggle('open', open);
      button.setAttribute('aria-expanded', open ? 'true' : 'false');
      button.setAttribute('aria-label', open ? 'Закрыть меню' : 'Меню');
    }

    button.addEventListener('click', function () {
      setOpen(!header.classList.contains('open'));
    });
    document.addEventListener('keydown', function (e) {
      if (e.key === 'Escape' && header.classList.contains('open')) {
        setOpen(false);
        button.focus();
      }
    });
    nav.addEventListener('click', function (e) {
      if (e.target.closest('a')) setOpen(false);
    });
    window.matchMedia('(min-width: 701px)').addEventListener('change', function (e) {
      if (e.matches) setOpen(false);
    });
  }

  /* ---------- Парящие кристаллы ----------
     Режимы: hero (главная, у первого экрана), title (заголовки внутренних страниц),
     off (служебные страницы с body.calm или нет подходящего места).
     Холст лежит под текстом и не ловит клики. Кристаллы и искры живут только
     у краёв блока (0–22% и 78–100% ширины), чтобы не закрывать надписи. */
  var MOBILE_QUERY = '(max-width: 700px)';
  var FACE_COLORS = [
    'rgba(120,190,255,.55)', 'rgba(47,107,255,.5)', 'rgba(30,70,200,.55)',
    'rgba(56,214,255,.45)', 'rgba(90,150,255,.5)', 'rgba(150,215,255,.6)'
  ];
  var params = new URLSearchParams(window.location.search);
  var forceReduce = params.has('reduce-motion'); // для проверок: то же, что «уменьшить анимацию»
  if (forceReduce) document.documentElement.classList.add('reduce-motion');
  var motionQuery = window.matchMedia('(prefers-reduced-motion: reduce)');

  var E = {
    mode: 'off', running: false, reduced: false, host: null, canvas: null, ctx: null,
    w: 0, h: 0, dpr: 1, mobile: false, raf: 0, last: 0, time: 0,
    crystals: [], sparks: [], cyan: '#38d6ff'
  };

  function rand(a, b) { return a + Math.random() * (b - a); }
  function clamp(v, a, b) { return Math.max(a, Math.min(b, v)); }

  function pickHost() {
    if (document.body.classList.contains('calm')) return null;
    var hero = document.querySelector('.hero-banner');
    if (hero) return { el: hero, mode: 'hero' };
    var title = document.querySelector('.page-title, .ap-hero');
    if (title) return { el: title, mode: 'title' };
    return null;
  }

  // Случайная точка только в боковых полосах блока
  function stripX(pad) {
    var x = Math.random() < 0.5 ? rand(0, E.w * 0.22) : rand(E.w * 0.78, E.w);
    return clamp(x, pad, Math.max(pad, E.w - pad));
  }

  function newCrystal(initial) {
    var size = rand(8, 24);
    return {
      size: size, x: stripX(size * 0.42 + 8),
      y: initial ? rand(0, E.h) : E.h + size * 2,
      speed: rand(0.12, 0.32),                    // пикселей за кадр при 60 кадрах/с
      phase: rand(0, 6.28), freq: rand(0.0006, 0.0012)
    };
  }

  function newSpark(initial) {
    return {
      x: stripX(4), y: initial ? rand(0, E.h) : E.h + 4, r: rand(0.6, 1.6),
      speed: rand(0.05, 0.15), phase: rand(0, 6.28), freq: rand(0.002, 0.005)
    };
  }

  function build() {
    var hero = E.mode === 'hero';
    var nCrystals = hero ? (E.mobile ? 4 : 9) : (E.mobile ? 2 : 4);
    var nSparks = hero ? (E.mobile ? 12 : 30) : 0;
    E.crystals = []; E.sparks = [];
    for (var i = 0; i < nCrystals; i++) E.crystals.push(newCrystal(true));
    for (var j = 0; j < nSparks; j++) E.sparks.push(newSpark(true));
  }

  // Шестиугольная бипирамида: 6 граней от точки у центра
  function drawCrystal(c) {
    var ctx = E.ctx, H = c.size, W = 0.42 * H;
    var x = c.x + Math.sin(E.time * c.freq + c.phase) * 6;
    var v = [[0, -H], [W, -0.4 * H], [W, 0.55 * H], [0, H], [-W, 0.55 * H], [-W, -0.4 * H]];
    function outline() {
      ctx.beginPath();
      ctx.moveTo(v[0][0], v[0][1]);
      for (var k = 1; k < 6; k++) ctx.lineTo(v[k][0], v[k][1]);
      ctx.closePath();
    }
    ctx.save();
    ctx.translate(x, c.y);
    ctx.rotate(Math.sin(E.time * c.freq * 0.7 + c.phase) * 0.1);
    // свечение: заливка с тенью цвета --cyan (shadowBlur не масштабируется матрицей, поэтому × dpr)
    ctx.shadowColor = E.cyan; ctx.shadowBlur = 0.5 * H * E.dpr;
    ctx.fillStyle = 'rgba(47,107,255,.35)';
    outline(); ctx.fill();
    ctx.shadowBlur = 0; ctx.shadowColor = 'transparent';
    var cx = 0.15 * W, cy = -0.05 * H;
    for (var i = 0; i < 6; i++) {
      var a = v[i], b = v[(i + 1) % 6];
      ctx.beginPath(); ctx.moveTo(cx, cy); ctx.lineTo(a[0], a[1]); ctx.lineTo(b[0], b[1]); ctx.closePath();
      ctx.fillStyle = FACE_COLORS[i]; ctx.fill();
    }
    ctx.strokeStyle = 'rgba(190,235,255,.85)'; ctx.lineWidth = Math.max(0.8, H / 16);
    outline(); ctx.stroke();
    ctx.restore();
  }

  function drawSpark(s) {
    var ctx = E.ctx;
    var a = 0.25 + 0.75 * (Math.sin(E.time * s.freq + s.phase) * 0.5 + 0.5);
    ctx.fillStyle = 'rgba(190,240,255,' + (a * 0.35).toFixed(3) + ')';
    ctx.beginPath(); ctx.arc(s.x, s.y, s.r * 2.4, 0, 6.2832); ctx.fill();
    ctx.fillStyle = 'rgba(235,250,255,' + a.toFixed(3) + ')';
    ctx.beginPath(); ctx.arc(s.x, s.y, s.r, 0, 6.2832); ctx.fill();
  }

  // dt — миллисекунды с прошлого кадра; 0 — просто перерисовать на месте
  function drawFrame(dt) {
    if (!E.ctx || !E.w) return;
    var step = dt / 16.667, i, c, s;
    E.ctx.setTransform(E.dpr, 0, 0, E.dpr, 0, 0);
    E.ctx.clearRect(0, 0, E.w, E.h);
    for (i = 0; i < E.sparks.length; i++) {
      s = E.sparks[i];
      s.y -= s.speed * step;
      if (s.y < -4) E.sparks[i] = s = newSpark(false);
      drawSpark(s);
    }
    for (i = 0; i < E.crystals.length; i++) {
      c = E.crystals[i];
      c.y -= c.speed * step;
      if (c.y < -c.size * 2) E.crystals[i] = c = newCrystal(false);
      drawCrystal(c);
    }
  }

  function loop(ts) {
    E.raf = window.requestAnimationFrame(loop);
    if (E.mobile && E.last && ts - E.last < 31) return; // на телефоне ~30 кадров/с
    var dt = E.last ? Math.min(ts - E.last, 100) : 16.667;
    E.last = ts; E.time = ts;
    drawFrame(dt);
  }

  function start() {
    if (E.mode === 'off' || E.running || E.reduced || document.hidden) return;
    E.last = 0; E.running = true;
    E.raf = window.requestAnimationFrame(loop);
  }

  function stop() {
    if (E.raf) window.cancelAnimationFrame(E.raf);
    E.raf = 0; E.running = false;
  }

  function resize() {
    var rect = E.host.getBoundingClientRect();
    var w = Math.round(rect.width), h = Math.round(rect.height);
    if (!w || !h) return;
    var mobile = window.matchMedia(MOBILE_QUERY).matches;
    var rebuild = w !== E.w || mobile !== E.mobile || !E.crystals.length;
    E.w = w; E.h = h; E.mobile = mobile;
    E.dpr = Math.min(window.devicePixelRatio || 1, 2);
    E.canvas.width = Math.round(w * E.dpr);
    E.canvas.height = Math.round(h * E.dpr);
    if (rebuild) build();
    if (!E.running) drawFrame(0); // стоим на месте (пауза или «уменьшить анимацию») — рисуем один кадр
  }

  function applyMotionPreference() {
    E.reduced = motionQuery.matches || forceReduce;
    if (E.reduced) { stop(); drawFrame(0); } else { start(); }
  }

  function initCrystals() {
    var found = pickHost();
    E.reduced = motionQuery.matches || forceReduce;
    if (!found) return;
    var canvas = document.createElement('canvas');
    var ctx = canvas.getContext && canvas.getContext('2d');
    if (!ctx) return;
    canvas.className = 'crystals';
    canvas.setAttribute('aria-hidden', 'true');
    found.el.classList.add('crystal-host');
    found.el.insertBefore(canvas, found.el.firstChild);
    var cyan = window.getComputedStyle(document.documentElement).getPropertyValue('--cyan').trim();
    E.mode = found.mode; E.host = found.el; E.canvas = canvas; E.ctx = ctx;
    if (cyan) E.cyan = cyan;
    resize();
    if (window.ResizeObserver) new ResizeObserver(resize).observe(E.host);
    else window.addEventListener('resize', resize);
    document.addEventListener('visibilitychange', function () {
      if (document.hidden) stop(); else start();
    });
    motionQuery.addEventListener('change', applyMotionPreference);
    applyMotionPreference();
  }

  // Для проверок: window.MMCrystals.state()
  window.MMCrystals = {
    state: function () {
      return { mode: E.mode, running: E.running, crystals: E.crystals.length, reduced: E.reduced };
    }
  };

  /* ---------- Проявление блоков при прокрутке ----------
     Класс reveal-on (его ставим здесь) прячет section.block, класс shown показывает.
     При «уменьшить анимацию» (и при ?reduce-motion) всё видно сразу. */
  function initReveal() {
    // проявление нужно только главной; на служебных страницах (calm) и внутренних блоки видны сразу
    if (document.body.classList.contains('calm') || !document.querySelector('.hero-banner')) return;
    var blocks = document.querySelectorAll('section.block');
    if (!blocks.length) return;
    var root = document.documentElement;
    function showAll() {
      for (var i = 0; i < blocks.length; i++) blocks[i].classList.add('shown');
    }
    root.classList.add('reveal-on');
    if (motionQuery.matches || forceReduce || !('IntersectionObserver' in window)) { showAll(); return; }
    motionQuery.addEventListener('change', function (e) { if (e.matches) showAll(); });
    Array.prototype.forEach.call(blocks, function (block) {
      // порог 0.15, но для очень высоких блоков меньше, чтобы они гарантированно проявились
      var ratio = Math.min(0.15, (window.innerHeight * 0.5) / Math.max(block.offsetHeight, 1));
      var observer = new IntersectionObserver(function (entries) {
        if (entries.some(function (e) { return e.isIntersecting; })) {
          block.classList.add('shown');
          observer.disconnect();
        }
      }, { threshold: ratio });
      observer.observe(block);
    });
  }

  /* ---------- Лёгкий наклон скриншота в витрине ----------
     Только для мыши (pointer: fine) и если анимация не отключена. До 6 градусов. */
  function initTilt() {
    var frame = document.querySelector('.showcase > a');
    if (!frame || motionQuery.matches || forceReduce) return;
    if (!window.matchMedia('(pointer: fine)').matches) return;
    var MAX = 6;
    frame.addEventListener('pointermove', function (e) {
      var r = frame.getBoundingClientRect();
      var px = (e.clientX - r.left) / r.width - 0.5;
      var py = (e.clientY - r.top) / r.height - 0.5;
      frame.style.transform = 'perspective(900px) rotateX(' + (-py * 2 * MAX).toFixed(2) +
        'deg) rotateY(' + (px * 2 * MAX).toFixed(2) + 'deg)';
    });
    frame.addEventListener('pointerleave', function () { frame.style.transform = ''; });
  }

  // Каждая часть запускается отдельно: сбой в одной не ломает остальные
  [initCrystals, initMenu, initReveal, initTilt].forEach(function (part) {
    try { part(); } catch (err) { /* сайт остаётся рабочим без этого эффекта */ }
  });
})();
