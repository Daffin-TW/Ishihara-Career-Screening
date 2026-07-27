/**
 * result.js – Animasi chart dan visualisasi untuk halaman hasil
 * IshiharaScreen
 */

document.addEventListener("DOMContentLoaded", () => {
  if (typeof RESULT_DATA === "undefined") return;

  // Jalankan semua animasi
  animateGaugeChart(RESULT_DATA.ishiharaPercentage);
  animateConfidenceCircle(RESULT_DATA.confidence);
  animateProgressBars();

  // Render radar chart saat accordion dibuka
  const radarAccordion = document.getElementById("acc-riasec");
  if (radarAccordion) {
    radarAccordion.addEventListener("shown.bs.collapse", () => {
      renderRadarChart(RESULT_DATA.riasec);
    });
  }

  // Scroll animation untuk cards
  initScrollAnimations();
});

/* ════════════════════════════════════════════════════════════════════════
   GAUGE CHART (Persentase Identifikasi Warna)
   Menggunakan Canvas Arc
   ════════════════════════════════════════════════════════════════════════ */
function animateGaugeChart(percentage) {
  const canvas = document.getElementById("gaugeChart");
  if (!canvas) return;

  const ctx   = canvas.getContext("2d");
  const W     = canvas.width;
  const H     = canvas.height;
  const cx    = W / 2;
  const cy    = H / 2;
  const R     = Math.min(W, H) / 2 - 15;
  const START = Math.PI * 0.75;        // 135°
  const END   = Math.PI * 2.25;        // 405° (270° sweep)
  const TOTAL_ANGLE = END - START;

  // Color based on percentage
  const color = percentage >= 85 ? "#10B981"
              : percentage >= 71 ? "#3B82F6"
              : percentage >= 35 ? "#F59E0B"
              : "#EF4444";

  // Background track color based on dark mode
  const isDark = document.documentElement.getAttribute("data-theme") === "dark";
  const trackColor = isDark ? "#2D3748" : "#E2E8F0";

  let animPct = 0;
  const duration  = 1500; // ms
  const startTime = performance.now();

  function draw(now) {
    const elapsed  = now - startTime;
    const progress = Math.min(elapsed / duration, 1);
    // Ease-out cubic
    const eased = 1 - Math.pow(1 - progress, 3);

    animPct = eased * percentage;

    ctx.clearRect(0, 0, W, H);

    // ── Background track ─────────────────────────────────────────────────
    ctx.beginPath();
    ctx.arc(cx, cy, R, START, END);
    ctx.strokeStyle = trackColor;
    ctx.lineWidth   = 18;
    ctx.lineCap     = "round";
    ctx.stroke();

    // ── Progress arc ─────────────────────────────────────────────────────
    const targetAngle = START + (animPct / 100) * TOTAL_ANGLE;

    // Gradient
    const grad = ctx.createLinearGradient(0, 0, W, H);
    grad.addColorStop(0, color);
    grad.addColorStop(1, lightenColor(color, 40));

    ctx.beginPath();
    ctx.arc(cx, cy, R, START, targetAngle);
    ctx.strokeStyle = grad;
    ctx.lineWidth   = 18;
    ctx.lineCap     = "round";
    ctx.stroke();

    // ── Center value update ───────────────────────────────────────────────
    const valEl = document.getElementById("gaugeValue");
    if (valEl) valEl.textContent = animPct.toFixed(1) + "%";

    if (progress < 1) requestAnimationFrame(draw);
  }

  requestAnimationFrame(draw);
}

function lightenColor(hex, amount) {
  const num    = parseInt(hex.replace("#", ""), 16);
  const r      = Math.min(255, (num >> 16) + amount);
  const g      = Math.min(255, ((num >> 8) & 0xFF) + amount);
  const b      = Math.min(255, (num & 0xFF) + amount);
  return `rgb(${r},${g},${b})`;
}

/* ════════════════════════════════════════════════════════════════════════
   CONFIDENCE CIRCLE (SVG stroke-dashoffset animation)
   ════════════════════════════════════════════════════════════════════════ */
function animateConfidenceCircle(confidence) {
  const fillEl = document.getElementById("confCircleFill");
  const valEl  = document.getElementById("confValue");

  if (!fillEl) return;

  // Add gradient to SVG
  const svg = fillEl.closest("svg");
  if (svg) {
    const defs = document.createElementNS("http://www.w3.org/2000/svg", "defs");
    const grad = document.createElementNS("http://www.w3.org/2000/svg", "linearGradient");
    grad.setAttribute("id", "confGradient");
    grad.setAttribute("x1", "0%"); grad.setAttribute("y1", "0%");
    grad.setAttribute("x2", "100%"); grad.setAttribute("y2", "100%");

    const stop1 = document.createElementNS("http://www.w3.org/2000/svg", "stop");
    stop1.setAttribute("offset", "0%");
    stop1.setAttribute("stop-color", "#5B6EF5");

    const stop2 = document.createElementNS("http://www.w3.org/2000/svg", "stop");
    stop2.setAttribute("offset", "100%");
    stop2.setAttribute("stop-color", "#7C3AED");

    grad.appendChild(stop1);
    grad.appendChild(stop2);
    defs.appendChild(grad);
    svg.insertBefore(defs, svg.firstChild);
  }

  const circumference = 314; // 2 * π * 50

  // Animate
  let current = 0;
  const duration  = 1500;
  const startTime = performance.now();

  function animate(now) {
    const progress = Math.min((now - startTime) / duration, 1);
    const eased    = 1 - Math.pow(1 - progress, 3);
    current        = eased * confidence;

    const offset = circumference - (current / 100) * circumference;
    fillEl.setAttribute("stroke-dashoffset", offset.toFixed(2));

    if (valEl) valEl.textContent = current.toFixed(1) + "%";

    if (progress < 1) requestAnimationFrame(animate);
  }

  requestAnimationFrame(animate);
}

/* ════════════════════════════════════════════════════════════════════════
   ANIMATE PROGRESS BARS (Probability)
   ════════════════════════════════════════════════════════════════════════ */
function animateProgressBars() {
  const bars = document.querySelectorAll(".progress-bar[data-width]");
  bars.forEach(bar => {
    const target = parseFloat(bar.dataset.width);
    bar.style.width = "0%";
    setTimeout(() => {
      bar.style.transition = "width 1s cubic-bezier(0.4,0,0.2,1)";
      bar.style.width = target + "%";
    }, 300);
  });
}

/* ════════════════════════════════════════════════════════════════════════
   RADAR CHART (RIASEC Profile) – Chart.js
   ════════════════════════════════════════════════════════════════════════ */
function renderRadarChart(riasec) {
  const canvas = document.getElementById("radarChart");
  if (!canvas) return;

  // Avoid re-rendering
  if (canvas._chartInstance) {
    canvas._chartInstance.destroy();
  }

  const isDark   = document.documentElement.getAttribute("data-theme") === "dark";
  const gridColor  = isDark ? "rgba(255,255,255,0.1)" : "rgba(0,0,0,0.08)";
  const tickColor  = isDark ? "rgba(255,255,255,0.5)" : "rgba(0,0,0,0.5)";

  const dims   = ["R", "I", "A", "S", "E", "C"];
  const labels = ["Realistic", "Investigative", "Artistic", "Social", "Enterprising", "Conventional"];
  const data   = dims.map(d => riasec[d] || 0);

  canvas._chartInstance = new Chart(canvas, {
    type: "radar",
    data: {
      labels: labels,
      datasets: [{
        label: "Skor RIASEC",
        data: data,
        backgroundColor: "rgba(91,110,245,0.15)",
        borderColor:     "rgba(91,110,245,0.8)",
        borderWidth: 2.5,
        pointBackgroundColor: "#5B6EF5",
        pointBorderColor:    "#fff",
        pointRadius: 5,
        pointHoverRadius: 7,
      }]
    },
    options: {
      responsive: true,
      animation: { duration: 1000, easing: "easeInOutQuart" },
      scales: {
        r: {
          min: 0, max: 25,
          ticks: {
            stepSize: 5,
            color: tickColor,
            font: { size: 10, family: "Inter" },
            backdropColor: "transparent",
          },
          grid:        { color: gridColor },
          angleLines:  { color: gridColor },
          pointLabels: {
            color: isDark ? "#E2E8F0" : "#1E293B",
            font: { size: 11, weight: "600", family: "Inter" },
          },
        }
      },
      plugins: {
        legend: { display: false },
        tooltip: {
          callbacks: {
            label: ctx => ` ${ctx.raw}/25`,
          }
        }
      }
    }
  });
}

/* ════════════════════════════════════════════════════════════════════════
   SCROLL ANIMATIONS
   ════════════════════════════════════════════════════════════════════════ */
function initScrollAnimations() {
  const observer = new IntersectionObserver((entries) => {
    entries.forEach(entry => {
      if (entry.isIntersecting) {
        entry.target.classList.add("visible");
      }
    });
  }, { threshold: 0.08 });

  document.querySelectorAll(".animate-slide-up").forEach(el => {
    el.style.opacity = "0";
    el.style.transform = "translateY(30px)";
    el.style.transition = "opacity 0.6s ease, transform 0.6s ease";
    observer.observe(el);
  });
}

// Add CSS for visible class
const style = document.createElement("style");
style.textContent = `
  .animate-slide-up.visible {
    opacity: 1 !important;
    transform: translateY(0) !important;
  }
`;
document.head.appendChild(style);
