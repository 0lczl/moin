'use strict';

const main = document.getElementById('content');
const make = (tag, className, value) => {
  const el = document.createElement(tag);
  if (className) el.className = className;
  if (value !== undefined) el.textContent = value;
  return el;
};
const tr = (en, ar) => locale === 'ar' ? ar : en;
const nameOf = value => value?.[locale] || value?.en || '';
const videoUrl = id => `/haramain/video/${id}`;
const mosqueUrl = id => `/haramain/${id}`;
const duration = seconds => `${Math.floor(seconds / 60)}:${String(seconds % 60).padStart(2, '0')}`;
let locale = MoinLocale.read();
let catalog = null;
let token = '';
let pollTimer = null;
let currentVideo = null;
let activeLanguage = 'arabic';
let activeSpeechAudio = null;
let publicMode = null;

const copy = {
  en: {
    header: 'HARAMAIN VIDEO CENTER', studio: 'Recording studio', center: 'Haramain videos', liveTranslator: 'Live translator',
    workspace: 'YOUR WORKSPACE',
    homeTitle: 'From the two holy mosques, closer to understanding.',
    homeIntro: 'Choose a mosque and browse lessons in your language.',
    choose: 'Choose a mosque', recorded: 'Recorded lessons', imams: 'Featured scholars',
    expansion: 'More scholars and official sources will be added.',
    live: 'Official broadcast', archive: 'Previous videos', all: 'All scholars',
    noLive: 'No live broadcast is currently verified for this mosque.',
    noLiveDetail: 'Previous recordings are available below.',
    liveAvailable: 'Open official broadcast', checked: 'Verified',
    liveCaution: 'The broadcast opens from its official source.',
    source: 'Source', official: 'Official source', openSource: 'Open original video',
    read: 'Open in Moin', back: 'Back to collection', processing: 'Processing',
    empty: 'No recordings for this scholar yet. Choose another scholar or view all.',
    noVideos: 'No recordings are in this mosque’s catalog yet.',
    unavailable: 'This recording is temporarily unavailable for processing. You can check its official source.',
    tooLong: 'This recording is longer than the current five-minute processing limit. Open the original video instead.',
    queueFull: 'The processing queue is full. Wait for a recording to finish, then try again.',
    reload: 'The session expired. Refresh the page and try again.',
    ready: 'Ready to read', start: 'Prepare transcript and translations',
    waiting: 'Waiting in the processing queue', working: 'Transcribing, translating, and preparing speech',
    importingProgress: 'Importing the official recording', preparingAudio: 'Preparing audio', audioPrepared: 'Audio prepared',
    transcribing: 'Transcribing and translating', safetyCheck: 'Checking translation safety', preparingSpeech: 'Preparing speech',
    segmentComplete: 'Segment complete', segmentProgress: 'Segment', of: 'of', segments: 'segments',
    failed: 'This recording could not be prepared. Check the official source or try again.',
    sourceMismatch: 'This recording no longer matches its approved publishing channel. Check the official source.',
    interrupted: 'Processing stopped. Try again.', retry: 'Try processing again',
    partial: 'Some passages could not be translated. Read the available text and check the original audio.',
    original: 'Original Arabic audio', language: 'Reading language', arabic: 'العربية', english: 'English', french: 'Français',
    listen: 'Listen to this translation', pause: 'Pause translation',
    noSpeech: 'Speech is unavailable for this passage. The text remains available.',
    noText: 'Text is unavailable for this passage.',
    caution: 'Machine-generated wording may contain errors. Check important meanings against the original Arabic audio.',
    sourceFailure: 'The source could not be imported or processed. Please use the official link and try later.',
    sourceBlocked: 'YouTube blocked this server from importing the lesson. Open the original video or upload a recording in the Studio.',
    catalogFailure: 'The Haramain collection is unavailable. Please refresh the page or try again later.',
    noTranslation: 'Translation is unavailable for this passage. Please check the original Arabic audio.',
    credentialMissing: 'Translation needs DeepL to be configured. Once it is available, prepare this lesson again.',
    retryTranslations: 'Prepare translations and speech again',
    fullEnglish: 'Full English audio', fullFrench: 'Full French audio',
    partialNote: 'Translation is experimental and should be reviewed for religious meaning.',
    count: 'recordings', photoUnavailable: 'Photo unavailable',
  },
  ar: {
    header: 'مركز فيديو الحرمين', studio: 'استديو التسجيل', center: 'فيديوهات الحرمين', liveTranslator: 'المترجم المباشر',
    workspace: 'مساحة العمل',
    homeTitle: 'من الحرمين الشريفين إلى فهمٍ أقرب.',
    homeIntro: 'إختر المسجد، وتصفح الدروس بلغتك!',
    choose: 'اختر المسجد', recorded: 'دروس مسجلة', imams: 'المشايخ المختارون',
    expansion: 'سنضيف مزيدًا من المشايخ والمصادر الرسمية لاحقًا.',
    live: 'البث الرسمي', archive: 'الفيديوهات السابقة', all: 'جميع المشايخ',
    noLive: 'لا يوجد بث مباشر متحقق منه حاليًا لهذا المسجد.',
    noLiveDetail: 'التسجيلات السابقة متاحة أدناه.',
    liveAvailable: 'افتح البث الرسمي', checked: 'تم التحقق',
    liveCaution: 'يفتح البث من مصدره الرسمي.',
    source: 'المصدر', official: 'المصدر الرسمي', openSource: 'افتح الفيديو الأصلي',
    read: 'افتح في مُعين', back: 'العودة للمجموعة', processing: 'جارٍ المعالجة',
    empty: 'لا توجد تسجيلات لهذا الشيخ بعد. اختر شيخًا آخر أو اعرض الجميع.',
    noVideos: 'لا توجد تسجيلات في فهرس هذا المسجد بعد.',
    unavailable: 'هذا التسجيل غير متاح للمعالجة حاليًا. يمكنك الاطلاع على مصدره الرسمي.',
    tooLong: 'هذا التسجيل أطول من حد المعالجة الحالي، وهو خمس دقائق. افتح الفيديو الأصلي بدلًا من ذلك.',
    queueFull: 'قائمة المعالجة ممتلئة. انتظر اكتمال تسجيل ثم حاول مرة أخرى.',
    reload: 'انتهت الجلسة. حدّث الصفحة ثم حاول مرة أخرى.',
    ready: 'جاهز للقراءة', start: 'جهّز النص والترجمة',
    waiting: 'بانتظار المعالجة', working: 'جارٍ إعداد النص والترجمة والصوت',
    importingProgress: 'جارٍ استيراد التسجيل الرسمي', preparingAudio: 'جارٍ تجهيز الصوت', audioPrepared: 'تم تجهيز الصوت',
    transcribing: 'جارٍ التعرّف على الكلام وترجمته', safetyCheck: 'جارٍ التحقق من سلامة الترجمة', preparingSpeech: 'جارٍ تجهيز الصوت المترجم',
    segmentComplete: 'اكتمل المقطع', segmentProgress: 'المقطع', of: 'من', segments: 'مقاطع',
    failed: 'تعذر تجهيز التسجيل. تحقق من المصدر الرسمي أو حاول مرة أخرى.',
    sourceMismatch: 'لم يعد التسجيل مطابقًا للقناة المؤسسية المعتمدة. تحقق من المصدر الرسمي.',
    interrupted: 'توقفت المعالجة. حاول مرة أخرى.', retry: 'أعد المعالجة',
    partial: 'تعذرت ترجمة بعض المقاطع. اقرأ المتاح وقارنه بالصوت العربي.',
    original: 'الصوت العربي الأصلي', language: 'لغة القراءة', arabic: 'العربية', english: 'English', french: 'Français',
    listen: 'استمع إلى هذه الترجمة', pause: 'أوقف الترجمة مؤقتًا',
    noSpeech: 'الصوت غير متاح لهذا المقطع. النص متاح للقراءة.',
    noText: 'النص غير متاح لهذا المقطع.',
    caution: 'قد يحتوي النص الآلي على أخطاء. راجع المعاني المهمة بمقارنتها بالصوت العربي الأصلي.',
    sourceFailure: 'تعذر استيراد المصدر أو معالجته. افتح الرابط الرسمي وحاول لاحقًا.',
    sourceBlocked: 'حجب يوتيوب استيراد الدرس على هذا الخادم. افتح الفيديو الأصلي أو ارفع تسجيلًا في الاستوديو.',
    catalogFailure: 'مجموعة الحرمين غير متاحة حاليًا. حدّث الصفحة أو حاول لاحقًا.',
    noTranslation: 'لا تتوفر ترجمة لهذا المقطع. استمع إلى الصوت العربي الأصلي.',
    credentialMissing: 'تحتاج الترجمة إلى ضبط مفتاح DeepL. أعد إعداد الدرس بعد توفيره.',
    retryTranslations: 'أعد إعداد الترجمة والصوت',
    fullEnglish: 'الصوت الإنجليزي كاملًا', fullFrench: 'الصوت الفرنسي كاملًا',
    partialNote: 'الترجمة تجريبية، وتحتاج إلى مراجعة المعنى الشرعي.',
    count: 'تسجيلات', photoUnavailable: 'الصورة غير متاحة',
  },
};
const t = key => copy[locale][key];

function applyLocale() {
  document.documentElement.lang = locale;
  document.documentElement.dir = locale === 'ar' ? 'rtl' : 'ltr';
  document.title = `${locale === 'ar' ? 'مُعين — مركز فيديو الحرمين' : 'Moin — Haramain Video Center'}`;
  document.getElementById('header-center').textContent = t('header');
  document.getElementById('workspace-label').textContent = t('workspace');
  document.getElementById('studio-label').textContent = t('studio');
  document.getElementById('haramain-label').textContent = t('center');
  document.getElementById('live-label').textContent = t('liveTranslator');
  document.querySelector('.skip-link').textContent = tr('Skip to content', 'انتقل إلى المحتوى');
  document.querySelector('.sidebar').setAttribute('aria-label', tr('Workspace navigation', 'التنقل في مساحة العمل'));
  document.querySelector('.sidebar-nav').setAttribute('aria-label', tr('Workspace', 'مساحة العمل'));
  document.querySelector('.locale-switch').setAttribute('aria-label', tr('Interface language', 'لغة الواجهة'));
  document.querySelector('.brand').setAttribute('aria-label', tr('Moin home', 'مُعين، الصفحة الرئيسية'));
  document.querySelectorAll('#studio-label, #haramain-label, #live-label').forEach(label => { label.lang = locale; label.dir = locale === 'ar' ? 'rtl' : 'ltr'; });
  for (const button of document.querySelectorAll('[data-locale]')) button.setAttribute('aria-pressed', String(button.dataset.locale === locale));
}

function link(text, href, className = '') {
  const a = make('a', className, text);
  a.href = href;
  return a;
}
function external(text, href, className = '') {
  const a = link(text, href, className);
  a.target = '_blank';
  a.rel = 'noopener noreferrer';
  return a;
}
function go(path) {
  if (location.pathname + location.search !== path) history.pushState({}, '', path);
  render();
  window.scrollTo({ top: 0, behavior: 'instant' });
}
function internal(a) {
  a.addEventListener('click', event => {
    if (event.button || event.metaKey || event.ctrlKey || event.shiftKey || event.altKey) return;
    event.preventDefault();
    go(a.getAttribute('href'));
  });
  return a;
}
function heading(text, className = '') { return make('h1', className, text); }
function eyebrow(text) { return make('p', 'section-label', text); }
function breadcrumb(parts) {
  const nav = make('nav', 'breadcrumb');
  nav.setAttribute('aria-label', tr('Page path', 'مسار الصفحة'));
  const list = make('ol');
  for (const part of parts) {
    const item = make('li');
    if (part.href) item.append(internal(link(part.text, part.href)));
    else {
      const current = make('span', '', part.text);
      current.setAttribute('aria-current', 'page');
      item.append(current);
    }
    list.append(item);
  }
  nav.append(list);
  return nav;
}
function titleRow(title, count) {
  const row = make('div', 'section-row');
  row.append(make('h2', '', title));
  if (count !== undefined) row.append(make('span', 'section-count', `${count} ${t('count')}`));
  return row;
}
function iconArrow() {
  const span = make('span', 'arrow');
  span.setAttribute('aria-hidden', 'true');
  span.innerHTML = '<svg viewBox="0 0 24 24" fill="none" stroke="currentColor" stroke-width="1.7" aria-hidden="true"><path d="M5 12h14m-6-6 6 6-6 6"/></svg>';
  return span;
}
function renderHome() {
  const hero = make('section', 'home-hero');
  const headline = make('div', 'hero-copy');
  headline.append(heading(t('homeTitle')), make('p', 'hero-description', t('homeIntro')));
  hero.append(headline);
  const locations = make('div', 'location-grid');
  for (const mosque of catalog.mosques) {
    const card = internal(link('', mosqueUrl(mosque.id), `location-card location-${mosque.id}`));
    const metadata = make('div', 'location-meta');
    metadata.append(make('span', '', nameOf(mosque.city)));
    card.append(metadata, make('h2', '', nameOf(mosque.name)));
    const bottom = make('div', 'location-bottom');
    bottom.append(make('span', '', t('choose')), iconArrow());
    card.append(bottom);
    locations.append(card);
  }
  const intro = make('div', 'home-collection-line');
  intro.append(make('span', '', t('expansion')));
  main.append(breadcrumb([{text: t('center')}]), hero, locations, intro);
}

function broadcastSection(mosqueId) {
  const item = catalog.broadcasts.find(b => b.mosque_id === mosqueId);
  const wrap = make('section', 'broadcast-section');
  wrap.append(titleRow(t('live')));
  const panel = make('div', 'broadcast-panel');
  const signal = make('span', `broadcast-indicator ${item?.state === 'available' ? 'on' : ''}`);
  signal.setAttribute('aria-hidden', 'true');
  const body = make('div', 'broadcast-body');
  if (item?.state === 'available') {
    body.append(make('h3', '', t('liveAvailable')));
    body.append(make('p', '', `${t('checked')}: ${item.verified_at}`));
    panel.append(signal, body, external(t('liveAvailable'), item.url, 'text-link'));
  } else {
    body.append(make('h3', '', t('noLive')), make('p', '', t('noLiveDetail')));
    panel.append(signal, body);
  }
  wrap.append(panel, make('p', 'broadcast-note', t('liveCaution')));
  return wrap;
}
function videoCard(video) {
  const source = catalog.sources.find(s => s.id === video.source_id);
  const imam = catalog.imams.find(i => i.id === video.imam_id);
  const article = make('article', 'video-card');
  const top = make('div', 'video-card-top');
  top.append(make('span', 'kind-label', t('recorded')), make('span', 'video-duration', duration(video.duration_seconds)));
  article.append(top);
  const title = make('h3', '', nameOf(video.title));
  title.lang = locale;
  article.append(title, make('p', 'video-imam', nameOf(imam.name)));
  const provenance = make('p', 'video-source', `${t('source')}: ${nameOf(source.name)}`);
  article.append(provenance);
  const actions = make('div', 'video-actions');
  actions.append(internal(link(t('read'), videoUrl(video.id), 'solid-link')));
  actions.append(external(t('official'), video.url, 'text-link'));
  article.append(actions);
  return article;
}
function renderMosque(mosqueId) {
  const mosque = catalog.mosques.find(m => m.id === mosqueId);
  if (!mosque) return renderNotFound();
  const videos = catalog.videos.filter(v => v.mosque_id === mosqueId);
  const imams = catalog.imams.filter(i => i.mosque_id === mosqueId);
  const path = breadcrumb([{text: t('center'), href: '/haramain'}, {text: nameOf(mosque.name)}]);
  const intro = make('section', 'mosque-intro');
  intro.append(make('p', 'city-label', nameOf(mosque.city)), heading(nameOf(mosque.name)));
  intro.append(make('p', 'expansion-note', t('expansion')));
  const archive = make('section', 'archive-section');
  archive.append(titleRow(t('archive')));
  const filters = make('div', 'imam-filters');
  filters.setAttribute('role', 'group');
  filters.setAttribute('aria-label', t('imams'));
  const requested = new URLSearchParams(location.search).get('imam');
  let selected = imams.some(imam => imam.id === requested) ? requested : 'all';
  const list = make('div', 'video-grid');
  function drawCards() {
    list.replaceChildren();
    for (const button of filters.querySelectorAll('button')) button.setAttribute('aria-pressed', String(button.dataset.imam === selected));
    const shown = selected === 'all' ? videos : videos.filter(v => v.imam_id === selected);
    if (!shown.length) list.append(make('p', 'empty-state', videos.length ? t('empty') : t('noVideos')));
    else for (const video of shown) list.append(videoCard(video));
  }
  function selectImam(id) {
    selected = id;
    history.replaceState({}, '', id === 'all' ? mosqueUrl(mosqueId) : `${mosqueUrl(mosqueId)}?imam=${encodeURIComponent(id)}`);
    drawCards();
  }
  const allButton = make('button', 'filter-button filter-all', t('all'));
  allButton.type = 'button';
  allButton.dataset.imam = 'all';
  allButton.onclick = () => selectImam('all');
  filters.append(allButton);
  for (const imam of imams) {
    const button = make('button', 'imam-button');
    button.type = 'button';
    button.dataset.imam = imam.id;
    const portrait = make('span', 'imam-portrait');
    const photo = make('img');
    photo.src = imam.portrait;
    photo.alt = tr(`Portrait of ${nameOf(imam.name)}`, `صورة ${nameOf(imam.name)}`);
    photo.width = 92;
    photo.height = 104;
    photo.loading = 'lazy';
    photo.decoding = 'async';
    const fallback = make('span', 'portrait-fallback', `${nameOf(imam.name)} · ${t('photoUnavailable')}`);
    fallback.hidden = true;
    fallback.setAttribute('aria-hidden', 'true');
    photo.addEventListener('error', () => { photo.hidden = true; fallback.hidden = false; });
    portrait.append(photo, fallback);
    const names = make('span', 'imam-names');
    const primary = make('span', 'imam-name-primary', nameOf(imam.name));
    primary.lang = locale;
    primary.dir = locale === 'ar' ? 'rtl' : 'ltr';
    const secondary = make('span', 'imam-name-secondary', imam.name[locale === 'ar' ? 'en' : 'ar']);
    secondary.lang = locale === 'ar' ? 'en' : 'ar';
    secondary.dir = locale === 'ar' ? 'ltr' : 'rtl';
    names.append(primary, secondary);
    button.append(portrait, names);
    button.onclick = () => selectImam(imam.id);
    filters.append(button);
  }
  archive.append(filters, list);
  main.append(path, intro, broadcastSection(mosqueId), archive);
  drawCards();
}

async function ensureToken() {
  if (token) return token;
  const response = await fetch('/api/state');
  if (!response.ok) throw Error(t('catalogFailure'));
  const state = await response.json();
  token = state.token;
  publicMode = Boolean(state.public);
  applyLocale();
  return token;
}
function statusLabel(job) {
  if (!job) return '';
  if (job.state === 'queued') return t('waiting');
  if (job.state === 'processing') {
    const stageLabels = {
      importing: 'importingProgress', canonicalize: 'preparingAudio', segmenting: 'audioPrepared',
      asr_translation: 'transcribing', safety_pre_translation: 'safetyCheck', safety_final: 'safetyCheck',
      tts: 'preparingSpeech', segment_complete: 'segmentComplete',
    };
    let stage = job.progress_stage;
    if (!stage && (job.message === 'Importing recorded YouTube audio' || job.message === 'Waiting to import the recorded YouTube video')) stage = 'importing';
    if (!stage && job.message?.startsWith('Preparing audio')) stage = 'canonicalize';
    if (!stage && job.message?.startsWith('Transcribing and translating')) stage = 'asr_translation';
    if (!stage && job.message?.startsWith('Checking translation safety')) stage = 'safety_final';
    if (!stage && job.message?.startsWith('Preparing speech')) stage = 'tts';
    if (!stage && job.message?.startsWith('Segment ')) stage = 'segment_complete';
    let label = t(stageLabels[stage] || 'working');
    const count = Number.isInteger(job.segment_count) && job.segment_count > 0 ? job.segment_count : 0;
    const current = Number.isInteger(job.current_segment) && job.current_segment > 0 ? job.current_segment : 0;
    if (stage === 'segmenting' && count) label += ` · ${count} ${t('segments')}`;
    else if (stage !== 'importing' && current && count) label += ` · ${t('segmentProgress')} ${current} ${t('of')} ${count}`;
    return label;
  }
  if (job.state === 'failed') {
    if (job.failure_code === 'source_mismatch') return t('sourceMismatch');
    if (job.failure_code === 'youtube_access_blocked') return t('sourceBlocked');
    return t('sourceFailure');
  }
  if (job.state === 'interrupted') return t('interrupted');
  if (job.state === 'partial') return t('partial');
  if (job.state === 'completed') return t('ready');
  return t('processing');
}
function renderVideoFrame(video, imam, source, job) {
  main.replaceChildren();
  const mosque = catalog.mosques.find(item => item.id === video.mosque_id);
  const path = breadcrumb([
    {text: t('center'), href: '/haramain'},
    {text: nameOf(mosque?.name), href: mosqueUrl(video.mosque_id)},
    {text: nameOf(imam.name), href: `${mosqueUrl(video.mosque_id)}?imam=${encodeURIComponent(imam.id)}`},
    {text: nameOf(video.title)},
  ]);
  const head = make('section', 'detail-header');
  head.append(make('p', 'city-label', `${t('recorded')} · ${duration(video.duration_seconds)}`), heading(nameOf(video.title)));
  const details = make('div', 'detail-meta');
  details.append(make('span', '', nameOf(imam.name)), make('span', '', `${t('source')}: ${nameOf(source.name)}`));
  head.append(details);
  const sourceLine = make('div', 'source-line');
  sourceLine.append(external(t('openSource'), video.url, 'text-link'));
  head.append(sourceLine);
  const content = make('section', 'detail-content');
  content.id = 'result-content';
  main.append(path, head, content);
  renderJob(video, job);
}
async function requestProcessing(video, button, container, retry = false) {
  button.disabled = true;
  button.textContent = t('waiting');
  try {
    await ensureToken();
    const response = await fetch(`/api/haramain/videos/${video.id}/process`, {
      method: 'POST', headers: {'Content-Type': 'application/json', 'X-Moin-Token': token},
      body: JSON.stringify(retry ? {retry: true} : {}),
    });
    const data = await response.json();
    if (!response.ok) {
      const messages = {
        video_unavailable: t('unavailable'), video_too_long: t('tooLong'),
        queue_full: t('queueFull'), catalog_unavailable: t('catalogFailure'),
        not_found: t('failed'),
      };
      throw Error(response.status === 403 ? t('reload') : messages[data.code] || t('failed'));
    }
    renderJob(video, data.job);
    if (['queued', 'processing'].includes(data.job.state)) beginPolling(video.id);
  } catch (error) {
    container.append(make('p', 'error-message', error.message || t('failed')));
    button.disabled = false;
    button.textContent = retry ? t('retryTranslations') : t('retry');
  }
}
function renderJob(video, job) {
  const container = document.getElementById('result-content');
  if (!container) return;
  container.replaceChildren();
  if (video.state !== 'available') {
    container.append(make('p', 'status-panel', t('unavailable')));
    return;
  }
  if (job && ['completed', 'partial'].includes(job.state)) {
    if (job.state === 'partial') container.append(make('p', 'status-panel caution', t('partial')));
    if (job.failures || job.withheld || job.missing_speech) {
      const retry = make('button', 'start-button result-retry', t('retryTranslations'));
      retry.type = 'button';
      retry.onclick = () => requestProcessing(video, retry, container, true);
      container.append(retry);
    }
    renderReader(container, job);
    return;
  }
  const box = make('div', 'processing-panel');
  const message = make('h2', '', job ? statusLabel(job) : tr('Prepare this recording', 'جهّز هذا التسجيل'));
  box.append(message, make('p', '', t('partialNote')));
  if (job && ['queued', 'processing'].includes(job.state)) {
    const pulse = make('div', 'processing-line');
    pulse.setAttribute('role', 'status');
    pulse.setAttribute('aria-label', statusLabel(job));
    box.append(pulse);
  } else {
    const button = make('button', 'start-button', job ? t('retry') : t('start'));
    button.type = 'button';
    button.onclick = () => requestProcessing(video, button, box);
    box.append(button);
  }
  container.append(box);
}
async function renderReader(container, job) {
  const jobId = job.id;
  const placeholder = make('p', 'loading', tr('Opening the saved result…', 'جارٍ فتح النتيجة المحفوظة…'));
  container.append(placeholder);
  try {
    const response = await fetch(`/api/jobs/${jobId}/result`);
    if (!response.ok) throw Error();
    const result = await response.json();
    if (location.pathname !== videoUrl(currentVideo)) return;
    placeholder.remove();
    const reader = make('div', 'reader');
    if (result.segments?.some(item => item.safety?.outcome === 'review_required')) {
      reader.append(make('p', 'status-panel caution', t('caution')));
    }
    let original = null;
    if (!job.prepared || job.original_audio) {
      const player = make('div', 'original-player');
      const label = make('label', '', t('original'));
      label.htmlFor = 'original-audio';
      original = make('audio');
      original.id = 'original-audio';
      original.controls = true;
      original.preload = 'metadata';
      original.src = `/media/${jobId}/source.wav`;
      original.onplay = () => {
        if (activeSpeechAudio) activeSpeechAudio.pause();
        activeSpeechAudio = null;
      };
      player.append(label, original);
      reader.append(player);
    }
    for (const language of ['en', 'fr']) {
      const complete = result.segments?.length && result.segments.every(item => {
        const speech = item.synthesis?.[language];
        return speech?.status === 'created' && new RegExp(`^segment-\\d{4,}-${language}\\.mp3$`).test(speech.file);
      });
      if (!complete) continue;
      const translatedPlayer = make('div', 'original-player translated-player');
      const translatedLabel = make('label', '', t(language === 'en' ? 'fullEnglish' : 'fullFrench'));
      const translatedAudio = make('audio');
      translatedAudio.id = `full-${language}-audio`;
      translatedAudio.controls = true;
      translatedAudio.preload = 'metadata';
      translatedAudio.src = `/media/${jobId}/full-${language}.mp3`;
      const segmentFiles = result.segments.map(item => `/media/${jobId}/${item.synthesis[language].file}`);
      const fallbackAudio = make('audio');
      fallbackAudio.preload = 'none';
      fallbackAudio.hidden = true;
      const fallbackButton = make('button', 'start-button full-audio-fallback', t(language === 'en' ? 'fullEnglish' : 'fullFrench'));
      fallbackButton.type = 'button';
      fallbackButton.hidden = true;
      let segmentIndex = 0;
      const playNext = () => {
        if (segmentIndex >= segmentFiles.length) {
          fallbackButton.textContent = t(language === 'en' ? 'fullEnglish' : 'fullFrench');
          if (activeSpeechAudio === fallbackAudio) activeSpeechAudio = null;
          return;
        }
        fallbackAudio.src = segmentFiles[segmentIndex];
        fallbackAudio.play().then(() => {
          fallbackButton.textContent = `${t('pause')} · ${segmentIndex + 1}/${segmentFiles.length}`;
        }).catch(() => { fallbackButton.textContent = t('noSpeech'); });
      };
      fallbackAudio.onended = () => { segmentIndex += 1; playNext(); };
      fallbackAudio.onpause = () => {
        if (activeSpeechAudio === fallbackAudio) activeSpeechAudio = null;
        fallbackButton.textContent = t(language === 'en' ? 'fullEnglish' : 'fullFrench');
      };
      fallbackButton.onclick = () => {
        if (activeSpeechAudio === fallbackAudio && !fallbackAudio.paused) { fallbackAudio.pause(); return; }
        original?.pause();
        if (activeSpeechAudio) activeSpeechAudio.pause();
        activeSpeechAudio = fallbackAudio;
        segmentIndex = 0;
        playNext();
      };
      translatedAudio.onerror = () => { translatedAudio.hidden = true; fallbackButton.hidden = false; };
      translatedLabel.htmlFor = translatedAudio.id;
      translatedAudio.onplay = () => {
        original?.pause();
        if (activeSpeechAudio && activeSpeechAudio !== translatedAudio) activeSpeechAudio.pause();
        activeSpeechAudio = translatedAudio;
      };
      translatedAudio.onpause = () => { if (activeSpeechAudio === translatedAudio) activeSpeechAudio = null; };
      translatedPlayer.append(translatedLabel, translatedAudio, fallbackAudio, fallbackButton);
      reader.append(translatedPlayer);
    }
    const tabs = make('div', 'reader-tabs');
    tabs.setAttribute('role', 'tablist');
    tabs.setAttribute('aria-label', t('language'));
    const segments = make('div', 'segments');
    segments.id = 'reading-segments';
    segments.setAttribute('role', 'tabpanel');
    const languages = [['arabic', t('arabic')], ['en', t('english')], ['fr', t('french')]];
    function drawSegments() {
      for (const button of tabs.querySelectorAll('button')) {
        const selected = button.dataset.lang === activeLanguage;
        button.setAttribute('aria-selected', String(selected));
        button.tabIndex = selected ? 0 : -1;
      }
      segments.replaceChildren();
      segments.setAttribute('aria-labelledby', `lang-${activeLanguage}`);
      for (const item of result.segments || []) {
        const row = make('article', 'segment');
        const seek = make('button', 'time-button', duration(Math.max(0, Math.floor(item.start_seconds || 0))));
        seek.type = 'button';
        seek.setAttribute('aria-label', `${t('original')} ${seek.textContent}`);
        seek.onclick = () => {
          if (activeSpeechAudio) activeSpeechAudio.pause();
          activeSpeechAudio = null;
          if (original) {
            original.currentTime = item.start_seconds || 0;
            original.play().catch(() => {});
          } else {
            const seconds = Math.max(0, Math.floor(item.start_seconds || 0));
            window.open(`${catalog.videos.find(video => video.id === currentVideo).url}&t=${seconds}s`, '_blank', 'noopener,noreferrer');
          }
        };
        const body = make('div', 'segment-body');
        const missingTranslation = item.result?.failure?.code === 'credential_unavailable' ? t('credentialMissing') : t('noTranslation');
        const text = make('p', 'segment-text', item.result?.[activeLanguage] || (activeLanguage !== 'arabic' ? missingTranslation : t('noText')));
        text.lang = activeLanguage === 'arabic' ? 'ar' : activeLanguage;
        text.dir = activeLanguage === 'arabic' ? 'rtl' : 'ltr';
        body.append(text);
        if (activeLanguage !== 'arabic') {
          const speech = item.synthesis?.[activeLanguage];
          if (speech?.status === 'created' && /^[a-zA-Z0-9_.-]+\.(mp3|wav|aiff)$/.test(speech.file)) {
            const audio = make('audio');
            audio.controls = true;
            audio.preload = 'none';
            audio.src = `/media/${jobId}/${speech.file.replace(/\.aiff$/, '.wav')}`;
            const listen = make('button', 'listen-button', t('listen'));
            listen.type = 'button';
            listen.onclick = () => {
              if (audio.paused) {
                original?.pause();
                if (activeSpeechAudio && activeSpeechAudio !== audio) activeSpeechAudio.pause();
                activeSpeechAudio = audio;
                audio.play().then(() => { listen.textContent = t('pause'); }).catch(() => { listen.textContent = t('noSpeech'); });
              }
              else { audio.pause(); listen.textContent = t('listen'); }
            };
            audio.onpause = () => { listen.textContent = t('listen'); if (activeSpeechAudio === audio) activeSpeechAudio = null; };
            audio.onended = () => { listen.textContent = t('listen'); };
            audio.onerror = () => { listen.disabled = true; listen.textContent = t('noSpeech'); };
            body.append(listen, audio);
          } else if (item.safety?.outcome !== 'withheld') body.append(make('p', 'no-speech', t('noSpeech')));
        }
        row.append(seek, body);
        segments.append(row);
      }
    }
    languages.forEach(([code, labelText], index) => {
      const button = make('button', 'language-tab', labelText);
      button.type = 'button';
      button.id = `lang-${code}`;
      button.dataset.lang = code;
      button.setAttribute('role', 'tab');
      button.setAttribute('aria-controls', 'reading-segments');
      button.tabIndex = index === 0 ? 0 : -1;
      button.onclick = () => {
        if (activeSpeechAudio) activeSpeechAudio.pause();
        activeSpeechAudio = null;
        activeLanguage = code;
        original?.pause();
        drawSegments();
      };
      button.onkeydown = event => {
        const all = [...tabs.querySelectorAll('button')];
        const position = all.indexOf(button);
        let next;
        const step = document.documentElement.dir === 'rtl' ? -1 : 1;
        if (event.key === 'ArrowRight') next = all[(position + step + all.length) % all.length];
        if (event.key === 'ArrowLeft') next = all[(position - step + all.length) % all.length];
        if (event.key === 'Home') next = all[0];
        if (event.key === 'End') next = all.at(-1);
        if (next) { event.preventDefault(); next.focus(); next.click(); }
      };
      tabs.append(button);
    });
    reader.append(tabs, segments, make('p', 'reader-caution', t('caution')));
    container.append(reader);
    drawSegments();
  } catch {
    placeholder.textContent = t('failed');
  }
}
async function renderVideo(id) {
  currentVideo = id;
  activeLanguage = 'arabic';
  main.replaceChildren(make('p', 'loading', tr('Opening the recording…', 'جارٍ فتح التسجيل…')));
  try {
    const response = await fetch(`/api/haramain/videos/${id}`);
    if (response.status === 404) { renderNotFound(); return; }
    if (!response.ok) throw Error();
    const data = await response.json();
    if (location.pathname !== videoUrl(id)) return;
    renderVideoFrame(data.video, data.imam, data.source, data.job);
    if (data.job && ['queued', 'processing'].includes(data.job.state)) beginPolling(id);
  } catch { main.replaceChildren(make('p', 'error-state', t('failed'))); }
}
function beginPolling(id) {
  if (pollTimer) clearInterval(pollTimer);
  pollTimer = setInterval(async () => {
    try {
      const update = await fetch(`/api/haramain/videos/${id}`);
      if (!update.ok) throw Error();
      const newer = await update.json();
      if (location.pathname !== videoUrl(id)) return;
      renderJob(newer.video, newer.job);
      if (!newer.job || !['queued', 'processing'].includes(newer.job.state)) { clearInterval(pollTimer); pollTimer = null; }
    } catch { /* Keep the last visible state and retry on the next poll. */ }
  }, 2500);
}
function renderNotFound() { main.replaceChildren(make('p', 'error-state', tr('This page is not in the collection.', 'هذه الصفحة ليست ضمن المجموعة.')), internal(link(t('back'), '/haramain', 'solid-link'))); }
function render() {
  if (pollTimer) { clearInterval(pollTimer); pollTimer = null; }
  for (const audio of main.querySelectorAll('audio')) audio.pause();
  activeSpeechAudio = null;
  applyLocale();
  main.replaceChildren();
  if (!catalog) { main.append(make('p', 'loading', t('catalogFailure'))); return; }
  const path = decodeURIComponent(location.pathname).replace(/\/$/, '') || '/';
  if (path === '/haramain') renderHome();
  else if (/^\/haramain\/(makkah|madinah)$/.test(path)) renderMosque(path.split('/')[2]);
  else if (/^\/haramain\/video\/[A-Za-z0-9_-]{11}$/.test(path)) renderVideo(path.split('/')[3]);
  else renderNotFound();
}
document.querySelectorAll('[data-locale]').forEach(button => button.onclick = () => {
  locale = button.dataset.locale;
  MoinLocale.save(locale);
  render();
});
window.addEventListener('popstate', render);
ensureToken().catch(() => {});
fetch('/api/haramain/catalog').then(response => { if (!response.ok) throw Error(); return response.json(); }).then(data => { catalog = data; render(); }).catch(() => {
  applyLocale(); main.replaceChildren(make('p', 'error-state', t('catalogFailure')));
});
