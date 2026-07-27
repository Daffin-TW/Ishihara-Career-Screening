/**
 * form.js – Multi-step wizard logic, validasi, dan Ishihara navigation
 * IshiharaScreen
 */

/* ════════════════════════════════════════════════════════════════════════
   STATE
   ════════════════════════════════════════════════════════════════════════ */
const TOTAL_STEPS = 6;
let currentStep   = 1;
let currentIsh    = 1;    // Slide Ishihara aktif
let totalIsh      = 0;    // Total gambar (dari ISHIHARA_IMAGES global)
let ishAnswered   = [];   // Track gambar mana sudah dijawab

/* ════════════════════════════════════════════════════════════════════════
   INIT
   ════════════════════════════════════════════════════════════════════════ */
document.addEventListener("DOMContentLoaded", () => {
  initTooltips();
  initIshihara();
  initRatingLabels();
  initRIASECScores();
  initCareerSearch();
  initFormSubmit();
  updateWizard();
});

/* ════════════════════════════════════════════════════════════════════════
   TOOLTIPS
   ════════════════════════════════════════════════════════════════════════ */
function initTooltips() {
  const tooltipTriggers = document.querySelectorAll('[data-bs-toggle="tooltip"]');
  tooltipTriggers.forEach(el => new bootstrap.Tooltip(el, { placement: 'top' }));
}

/* ════════════════════════════════════════════════════════════════════════
   ISHIHARA NAVIGATION
   ════════════════════════════════════════════════════════════════════════ */
function initIshihara() {
  if (typeof ISHIHARA_IMAGES === 'undefined') return;
  totalIsh = ISHIHARA_IMAGES.length;
  ishAnswered = new Array(totalIsh).fill(false);

  // Mark slide sebagai answered saat input diubah
  document.querySelectorAll(".ishihara-answer").forEach(input => {
    input.addEventListener("input", () => {
      const no = parseInt(input.dataset.no);
      const idx = ISHIHARA_IMAGES.findIndex(img => img.no === no);
      if (idx >= 0) {
        ishAnswered[idx] = input.value.trim() !== "";
        updateIshiharaProgress();
      }
    });
  });

  showIshiharaSlide(1);
}

function showIshiharaSlide(no) {
  currentIsh = no;

  document.querySelectorAll(".ishihara-slide").forEach(slide => {
    slide.classList.remove("active");
  });
  const target = document.getElementById(`ish-slide-${no}`);
  if (target) {
    target.classList.add("active");
    // Scroll ke gambar
    target.scrollIntoView({ behavior: "smooth", block: "nearest" });
  }

  const currentIdx = ISHIHARA_IMAGES.findIndex(img => img.no === no);
  const pct = totalIsh > 0 ? ((currentIdx) / totalIsh) * 100 : 0;

  const progressBar = document.getElementById("ishProgressBar");
  const currentNo   = document.getElementById("ishCurrentNo");
  if (progressBar) progressBar.style.width = pct + "%";
  if (currentNo)   currentNo.textContent = no;

  updateIshiharaProgress();
}

function nextIshihara(currentNo) {
  const input = document.getElementById(`ishihara_${currentNo}`);
  if (!input || input.value.trim() === "") {
    showToast("⚠️ Masukkan jawaban terlebih dahulu (ketik 0 jika tidak terlihat).", "warning");
    input && input.focus();
    return;
  }
  const idx = ISHIHARA_IMAGES.findIndex(img => img.no === currentNo);
  if (idx < totalIsh - 1) {
    showIshiharaSlide(ISHIHARA_IMAGES[idx + 1].no);
  }
}

function prevIshihara(currentNo) {
  const idx = ISHIHARA_IMAGES.findIndex(img => img.no === currentNo);
  if (idx > 0) {
    showIshiharaSlide(ISHIHARA_IMAGES[idx - 1].no);
  }
}

function finishIshihara() {
  const lastInput = document.getElementById(`ishihara_${currentIsh}`);
  if (!lastInput || lastInput.value.trim() === "") {
    showToast("⚠️ Masukkan jawaban untuk gambar terakhir.", "warning");
    return;
  }

  // Cek semua Ishihara sudah dijawab
  const allAnswered = Array.from(
    document.querySelectorAll(".ishihara-answer")
  ).every(inp => inp.value.trim() !== "");

  if (!allAnswered) {
    showToast("⚠️ Ada beberapa gambar yang belum dijawab. Silakan isi semua.", "warning");
    return;
  }

  // Update progress bar ke 100%
  const pb = document.getElementById("ishProgressBar");
  if (pb) pb.style.width = "100%";

  showToast("✅ Tes Ishihara selesai!", "success");
  nextStep();
}

function updateIshiharaProgress() {
  const answered = Array.from(
    document.querySelectorAll(".ishihara-answer")
  ).filter(inp => inp.value.trim() !== "").length;

  const badge = document.getElementById("ishScore");
  if (badge) badge.textContent = `${answered} Terjawab`;
}

/* ════════════════════════════════════════════════════════════════════════
   RATING LABELS (Color Questions)
   ════════════════════════════════════════════════════════════════════════ */
const SCALE_LABELS = { 1: "Sangat Sulit", 2: "Sulit", 3: "Netral", 4: "Mudah", 5: "Sangat Mudah" };

function initRatingLabels() {
  const colors = ["merah", "hijau", "biru", "kuning", "orange", "ungu", "coklat"];
  colors.forEach(color => {
    const inputs = document.querySelectorAll(`input[name="color_${color}"]`);
    inputs.forEach(inp => {
      inp.addEventListener("change", () => {
        const label = document.getElementById(`label-${color}`);
        if (label) label.textContent = SCALE_LABELS[inp.value] || inp.value;
      });
      // Inisialisasi
      if (inp.checked) {
        const label = document.getElementById(`label-${color}`);
        if (label) label.textContent = SCALE_LABELS[inp.value] || inp.value;
      }
    });
  });
}

/* ════════════════════════════════════════════════════════════════════════
   RIASEC LIVE SCORES
   ════════════════════════════════════════════════════════════════════════ */
function initRIASECScores() {
  const dims = ["R", "I", "A", "S", "E", "C"];
  dims.forEach(dim => updateRIASECDim(dim));

  document.querySelectorAll(".riasec-input").forEach(input => {
    input.addEventListener("change", () => {
      updateRIASECDim(input.dataset.dim);
    });
  });
}

function updateRIASECDim(dim) {
  let total = 0;
  for (let i = 1; i <= 5; i++) {
    const checked = document.querySelector(
      `input[name="riasec_${dim}_${i}"]:checked`
    );
    total += checked ? parseInt(checked.value) : 3;
  }

  // Update badge
  const badge = document.getElementById(`score-badge-${dim}`);
  if (badge) badge.textContent = `Skor: ${total}`;

  // Update summary bar
  const bar = document.getElementById(`bar-${dim}`);
  if (bar) bar.style.width = (total / 25 * 100) + "%";

  const scoreEl = document.getElementById(`score-${dim}`);
  if (scoreEl) scoreEl.textContent = total;
}

/* ════════════════════════════════════════════════════════════════════════
   CAREER SEARCH
   ════════════════════════════════════════════════════════════════════════ */
function initCareerSearch() {
  const searchInput = document.getElementById("careerSearch");
  if (!searchInput) return;

  searchInput.addEventListener("input", () => {
    const query = searchInput.value.toLowerCase().trim();
    document.querySelectorAll(".career-option").forEach(opt => {
      const label = opt.dataset.career.toLowerCase();
      opt.classList.toggle("hidden", !label.includes(query));
    });
  });

  // Sync career radio to hidden select
  document.querySelectorAll(".career-radio").forEach(radio => {
    radio.addEventListener("change", () => {
      const sel = document.getElementById("karierSelect");
      if (sel) sel.value = radio.value;

      const msg = document.getElementById("careerValidationMsg");
      if (msg) msg.classList.add("d-none");
    });
  });
}

/* ════════════════════════════════════════════════════════════════════════
   WIZARD NAVIGATION
   ════════════════════════════════════════════════════════════════════════ */
function nextStep() {
  if (!validateStep(currentStep)) return;
  if (currentStep < TOTAL_STEPS) {
    currentStep++;
    updateWizard();
    if (currentStep === TOTAL_STEPS) populateReview();
    window.scrollTo({ top: 0, behavior: "smooth" });
  }
}

function prevStep() {
  if (currentStep > 1) {
    currentStep--;
    updateWizard();
    window.scrollTo({ top: 0, behavior: "smooth" });
  }
}

function updateWizard() {
  // Panes
  document.querySelectorAll(".wizard-pane").forEach(p => p.classList.remove("active"));
  const activePane = document.getElementById(`step-${currentStep}`);
  if (activePane) activePane.classList.add("active");

  // Step indicators
  document.querySelectorAll(".wizard-step").forEach((step, i) => {
    const stepNo = i / 2 + 1; // account for connectors
    step.classList.remove("active", "completed");
  });

  // Re-index (steps are every other child because of connectors)
  const steps = document.querySelectorAll(".wizard-step");
  steps.forEach((step, i) => {
    const no = parseInt(step.dataset.step);
    if (no < currentStep) step.classList.add("completed");
    else if (no === currentStep) step.classList.add("active");
  });

  // Progress bar
  const pct = (currentStep / TOTAL_STEPS) * 100;
  const fill = document.getElementById("progressFill");
  if (fill) fill.style.width = pct + "%";

  const txt = document.getElementById("progressText");
  if (txt) txt.textContent = `Langkah ${currentStep} dari ${TOTAL_STEPS}`;

  // Navigation buttons
  const prevBtn = document.getElementById("prevBtn");
  const nextBtn = document.getElementById("nextBtn");

  if (prevBtn) {
    prevBtn.style.display = currentStep > 1 ? "inline-flex" : "none";
  }
  if (nextBtn) {
    nextBtn.style.display = currentStep < TOTAL_STEPS ? "inline-flex" : "none";
  }

  // Jika di step 2 (Ishihara), reset ke slide pertama
  if (currentStep === 2 && totalIsh > 0) {
    showIshiharaSlide(ISHIHARA_IMAGES[0].no);
  }
}

/* ════════════════════════════════════════════════════════════════════════
   VALIDASI PER STEP
   ════════════════════════════════════════════════════════════════════════ */
function validateStep(step) {
  let valid = true;

  if (step === 1) {
    // Data Diri
    valid = validateFields(["nama", "usia", "pendidikan"]);
    if (valid) {
      const usia = parseInt(document.getElementById("usia").value);
      if (isNaN(usia) || usia < 15 || usia > 80) {
        setInvalid("usia", "Usia harus antara 15 hingga 80 tahun.");
        valid = false;
      }
    }
  }
  else if (step === 2) {
    // Ishihara – cek semua terjawab
    const allAnswers = Array.from(document.querySelectorAll(".ishihara-answer"));
    const unanswered = allAnswers.filter(inp => inp.value.trim() === "");
    if (unanswered.length > 0) {
      showToast(`⚠️ Masih ada ${unanswered.length} gambar yang belum dijawab.`, "warning");
      showIshiharaSlide(
        parseInt(unanswered[0].dataset.no)
      );
      valid = false;
    }
  }
  else if (step === 5) {
    // Karier
    const checked = document.querySelector(".career-radio:checked");
    if (!checked) {
      const msg = document.getElementById("careerValidationMsg");
      if (msg) msg.classList.remove("d-none");
      showToast("⚠️ Silakan pilih bidang karier.", "warning");
      valid = false;
    }
  }

  return valid;
}

function validateFields(ids) {
  let allValid = true;
  ids.forEach(id => {
    const el = document.getElementById(id);
    if (!el) return;
    if (!el.value.trim()) {
      el.classList.add("is-invalid");
      allValid = false;
    } else {
      el.classList.remove("is-invalid");
      el.classList.add("is-valid");
    }
    el.addEventListener("input", () => {
      if (el.value.trim()) {
        el.classList.remove("is-invalid");
        el.classList.add("is-valid");
      }
    }, { once: false });
  });
  return allValid;
}

function setInvalid(id, msg) {
  const el = document.getElementById(id);
  if (!el) return;
  el.classList.add("is-invalid");
  const feedback = el.closest(".col-md-6, .col-12")?.querySelector(".invalid-feedback");
  if (feedback) feedback.textContent = msg;
}

/* ════════════════════════════════════════════════════════════════════════
   REVIEW POPULATION (Step 6)
   ════════════════════════════════════════════════════════════════════════ */
const SCALE_LABELS_SHORT = { 1: "Sangat Sulit", 2: "Sulit", 3: "Netral", 4: "Mudah", 5: "Sangat Mudah" };
const SEVERITY_THRESHOLDS = [
  [85.71, "Normal"],
  [71.43, "Ringan"],
  [35.71, "Sedang"],
  [0,     "Berat"],
];

function populateReview() {
  // ── Data Diri ─────────────────────────────────────────────────────────
  setText("rv-nama",       document.getElementById("nama")?.value || "-");
  setText("rv-usia",       (document.getElementById("usia")?.value || "-") + " tahun");
  const jkVal = document.querySelector('input[name="jk"]:checked')?.value;
  setText("rv-jk",         jkVal === "L" ? "Laki-laki" : jkVal === "P" ? "Perempuan" : "-");
  setText("rv-pendidikan", document.getElementById("pendidikan")?.value || "-");
  const riwayat = document.querySelector('input[name="riwayat_keluarga"]:checked')?.value || "-";
  setText("rv-riwayat",    riwayat);
  const alat    = document.querySelector('input[name="alat_bantu"]:checked')?.value;
  setText("rv-alat",       alat === "1" ? "Ya" : "Tidak");
  const penyakit = document.querySelector('input[name="penyakit_mata"]:checked')?.value;
  setText("rv-penyakit",   penyakit === "1" ? "Ya" : "Tidak");

  // ── Ishihara Score ────────────────────────────────────────────────────
  const answers = Array.from(document.querySelectorAll(".ishihara-answer"));
  let correct = 0;
  answers.forEach(inp => {
    const no = parseInt(inp.dataset.no);
    const imgData = ISHIHARA_IMAGES.find(img => img.no === no);
    if (imgData && parseInt(inp.value) === imgData.answer) correct++;
  });
  const total = answers.length;
  const pct   = total > 0 ? ((correct / total) * 100).toFixed(2) : 0;

  setText("rv-ish-pct",    pct + "%");
  setText("rv-ish-detail", `${correct} benar dari ${total} gambar`);

  const severity   = getSeverity(parseFloat(pct));
  const sevEl      = document.getElementById("rv-ish-severity");
  if (sevEl) {
    sevEl.textContent = severity;
    sevEl.className   = `badge mt-2 ${getSeverityBadgeClass(severity)}`;
  }

  // Ring color
  const ring = document.getElementById("rvIshiharaRing");
  if (ring) {
    const gradient = parseFloat(pct) >= 85 ? "var(--gradient-green)"
                   : parseFloat(pct) >= 71 ? "var(--gradient-blue)"
                   : parseFloat(pct) >= 35 ? "var(--gradient-orange)"
                   : "linear-gradient(135deg,#EF4444,#DC2626)";
    ring.style.background = gradient;
  }

  // ── RIASEC ────────────────────────────────────────────────────────────
  const dims = ["R", "I", "A", "S", "E", "C"];
  const COLORS = {
    R: "#e74c3c", I: "#2980b9", A: "#8e44ad",
    S: "#27ae60", E: "#f39c12", C: "#16a085"
  };
  const miniContainer = document.getElementById("rv-riasec");
  if (miniContainer) {
    miniContainer.innerHTML = "";
    dims.forEach(dim => {
      let total = 0;
      for (let i = 1; i <= 5; i++) {
        const checked = document.querySelector(`input[name="riasec_${dim}_${i}"]:checked`);
        total += checked ? parseInt(checked.value) : 3;
      }
      const pctW = (total / 25 * 100).toFixed(0);
      miniContainer.innerHTML += `
        <div class="riasec-bar-item mb-2">
          <span class="riasec-dim-label">${dim}</span>
          <div class="progress flex-fill" style="height:8px; border-radius:99px;">
            <div class="progress-bar" style="width:${pctW}%; background:${COLORS[dim]}; border-radius:99px;"></div>
          </div>
          <span class="riasec-dim-score">${total}</span>
        </div>`;
    });
  }

  // ── Karier ────────────────────────────────────────────────────────────
  const career = document.querySelector(".career-radio:checked")?.value || "-";
  setText("rv-karier", career);
}

function getSeverity(pct) {
  if (pct >= 85.71) return "Normal";
  if (pct >= 71.43) return "Ringan";
  if (pct >= 35.71) return "Sedang";
  return "Berat";
}

function getSeverityBadgeClass(severity) {
  const map = { Normal: "bg-success", Ringan: "bg-info", Sedang: "bg-warning text-dark", Berat: "bg-danger" };
  return map[severity] || "bg-secondary";
}

function setText(id, val) {
  const el = document.getElementById(id);
  if (el) el.textContent = val;
}

/* ════════════════════════════════════════════════════════════════════════
   FORM SUBMIT & LOADING
   ════════════════════════════════════════════════════════════════════════ */
function initFormSubmit() {
  const form   = document.getElementById("screeningForm");
  const overlay = document.getElementById("loadingOverlay");
  if (!form) return;

  form.addEventListener("submit", (e) => {
    // Final validation
    const career = document.querySelector(".career-radio:checked");
    if (!career) {
      e.preventDefault();
      showToast("⚠️ Silakan pilih bidang karier.", "warning");
      return;
    }

    // Show loading overlay
    if (overlay) {
      overlay.classList.add("show");
      animateLoadingSteps();
    }

    // Disable submit button
    const btn = document.getElementById("submitBtn");
    if (btn) {
      btn.disabled = true;
      document.getElementById("submitSpinner")?.classList.remove("d-none");
      document.getElementById("submitIcon")?.classList.add("d-none");
    }
  });
}

function animateLoadingSteps() {
  const stepIds = ["ls-1", "ls-2", "ls-3", "ls-4"];
  const icons   = ["✓", "✓", "✓", "✓"];
  const activeIcon = "◌";

  stepIds.forEach((id, i) => {
    setTimeout(() => {
      // Mark previous as done
      if (i > 0) {
        const prev = document.getElementById(stepIds[i - 1]);
        if (prev) {
          prev.classList.remove("active");
          prev.classList.add("done");
          prev.textContent = `✓ ${prev.textContent.replace(/^[◌✓]\s*/, "")}`;
        }
      }
      // Mark current as active
      const el = document.getElementById(id);
      if (el) {
        el.classList.add("active");
        el.textContent = el.textContent.replace("◌", "◌");
      }
    }, i * 600);
  });
}

/* ════════════════════════════════════════════════════════════════════════
   TOAST NOTIFICATION
   ════════════════════════════════════════════════════════════════════════ */
function showToast(message, type = "info") {
  // Remove existing
  document.querySelectorAll(".custom-toast").forEach(t => t.remove());

  const colors = {
    success: "#10B981", warning: "#F59E0B",
    danger:  "#EF4444", info:    "#3B82F6"
  };
  const icons = {
    success: "bi-check-circle-fill", warning: "bi-exclamation-triangle-fill",
    danger:  "bi-x-circle-fill",     info:    "bi-info-circle-fill"
  };

  const toast = document.createElement("div");
  toast.className = "custom-toast";
  toast.innerHTML = `
    <i class="bi ${icons[type] || icons.info}" style="color:${colors[type]}"></i>
    <span>${message}</span>
  `;
  toast.style.cssText = `
    position: fixed;
    top: 80px;
    right: 20px;
    z-index: 9999;
    background: var(--bg-card);
    border: 1px solid var(--border);
    border-left: 4px solid ${colors[type] || colors.info};
    border-radius: 12px;
    padding: 14px 20px;
    display: flex;
    align-items: center;
    gap: 10px;
    font-size: 0.9rem;
    font-weight: 500;
    box-shadow: 0 8px 24px rgba(0,0,0,0.12);
    max-width: 360px;
    animation: slideInRight 0.4s ease both;
    color: var(--text-primary);
  `;

  document.body.appendChild(toast);

  setTimeout(() => {
    toast.style.animation = "slideOutRight 0.3s ease both";
    setTimeout(() => toast.remove(), 350);
  }, 3500);
}

// Inject keyframes for toast
const toastStyle = document.createElement("style");
toastStyle.textContent = `
  @keyframes slideInRight {
    from { opacity:0; transform:translateX(100%); }
    to   { opacity:1; transform:translateX(0); }
  }
  @keyframes slideOutRight {
    from { opacity:1; transform:translateX(0); }
    to   { opacity:0; transform:translateX(100%); }
  }
`;
document.head.appendChild(toastStyle);
