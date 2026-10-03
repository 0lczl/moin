(() => {
  'use strict';

  const API = '/api/live/rooms';
  const app = document.querySelector('#app');
  const toast = document.querySelector('#toast');
  const translations = {
    en: {
      workspace:'YOUR WORKSPACE', recording:'Recording studio', videos:'Haramain videos', live:'Live translator', onDevice:'Private by design', sidebarNote:'A simple way to follow a live gathering.', experimental:'Live room pilot', eyebrow:'LISTEN TOGETHER, IN YOUR LANGUAGE', headline:'Make space for<br>every listener.', intro:'Create a room for a live gathering. Share one link so listeners can follow along in English or French.', loading:'Opening your live room…', footer:'Made for careful listening.', createTitle:'Create a live room', roomName:'Room name', roomPlaceholder:'Friday lesson · Main hall', targetLanguage:'Listener language', english:'English', french:'French', nameHint:'Choose a name listeners will recognize.', createButton:'Create room', createArrow:'↗', shareCarefully:'A room made for sharing.', shareNote:'Listeners can join from their phone browser. No account or app is needed.', createEyebrow:'NEW GATHERING', adminEyebrow:'YOUR PRIVATE ROOM', listenerEyebrow:'LISTENER ROOM', waiting:'Waiting to begin', active:'Room open', ended:'Session ended', invalid:'Room unavailable', roomNotFound:'We couldn’t find this room.', invalidHelp:'Check the link with the person hosting the gathering.', roomEndedTitle:'This session has ended', roomEndedHelp:'The host has closed this room. Ask them for a new link if another session is planned.', backHome:'Create a room', retry:'Try again', listeners:'connected listeners', publicLink:'Public join link', copyLink:'Copy link', copied:'Link copied', copyFailed:'Could not copy. Select and copy the link.', qrTitle:'Scan to join', qrDescription:'Point your phone camera at this code to open the listener room.', qrLoading:'Preparing the room code…', qrUnavailable:'Room code is not available yet. Share the join link instead.', roomCode:'ROOM ID', privateRoom:'Private room link', privateWarning:'Keep this link private. Anyone with it can manage and end the room.', copyPrivate:'Copy private link', endRoom:'End this session', endConfirm:'End this session? Listeners will see that the room has closed.', ending:'Ending…', roomEnded:'Session ended', joinBefore:'Before you join', confirmJoin:'Join this room', joinArrow:'→', joinNotice:'This room is for listening in {language}. You can leave at any time.', noTranslationTitle:'You’re in the room', noTranslation:'Arabic text and its translation will appear here as the host shares speech. Processing may take a moment.', connection:'Connected to room updates', reconnect:'Trying to reconnect…', joined:'You joined the room', joinError:'Could not join this room. Please try again.', createError:'Could not create the room. Please try again.', networkError:'Could not reach Moin. Check your connection and try again.', languageNameEn:'English', languageNameFr:'French', enTarget:'EN · FR', adminLinkCopied:'Private room link copied', endedNotice:'This room has ended.', roomLoadingError:'We could not load this room.', countUnknown:'—', notActiveNote:'The host has not started the gathering yet.', joinWaitNote:'You can join now and wait for the host to begin.', requestPending:'Joining…', roomId:'Room', listenerJoinLabel:'This room is set for', endedMessage:'The gathering has ended. Thank you for joining.', pageTitle:'Moin — Live Mosque Translator', closePrivate:'Private management link', micTitle:'Live audio', micIntro:'Allow microphone access, then share short audio segments with the room.', micStart:'Start microphone', micStop:'Stop microphone', micReady:'Microphone is off', micRequesting:'Requesting microphone access…', micRecording:'Microphone is on · sharing short segments', micUploading:'Sending audio segment…', micProcessing:'Audio sent · waiting for text', micPermission:'Microphone access was denied. Allow it in your browser settings and try again.', micUnsupported:'This browser cannot record audio. Try a recent version of Safari, Chrome, or Firefox.', micNetwork:'Audio could not be sent. Check your connection; sharing will continue with the next segment.', micUnavailable:'Live audio processing is not available on this server yet.', micStopped:'Microphone stopped', segmentTitle:'Live text', segmentWait:'When the host shares speech, Arabic text and its translation will appear here.', segmentProcessing:'Preparing this segment…', segmentError:'This segment could not be processed.', arabicLabel:'Arabic', translationLabel:'Translation', loadAudio:'Load translated audio', audioLoading:'Loading audio…', audioUnavailable:'Audio is not available for this segment yet.', liveConnection:'Receiving room updates', noSegments:'Waiting for the host to share speech…', audioError:'Could not load audio. Please try again.', audioReady:'Audio ready', textReady:'Text ready', working:'Working'
    },
    ar: {
      workspace:'مساحة العمل', recording:'استوديو التسجيل', videos:'فيديوهات الحرمين', live:'المترجم المباشر', onDevice:'الخصوصية أولاً', sidebarNote:'طريقة سهلة لمتابعة اللقاء المباشر.', experimental:'تجربة الغرف المباشرة', eyebrow:'استمعوا معاً بلغتكم', headline:'مساحة لكل<br>مستمع.', intro:'أنشئ غرفة للقاء مباشر وشارك رابطاً واحداً ليتابع المستمعون بالإنجليزية أو الفرنسية.', loading:'جارٍ فتح الغرفة…', footer:'للاستماع بعناية.', createTitle:'إنشاء غرفة مباشرة', roomName:'اسم الغرفة', roomPlaceholder:'درس الجمعة · القاعة الرئيسية', targetLanguage:'لغة المستمعين', english:'الإنجليزية', french:'الفرنسية', nameHint:'اختر اسماً يسهل على المستمعين التعرّف عليه.', createButton:'إنشاء الغرفة', createArrow:'↗', shareCarefully:'غرفة تجمع المستمعين.', shareNote:'يمكن الانضمام من متصفح الهاتف دون حساب أو تطبيق.', createEyebrow:'لقاء جديد', adminEyebrow:'غرفتك الخاصة', listenerEyebrow:'غرفة المستمعين', waiting:'بانتظار البدء', active:'الغرفة مفتوحة', ended:'انتهى اللقاء', invalid:'الغرفة غير متاحة', roomNotFound:'لم نعثر على هذه الغرفة.', invalidHelp:'تحقق من الرابط مع مستضيف اللقاء.', roomEndedTitle:'انتهى هذا اللقاء', roomEndedHelp:'أغلق المستضيف هذه الغرفة. اطلب منه رابطاً جديداً إذا كان هناك لقاء آخر.', backHome:'إنشاء غرفة', retry:'إعادة المحاولة', listeners:'مستمعون متصلون', publicLink:'رابط الانضمام العام', copyLink:'نسخ الرابط', copied:'تم نسخ الرابط', copyFailed:'تعذر النسخ. حدد الرابط وانسخه.', qrTitle:'امسح للانضمام', qrDescription:'وجّه كاميرا هاتفك إلى الرمز لفتح غرفة المستمعين.', qrLoading:'جارٍ تجهيز رمز الغرفة…', qrUnavailable:'رمز الغرفة غير متاح حالياً. شارك رابط الانضمام.', roomCode:'معرّف الغرفة', privateRoom:'رابط الغرفة الخاص', privateWarning:'احتفظ بهذا الرابط لنفسك. يمكن لمن يملكه إدارة الغرفة وإنهاءها.', copyPrivate:'نسخ الرابط الخاص', endRoom:'إنهاء هذا اللقاء', endConfirm:'هل تريد إنهاء هذا اللقاء؟ سيظهر للمستمعين أن الغرفة أُغلقت.', ending:'جارٍ الإنهاء…', roomEnded:'انتهى اللقاء', joinBefore:'قبل الانضمام', confirmJoin:'انضم إلى الغرفة', joinArrow:'←', joinNotice:'هذه الغرفة للاستماع بـ{language}. يمكنك المغادرة متى شئت.', noTranslationTitle:'أنت في الغرفة', noTranslation:'سيظهر النص العربي وترجمته هنا عندما يشارك المستضيف الكلام. قد تستغرق المعالجة بعض الوقت.', connection:'متصل بتحديثات الغرفة', reconnect:'جارٍ إعادة الاتصال…', joined:'انضممت إلى الغرفة', joinError:'تعذر الانضمام إلى هذه الغرفة. حاول مرة أخرى.', createError:'تعذر إنشاء الغرفة. حاول مرة أخرى.', networkError:'تعذر الاتصال بمعين. تحقق من اتصالك وحاول مجدداً.', languageNameEn:'الإنجليزية', languageNameFr:'الفرنسية', enTarget:'EN · FR', adminLinkCopied:'تم نسخ رابط الإدارة الخاص', endedNotice:'انتهت هذه الغرفة.', roomLoadingError:'تعذر تحميل هذه الغرفة.', countUnknown:'—', notActiveNote:'لم يبدأ مستضيف اللقاء بعد.', joinWaitNote:'يمكنك الانضمام الآن وانتظار بدء اللقاء.', requestPending:'جارٍ الانضمام…', roomId:'الغرفة', listenerJoinLabel:'لغة هذه الغرفة', endedMessage:'انتهى اللقاء. شكراً لانضمامك.', pageTitle:'معين — المترجم المباشر', closePrivate:'رابط الإدارة الخاص', micTitle:'الصوت المباشر', micIntro:'اسمح باستخدام الميكروفون ثم شارك مقاطع صوتية قصيرة مع الغرفة.', micStart:'تشغيل الميكروفون', micStop:'إيقاف الميكروفون', micReady:'الميكروفون متوقف', micRequesting:'جارٍ طلب إذن الميكروفون…', micRecording:'الميكروفون يعمل · جارٍ مشاركة مقاطع قصيرة', micUploading:'جارٍ إرسال المقطع الصوتي…', micProcessing:'أُرسل الصوت · بانتظار النص', micPermission:'رُفض إذن الميكروفون. اسمح به من إعدادات المتصفح ثم حاول مرة أخرى.', micUnsupported:'هذا المتصفح لا يدعم تسجيل الصوت. جرّب إصداراً حديثاً من Safari أو Chrome أو Firefox.', micNetwork:'تعذر إرسال الصوت. تحقق من اتصالك؛ ستستمر المشاركة مع المقطع التالي.', micUnavailable:'معالجة الصوت المباشر غير متاحة على هذا الخادم بعد.', micStopped:'تم إيقاف الميكروفون', segmentTitle:'النص المباشر', segmentWait:'عندما يشارك المستضيف كلاماً، سيظهر النص العربي وترجمته هنا.', segmentProcessing:'جارٍ إعداد هذا المقطع…', segmentError:'تعذرت معالجة هذا المقطع.', arabicLabel:'العربية', translationLabel:'الترجمة', loadAudio:'تحميل الصوت المترجم', audioLoading:'جارٍ تحميل الصوت…', audioUnavailable:'الصوت غير متاح لهذا المقطع بعد.', liveConnection:'جارٍ استقبال تحديثات الغرفة', noSegments:'بانتظار مشاركة المستضيف للكلام…', audioError:'تعذر تحميل الصوت. حاول مرة أخرى.', audioReady:'الصوت جاهز', textReady:'النص جاهز', working:'جارٍ العمل'
    }
  };

  const state = { uiLang: localStorage.getItem('moin-live-language') || 'en', room: null, interval: null, listenerId: null, joined: false, adminToken: null, adminUrl: null, joinUrl: null, lastEventSeq: 0, segments: new Map(), micStream: null, recorder: null, chunkTimer: null, uploadPromise: Promise.resolve(), stopResolve: null, recording: false, micUnavailable: false, audioObjectUrls: new Map(), busy: false };
  const t = (key) => (translations[state.uiLang] && translations[state.uiLang][key]) || translations.en[key] || key;
  const escapeHTML = (value) => String(value ?? '').replace(/[&<>"']/g, (c) => ({'&':'&amp;','<':'&lt;','>':'&gt;','"':'&quot;',"'":'&#39;'}[c]));
  const currentPath = () => window.location.pathname.replace(/\/$/, '') || '/live';
  const route = () => {
    const path = currentPath();
    const admin = path.match(/\/live\/session\/([^/]+)$/);
    const join = path.match(/\/live\/join\/([^/]+)$/);
    return admin ? {kind:'admin', id:decodeURIComponent(admin[1])} : join ? {kind:'join', id:decodeURIComponent(join[1])} : {kind:'create'};
  };
  const roomIdFrom = (payload) => String(payload?.id ?? payload?.room?.id ?? '');
  const apiUrl = (id, suffix='') => `${API}/${encodeURIComponent(id)}${suffix}`;
  const langName = (lang) => ['fr','french'].includes(String(lang || '').toLowerCase()) ? t('languageNameFr') : t('languageNameEn');
  const roomStatus = (room) => String(room?.status || room?.state || (room?.ended_at ? 'ended' : 'waiting')).toLowerCase();
  const isEnded = (room) => ['ended','closed','complete','completed','finished'].includes(roomStatus(room));
  const isInvalidStatus = (room) => ['invalid','missing','not_found','deleted'].includes(roomStatus(room));
  const roomCount = (room) => Number(room?.listener_count ?? room?.connected_count ?? room?.listeners ?? 0);
  const uiDir = () => { document.documentElement.lang = state.uiLang; document.documentElement.dir = state.uiLang === 'ar' ? 'rtl' : 'ltr'; document.title = t('pageTitle'); };
  const applyTranslations = () => {
    uiDir();
    document.querySelectorAll('[data-i18n]').forEach((el) => { const value=t(el.dataset.i18n); if (el.tagName === 'H1') el.innerHTML=value; else el.textContent=value; });
    document.querySelectorAll('[data-ui-lang]').forEach((button) => button.setAttribute('aria-pressed', String(button.dataset.uiLang === state.uiLang)));
    const target=document.querySelector('#header-target'); if(target) target.textContent=t('enTarget');
  };
  const setBusy = (busy) => { state.busy=busy; app.setAttribute('aria-busy',String(busy)); };
  const showToast = (message) => { toast.textContent=message; toast.classList.add('show'); window.clearTimeout(showToast.timer); showToast.timer=window.setTimeout(()=>toast.classList.remove('show'),2400); };
  async function request(url, options={}) {
    let response;
    try { response=await fetch(url,{...options,headers:{...(options.body?{'Content-Type':'application/json'}:{}),...(options.headers||{})}}); }
    catch { throw new Error('network'); }
    let data={};
    try { data=await response.json(); } catch { /* Empty response. */ }
    if (!response.ok) { const error=new Error(data?.error || data?.message || `http_${response.status}`); error.status=response.status; throw error; }
    return data;
  }
  const eventList = (data) => Array.isArray(data) ? data : (data?.events || data?.items || []);
  async function pollRoomEvents(id, roleToken, roleHeader) {
    const url=`${apiUrl(id,'/events')}?after=${state.lastEventSeq}`;
    const data=await request(url,{headers:{[roleHeader]:roleToken}});
    const events=eventList(data);
    for(const event of events) {
      const sequence=Number(event?.seq || event?.sequence || 0);
      if(sequence && sequence<=state.lastEventSeq) continue;
      if(sequence>state.lastEventSeq) state.lastEventSeq=sequence;
      if(event?.type==='segment' && event.segment) upsertSegment(event.segment);
      if(event?.type==='room_ended' || event?.type==='session_ended') return true;
    }
    return false;
  }
  function quranSourceMarkup(segment) {
    if(segment.safety!=='quran_rendering') return '';
    const source=segment.sources?.[segment.language];
    if(!source) return '';
    const label=state.uiLang==='ar'?'ترجمة منشورة من QuranEnc.com':'Published rendering from QuranEnc.com';
    const detail=`${source.source || ''} · ${source.version || ''}`;
    const notes=source.footnotes?`<p class="segment-safety">${escapeHTML(source.footnotes)}</p>`:'';
    const url=typeof source.source_url==='string'&&source.source_url.startsWith('https://quranenc.com/')?source.source_url:null;
    const link=url?` <a href="${escapeHTML(url)}" target="_blank" rel="noopener noreferrer">QuranEnc.com ↗</a>`:'';
    return `<div class="segment-source"><p>${escapeHTML(label)} · ${escapeHTML(detail)}${link}</p>${notes}</div>`;
  }
  function segmentMarkup(segment, listener=false) {
    const index=Number(segment.index);
    const phase=String(segment.phase || 'processing');
    const phaseLabel=phase==='error'?t('segmentError'):phase==='processing'?t('segmentProcessing'):'';
    const textMarkup=segment.arabic || segment.translation ? `<div class="segment-copy">${segment.arabic?`<p class="segment-label">${escapeHTML(t('arabicLabel'))}</p><p class="segment-text" lang="ar" dir="rtl">${escapeHTML(segment.arabic)}</p>`:''}${segment.translation?`<p class="segment-label translated-label">${escapeHTML(t('translationLabel'))}</p><p class="segment-text" lang="${escapeHTML(segment.language || (state.room?.language==='fr'?'fr':'en'))}">${escapeHTML(segment.translation)}</p>`:''}</div>` : `<p class="segment-placeholder">${escapeHTML(phaseLabel || t('segmentProcessing'))}</p>`;
    let audioMarkup='';
    if(listener) {
      if(state.audioObjectUrls.has(index)) audioMarkup=`<audio class="segment-audio" controls preload="none" src="${escapeHTML(state.audioObjectUrls.get(index))}" aria-label="${escapeHTML(t('translationLabel'))} ${index+1}"></audio>`;
      else if(segment.audio_status==='available' || segment.audio_url || phase==='audio') audioMarkup=`<button class="audio-load" type="button" data-load-audio="${index}">${escapeHTML(t('loadAudio'))}</button>`;
      else if(segment.audio_status==='error') audioMarkup=`<p class="audio-note">${escapeHTML(t('audioUnavailable'))}</p>`;
    }
    const safety=segment.safety==='withheld'?`<p class="segment-safety">${escapeHTML(state.uiLang==='ar'?'حُجبت الترجمة للمراجعة مع الصوت العربي.':'Translation withheld for review against the original Arabic audio.')}</p>`:quranSourceMarkup(segment);
    return `<div class="segment-heading"><span>${escapeHTML(t('roomCode'))} ${index+1}</span><span class="segment-phase ${escapeHTML(phase)}">${escapeHTML(phaseLabel || (phase==='audio'?t('audioReady'):phase==='text'?t('textReady'):t('working')))}</span></div>${textMarkup}${safety}${audioMarkup}`;
  }
  function renderSegmentFeeds(index) {
    const segment=state.segments.get(index); if(!segment) return;
    for(const [id,listener] of [['admin-segments',false],['live-segments',true]]) {
      const feed=document.getElementById(id); if(!feed) continue;
      const empty=feed.querySelector('.empty-segments'); if(empty) empty.remove();
      let node=feed.querySelector(`[data-segment-index="${index}"]`);
      if(!node) { node=document.createElement('article'); node.className='live-segment'; node.dataset.segmentIndex=String(index); }
      node.innerHTML=segmentMarkup(segment,listener);
      const ordered=[...feed.querySelectorAll('.live-segment')].filter((item)=>item!==node).concat(node).sort((a,b)=>Number(a.dataset.segmentIndex)-Number(b.dataset.segmentIndex));
      ordered.forEach((item)=>feed.appendChild(item));
    }
  }
  function upsertSegment(input) {
    const index=Number(input?.index);
    if(!Number.isInteger(index) || index<0) return;
    const previous=state.segments.get(index) || {};
    state.segments.set(index,{...previous,...input,index});
    if(state.joined) document.querySelector('.translation-empty')?.remove();
    renderSegmentFeeds(index);
  }
  async function loadSegmentAudio(index,button) {
    if(state.audioObjectUrls.has(index)) return;
    button.disabled=true; button.textContent=t('audioLoading');
    const r=route();
    try {
      const response=await fetch(apiUrl(r.id,`/audio/${encodeURIComponent(index)}`),{headers:{'X-Moin-Listener':state.listenerId}});
      if(!response.ok) { const err=new Error(`http_${response.status}`); err.status=response.status; throw err; }
      const url=URL.createObjectURL(await response.blob()); state.audioObjectUrls.set(index,url);
      renderSegmentFeeds(index);
    } catch {
      button.disabled=false; button.textContent=t('audioError');
    }
  }
  const errorCopy = (error, fallback) => error?.status===404 ? t('roomNotFound') : error?.message==='network' ? t('networkError') : fallback;
  const clearPolling = () => { if(state.interval) window.clearInterval(state.interval); state.interval=null; };
  const setHtml = (html) => { app.innerHTML=html; setBusy(false); };
  const statePill = (status) => {
    const ended=isEnded({status}); const active=['active','open','live','running','started'].includes(status);
    return `<span class="state-pill ${ended?'ended':active?'live':''}">${escapeHTML(t(ended?'ended':active?'active':'waiting'))}</span>`;
  };
  const stateCard = (kind, message='') => {
    const ended=kind==='ended'; const invalid=kind==='invalid';
    const title=ended?t('roomEndedTitle'):t('roomNotFound'); const body=message || (ended?t('roomEndedHelp'):t('invalidHelp'));
    return `<div class="room-state-card"><div class="state-symbol" aria-hidden="true">${ended?'✓':'⌕'}</div><h2>${escapeHTML(title)}</h2><p>${escapeHTML(body)}</p><div class="state-actions"><a class="primary state-link" href="/live">${escapeHTML(t('backHome'))}<span>↗</span></a></div></div>`;
  };
  function renderCreate(error='') {
    clearPolling();
    setHtml(`<div class="create-layout"><section class="create-card"><div class="section-heading"><span class="number">01</span><h2>${escapeHTML(t('createTitle'))}</h2></div>${error?`<div class="error-banner" role="alert">${escapeHTML(error)}</div>`:''}<form id="create-form"><label class="field"><span>${escapeHTML(t('roomName'))}</span><input name="name" maxlength="100" required autocomplete="off" placeholder="${escapeHTML(t('roomPlaceholder'))}"></label><label class="field"><span>${escapeHTML(t('targetLanguage'))}</span><select name="language"><option value="en">${escapeHTML(t('english'))}</option><option value="fr">${escapeHTML(t('french'))}</option></select></label><p class="hint">${escapeHTML(t('nameHint'))}</p><button class="primary" type="submit"><span>${escapeHTML(t('createButton'))}</span><span aria-hidden="true">${escapeHTML(t('createArrow'))}</span></button></form></section><aside class="side-note"><div class="ornament" aria-hidden="true">✳</div><div><h3>${escapeHTML(t('shareCarefully'))}</h3><p>${escapeHTML(t('shareNote'))}</p></div></aside></div>`);
  }
  const buildAdminUrl = (payload, id) => {
    const raw=payload?.admin_url || payload?.admin_link;
    if(raw) { try { return new URL(raw,window.location.origin).href; } catch { /* Build below. */ } }
    const token=payload?.admin_token || payload?.secret || payload?.admin_secret;
    const url=new URL(`/live/session/${encodeURIComponent(id)}`,window.location.origin);
    if(token) url.hash=`secret=${encodeURIComponent(token)}`;
    return url.href;
  };
  const tokenFromLocation = () => {
    const params=new URLSearchParams(window.location.hash.slice(1));
    return params.get('secret') || params.get('token') || '';
  };
  const setRouteUrl = (url) => {
    try { const parsed=new URL(url,window.location.origin); history.replaceState({},'',parsed.pathname+parsed.search+parsed.hash); } catch { /* Keep current route. */ }
  };
  function renderAdmin(room, id) {
    clearPolling(); state.room=room;
    const status=roomStatus(room); const ended=isEnded(room);
    if(isInvalidStatus(room)) { setHtml(stateCard('invalid')); return; }
    const hostName=room.name || room.title || t('createTitle');
    const joinUrl=state.joinUrl || room.join_url || room.join_link || `${window.location.origin}/live/join/${encodeURIComponent(id)}`;
    state.joinUrl=joinUrl;
    const adminUrl=state.adminUrl || window.location.href; state.adminUrl=adminUrl;
    const qrSource=apiUrl(id,'/qr.svg');
    const qrMarkup=`<img id="room-qr" src="${escapeHTML(qrSource)}" alt="${escapeHTML(t('qrTitle'))}" />`;
    setHtml(`<div class="room-shell"><div class="room-topline"><span class="room-kicker">${escapeHTML(t('adminEyebrow'))} · ${escapeHTML(t('roomId'))} ${escapeHTML(id)}</span>${statePill(status)}</div>${ended?`<div class="error-banner" role="status">${escapeHTML(t('endedNotice'))}</div>`:''}<div class="admin-grid"><section class="panel share-panel"><p class="eyebrow">${escapeHTML(t('adminEyebrow'))}</p><h2 class="room-title">${escapeHTML(hostName)}</h2><p class="room-subtitle">AR <span aria-hidden="true">→</span> ${escapeHTML(langName(room.language || room.target_language))}</p><div class="count-card"><div class="count-icon" aria-hidden="true">♧</div><div><span class="count-value" id="listener-count">${escapeHTML(String(roomCount(room)))}</span><span class="count-label">${escapeHTML(t('listeners'))}</span></div></div><div class="share-controls"><div><div class="room-kicker">${escapeHTML(t('publicLink'))}</div><div class="share-box"><input id="join-url" aria-label="${escapeHTML(t('publicLink'))}" readonly value="${escapeHTML(joinUrl)}"><button type="button" data-copy="join-url">${escapeHTML(t('copyLink'))}</button></div></div></div><details class="admin-private"><summary>${escapeHTML(t('privateRoom'))}</summary><div class="private-row"><input id="admin-url" aria-label="${escapeHTML(t('closePrivate'))}" readonly value="${escapeHTML(adminUrl)}"><button type="button" data-copy="admin-url">${escapeHTML(t('copyPrivate'))}</button></div><p class="caution">${escapeHTML(t('privateWarning'))}</p></details><section class="mic-controls" aria-labelledby="mic-title"><div><h3 id="mic-title">${escapeHTML(t('micTitle'))}</h3><p>${escapeHTML(t('micIntro'))}</p></div><p id="mic-status" class="mic-status" role="status" aria-live="polite">${escapeHTML(t('micReady'))}</p><button id="mic-toggle" class="mic-button" type="button">${escapeHTML(t('micStart'))}</button></section><button id="end-room" class="end-button" type="button" ${ended?'disabled':''}>${escapeHTML(ended?t('roomEnded'):t('endRoom'))}</button></section><section class="panel qr-panel"><h3 class="qr-heading">${escapeHTML(t('qrTitle'))}</h3><p class="qr-description">${escapeHTML(t('qrDescription'))}</p><div class="qr-frame ${qrSource?'':'qr-error'}" id="qr-frame">${qrMarkup}</div><div class="join-code">${escapeHTML(t('roomCode'))} <strong>${escapeHTML(id)}</strong></div></section></div><section class="panel segment-stream"><div class="section-heading"><span class="number">02</span><h2>${escapeHTML(t('segmentTitle'))}</h2></div><div id="admin-segments" class="segment-feed"><p class="empty-segments">${escapeHTML(t('noSegments'))}</p></div></section></div>`);
    for(const index of state.segments.keys()) renderSegmentFeeds(index);
    updateMicUi();
    loadQr();
    if(!ended) startAdminPolling(id);
  }
  function loadQr() {
    const qr=document.querySelector('#room-qr');
    if(!qr) return;
    qr.onerror=()=>{
      const frame=document.querySelector('#qr-frame');
      if(!frame) return;
      frame.classList.add('qr-error');
      const placeholder=document.createElement('div');
      placeholder.className='qr-placeholder';
      placeholder.textContent=t('qrUnavailable');
      frame.replaceChildren(placeholder);
    };
  }
  async function loadAdmin(id, first=true) {
    if(!state.adminToken) { setHtml(stateCard('invalid',t('invalidHelp'))); return; }
    try {
      const data=await request(apiUrl(id,'/admin'),{headers:{'X-Moin-Admin':state.adminToken}});
      const room=data.room || data;
      if(data.join_url) state.joinUrl=data.join_url;
      if(data.admin_url) state.adminUrl=data.admin_url;
      renderAdmin(room,id);
    } catch(error) {
      if(error.status===404 || error.status===401 || error.status===403) { clearPolling(); setHtml(stateCard('invalid',t('invalidHelp'))); return; }
      if(first) { setHtml(`<div class="error-banner" role="alert">${escapeHTML(errorCopy(error,t('roomLoadingError')))}</div><div class="room-state-card"><div class="state-symbol" aria-hidden="true">↻</div><h2>${escapeHTML(t('roomLoadingError'))}</h2><button type="button" id="retry-room" class="quiet">${escapeHTML(t('retry'))}</button></div>`); }
    }
  }
  function startAdminPolling(id) {
    clearPolling();
    state.interval=window.setInterval(async()=>{
      try {
        const endedEvent=await pollRoomEvents(id,state.adminToken,'X-Moin-Admin');
        const data=await request(apiUrl(id,'/admin'),{headers:{'X-Moin-Admin':state.adminToken}});
        const room=data.room || data;
        if(endedEvent || isEnded(room)) { clearPolling(); renderAdmin({...room,status:endedEvent?'ended':room.status},id); return; }
        const count=document.querySelector('#listener-count'); if(count) count.textContent=String(roomCount(room));
        const pill=document.querySelector('.state-pill'); if(pill) { const replacement=document.createElement('span'); replacement.outerHTML=statePill(roomStatus(room)); pill.replaceWith(replacement); }
      } catch(error) { if(error.status===404 || error.status===401 || error.status===403) { clearPolling(); setHtml(stateCard('invalid',t('invalidHelp'))); } }
    },4000);
  }
  async function loadPublic(id, joining=false) {
    clearPolling();
    try {
      const room=await request(apiUrl(id)); state.room=room.room || room;
      const actual=state.room;
      if(isInvalidStatus(actual)) { setHtml(stateCard('invalid')); return; }
      if(isEnded(actual)) { setHtml(stateCard('ended')); return; }
      if(joining && state.listenerId) { state.joined=true; renderJoined(actual,id); return; }
      renderJoinConfirm(actual,id);
      startPublicPolling(id);
    } catch(error) { setHtml(stateCard('invalid',errorCopy(error,t('roomNotFound')))); }
  }
  function renderJoinConfirm(room,id,error='') {
    const name=room.name || room.title || t('createTitle'); const language=langName(room.language || room.target_language);
    setHtml(`<div class="room-topline"><span class="room-kicker">${escapeHTML(t('listenerEyebrow'))} · ${escapeHTML(t('roomId'))} ${escapeHTML(id)}</span>${statePill(roomStatus(room))}</div>${error?`<div class="error-banner" role="alert">${escapeHTML(error)}</div>`:''}<section class="join-confirm"><div class="confirm-top"><p class="eyebrow">${escapeHTML(t('joinBefore'))}</p><span class="local-tag">AR <span class="arrow">→</span>${escapeHTML(language)}</span></div><h2 class="confirm-title">${escapeHTML(name)}</h2><p class="confirm-language">${escapeHTML(t('listenerJoinLabel'))} ${escapeHTML(language)}</p><div class="confirm-rule"></div><p class="confirm-note">${escapeHTML(t('joinNotice').replace('{language}',language))}</p><p class="hint">${escapeHTML(t('joinWaitNote'))}</p><button id="join-room" type="button" class="primary"><span>${escapeHTML(t('confirmJoin'))}</span><span aria-hidden="true">${escapeHTML(t('joinArrow'))}</span></button></section>`);
  }
  function renderJoined(room,id) {
    const name=room.name || room.title || t('createTitle');
    setHtml(`<div class="room-topline"><span class="room-kicker">${escapeHTML(t('listenerEyebrow'))} · ${escapeHTML(t('roomId'))} ${escapeHTML(id)}</span><span class="state-pill live">${escapeHTML(t('joined'))}</span></div><div class="joined-room"><div class="listener-title"><p class="eyebrow">${escapeHTML(t('listenerEyebrow'))}</p><h2>${escapeHTML(name)}</h2><p class="room-subtitle">AR <span aria-hidden="true">→</span> ${escapeHTML(langName(room.language || room.target_language))}</p></div><section class="translation-empty"><div class="listen-symbol" aria-hidden="true">⌁</div><h2>${escapeHTML(isEnded(room)?t('roomEndedTitle'):t('noTranslationTitle'))}</h2><p>${escapeHTML(isEnded(room)?t('endedMessage'):t('noTranslation'))}</p></section><div class="segment-feed listener-feed" id="live-segments"><p class="empty-segments">${escapeHTML(t('noSegments'))}</p></div><p class="connection-note" id="connection-note">${escapeHTML(t('connection'))}</p></div>`);
    for(const index of state.segments.keys()) renderSegmentFeeds(index);
  }
  function startPublicPolling(id) {
    clearPolling(); state.interval=window.setInterval(async()=>{
      try {
        if(state.listenerId) {
          let endedEvent=false;
          try { endedEvent=await pollRoomEvents(id,state.listenerId,'X-Moin-Listener'); } catch { /* Public room state below still reports a closed room. */ }
          if(endedEvent) { clearPolling(); const endedRoom={...(state.room||{}),status:'ended'}; state.room=endedRoom; if(state.joined) renderJoined(endedRoom,id); else setHtml(stateCard('ended')); return; }
        }
        const data=await request(apiUrl(id)); const room=data.room || data; state.room=room;
        const note=document.querySelector('#connection-note'); if(note) note.textContent=t('connection');
        if(isEnded(room)) { clearPolling(); if(state.joined) renderJoined(room,id); else setHtml(stateCard('ended')); }
        else if(!state.joined) { const pill=document.querySelector('.state-pill'); if(pill) { const next=document.createElement('span'); next.outerHTML=statePill(roomStatus(room)); pill.replaceWith(next); } }
      } catch { const note=document.querySelector('#connection-note'); if(note) note.textContent=t('reconnect'); }
    },5000);
  }
  async function createRoom(form) {
    if(state.busy) return;
    const formData=new FormData(form); const name=String(formData.get('name')||'').trim(); const language=String(formData.get('language')||'en');
    if(!name) { form.elements.name.focus(); return; }
    setBusy(true); const button=form.querySelector('button[type=submit]'); button.disabled=true; button.querySelector('span').textContent=t('requestPending');
    try {
      const result=await request(API,{method:'POST',body:JSON.stringify({name,language})});
      const id=roomIdFrom(result); if(!id) throw new Error('missing id');
      state.adminToken=result.admin_token || result.secret || result.admin_secret || tokenFromAdminUrl(result.admin_url || result.admin_link);
      state.adminUrl=buildAdminUrl(result,id); state.joinUrl=result.join_url || result.join_link || `${window.location.origin}/live/join/${encodeURIComponent(id)}`;
      const room=result.room || result;
      if(!room.status) room.status='waiting';
      setRouteUrl(state.adminUrl); renderAdmin(room,id);
    } catch(error) { renderCreate(errorCopy(error,t('createError'))); }
  }
  function tokenFromAdminUrl(url) { try { return new URL(url,window.location.origin).hash.match(/(?:secret|token)=([^&]+)/)?.[1] ? decodeURIComponent(new URL(url,window.location.origin).hash.match(/(?:secret|token)=([^&]+)/)[1]) : ''; } catch { return ''; } }
  async function joinRoom() {
    const r=route(); if(r.kind!=='join' || state.busy) return;
    const button=document.querySelector('#join-room'); if(!button) return;
    button.disabled=true; button.querySelector('span').textContent=t('requestPending');
    try {
      const data=await request(apiUrl(r.id,'/join'),{method:'POST',body:JSON.stringify({})});
      state.listenerId=String(data.listener_id || data.id || ''); state.joined=true;
      if(state.listenerId) sessionStorage.setItem(`moin-live:${r.id}`,state.listenerId);
      renderJoined(state.room || {},r.id); startPublicPolling(r.id);
    } catch(error) { renderJoinConfirm(state.room || {},r.id,errorCopy(error,t('joinError'))); }
  }
  async function endRoom() {
    const r=route(); if(r.kind!=='admin'||state.busy) return;
    if(!window.confirm(t('endConfirm'))) return;
    const button=document.querySelector('#end-room'); if(!button) return;
    button.disabled=true; button.textContent=t('ending');
    try {
      await stopMicrophone();
      const result=await request(apiUrl(r.id,'/end'),{method:'POST',headers:{'X-Moin-Admin':state.adminToken},body:JSON.stringify({})});
      const room=result.room || {...(state.room||{}),status:'ended'}; clearPolling(); renderAdmin({...room,status:room.status||'ended'},r.id);
    } catch(error) { button.disabled=false; button.textContent=t('endRoom'); showToast(errorCopy(error,t('roomLoadingError'))); }
  }
  function setMicStatus(message, kind='') {
    const status=document.querySelector('#mic-status'); if(status) { status.textContent=message; status.className=`mic-status ${kind}`; }
  }
  function updateMicUi() {
    const button=document.querySelector('#mic-toggle'); if(!button) return;
    button.textContent=state.recording?t('micStop'):t('micStart');
    button.classList.toggle('recording',state.recording);
    button.disabled=state.micUnavailable || isEnded(state.room);
    setMicStatus(state.recording?t('micRecording'):state.micUnavailable?t('micUnavailable'):t('micReady'),state.recording?'recording':state.micUnavailable?'error':'');
  }
  function mediaRecorderOptions() {
    const types=['audio/webm;codecs=opus','audio/webm','audio/mp4'];
    const supported=types.find((type)=>MediaRecorder.isTypeSupported?.(type));
    return supported?{mimeType:supported}:undefined;
  }
  function releaseMicrophone() {
    if(state.micStream) state.micStream.getTracks().forEach((track)=>track.stop());
    state.micStream=null; state.recorder=null;
  }
  function stopMicrophone() {
    state.recording=false;
    if(state.chunkTimer) window.clearTimeout(state.chunkTimer);
    state.chunkTimer=null;
    if(state.recorder && state.recorder.state==='recording') {
      setMicStatus(t('micUploading'));
      return new Promise((resolve)=>{ state.stopResolve=resolve; try { state.recorder.stop(); } catch { releaseMicrophone(); resolve(); } });
    }
    releaseMicrophone(); updateMicUi(); return state.uploadPromise;
  }
  function disableUnavailableMic() {
    state.micUnavailable=true; state.recording=false;
    if(state.chunkTimer) window.clearTimeout(state.chunkTimer);
    state.chunkTimer=null;
    const recorder=state.recorder; state.recorder=null;
    if(recorder && recorder.state==='recording') { try { recorder.stop(); } catch { /* Recorder is already closed. */ } }
    releaseMicrophone(); setMicStatus(t('micUnavailable'),'error'); updateMicUi();
  }
  async function uploadAudioChunk(blob,id,mimeType) {
    if(!blob || !blob.size || state.micUnavailable) return true;
    const micStatus=document.querySelector('#mic-status'); if(micStatus) setMicStatus(t('micUploading'));
    try {
      const response=await fetch(apiUrl(id,'/audio'),{method:'POST',headers:{'X-Moin-Admin':state.adminToken,'Content-Type':mimeType || blob.type || 'audio/webm'},body:blob});
      let data={}; try { data=await response.json(); } catch { /* Some successful responses have no JSON. */ }
      if(response.status===501) { disableUnavailableMic(); return false; }
      if(!response.ok) { const error=new Error(data?.message || `http_${response.status}`); error.status=response.status; throw error; }
      const index=Number(data.index ?? data.segment_index);
      if(Number.isInteger(index) && index>=0) upsertSegment({index,phase:'processing'});
      if(state.recording) setMicStatus(t('micProcessing'),'recording'); else if(!state.micUnavailable) setMicStatus(t('micStopped'));
      return true;
    } catch(error) {
      if(error.status===501) disableUnavailableMic();
      else setMicStatus(t('micNetwork'),'error');
      return false;
    }
  }
  function startRecorderChunk(id) {
    if(!state.recording || !state.micStream || state.micUnavailable) return;
    let recorder;
    try { recorder=new MediaRecorder(state.micStream,mediaRecorderOptions()); }
    catch { setMicStatus(t('micUnsupported'),'error'); state.recording=false; releaseMicrophone(); updateMicUi(); return; }
    if(recorder.mimeType && !/^audio\/(webm|mp4)/i.test(recorder.mimeType)) { setMicStatus(t('micUnsupported'),'error'); state.recording=false; releaseMicrophone(); updateMicUi(); return; }
    state.recorder=recorder;
    const parts=[];
    recorder.addEventListener('dataavailable',(event)=>{ if(event.data?.size) parts.push(event.data); });
    recorder.addEventListener('error',()=>setMicStatus(t('micNetwork'),'error'),{once:true});
    recorder.addEventListener('stop',async()=>{
      if(state.recorder===recorder) state.recorder=null;
      const blob=parts.length?new Blob(parts,{type:recorder.mimeType || parts[0].type || 'audio/webm'}):null;
      if(blob && !state.micUnavailable) { state.uploadPromise=uploadAudioChunk(blob,id,(recorder.mimeType || blob.type || 'audio/webm').split(';')[0]); await state.uploadPromise; }
      if(state.recording && state.micStream && !state.micUnavailable) startRecorderChunk(id);
      else { releaseMicrophone(); if(state.stopResolve) { const resolve=state.stopResolve; state.stopResolve=null; resolve(); } updateMicUi(); }
    },{once:true});
    try { recorder.start(); }
    catch { state.recording=false; releaseMicrophone(); setMicStatus(t('micUnsupported'),'error'); updateMicUi(); return; }
    state.chunkTimer=window.setTimeout(()=>{ if(state.recorder===recorder && recorder.state==='recording') recorder.stop(); },5000);
  }
  async function startMicrophone() {
    const r=route(); if(r.kind!=='admin' || state.recording || state.micUnavailable) return;
    if(!navigator.mediaDevices?.getUserMedia || typeof MediaRecorder==='undefined') { setMicStatus(t('micUnsupported'),'error'); return; }
    setMicStatus(t('micRequesting'));
    try {
      state.micStream=await navigator.mediaDevices.getUserMedia({audio:true});
      state.recording=true; updateMicUi(); startRecorderChunk(r.id);
    } catch(error) {
      const denied=['NotAllowedError','PermissionDeniedError','SecurityError'].includes(error?.name);
      setMicStatus(denied?t('micPermission'):t('micUnsupported'),'error');
    }
  }
  async function leaveRoom() {
    if(!state.listenerId) return;
    const r=route(); if(r.kind!=='join') return;
    const body=JSON.stringify({listener_id:state.listenerId});
    try { await fetch(apiUrl(r.id,'/leave'),{method:'POST',headers:{'Content-Type':'application/json'},body,keepalive:true}); } catch { /* Leaving the page must not be blocked by a network error. */ }
    sessionStorage.removeItem(`moin-live:${r.id}`); state.listenerId=null;
  }
  async function copyValue(id, privateLink=false) {
    const input=document.getElementById(id); if(!input) return;
    try { await navigator.clipboard.writeText(input.value); showToast(t(privateLink?'adminLinkCopied':'copied')); }
    catch {
      input.focus(); input.select();
      try { if(document.execCommand('copy')) showToast(t(privateLink?'adminLinkCopied':'copied')); else showToast(t('copyFailed')); } catch { showToast(t('copyFailed')); }
    }
  }
  function navigateUiLang(lang) {
    state.uiLang=lang; localStorage.setItem('moin-live-language',lang); applyTranslations();
    const r=route();
    if(r.kind==='admin' && state.room) renderAdmin(state.room,r.id);
    else if(r.kind==='join' && state.room) { state.joined ? renderJoined(state.room,r.id) : renderJoinConfirm(state.room,r.id); }
    else renderCreate();
  }
  document.addEventListener('click',(event)=>{
    const langButton=event.target.closest('[data-ui-lang]'); if(langButton) { navigateUiLang(langButton.dataset.uiLang); return; }
    const copyButton=event.target.closest('[data-copy]'); if(copyButton) { copyValue(copyButton.dataset.copy,copyButton.dataset.copy==='admin-url'); return; }
    if(event.target.closest('#join-room')) { joinRoom(); return; }
    if(event.target.closest('#end-room')) { endRoom(); return; }
    if(event.target.closest('#mic-toggle')) { state.recording?stopMicrophone():startMicrophone(); return; }
    const audioButton=event.target.closest('[data-load-audio]'); if(audioButton) { loadSegmentAudio(Number(audioButton.dataset.loadAudio),audioButton); return; }
    if(event.target.closest('#retry-room')) { const r=route(); if(r.kind==='admin') loadAdmin(r.id); else if(r.kind==='join') loadPublic(r.id); return; }
  });
  document.addEventListener('submit',(event)=>{ if(event.target.id==='create-form') { event.preventDefault(); createRoom(event.target); } });
  window.addEventListener('pagehide',()=>{ leaveRoom(); if(route().kind==='admin') stopMicrophone(); });

  async function init() {
    applyTranslations();
    const r=route();
    if(r.kind==='create') { renderCreate(); return; }
    if(r.kind==='admin') { state.adminToken=tokenFromLocation(); state.adminUrl=window.location.href; await loadAdmin(r.id); return; }
    state.listenerId=sessionStorage.getItem(`moin-live:${r.id}`) || null;
    state.joined=Boolean(state.listenerId);
    await loadPublic(r.id,state.joined);
  }
  init();
})();
