'use strict';
const welcomeCopy = {
  en: { title:'Moin — Follow Arabic teaching with care', skip:'Skip to content', studio:'Recording studio', videos:'Haramain videos', live:'Live translator', headline:'Translation as It Should Be', tryStudio:'Try the recording studio', seeHow:'See how it works ↓', exampleHeading:'One recording, clearer paths to understanding.', examplePreview:'Explore the recording studio, Haramain videos, or the live translator.' },
  ar: { title:'مُعين — تابع الدروس العربية بتأنٍ', skip:'انتقل إلى المحتوى', studio:'استوديو التسجيل', videos:'فيديوهات الحرمين', live:'المترجم المباشر', headline:'الترجمة كما يجب أن تكون...', tryStudio:'جرّب استوديو التسجيل', seeHow:'تعرّف على طريقة العمل ↓', exampleHeading:'تسجيل واحد، وطرق أوضح لفهمه.', examplePreview:'استكشف استوديو التسجيل، وفيديوهات الحرمين، والمترجم المباشر.' }
};
Object.assign(welcomeCopy.en, {
  exampleHeading:'Hear two translated examples.',
  sourceTitle:'Original Arabic audio', sourceDetail:'Recorded teaching · 8 seconds',
  audioFallback:'Your browser cannot play this audio.',
  transcriptLabel:'Machine-generated Arabic transcript', englishExample:'English example', frenchExample:'French example', englishLabel:'Machine-generated translation', frenchLabel:'Machine-generated translation',
  englishVoice:'English voice · ElevenLabs', frenchVoice:'French voice · ElevenLabs',
  imageFallback:'Product screenshot unavailable; the example and service links remain available.',
  pathsHeading:'Choose how you want to listen.',
  studioDetail:'Upload audio or video, or import a recorded YouTube lesson. Read the Arabic and translations together.',
  videosDetail:'Find recorded lessons from selected scholars at the Grand Mosque and the Prophet’s Mosque.',
  liveDetail:'Create a room and share a listener link for English or French text as speech is processed.',
  studioCaption:'The current recording studio', liveCaption:'The current live-room entry',
  stepsHeading:'From recording to reading in three steps.', step1Title:'Bring a recording', step1Detail:'Choose a file or a recorded YouTube lesson.',
  step2Title:'Let Moin prepare it', step2Detail:'Moin transcribes Arabic and prepares English and French text. Speech is offered when available.',
  step3Title:'Read with the original', step3Detail:'Compare each passage with its Arabic audio, and check important meanings carefully.',
  closingHeading:'Start with a voice worth listening to.', closingDetail:'Moin is an experimental aid for understanding. It does not replace careful review of religious meaning.', footer:'Made for careful listening.',
  resultAlt:'Moin recording reader showing a separate result with original audio, Arabic transcript and translation tabs',
  studioAlt:'Current Moin recording studio upload and YouTube import', liveAlt:'Current Moin live translator room form'
});
Object.assign(welcomeCopy.ar, {
  exampleHeading:'استمع إلى مثالين مترجمين.',
  sourceTitle:'الصوت العربي الأصلي', sourceDetail:'مقتطف من درس مسجّل · ٨ ثوانٍ',
  audioFallback:'يتعذر تشغيل الصوت في هذا المتصفح.',
  transcriptLabel:'النص العربي الناتج آليًا', englishExample:'المثال الإنجليزي', frenchExample:'المثال الفرنسي', englishLabel:'الترجمة الناتجة آليًا', frenchLabel:'الترجمة الناتجة آليًا',
  englishVoice:'الصوت الإنجليزي · ElevenLabs', frenchVoice:'الصوت الفرنسي · ElevenLabs',
  imageFallback:'تعذّر عرض لقطة المنتج؛ يبقى المثال وروابط الخدمات متاحين.',
  pathsHeading:'اختر طريقة الاستماع المناسبة لك.',
  studioDetail:'ارفع ملفًا صوتيًا أو مرئيًا، أو استورد درسًا مسجلًا من يوتيوب، ثم اقرأ النص العربي وترجماته معًا.',
  videosDetail:'تصفّح دروسًا مسجلة لمشايخ مختارين من المسجد الحرام والمسجد النبوي.',
  liveDetail:'أنشئ غرفة وشارك رابط المستمعين ليتابعوا النص بالإنجليزية أو الفرنسية أثناء معالجة الكلام.',
  studioCaption:'استوديو التسجيل الحالي', liveCaption:'صفحة إنشاء غرفة مباشرة الحالية',
  stepsHeading:'من التسجيل إلى القراءة في ثلاث خطوات.', step1Title:'أحضر تسجيلًا', step1Detail:'اختر ملفًا أو رابط درس مسجل من يوتيوب.',
  step2Title:'دع مُعين يجهّزه', step2Detail:'يحوّل مُعين الكلام العربي إلى نص ويعدّ ترجمتين إنجليزية وفرنسية، ويقدّم الصوت المترجم حين يتوفر.',
  step3Title:'اقرأ مع الرجوع للأصل', step3Detail:'قارن كل مقطع بصوته العربي، وراجع المعاني المهمة بعناية.',
  closingHeading:'ابدأ بصوت يستحق الإصغاء.', closingDetail:'مُعين أداة تجريبية للمساعدة على الفهم؛ ولا يغني عن مراجعة المعاني الشرعية بعناية.', footer:'صُنع للإصغاء بتأنٍ.',
  resultAlt:'قارئ نتائج مُعين يعرض نتيجة منفصلة بصوتها الأصلي ونصها العربي وألسنة الترجمات',
  studioAlt:'استوديو مُعين الحالي لرفع التسجيلات واستيراد روابط يوتيوب', liveAlt:'نموذج إنشاء غرفة المترجم المباشر في مُعين'
});
let welcomeLocale = MoinLocale.read();
function applyWelcomeLocale() {
  const copy = welcomeCopy[welcomeLocale];
  document.documentElement.lang = welcomeLocale;
  document.documentElement.dir = welcomeLocale === 'ar' ? 'rtl' : 'ltr';
  document.title = copy.title;
  document.querySelectorAll('[data-i18n]').forEach(el => {
    const value = copy[el.dataset.i18n];
    el.textContent = value;
  });
  document.querySelector('.welcome-brand').setAttribute('aria-label', welcomeLocale === 'ar' ? 'مُعين، الصفحة الرئيسية' : 'Moin home');
  document.querySelector('.welcome-nav').setAttribute('aria-label', welcomeLocale === 'ar' ? 'خدمات مُعين' : 'Moin services');
  document.querySelector('.locale-switch').setAttribute('aria-label', welcomeLocale === 'ar' ? 'لغة الواجهة' : 'Interface language');
  document.querySelectorAll('[data-locale]').forEach(button => button.setAttribute('aria-pressed', String(button.dataset.locale === welcomeLocale)));
  document.querySelectorAll('.product-shot img').forEach((image, index) => { image.alt = copy[['resultAlt', 'studioAlt', 'liveAlt'][index]]; });
  document.querySelectorAll('.example-content audio').forEach((player, index) => {
    player.setAttribute('aria-label', welcomeLocale === 'ar'
      ? ['تشغيل الصوت العربي الأصلي', 'تشغيل الترجمة الإنجليزية', 'تشغيل الترجمة الفرنسية'][index]
      : ['Play original Arabic audio', 'Play English translation', 'Play French translation'][index]);
  });
}
document.querySelectorAll('[data-locale]').forEach(button => button.addEventListener('click', () => {
  welcomeLocale = button.dataset.locale;
  MoinLocale.save(welcomeLocale);
  applyWelcomeLocale();
}));
applyWelcomeLocale();
document.querySelectorAll('.product-shot img').forEach(image => image.addEventListener('error', () => {
  image.hidden = true;
  image.parentElement.querySelector('.media-fallback').hidden = false;
}));
