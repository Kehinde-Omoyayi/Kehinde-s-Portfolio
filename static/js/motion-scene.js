(function () {
  'use strict';

  var prefersReduced = window.matchMedia('(prefers-reduced-motion: reduce)').matches;

  /* ────── Ambient background behind the avatar ────── */
  function initProfileBackground(canvas) {
    if (!canvas || prefersReduced) return;
    var ctx = canvas.getContext('2d');
    var w, h, dpr;

    var blobs = [
      { baseX: 0.35, baseY: 0.4, r: 0.35, hueVar: '--brand-accent', speed: 0.5, phase: 0 },
      { baseX: 0.65, baseY: 0.55, r: 0.3, hueVar: '--brand-emerald', speed: 0.4, phase: 2.6 }
    ];

    function resize() {
      dpr = Math.min(window.devicePixelRatio || 1, 2);
      w = canvas.clientWidth;
      h = canvas.clientHeight;
      canvas.width = w * dpr;
      canvas.height = h * dpr;
      ctx.setTransform(dpr, 0, 0, dpr, 0, 0);
    }

    function colorFor(varName) {
      var raw = getComputedStyle(document.documentElement).getPropertyValue(varName).trim();
      return raw || '#5b8cff';
    }

    function noise(x, y, t) {
      return (Math.sin(x * 0.9 + t) + Math.sin(y * 1.3 - t * 0.7) + Math.sin((x + y) * 0.6 + t * 1.1)) / 3;
    }

    function draw(t) {
      t *= 0.0003;
      ctx.clearRect(0, 0, w, h);
      blobs.forEach(function (b) {
        var n = noise(b.baseX * 6, b.baseY * 6, t * b.speed + b.phase);
        var x = (b.baseX + n * 0.08) * w;
        var y = (b.baseY + Math.cos(t * b.speed + b.phase) * 0.07) * h;
        var r = (b.r + n * 0.04) * Math.max(w, h);
        var grad = ctx.createRadialGradient(x, y, 0, x, y, r);
        grad.addColorStop(0, colorFor(b.hueVar) + '40');
        grad.addColorStop(1, colorFor(b.hueVar) + '00');
        ctx.fillStyle = grad;
        ctx.beginPath();
        ctx.arc(x, y, r, 0, Math.PI * 2);
        ctx.fill();
      });
      requestAnimationFrame(draw);
    }

    window.addEventListener('resize', resize, { passive: true });
    resize();
    draw(0);
  }

  /* ────── One-shot resolve reveal ────── */
  function buildNoiseTexture() {
    var c = document.createElement('canvas');
    c.width = c.height = 96;
    var ctx = c.getContext('2d');
    var imgData = ctx.createImageData(96, 96);
    for (var i = 0; i < imgData.data.length; i += 4) {
      var v = Math.random() * 255;
      imgData.data[i] = imgData.data[i + 1] = imgData.data[i + 2] = v;
      imgData.data[i + 3] = 255;
    }
    ctx.putImageData(imgData, 0, 0);
    return c.toDataURL('image/png');
  }

function initProfileReveal(img, scan) {
    if (!img) return;

    if (prefersReduced) {
      img.classList.add('is-revealed');
      if (scan) scan.classList.add('is-revealed');
      return;
    }

    if (scan) scan.style.backgroundImage = 'url(' + buildNoiseTexture() + ')';

    function reveal() {
      // 2s delay for the scan pop-out
      setTimeout(function() {
        if (scan) scan.classList.add('is-revealed');
      }, 2000);

      // 7s delay for the image blur reveal
      setTimeout(function() {
        img.classList.add('is-revealed');
      }, 7000);
    }

    function resetForReplay() {
      img.style.transition = 'none';
      if (scan) scan.style.transition = 'none';

      img.classList.remove('is-revealed');
      if (scan) scan.classList.remove('is-revealed');

      void img.offsetWidth;

      img.style.transition = '';
      if (scan) scan.style.transition = '';
    }

    function playCycle() {
      resetForReplay();
      requestAnimationFrame(function () {
        requestAnimationFrame(reveal);
      });
    }

    if (img.complete) {
      setTimeout(reveal, 350);
    } else {
      img.addEventListener('load', function () { setTimeout(reveal, 350); }, { once: true });
    }

    // Since the full reveal takes 7s, repeat the cycle every 14s.
    setInterval(playCycle, 14000);
  }

  document.addEventListener('DOMContentLoaded', function () {
    initProfileBackground(document.getElementById('profileMotionBg'));
    initProfileReveal(
      document.getElementById('profileMotionImg'),
      document.getElementById('profileMotionScan')
    );
  });
})();