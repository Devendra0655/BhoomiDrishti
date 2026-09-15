// ===================================================================
// BHOOMIDRISHTI — APP LOGIC
// Vanilla JS: screen routing, real backend fetch calls, i18n
// ===================================================================

const API_BASE = 'https://bhoomidrishti-backend-qqd9.onrender.com';

const DISTRICT_LABELS = {
  Amravati: { mr: 'अमरावती', en: 'Amravati' },
  Akola: { mr: 'अकोला', en: 'Akola' },
  Bhandara: { mr: 'भंडारा', en: 'Bhandara' },
  Buldhana: { mr: 'बुलढाणा', en: 'Buldhana' },
  Chandrapur: { mr: 'चंद्रपूर', en: 'Chandrapur' },
  Gadchiroli: { mr: 'गडचिरोली', en: 'Gadchiroli' },
  Gondia: { mr: 'गोंदिया', en: 'Gondia' },
  Nagpur: { mr: 'नागपूर', en: 'Nagpur' },
  Wardha: { mr: 'वर्धा', en: 'Wardha' },
  Washim: { mr: 'वाशिम', en: 'Washim' },
  Yavatmal: { mr: 'यवतमाळ', en: 'Yavatmal' }
};

const CROP_LABELS = {
  Cotton: { mr: 'कापूस', en: 'Cotton' },
  Soybean: { mr: 'सोयाबीन', en: 'Soybean' },
  Orange: { mr: 'संत्रा', en: 'Orange' },
  'Tur Dal': { mr: 'तूर डाळ', en: 'Tur Dal' },
  Wheat: { mr: 'गहू', en: 'Wheat' }
};

// Frontend display value -> backend crop key. Every backend file (thresholds,
// XGBoost, crop windows) uses "Tur", not "Tur Dal" - translate here so neither
// side needs renaming.
const CROP_API_NAME = {
  Cotton: 'Cotton', Soybean: 'Soybean', Orange: 'Orange', 'Tur Dal': 'Tur', Wheat: 'Wheat'
};

const BAND_LABELS = {
  Low: { mr: 'कमी', en: 'Low' },
  Moderate: { mr: 'मध्यम', en: 'Moderate' },
  Severe: { mr: 'गंभीर', en: 'Severe' }
};

const STRESS_LEVEL_PREFIX = { mr: 'ताण पातळी', en: 'Stress Level' };
const NO_DATA_TEXT = { mr: 'या निवडीसाठी सध्या माहिती उपलब्ध नाही.', en: 'No data available for this selection right now.' };
const OFFLINE_TEXT = { mr: 'ऑफलाइन — शेवटची जतन केलेली माहिती दाखवत आहोत', en: 'Offline — showing last cached advisory' };

const GAUGE_CIRCUMFERENCE = 2 * Math.PI * 85; // r=85
const CACHE_KEY = 'bhoomidrishti_last_advisory';

let state = { district: null, crop: null };
let currentLang = 'mr';

function getQueryParam(name) {
  return new URLSearchParams(window.location.search).get(name);
}

// ---------- Screen routing ----------
function showScreen(id) {
  document.querySelectorAll('.screen').forEach(s => s.classList.remove('active'));
  const target = document.getElementById(id);
  if (target) target.classList.add('active');
  window.scrollTo(0, 0);
}

// ---------- API layer ----------
async function apiGet(path) {
  const res = await fetch(API_BASE + path);
  if (!res.ok) {
    const body = await res.json().catch(() => ({}));
    throw new Error(body.detail || `Request failed: ${res.status}`);
  }
  return res.json();
}

function buildQuery(asOfDate) {
  return asOfDate ? `?as_of_date=${encodeURIComponent(asOfDate)}` : '';
}

async function fetchCahsi(district, crop, asOfDate) {
  return apiGet(`/cahsi/${district}/${crop}${buildQuery(asOfDate)}`);
}

async function fetchAdvisory(district, crop, asOfDate) {
  return apiGet(`/advisory/${district}/${crop}${buildQuery(asOfDate)}`);
}

async function fetchCropCalendar(crop, asOfDate) {
  return apiGet(`/crop-calendar/${crop}${buildQuery(asOfDate)}`);
}

async function fetchValidationHistory(district, crop) {
  return apiGet(`/validation-history/${district}/${crop}`);
}

// ---------- Splash auto-advance + demo URL param handling ----------
window.addEventListener('DOMContentLoaded', () => {
  initSelectors();
  initNavigation();
  initHeatmap();
  initLangToggle();
  initOfflineBanner();
  initSpeakButton();
  initShareButton();

  const demoDistrict = getQueryParam('district');
  const demoCrop = getQueryParam('crop');
  const demoDate = getQueryParam('as_of_date');

  setTimeout(() => {
    if (demoDistrict && demoCrop) {
      document.getElementById('district-select').value = demoDistrict;
      document.getElementById('crop-select').value = demoCrop;
      state.district = demoDistrict;
      state.crop = demoCrop;
      state.asOfDate = demoDate || null;
      populateStatusScreen(demoDistrict, demoCrop, demoDate);
      showScreen('screen-2');
    } else {
      showScreen('screen-1');
    }
  }, 2000);
});

// ---------- Screen 1: selectors ----------
function initSelectors() {
  const districtSelect = document.getElementById('district-select');
  const cropSelect = document.getElementById('crop-select');
  const checkBtn = document.getElementById('check-status-btn');

  function validate() {
    checkBtn.disabled = !(districtSelect.value && cropSelect.value);
  }

  districtSelect.addEventListener('change', validate);
  cropSelect.addEventListener('change', validate);

  checkBtn.addEventListener('click', () => {
    state.district = districtSelect.value;
    state.crop = cropSelect.value;
    state.asOfDate = null;
    populateStatusScreen(state.district, state.crop, null);
    showScreen('screen-2');
  });

  document.getElementById('goto-heatmap').addEventListener('click', () => showScreen('screen-4'));
}

// ---------- Screen 2: CAHSI status (real backend call) ----------
async function populateStatusScreen(district, crop, asOfDate) {
  const apiCrop = CROP_API_NAME[crop] || crop;

  document.getElementById('status-district').textContent = DISTRICT_LABELS[district][currentLang];
  document.getElementById('status-crop').textContent = CROP_LABELS[crop][currentLang];
  document.getElementById('calendar-crop').textContent = CROP_LABELS[crop][currentLang];

  const number = document.getElementById('cahsi-number');
  const label = document.getElementById('cahsi-label');
  const fill = document.getElementById('gauge-fill');
  const reasonText = document.getElementById('reason-text');
  const advisoryText = document.getElementById('advisory-text');
  const lastUpdated = document.getElementById('last-updated');

  number.textContent = '…';
  advisoryText.textContent = '…';

  try {
    const [cahsiData, advisoryData] = await Promise.all([
      fetchCahsi(district, apiCrop, asOfDate),
      fetchAdvisory(district, apiCrop, asOfDate),
    ]);

    const bandColors = { Low: 'var(--low)', Moderate: 'var(--moderate)', Severe: 'var(--severe)' };
    const score = cahsiData.cahsi_score;
    const severity = cahsiData.severity;

    state.severity = severity;
    state.cahsiData = cahsiData;
    state.advisoryData = advisoryData;

    number.textContent = score;
    label.textContent = `${STRESS_LEVEL_PREFIX[currentLang]}: ${BAND_LABELS[severity][currentLang]}`;
    reasonText.textContent = advisoryData.reason_text;
    advisoryText.textContent = advisoryData.advisory_text;
    lastUpdated.textContent = (currentLang === 'en' ? 'Last updated: ' : 'शेवटचे अपडेट: ') + advisoryData.last_updated;

    fill.style.stroke = bandColors[severity];

    // Normalize -2..+2 CAHSI range onto a 0-100 gauge fill (severe = fuller arc)
    const normalized = Math.max(0, Math.min(1, (2 - score) / 4));
    fill.style.strokeDashoffset = GAUGE_CIRCUMFERENCE;
    requestAnimationFrame(() => {
      requestAnimationFrame(() => {
        fill.style.strokeDashoffset = GAUGE_CIRCUMFERENCE * (1 - normalized);
      });
    });

    drawSparkline(cahsiData);

    localStorage.setItem(CACHE_KEY, JSON.stringify({ district, crop, cahsiData, advisoryData }));
  } catch (err) {
    number.textContent = '—';
    advisoryText.textContent = NO_DATA_TEXT[currentLang];
    reasonText.textContent = '';
    lastUpdated.textContent = '';
    document.getElementById('cahsi-sparkline').innerHTML = '';
    console.error(err);
  }

  populateValidationPanel(district, apiCrop);
}

// ---------- CAHSI trend sparkline (Addition 3) ----------
function drawSparkline(cahsiData) {
  const svg = document.getElementById('cahsi-sparkline');
  const points = [cahsiData.cahsi_lag3, cahsiData.cahsi_lag2, cahsiData.cahsi_lag1, cahsiData.cahsi_score];

  if (points.some(v => v === undefined || v === null || Number.isNaN(v))) {
    svg.innerHTML = '';
    return;
  }

  const min = Math.min(...points);
  const max = Math.max(...points);
  const range = max - min || 1; // avoid divide-by-zero when all values are equal
  const width = 100, height = 30, pad = 3;

  const coords = points.map((v, i) => {
    const x = pad + (i / (points.length - 1)) * (width - pad * 2);
    const y = height - pad - ((v - min) / range) * (height - pad * 2);
    return [x, y];
  });

  const polylinePoints = coords.map(([x, y]) => `${x},${y}`).join(' ');
  const [lastX, lastY] = coords[coords.length - 1];

  svg.innerHTML =
    `<polyline points="${polylinePoints}"/>` +
    `<circle cx="${lastX}" cy="${lastY}" r="2.5"/>`;
}
async function populateValidationPanel(district, apiCrop) {
  const panel = document.getElementById('validation-panel');
  const text = document.getElementById('validation-text');
  panel.hidden = true;

  try {
    const records = await fetchValidationHistory(district, apiCrop);
    if (!records || records.length === 0) return;

    const best = records[0]; // backend sorts by lead_time_weeks descending
    const monthYear = new Intl.DateTimeFormat(currentLang === 'en' ? 'en-IN' : 'mr-IN', {
      month: 'long', year: 'numeric'
    }).format(new Date(best.first_severe_date));
    const weeks = Number(best.lead_time_weeks).toFixed(1);

    text.textContent = currentLang === 'en'
      ? `This system was accurate in ${monthYear} — ${weeks} weeks before the official declaration.`
      : `यापूर्वी हे यंत्र ${monthYear} मध्ये अचूक ठरले — सरकारी घोषणेच्या ${weeks} आठवडे आधी.`;

    panel.hidden = false;
  } catch (err) {
    console.error(err);
    // stays hidden on any failure - never shows an empty/error state
  }
}

// ---------- Screen 3: crop calendar (real backend call) ----------
async function populateCropCalendar(crop, asOfDate) {
  const apiCrop = CROP_API_NAME[crop] || crop;
  try {
    const data = await fetchCropCalendar(apiCrop, asOfDate);
    document.getElementById('timeline-sowing').textContent = data.sowing_window;
    document.getElementById('timeline-critical').textContent = data.critical_stage;
    document.getElementById('timeline-guidance').textContent = data.critical_stage_guidance;
    document.getElementById('timeline-harvest').textContent = data.harvest_window;

    document.querySelectorAll('.timeline-node').forEach(n => n.classList.remove('active-stage'));
    document.querySelectorAll('.here-marker').forEach(m => m.remove());

    const stageMap = { sowing: 'sowing', growth: 'growth', harvest: 'harvest' };
    const activeKey = data.current_stage.includes('harvest') ? 'harvest'
                     : data.current_stage.includes('sowing') ? 'sowing' : 'growth';
    const activeNode = document.querySelector(`.timeline-node[data-stage="${stageMap[activeKey]}"]`);
    if (activeNode) {
      activeNode.classList.add('active-stage');
      const marker = document.createElement('span');
      marker.className = 'here-marker';
      marker.dataset.en = 'You are here';
      marker.textContent = currentLang === 'en' ? 'You are here' : 'आपण येथे आहात';
      activeNode.querySelector('.node-dot').appendChild(marker);
    }
  } catch (err) {
    console.error(err);
  }
}

// ---------- Navigation ----------
function initNavigation() {
  document.querySelectorAll('.back-btn').forEach(btn => {
    btn.addEventListener('click', () => showScreen(btn.dataset.target));
  });
  document.getElementById('goto-calendar').addEventListener('click', () => {
    populateCropCalendar(state.crop, state.asOfDate);
    showScreen('screen-3');
  });
  document.getElementById('goto-home').addEventListener('click', () => showScreen('screen-1'));
}

// ---------- Screen 4: heatmap (real backend calls, one per district) ----------
async function initHeatmap() {
  const grid = document.getElementById('heatmap-grid');
  const districts = Object.keys(DISTRICT_LABELS);
  const referenceCrop = 'Cotton'; // fixed reference crop for the overview map, per PRD Section 7 item 4

  grid.innerHTML = '';
  districts.forEach(d => {
    const block = document.createElement('div');
    block.className = 'heat-block loading';
    block.dataset.district = d;
    block.innerHTML = `<span>${DISTRICT_LABELS[d][currentLang]}</span>`;
    block.addEventListener('click', () => {
      document.getElementById('district-select').value = d;
      document.getElementById('check-status-btn').disabled = !document.getElementById('crop-select').value;
      showScreen('screen-1');
    });
    grid.appendChild(block);
  });

  const results = await Promise.allSettled(districts.map(d => fetchCahsi(d, referenceCrop, null)));
  results.forEach((result, i) => {
    const d = districts[i];
    const block = grid.querySelector(`.heat-block[data-district="${d}"]`);
    block.classList.remove('loading');
    if (result.status === 'fulfilled') {
      block.classList.add(result.value.severity.toLowerCase());
    } else {
      block.classList.add('error');
    }
  });
}

function refreshHeatmapLabels() {
  document.querySelectorAll('#heatmap-grid .heat-block').forEach(block => {
    const d = block.dataset.district;
    block.querySelector('span').textContent = DISTRICT_LABELS[d][currentLang];
  });
}

// ---------- Offline resilience (PRD Section 5) ----------
function initOfflineBanner() {
  const banner = document.createElement('div');
  banner.className = 'offline-banner';
  banner.textContent = OFFLINE_TEXT[currentLang];
  document.body.prepend(banner);

  function updateStatus() {
    if (!navigator.onLine) {
      banner.textContent = OFFLINE_TEXT[currentLang];
      banner.classList.add('show');
      const cached = localStorage.getItem(CACHE_KEY);
      if (cached) {
        const { district, crop, cahsiData, advisoryData } = JSON.parse(cached);
        state.district = district; state.crop = crop;
        document.getElementById('status-district').textContent = DISTRICT_LABELS[district][currentLang];
        document.getElementById('status-crop').textContent = CROP_LABELS[crop][currentLang];
        document.getElementById('cahsi-number').textContent = cahsiData.cahsi_score;
        document.getElementById('reason-text').textContent = advisoryData.reason_text;
        document.getElementById('advisory-text').textContent = advisoryData.advisory_text;
        showScreen('screen-2');
      }
    } else {
      banner.classList.remove('show');
    }
  }

  window.addEventListener('online', updateStatus);
  window.addEventListener('offline', updateStatus);
}

// ---------- Language toggle ----------
function initLangToggle() {
  const toggle = document.getElementById('lang-toggle');
  toggle.addEventListener('click', () => {
    currentLang = currentLang === 'mr' ? 'en' : 'mr';
    toggle.classList.toggle('lang-en', currentLang === 'en');

    toggle.classList.remove('pulse');
    void toggle.offsetWidth;
    toggle.classList.add('pulse');

    applyStaticTranslations();
    refreshHeatmapLabels();

    if (state.district && state.crop) {
      populateStatusScreen(state.district, state.crop, state.asOfDate);
    }
  });
}

function applyStaticTranslations() {
  document.querySelectorAll('[data-en]').forEach(el => {
    if (!el.dataset.mr) el.dataset.mr = el.textContent;
    el.textContent = currentLang === 'en' ? el.dataset.en : el.dataset.mr;
  });
  document.querySelectorAll('[data-aria-en]').forEach(el => {
    if (!el.dataset.ariaMr) el.dataset.ariaMr = el.getAttribute('aria-label');
    el.setAttribute('aria-label', currentLang === 'en' ? el.dataset.ariaEn : el.dataset.ariaMr);
  });
}

// ---------- Text-to-speech (Addition 2) ----------
function speakAdvisory(text) {
  if (!('speechSynthesis' in window) || !text) return;
  const btn = document.getElementById('speak-btn');
  const utterance = new SpeechSynthesisUtterance(text);
  utterance.lang = currentLang === 'en' ? 'en-IN' : 'mr-IN';
  utterance.onstart = () => btn.classList.add('speaking');
  utterance.onend = () => btn.classList.remove('speaking');
  utterance.onerror = () => btn.classList.remove('speaking');
  speechSynthesis.cancel();
  speechSynthesis.speak(utterance);
}

function initSpeakButton() {
  document.getElementById('speak-btn').addEventListener('click', () => {
    const text = document.getElementById('advisory-text').textContent;
    speakAdvisory(text);
  });
}

// ---------- WhatsApp share (Addition 4, Version A — wa.me link only) ----------
function shareToWhatsApp(district, crop, advisoryText) {
  const message = `BhoomiDrishti — ${district}, ${crop}:\n\n${advisoryText}`;
  const encodedMessage = encodeURIComponent(message);
  window.open(`https://wa.me/?text=${encodedMessage}`, '_blank');
}

function initShareButton() {
  document.getElementById('share-btn').addEventListener('click', () => {
    const districtLabel = document.getElementById('status-district').textContent;
    const cropLabel = document.getElementById('status-crop').textContent;
    const advisoryText = document.getElementById('advisory-text').textContent;
    shareToWhatsApp(districtLabel, cropLabel, advisoryText);
  });
}