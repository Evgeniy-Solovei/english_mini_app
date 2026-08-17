const state = {
  user: null,
  dashboard: null,
  lessons: [],
  exercises: [],
  exerciseIndex: 0,
  currentLesson: null,
  lessonStage: 'learn',
  selectedLessonLevel: null,
  selectedLessonTrack: 'main',
  words: [],
  books: [],
  reviews: [],
  reviewIndex: 0,
  recording: false,
  mediaRecorder: null,
  audioChunks: [],
  packs: [],
  dialogues: [],
  shadowPhrases: [],
  shadowIndex: 0,
  currentDialogue: null,
  dialogueTurn: 0,
};

const tg = window.Telegram?.WebApp;
if (tg) {
  tg.ready();
  tg.expand();
}

function getInitData() {
  return tg?.initData || '';
}

async function apiFetch(endpoint, options = {}) {
  const headers = { ...(options.headers || {}) };
  headers['X-Telegram-Init-Data'] = getInitData();
  if (options.body && typeof options.body === 'string') {
    headers['Content-Type'] = 'application/json';
  }
  const res = await fetchWithTimeout(`/api${endpoint}`, { ...options, headers });
  if (!res.ok) {
    const err = await res.json().catch(() => ({}));
    throw new Error(err.detail || err.message || `Сервер вернул ошибку ${res.status}`);
  }
  return res.json();
}

async function fetchWithTimeout(url, options = {}, timeoutMs = 20000) {
  const controller = new AbortController();
  const timer = setTimeout(() => controller.abort(), timeoutMs);
  try {
    return await fetch(url, { ...options, signal: controller.signal });
  } catch (error) {
    if (error.name === 'AbortError') {
      throw new Error('Сервер не ответил за 20 секунд. Проверьте интернет и попробуйте ещё раз.');
    }
    throw error;
  } finally {
    clearTimeout(timer);
  }
}

function escapeHtml(value) {
  return String(value ?? '').replace(/[&<>'"]/g, ch => ({
    '&': '&amp;', '<': '&lt;', '>': '&gt;', "'": '&#39;', '"': '&quot;',
  }[ch]));
}

function showToast(msg) {
  const t = document.getElementById('toast');
  if (!t) return;
  t.textContent = msg;
  t.classList.remove('hidden');
  setTimeout(() => t.classList.add('hidden'), 2500);
}

// ── Dashboard & Language Sync ──
async function loadDashboard() {
  try {
    state.dashboard = await apiFetch('/dashboard');
    renderDashboard();
  } catch (e) {
    console.error('Error loading dashboard:', e);
  }
}

function renderDashboard() {
  const d = state.dashboard;
  if (!d) return;

  const isEn = d.language_code === 'en';

  // Stats Header
  document.getElementById('user-name').textContent = tg?.initDataUnsafe?.user?.first_name || 'Learner';
  document.getElementById('hdr-welcome').textContent = isEn ? 'Welcome back' : 'С возвращением';
  document.getElementById('streak-count').textContent = d.streak_days;
  document.getElementById('streak-unit').textContent = isEn ? 'days' : 'дн.';

  // Level Card
  document.getElementById('level-tag').textContent = d.level.replace('_', '-');
  document.getElementById('level-name').textContent = getLevelLabel(d.level, isEn);
  document.getElementById('level-progress').style.width = `${d.level_progress}%`;
  document.getElementById('level-pct').textContent = `${Math.round(d.level_progress)}%`;
  document.getElementById('xp-count').textContent = `${d.total_xp} XP`;

  // Navigation Tab Labels
  document.getElementById('lbl-tab-home').textContent = isEn ? 'Home' : 'Главная';
  document.getElementById('lbl-tab-speak').textContent = isEn ? 'Speak' : 'Разговор';
  document.getElementById('lbl-tab-lessons').textContent = isEn ? 'Learn' : 'Уроки';
  document.getElementById('lbl-tab-library').textContent = isEn ? 'Read' : 'Чтение';
  document.getElementById('lbl-tab-profile').textContent = isEn ? 'Profile' : 'Профиль';

  // Home Banners
  document.getElementById('home-daily-title').textContent = isEn ? 'Active study today' : 'Активное обучение сегодня';
  document.getElementById('daily-goal-text').textContent = isEn ? `${d.minutes_today} / ${d.daily_goal} active min` : `${d.minutes_today} / ${d.daily_goal} активных мин`;
  document.getElementById('btn-start-daily').textContent = isEn ? 'Start' : 'Начать';

  document.getElementById('home-speak-title').textContent = isEn ? 'Speaking Practice' : 'Разговорная практика';
  const sp = d.speaking || {};
  const sg = sp.speak_goal || 10;
  document.getElementById('speak-goal-hint').textContent = isEn ? `Speak ${sg} min daily` : `Занимайтесь говорением ${sg} мин в день`;
  document.getElementById('btn-start-speak').textContent = isEn ? 'Speak' : 'Говорить';

  // Quick Start Labels
  document.getElementById('lbl-quick-start').textContent = isEn ? 'Quick Start' : 'Быстрый старт';
  document.getElementById('lbl-qs-speak').textContent = isEn ? 'Speak' : 'Разговор';
  document.getElementById('sub-qs-speak').textContent = isEn ? 'Dialogues & Phrases' : 'Диалоги и фразы';
  document.getElementById('lbl-qs-shadow').textContent = isEn ? 'Shadowing' : 'Повторение';
  document.getElementById('sub-qs-shadow').textContent = isEn ? 'Pronunciation' : 'Тренировка речи';
  document.getElementById('lbl-qs-exam').textContent = isEn ? 'Level Exam' : 'Экзамен';
  document.getElementById('sub-qs-exam').textContent = isEn ? 'Check Level' : 'Проверка уровня';
  document.getElementById('lbl-qs-review').textContent = isEn ? 'Vocabulary' : 'Словарь';
  document.getElementById('sub-qs-review').textContent = isEn ? 'SRS Review' : 'Повторение слов';
  document.getElementById('due-count').textContent = d.due_reviews || 0;

  // Skills
  document.getElementById('lbl-skills-title').textContent = isEn ? 'Skills Progress' : 'Прогресс навыков';
  const skillNamesMap = {
    listening: { en: 'Listening', ru: 'Слушание' },
    reading: { en: 'Reading', ru: 'Чтение' },
    writing: { en: 'Writing', ru: 'Письмо' },
    speaking: { en: 'Speaking', ru: 'Говорение' },
    grammar: { en: 'Grammar', ru: 'Грамматика' },
    vocabulary: { en: 'Vocabulary', ru: 'Словарь' },
  };
  const skillEmojis = { listening: '🎧', reading: '📖', writing: '✍️', speaking: '🗣', grammar: '📝', vocabulary: '📚' };

  document.getElementById('skills-grid').innerHTML = Object.entries(d.skills).map(([k, v]) => {
    const item = skillNamesMap[k] || { en: k, ru: k };
    return `<div class="skill-chip"><span class="skill-emoji">${skillEmojis[k] || '✨'}</span><span class="skill-name">${isEn ? item.en : item.ru}</span><span class="skill-val">${Math.round(v)}%</span></div>`;
  }).join('');

  document.getElementById('profile-skills').innerHTML = Object.entries(d.skills).map(([k, v]) => {
    const item = skillNamesMap[k] || { en: k, ru: k };
    return `<div class="skill-bar-item"><div class="skill-bar-header"><span>${skillEmojis[k] || ''} ${isEn ? item.en : item.ru}</span><span>${Math.round(v)}%</span></div><div class="skill-bar"><div class="skill-bar-fill" style="width:${v}%"></div></div></div>`;
  }).join('');

  // Profile Stats
  document.getElementById('stat-xp').textContent = d.total_xp;
  document.getElementById('stat-streak').textContent = d.streak_days;
  document.getElementById('stat-best').textContent = d.longest_streak;
  document.getElementById('stat-lessons').textContent = d.lessons_completed;

  document.getElementById('lbl-stat-xp').textContent = isEn ? 'Total XP' : 'Очки XP';
  document.getElementById('lbl-stat-streak').textContent = isEn ? 'Days Streak' : 'Дней подряд';
  document.getElementById('lbl-stat-best').textContent = isEn ? 'Best Record' : 'Рекорд дней';
  document.getElementById('lbl-stat-lessons').textContent = isEn ? 'Lessons Done' : 'Пройдено';
  document.getElementById('lbl-profile-skills-title').textContent = isEn ? 'Detailed Skill Progress' : 'Прогресс по навыкам';

  renderTrackControls();

  // Sync Settings Buttons active state
  syncProfileSettingsUI(d);
}

function getLevelLabel(code, isEn) {
  const map = {
    PRE_A1: isEn ? 'Pre-A1 (Starter)' : 'Pre-A1 (С нуля)',
    A1: isEn ? 'A1 Beginner' : 'A1 (Начинающий)',
    A2: isEn ? 'A2 Elementary' : 'A2 (Элементарный)',
    B1: isEn ? 'B1 Intermediate' : 'B1 (Средний)',
    B2: isEn ? 'B2 Upper-Int.' : 'B2 (Выше среднего)',
    C1: isEn ? 'C1 Advanced' : 'C1 (Продвинутый)',
  };
  return map[code] || code;
}

function syncProfileSettingsUI(d) {
  const isEn = d.language_code === 'en';
  // Lang
  document.querySelectorAll('#lang-options .settings-opt-btn').forEach(btn => {
    btn.classList.toggle('active', btn.dataset.lang === d.language_code);
  });
  // Goal
  document.querySelectorAll('#goal-options .settings-opt-btn').forEach(btn => {
    btn.classList.toggle('active', parseInt(btn.dataset.goal) === d.daily_goal);
  });
  // Course level: only levels with published lessons are selectable.
  const levelOptions = document.getElementById('level-options');
  if (levelOptions) {
    levelOptions.innerHTML = (d.available_levels || []).map(level =>
      `<button class="settings-opt-btn ${level === d.level ? 'active' : ''}" data-level="${level}">${level.replace('_', '-')}</button>`
    ).join('');
    levelOptions.querySelectorAll('.settings-opt-btn').forEach(btn => {
      btn.addEventListener('click', () => updateSetting({ current_level: btn.dataset.level }));
    });
  }
  document.getElementById('lbl-settings-level').textContent = isEn ? 'Course Level' : 'Уровень обучения';
  document.getElementById('settings-level-note').textContent = isEn
    ? 'Choose any published course. Progress on other levels is preserved.'
    : 'Можно выбрать любой опубликованный курс. Прогресс других уровней сохранится.';
}

async function updateSetting(data) {
  try {
    await apiFetch('/settings', { method: 'POST', body: JSON.stringify(data) });
    if (data.current_level) state.selectedLessonLevel = null;
    await loadDashboard();
    await loadLessons();
    showToast(state.dashboard?.language_code === 'en' ? 'Settings saved!' : 'Настройки сохранены!');
  } catch (e) {
    showToast('Error saving settings');
  }
}

// ── Lessons Tab ──
async function loadLessons(level = null) {
  const lvl = level || state.selectedLessonLevel || state.dashboard?.level || 'PRE_A1';
  try {
    state.lessons = await apiFetch(`/lessons?level=${lvl}`);
  } catch (_) {
    state.lessons = [];
  }
  renderLevelPills();
  renderLessons();
}

function renderLevelPills() {
  const container = document.getElementById('lessons-level-pills');
  if (!container) return;
  const isEn = state.dashboard?.language_code === 'en';
  const levels = (state.dashboard?.available_levels || ['PRE_A1']).map(code => ({
    code, label: code.replace('_', '-'),
  }));
  const activeLevel = state.selectedLessonLevel || state.dashboard?.level || 'PRE_A1';
  container.innerHTML = levels.map(l =>
    `<button class="level-pill ${l.code === activeLevel ? 'active' : ''}" data-lvl="${l.code}">${l.label}</button>`
  ).join('');

  container.querySelectorAll('.level-pill').forEach(btn => {
    btn.addEventListener('click', async () => {
      state.selectedLessonLevel = btn.dataset.lvl;
      renderLevelPills();
      await loadLessons(state.selectedLessonLevel);
    });
  });
}

function renderTrackControls() {
  const container = document.getElementById('course-track-tabs');
  if (!container) return;
  const isEn = state.dashboard?.language_code === 'en';
  container.querySelector('[data-track="main"]').textContent = isEn ? '📘 Main course' : '📘 Основной курс';
  container.querySelector('[data-track="it"]').textContent = '💻 English for IT';
  container.querySelectorAll('.course-track-btn').forEach(btn => {
    btn.classList.toggle('active', btn.dataset.track === state.selectedLessonTrack);
    btn.onclick = () => {
      state.selectedLessonTrack = btn.dataset.track;
      renderTrackControls();
      renderLessons();
    };
  });
  const note = document.getElementById('track-note');
  if (state.selectedLessonTrack === 'it') {
    note.textContent = isEn
      ? 'Backend English: devices, login, errors, API, PostgreSQL, Git, debugging and deployment.'
      : 'Английский для backend: устройства, логин, ошибки, API, PostgreSQL, Git, отладка и деплой.';
  } else {
    note.textContent = isEn
      ? 'Start with the alphabet and reading rules, then move on to everyday communication.'
      : 'Начните с алфавита и правил чтения, затем переходите к бытовому общению.';
  }
}

function renderLessons() {
  const list = document.getElementById('lessons-list');
  const isEn = state.dashboard?.language_code === 'en';
  const visibleLessons = state.lessons.filter(l => (l.track || 'main') === state.selectedLessonTrack);
  if (!visibleLessons.length) {
    list.innerHTML = `<p style="text-align:center;color:#8a8075;padding:20px">${isEn ? 'No lessons for this level yet' : 'Для этого уровня уроков пока нет'}</p>`;
    return;
  }
  list.innerHTML = visibleLessons.map((l, index) => `
    <div class="lesson-item ${l.status} ${l.is_locked ? 'locked' : ''}" data-id="${l.id}" data-locked="${l.is_locked ? '1' : '0'}">
      <div class="lesson-num">${l.is_locked ? '🔒' : (l.status === 'completed' ? '✓' : index + 1)}</div>
      <div class="lesson-info">
        <h3>${l.title}</h3>
        <p>${(!isEn && l.title_ru) ? l.title_ru + ' · ' : ''}${l.estimated_minutes} min</p>
        ${l.track === 'it' ? '<span class="lesson-track-tag">💻 English for IT</span>' : ''}
      </div>
      <div class="lesson-meta">
        ${l.score > 0 ? `<div>${Math.round(l.score)}%</div>` : ''}
        <div class="xp">+${l.xp_reward} XP</div>
      </div>
    </div>`).join('');

  list.querySelectorAll('.lesson-item').forEach(el => {
    el.addEventListener('click', () => {
      if (el.dataset.locked === '1') {
        showToast(isEn ? 'Complete the previous lesson first' : 'Сначала завершите предыдущий урок');
        return;
      }
      openLesson(parseInt(el.dataset.id));
    });
  });
}

async function openLesson(id) {
  try {
    showToast('Загружаю урок…');
    state.currentLesson = await apiFetch(`/lessons/${id}`);
    state.exercises = await apiFetch(`/lessons/${id}/exercises`);
    state.exerciseIndex = 0;
    state.lessonStage = 'learn';
    document.getElementById('lesson-title').textContent = state.currentLesson.title;
    renderLessonContent();
    document.getElementById('lesson-content').classList.remove('hidden');
    document.getElementById('exercise-area').classList.add('hidden');
    document.getElementById('lesson-overlay').classList.remove('hidden');
  } catch (error) {
    showToast(error.message || 'Не удалось загрузить урок. Попробуйте ещё раз.');
  }
}

function renderLessonContent() {
  const content = state.currentLesson.content;
  const el = document.getElementById('lesson-content');
  const isEn = state.dashboard?.language_code === 'en';

  if (!content?.blocks) {
    el.innerHTML = `<p>${state.currentLesson.description || ''}</p>`;
    return;
  }
  el.innerHTML = content.blocks.map(b => {
    if (b.type === 'text') return `<div class="lesson-block"><h3>${b.title || ''}</h3><p>${b.body}</p></div>`;
    if (b.type === 'example') return `<button type="button" class="lesson-block example-audio" data-audio="${escapeHtml(b.audio || b.en)}"><span class="example">🔊 ${b.en}${(!isEn && b.ru) ? `<br><small>${b.ru}</small>` : ''}</span></button>`;
    if (b.type === 'alphabet') {
      return `<div class="lesson-block"><h3>${b.title}</h3><div style="display:flex;flex-wrap:wrap;gap:6px;margin-top:8px">${b.letters.map(l =>
        `<button type="button" class="alphabet-key" data-audio="${escapeHtml(l.char.split(' ')[0])}"><b>${l.char}</b><small>${l.sound}</small><span>🔊</span></button>`
      ).join('')}</div></div>`;
    }
    if (b.type === 'reading') return `<div class="lesson-block"><h3>${b.title || 'Reading'}</h3><div class="reading-body">${b.body}</div></div>`;
    return '';
  }).join('') + `
    <div class="study-complete-card">
      <p>${isEn ? 'Listen to every example. When you are ready, the material will be hidden and practice will begin.' : 'Прослушайте буквы и примеры. После старта материал скроется — ответы списать будет нельзя.'}</p>
      <button class="btn-primary" id="btn-start-lesson-practice">${isEn ? 'Start practice' : 'Начать тренировку'}</button>
    </div>`;

  el.querySelectorAll('[data-audio]').forEach(button => {
    button.addEventListener('click', () => playTts(button.dataset.audio || ''));
  });
  document.getElementById('btn-start-lesson-practice')?.addEventListener('click', startLessonPractice);
}

function startLessonPractice() {
  state.lessonStage = 'practice';
  document.getElementById('lesson-content').classList.add('hidden');
  document.getElementById('exercise-area').classList.remove('hidden');
  renderExercise();
  document.getElementById('lesson-overlay').scrollTo({ top: 0, behavior: 'smooth' });
}

function renderExercise() {
  const area = document.getElementById('exercise-area');
  const isEn = state.dashboard?.language_code === 'en';

  if (!state.exercises.length) {
    area.innerHTML = `<p style="text-align:center;padding:20px">${isEn ? 'No exercises in this lesson' : 'В этом уроке пока нет упражнений'}</p>`;
    return;
  }
  const ex = state.exercises[state.exerciseIndex];
  const progress = `${state.exerciseIndex + 1} / ${state.exercises.length}`;

  let instruction = isEn ? 'Exercise:' : 'Задание:';
  if (isEn) {
    if (ex.exercise_type === 'mc') instruction = 'Choose the correct answer:';
    else if (ex.exercise_type === 'fill') instruction = 'Fill in the blank:';
    else if (ex.exercise_type === 'translate') instruction = 'Translate to English:';
    else if (ex.exercise_type === 'speak') instruction = 'Listen and speak out loud:';
    else if (ex.exercise_type === 'listen') instruction = 'Listen and choose the answer:';
    else if (ex.exercise_type === 'read') instruction = 'Read and choose the answer:';
    else if (ex.exercise_type === 'write') instruction = 'Write a short answer:';
  } else {
    if (ex.exercise_type === 'mc') instruction = 'Выберите правильный вариант ответа:';
    else if (ex.exercise_type === 'fill') instruction = 'Вставьте пропущенное слово:';
    else if (ex.exercise_type === 'translate') instruction = 'Переведите предложение на английский язык:';
    else if (ex.exercise_type === 'speak') instruction = 'Прослушайте и произнесите фразу:';
    else if (ex.exercise_type === 'listen') instruction = 'Прослушайте и выберите ответ:';
    else if (ex.exercise_type === 'read') instruction = 'Прочитайте и выберите ответ:';
    else if (ex.exercise_type === 'write') instruction = 'Напишите короткий ответ:';
  }

  let body = '';
  if (ex.exercise_type === 'mc' || ex.exercise_type === 'listen' || ex.exercise_type === 'read') {
    const listenButton = ex.exercise_type === 'listen'
      ? `<button class="btn-audio" id="btn-listen-exercise">🔊 ${isEn ? 'Play audio' : 'Прослушать'}</button>`
      : '';
    body = `${listenButton}<div class="options-list">${(ex.data.options || []).map((o, i) => `<button class="option-btn" data-option="${i}">${escapeHtml(o)}</button>`).join('')}</div>`;
  } else if (ex.exercise_type === 'speak') {
    body = `<p style="text-align:center;margin:12px 0;color:#8a8075">Say: «${ex.data.audio_text || ''}»</p>
            <button class="btn-record" id="btn-speak-exercise">🎤 ${isEn ? 'Record Answer' : 'Записать ответ'}</button>`;
  } else if (ex.exercise_type === 'write') {
    body = `<textarea class="fill-input writing-input" id="fill-answer" rows="5" placeholder="${isEn ? `Write at least ${ex.data.min_words || 4} words...` : `Напишите минимум ${ex.data.min_words || 4} английских слов...`}"></textarea>
            <button class="btn-primary" style="margin-top:12px;width:100%" id="btn-submit-fill">${isEn ? 'Check' : 'Проверить'}</button>`;
  } else {
    body = `<input class="fill-input" id="fill-answer" placeholder="${isEn ? 'Type your answer...' : 'Введите ваш ответ'}" autocomplete="off">
            <button class="btn-primary" style="margin-top:12px;width:100%" id="btn-submit-fill">${isEn ? 'Check' : 'Проверить'}</button>`;
  }

  area.innerHTML = `
    <div class="exercise-card">
      <div style="font-size:12px;color:#8a8075;margin-bottom:6px">${progress} · +${ex.points} XP</div>
      <div style="font-size:13px;font-weight:600;color:var(--accent);margin-bottom:8px">${instruction}</div>
      <h3 style="margin-bottom:12px">${ex.question}</h3>
      ${(!isEn && ex.question_ru) ? `<p style="font-size:13px;color:#8a8075;margin-bottom:12px">${ex.question_ru}</p>` : ''}
      ${body}
      <div id="exercise-feedback"></div>
      <div class="exercise-nav">
        ${state.exerciseIndex > 0 ? `<button class="btn-back" id="btn-prev-ex">← ${isEn ? 'Prev' : 'Назад'}</button>` : '<span></span>'}
        ${state.exerciseIndex < state.exercises.length - 1 ? `<button class="btn-primary" id="btn-next-ex" style="display:none">${isEn ? 'Next →' : 'Далее →'}</button>` : ''}
      </div>
    </div>`;

  area.querySelectorAll('.option-btn').forEach(btn => btn.addEventListener('click', () => submitAnswer(ex.data.options[Number(btn.dataset.option)], btn)));
  document.getElementById('btn-listen-exercise')?.addEventListener('click', () => playTts(ex.data.audio_text || ''));
  document.getElementById('btn-submit-fill')?.addEventListener('click', () => submitAnswer(document.getElementById('fill-answer').value));
  document.getElementById('fill-answer')?.addEventListener('keydown', event => {
    if (event.key === 'Enter') submitAnswer(event.currentTarget.value);
  });
  document.getElementById('btn-speak-exercise')?.addEventListener('click', () => recordAndScore(
    ex.data.audio_text || '',
    async result => submitAnswer(result.spoken || ''),
  ));
  document.getElementById('btn-prev-ex')?.addEventListener('click', () => { state.exerciseIndex--; renderExercise(); });
  document.getElementById('btn-next-ex')?.addEventListener('click', () => { state.exerciseIndex++; renderExercise(); });
}

async function submitAnswer(answer, btnEl) {
  const ex = state.exercises[state.exerciseIndex];
  const isEn = state.dashboard?.language_code === 'en';
  try {
    const result = await apiFetch(`/exercises/${ex.id}/answer`, { method: 'POST', body: JSON.stringify({ answer }) });
    const fb = document.getElementById('exercise-feedback');

    if (result.is_correct) {
      // ✅ Correct Answer -> Show success feedback and advance
      fb.className = 'exercise-feedback correct';
      fb.textContent = isEn ? `✅ Correct! +${result.xp_earned} XP` : `✅ Правильно! +${result.xp_earned} XP`;
      btnEl?.classList.add('correct');

      document.getElementById('exercise-area').querySelectorAll('.option-btn, .fill-input, #btn-submit-fill, #btn-speak-exercise').forEach(el => {
        el.disabled = true; el.style.pointerEvents = 'none';
      });

      const isLastExercise = state.exerciseIndex >= state.exercises.length - 1;
      if (isLastExercise) {
        setTimeout(async () => {
          showLessonCompletionCard(result);
          await loadDashboard();
          await loadLessons();
        }, 1200);
      } else {
        setTimeout(() => {
          state.exerciseIndex++;
          renderExercise();
        }, 1200);
      }
    } else {
      // ❌ Incorrect Answer -> Stay on current exercise and allow trying again!
      fb.className = 'exercise-feedback wrong';
      fb.textContent = isEn
        ? `❌ Incorrect. Try again! ${result.explanation ? '(' + result.explanation + ')' : ''}`
        : `❌ Неправильно. Попробуйте ещё раз! ${result.explanation ? '(' + result.explanation + ')' : ''}`;

      btnEl?.classList.add('wrong');
      setTimeout(() => btnEl?.classList.remove('wrong'), 900);

      const fillInput = document.getElementById('fill-answer');
      if (fillInput) {
        fillInput.value = '';
        fillInput.focus();
      }
    }
  } catch (e) {
    showToast(isEn ? 'Error submitting answer' : 'Ошибка отправки ответа');
  }
}

function showLessonCompletionCard(result) {
  const area = document.getElementById('exercise-area');
  const isEn = state.dashboard?.language_code === 'en';
  const xp = result?.xp_earned !== undefined ? result.xp_earned : 0;
  area.innerHTML = `
    <div class="completion-card">
      <span class="completion-emoji">🎉</span>
      <h2 class="completion-title">${isEn ? 'Lesson Completed!' : 'Урок пройден!'}</h2>
      <p class="completion-sub">${isEn ? 'Great job! You made another step toward fluent English.' : 'Отличная работа! Вы сделали шаг к свободному английскому.'}</p>
      <div class="completion-stats">
        <div class="comp-stat-badge">⭐ +${xp} XP</div>
        <div class="comp-stat-badge">🔥 ${isEn ? 'Daily streak active' : 'Дневная серия активна'}</div>
      </div>
      <div style="display:flex;gap:8px">
        <button class="btn-secondary" style="flex:1" id="btn-comp-retake">${isEn ? '🔁 Retake' : '🔁 Пройти заново'}</button>
        <button class="btn-primary" style="flex:1" id="btn-comp-home">${isEn ? 'Home' : 'На главную'}</button>
      </div>
    </div>`;

  document.getElementById('btn-comp-retake')?.addEventListener('click', async () => {
    state.exercises = await apiFetch(`/lessons/${state.currentLesson.id}/exercises`);
    state.exerciseIndex = 0;
    renderExercise();
  });
  document.getElementById('btn-comp-home')?.addEventListener('click', closeLessonAndGoHome);
}

function closeLessonAndGoHome() {
  document.getElementById('lesson-overlay')?.classList.add('hidden');
  document.getElementById('tab-btn-home')?.click();
}

// ── Tab Setup & Button Bindings ──
function setupTabs() {
  document.querySelectorAll('.nav-tab').forEach(tab => {
    tab.addEventListener('click', () => {
      document.querySelectorAll('.nav-tab').forEach(t => t.classList.remove('active'));
      document.querySelectorAll('.tab-content').forEach(t => t.classList.remove('active'));
      tab.classList.add('active');
      const target = document.getElementById(`tab-${tab.dataset.tab}`);
      if (target) target.classList.add('active');

      if (tab.dataset.tab === 'lessons' && !state.lessons.length) loadLessons();
      if (tab.dataset.tab === 'library' && !state.books.length) loadBooks();
      if (tab.dataset.tab === 'speak' && !state.packs.length) loadSpeakData();
    });
  });

  document.querySelectorAll('.speak-subtab').forEach(tab => {
    tab.addEventListener('click', () => {
      document.querySelectorAll('.speak-subtab').forEach(t => t.classList.remove('active'));
      tab.classList.add('active');
      const key = tab.dataset.speak;
      document.getElementById('speak-panel-shadow').classList.toggle('hidden', key !== 'shadow');
      document.getElementById('speak-panel-talk').classList.toggle('hidden', key !== 'talk');
      document.getElementById('speak-panel-phonetics').classList.toggle('hidden', key !== 'phonetics');
      renderPacks();
    });
  });

  document.querySelectorAll('.lib-tab').forEach(tab => {
    tab.addEventListener('click', () => {
      document.querySelectorAll('.lib-tab').forEach(t => t.classList.remove('active'));
      tab.classList.add('active');
      const isBooks = tab.dataset.lib === 'books';
      document.getElementById('library-books').classList.toggle('hidden', !isBooks);
      document.getElementById('library-words').classList.toggle('hidden', isBooks);
      if (isBooks && !state.books.length) loadBooks();
      if (!isBooks && !state.words.length) loadWords();
    });
  });
}

function setupButtons() {
  // Start Banners
  document.getElementById('btn-start-daily')?.addEventListener('click', () => {
    document.getElementById('tab-btn-lessons')?.click();
  });

  document.getElementById('btn-start-speak')?.addEventListener('click', () => {
    document.getElementById('tab-btn-speak')?.click();
  });

  // Quick Action Cards
  document.querySelectorAll('.quick-card[data-action]').forEach(card => {
    card.addEventListener('click', () => {
      const action = card.dataset.action;
      if (action === 'speak') {
        document.getElementById('tab-btn-speak')?.click();
        document.getElementById('subtab-talk')?.click();
      } else if (action === 'shadow') {
        document.getElementById('tab-btn-speak')?.click();
        document.getElementById('subtab-shadow')?.click();
      } else if (action === 'exam') {
        openExam();
      }
    });
  });

  document.getElementById('card-review')?.addEventListener('click', () => {
    loadReviews();
    document.getElementById('review-overlay').classList.remove('hidden');
  });

  // Profile Settings Event Handlers
  document.querySelectorAll('#lang-options .settings-opt-btn').forEach(btn => {
    btn.addEventListener('click', () => {
      updateSetting({ language_code: btn.dataset.lang });
    });
  });

  document.querySelectorAll('#goal-options .settings-opt-btn').forEach(btn => {
    btn.addEventListener('click', () => {
      updateSetting({ daily_goal_minutes: parseInt(btn.dataset.goal) });
    });
  });

  // Overlays Close
  document.getElementById('btn-back-review')?.addEventListener('click', () => document.getElementById('review-overlay').classList.add('hidden'));
  document.getElementById('btn-back-reading')?.addEventListener('click', () => document.getElementById('reading-overlay').classList.add('hidden'));
  document.getElementById('btn-back-lesson')?.addEventListener('click', () => document.getElementById('lesson-overlay').classList.add('hidden'));
  document.getElementById('btn-back-shadow')?.addEventListener('click', () => document.getElementById('shadow-overlay').classList.add('hidden'));
  document.getElementById('btn-back-dialogue')?.addEventListener('click', () => document.getElementById('dialogue-overlay').classList.add('hidden'));
  document.getElementById('btn-back-exam')?.addEventListener('click', () => document.getElementById('exam-overlay').classList.add('hidden'));

  document.getElementById('btn-shadow-slow')?.addEventListener('click', () => playTts(state.shadowPhrases[state.shadowIndex]?.english || '', true));
  document.getElementById('btn-shadow-listen')?.addEventListener('click', () => playTts(state.shadowPhrases[state.shadowIndex]?.english || ''));
  document.getElementById('btn-shadow-record')?.addEventListener('click', () => {
    const phrase = state.shadowPhrases[state.shadowIndex];
    if (!phrase) return;
    recordAndScore(phrase.english, result => {
      const card = document.getElementById('shadow-score');
      card.textContent = `${result.passed ? '✅' : '🔄'} ${result.feedback} (${result.score}%)`;
      card.classList.remove('hidden');
    }, phrase.id);
  });
  document.getElementById('btn-shadow-prev')?.addEventListener('click', () => {
    if (state.shadowIndex > 0) state.shadowIndex--;
    renderShadowPhrase();
  });
  document.getElementById('btn-shadow-next')?.addEventListener('click', () => {
    if (state.shadowIndex < state.shadowPhrases.length - 1) {
      state.shadowIndex++;
      renderShadowPhrase();
    } else {
      document.getElementById('shadow-overlay').classList.add('hidden');
      loadDashboard();
    }
  });

  document.getElementById('btn-dialogue-type')?.addEventListener('click', () => document.getElementById('type-reply-box').classList.toggle('hidden'));
  document.getElementById('btn-dialogue-send')?.addEventListener('click', () => sendDialogueReply(document.getElementById('dialogue-text-input').value));
  document.getElementById('dialogue-text-input')?.addEventListener('keydown', event => {
    if (event.key === 'Enter') sendDialogueReply(event.currentTarget.value);
  });
  document.getElementById('btn-dialogue-record')?.addEventListener('click', () => {
    recordDialogueReply();
  });
}

// ── Additional Loaders (Books, Words, Speak, SRS) ──
async function loadBooks() {
  try {
    state.books = await apiFetch('/reading/texts');
    renderBooks();
  } catch (_) { state.books = []; }
}

function renderBooks() {
  const container = document.getElementById('library-books');
  const isEn = state.dashboard?.language_code === 'en';
  if (!state.books.length) {
    container.innerHTML = `<p style="text-align:center;color:#8a8075;padding:20px">${isEn ? 'No books available yet' : 'Книг пока нет'}</p>`;
    return;
  }
  container.innerHTML = state.books.map(b => `
    <div class="book-card" data-id="${b.id}">
      <div class="book-cover">${escapeHtml(b.cover_emoji || '📖')}</div>
      <div class="book-info">
        <h3>${escapeHtml(b.title)}</h3>
        <p>${(!isEn && b.title_ru) ? escapeHtml(b.title_ru) + ' · ' : ''}${escapeHtml(b.level)} · ${b.chapter_count} ${isEn ? 'chapters' : 'глав'}</p>
      </div>
    </div>`).join('');

  container.querySelectorAll('.book-card').forEach(card => {
    card.addEventListener('click', () => openBook(parseInt(card.dataset.id)));
  });
}

async function openBook(id) {
  const book = await apiFetch(`/reading/texts/${id}`);
  const isEn = state.dashboard?.language_code === 'en';
  document.getElementById('reading-title').textContent = book.title;
  document.getElementById('reading-meta').textContent = `${book.author || ''} · ${book.level} · ${book.total_words} слов`;
  const chapters = document.getElementById('chapter-list');
  chapters.innerHTML = book.chapters.map(ch => `
    <button class="chapter-item" data-index="${ch.index}">
      <strong>${escapeHtml(ch.title)}</strong><span>${ch.word_count} слов</span>
    </button>`).join('');
  chapters.querySelectorAll('.chapter-item').forEach(button => button.addEventListener('click', () => openChapter(id, Number(button.dataset.index))));
  chapters.classList.remove('hidden');
  document.getElementById('reading-text').classList.add('hidden');
  document.getElementById('reading-overlay').classList.remove('hidden');
}

async function openChapter(bookId, index) {
  const chapter = await apiFetch(`/library/${bookId}/chapter/${index}`);
  const isEn = state.dashboard?.language_code === 'en';
  const reading = document.getElementById('reading-text');
  reading.innerHTML = `
    <button class="btn-back" id="btn-back-chapters">← ${isEn ? 'Chapters' : 'К главам'}</button>
    <h3>${escapeHtml(chapter.title)}</h3>
    <div style="display:flex;gap:8px;margin:10px 0">
      <button class="btn-audio" id="btn-read-female">🔊 ${isEn ? 'Female voice' : 'Женский голос'}</button>
      <button class="btn-audio" id="btn-read-male">🔊 ${isEn ? 'Male voice' : 'Мужской голос'}</button>
    </div>
    <div style="line-height:1.8;font-size:16px;white-space:pre-wrap">${escapeHtml(chapter.text)}</div>
    ${(!isEn && chapter.text_ru) ? `<div class="trans-block"><strong>🇷🇺 Перевод</strong><br>${escapeHtml(chapter.text_ru)}</div>` : ''}`;
  document.getElementById('chapter-list').classList.add('hidden');
  reading.classList.remove('hidden');
  document.getElementById('btn-back-chapters').addEventListener('click', () => {
    reading.classList.add('hidden');
    document.getElementById('chapter-list').classList.remove('hidden');
  });
  document.getElementById('btn-read-female').addEventListener('click', () => playTts(chapter.text, false, 'female'));
  document.getElementById('btn-read-male').addEventListener('click', () => playTts(chapter.text, false, 'male'));
}

async function loadWords() {
  try {
    state.words = await apiFetch('/srs/items');
    renderWords();
  } catch (_) { state.words = []; }
}

function renderWords() {
  const container = document.getElementById('library-words');
  const isEn = state.dashboard?.language_code === 'en';
  if (!state.words.length) {
    container.innerHTML = `<p style="text-align:center;color:#8a8075;padding:20px">${isEn ? 'No saved words yet' : 'Ваш словарь пока пуст'}</p>`;
    return;
  }
  container.innerHTML = state.words.map(w => `
    <div class="word-row">
      <span class="word-en">${w.front}</span>
      <span class="word-ru">${w.back}</span>
    </div>`).join('');
}

async function loadReviews() {
  try {
    state.reviews = await apiFetch('/srs/due');
    state.reviewIndex = 0;
    renderReviewCard();
  } catch (_) { state.reviews = []; }
}

function renderReviewCard() {
  const empty = document.getElementById('review-empty');
  const card = document.getElementById('review-card');
  if (!state.reviews.length || state.reviewIndex >= state.reviews.length) {
    empty.classList.remove('hidden');
    card.classList.add('hidden');
    return;
  }
  empty.classList.add('hidden');
  card.classList.remove('hidden');

  const item = state.reviews[state.reviewIndex];
  document.getElementById('review-front').textContent = item.front;
  document.getElementById('review-back').textContent = item.back;
  document.getElementById('review-back').classList.add('hidden');
  document.getElementById('review-rating').classList.add('hidden');
  document.getElementById('btn-show-answer').classList.remove('hidden');
}

document.getElementById('btn-show-answer')?.addEventListener('click', () => {
  document.getElementById('review-back').classList.remove('hidden');
  document.getElementById('review-rating').classList.remove('hidden');
  document.getElementById('btn-show-answer').classList.add('hidden');
});

document.querySelectorAll('#review-rating button').forEach(btn => {
  btn.addEventListener('click', async () => {
    const item = state.reviews[state.reviewIndex];
    const q = parseInt(btn.dataset.q);
    await apiFetch(`/srs/${item.id}/rate`, { method: 'POST', body: JSON.stringify({ quality: q }) });
    state.reviewIndex++;
    renderReviewCard();
    await loadDashboard();
  });
});

async function loadSpeakData() {
  try {
    [state.packs, state.dialogues] = await Promise.all([
      apiFetch('/shadowing/packs'),
      apiFetch('/speak/dialogues'),
    ]);
    renderPacks();
    renderDialogues();
  } catch (e) { showToast(e.message); }
}

function renderPacks() {
  const list = document.getElementById('packs-list');
  const isEn = state.dashboard?.language_code === 'en';
  const active = document.querySelector('.speak-subtab.active')?.dataset.speak || 'shadow';
  const wantedType = active === 'phonetics' ? 'phonetics' : null;
  const packs = state.packs.filter(p => wantedType ? p.pack_type === wantedType : p.pack_type !== 'phonetics');
  const target = active === 'phonetics' ? document.getElementById('phonetics-list') : list;
  if (!packs.length) {
    target.innerHTML = `<p style="text-align:center;color:#8a8075;padding:20px">${isEn ? 'No practice packs available' : 'Наборы для практики пока не загружены'}</p>`;
    return;
  }
  target.innerHTML = packs.map(p => `
    <button class="pack-card" data-id="${p.id}">
      <div class="pack-emoji">${escapeHtml(p.emoji || '🎧')}</div>
      <div class="pack-info">
        <h3>${escapeHtml(!isEn && p.title_ru ? p.title_ru : p.title)}</h3>
        <p>${p.phrase_count} ${isEn ? 'phrases' : 'фраз'}</p>
      </div>
    </button>`).join('');
  target.querySelectorAll('.pack-card').forEach(card => card.addEventListener('click', () => openShadowPack(Number(card.dataset.id))));
}

function renderDialogues() {
  const list = document.getElementById('dialogues-list');
  const isEn = state.dashboard?.language_code === 'en';
  list.innerHTML = state.dialogues.map(d => `
    <button class="pack-card" data-id="${d.id}">
      <div class="pack-emoji">${escapeHtml(d.emoji || '💬')}</div>
      <div class="pack-info"><h3>${escapeHtml(!isEn && d.title_ru ? d.title_ru : d.title)}</h3>
      <p>${escapeHtml(d.setting)} · ${d.turn_count} ${isEn ? 'steps' : 'шагов'}${d.completed ? ' · ✓' : ''}</p></div>
    </button>`).join('') || `<p class="panel-hint">${isEn ? 'No dialogues yet' : 'Диалогов пока нет'}</p>`;
  list.querySelectorAll('.pack-card').forEach(card => card.addEventListener('click', () => openDialogue(Number(card.dataset.id))));
}

async function openShadowPack(packId) {
  state.shadowPhrases = await apiFetch(`/speak/packs/${packId}/phrases`);
  state.shadowIndex = 0;
  const pack = state.packs.find(p => p.id === packId);
  document.getElementById('shadow-title').textContent = pack?.title_ru || pack?.title || 'Повторение';
  renderShadowPhrase();
  document.getElementById('shadow-overlay').classList.remove('hidden');
}

function renderShadowPhrase() {
  const phrase = state.shadowPhrases[state.shadowIndex];
  if (!phrase) return;
  document.getElementById('shadow-progress-label').textContent = `${state.shadowIndex + 1} / ${state.shadowPhrases.length}`;
  document.getElementById('shadow-phrase').textContent = phrase.english;
  document.getElementById('shadow-ru').textContent = phrase.russian;
  document.getElementById('shadow-phonetic').textContent = phrase.phonetic;
  document.getElementById('shadow-tip').textContent = phrase.tip;
  document.getElementById('shadow-score').classList.add('hidden');
  document.getElementById('btn-shadow-prev').disabled = state.shadowIndex === 0;
  document.getElementById('btn-shadow-next').textContent = state.shadowIndex === state.shadowPhrases.length - 1 ? 'Готово ✓' : 'Далее →';
}

function playTts(text, slow = false, voice = '') {
  const selectedVoice = voice || (text.length % 2 ? 'female' : 'male');
  const player = new Audio(`/voice/tts/?text=${encodeURIComponent(text)}&slow=${slow ? '1' : '0'}&voice=${encodeURIComponent(selectedVoice)}`);
  const timeout = setTimeout(() => {
    player.pause();
    showToast('Аудио не загрузилось. Проверьте соединение и нажмите ещё раз.');
  }, 15000);
  const clearAudioTimeout = () => clearTimeout(timeout);
  player.addEventListener('playing', clearAudioTimeout, { once: true });
  player.addEventListener('error', () => {
    clearAudioTimeout();
    showToast('Не удалось загрузить аудио. Нажмите ещё раз.');
  }, { once: true });
  player.play().catch(() => {
    clearAudioTimeout();
    showToast('Не удалось воспроизвести аудио.');
  });
}

async function openDialogue(id) {
  state.currentDialogue = await apiFetch(`/speak/dialogues/${id}`);
  state.dialogueTurn = state.currentDialogue.current_turn || 0;
  document.getElementById('dialogue-title').textContent = state.currentDialogue.title_ru || state.currentDialogue.title;
  const chat = document.getElementById('chat-box');
  chat.innerHTML = '';
  const firstBot = state.currentDialogue.turns.find((t, i) => i >= state.dialogueTurn && t.role === 'bot');
  if (firstBot) {
    appendChat('bot', firstBot.text);
    playTts(firstBot.text, false, 'female');
  }
  renderDialogueHint();
  document.getElementById('dialogue-overlay').classList.remove('hidden');
}

function appendChat(role, text) {
  const line = document.createElement('div');
  line.className = `chat-message ${role}`;
  line.textContent = text;
  document.getElementById('chat-box').appendChild(line);
}

function renderDialogueHint() {
  const turn = state.currentDialogue?.turns.find((t, i) => i >= state.dialogueTurn && t.role === 'user');
  document.getElementById('dialogue-hint').textContent = turn?.hint_ru ? `Подсказка: ${turn.hint_ru}` : '';
}

async function sendDialogueReply(spoken) {
  if (!spoken.trim()) return;
  appendChat('user', spoken);
  const result = await apiFetch(`/speak/dialogues/${state.currentDialogue.id}/reply`, {
    method: 'POST', body: JSON.stringify({ spoken, turn_index: state.dialogueTurn }),
  });
  renderDialogueResult(result);
}

function renderDialogueResult(result) {
  const score = document.getElementById('dialogue-score');
  score.textContent = `${result.passed ? '✅' : '🔄'} ${result.feedback} (${result.score}%)`;
  score.classList.remove('hidden');
  if (result.next_bot?.text) {
    appendChat('bot', result.next_bot.text);
    playTts(result.next_bot.text, false, state.dialogueTurn % 2 ? 'male' : 'female');
  }
  state.dialogueTurn = result.next_turn_index;
  if (result.finished) {
    document.getElementById('dialogue-hint').textContent = 'Диалог завершён! Отличная работа.';
  } else {
    renderDialogueHint();
  }
  document.getElementById('dialogue-text-input').value = '';
}

async function recordDialogueReply() {
  if (state.recording && state.mediaRecorder) {
    state.mediaRecorder.stop();
    return;
  }
  try {
    const stream = await navigator.mediaDevices.getUserMedia({ audio: true });
    state.mediaRecorder = new MediaRecorder(stream);
    state.audioChunks = [];
    state.mediaRecorder.ondataavailable = event => state.audioChunks.push(event.data);
    state.mediaRecorder.onstop = async () => {
      state.recording = false;
      stream.getTracks().forEach(track => track.stop());
      const mimeType = state.mediaRecorder.mimeType || 'audio/webm';
      const form = new FormData();
      form.append('audio', new Blob(state.audioChunks, { type: mimeType }), 'dialogue.webm');
      form.append('turn_index', String(state.dialogueTurn));
      try {
        const response = await fetchWithTimeout(`/api/speak/dialogues/${state.currentDialogue.id}/reply`, {
          method: 'POST', headers: { 'X-Telegram-Init-Data': getInitData() }, body: form,
        });
        const result = await response.json();
        if (!response.ok) throw new Error(result.detail || 'Voice recognition failed');
        appendChat('user', result.spoken || '…');
        renderDialogueResult(result);
      } catch (error) {
        showToast(error.message || 'Не удалось распознать ответ');
      }
    };
    state.mediaRecorder.start();
    state.recording = true;
    showToast('Запись идёт. Нажмите ещё раз, когда закончите.');
  } catch (_) {
    showToast('Нет доступа к микрофону.');
  }
}

async function openExam() {
  const lvl = state.dashboard?.level || 'PRE_A1';
  try {
    const exam = await apiFetch(`/exam/${lvl}`);
    document.getElementById('exam-title').textContent = exam.title;
    let html = `<p style="margin-bottom:16px;color:#8a8075">${exam.description}</p>`;
    html += exam.questions.map((q, i) => {
      const isChoice = ['mc', 'listening', 'reading'].includes(q.type) && q.options;
      const listen = q.type === 'listening'
        ? `<button type="button" class="btn-audio exam-listen" data-text="${encodeURIComponent(q.audio_text || '')}">🔊 Listen</button>` : '';
      const speak = q.type === 'speaking'
        ? `<button type="button" class="btn-record exam-record" data-index="${i}" data-expected="${encodeURIComponent(q.question || '')}">🎤 Record</button>` : '';
      const answer = isChoice
        ? `<div class="options-list">${q.options.map((option, optionIndex) => `<label class="option-btn"><input type="radio" name="exam-q${i}" value="${optionIndex}"> ${escapeHtml(option)}</label>`).join('')}</div>`
        : `${q.type === 'writing' ? `<textarea class="fill-input writing-input" rows="5" id="exam-q${i}"></textarea>` : `<input class="fill-input" id="exam-q${i}" placeholder="${state.dashboard?.language_code === 'en' ? 'Type answer...' : 'Введите ответ...'}">`}${speak}`;
      return `<div style="background:#fff;border-radius:12px;padding:14px;margin-bottom:12px;border:1px solid #e8e2d9">
        <p style="font-weight:600;margin-bottom:8px">${i + 1}. ${escapeHtml(q.question)}</p>${listen}${answer}</div>`;
    }).join('');
    html += `<button class="btn-primary" style="width:100%;margin-top:12px" id="btn-submit-exam">${state.dashboard?.language_code === 'en' ? 'Submit Exam' : 'Завершить экзамен'}</button>`;
    document.getElementById('exam-content').innerHTML = html;
    document.getElementById('exam-overlay').classList.remove('hidden');

    document.querySelectorAll('.exam-listen').forEach(btn => {
      btn.addEventListener('click', () => playTts(decodeURIComponent(btn.dataset.text || '')));
    });
    document.querySelectorAll('.exam-record').forEach(btn => {
      btn.addEventListener('click', () => recordToText(
        text => { document.getElementById(`exam-q${btn.dataset.index}`).value = text; },
      ));
    });

    document.getElementById('btn-submit-exam')?.addEventListener('click', async () => {
      const answers = {};
      exam.questions.forEach((q, i) => {
        if (['mc', 'listening', 'reading'].includes(q.type) && q.options) {
          const selected = document.querySelector(`input[name="exam-q${i}"]:checked`);
          answers[i] = selected ? q.options[Number(selected.value)] : '';
        } else {
          answers[i] = document.getElementById(`exam-q${i}`)?.value || '';
        }
      });
      const res = await apiFetch(`/exam/${lvl}/submit`, { method: 'POST', body: JSON.stringify({ answers }) });
      document.getElementById('exam-content').innerHTML = `
        <div style="text-align:center;padding:20px">
          <h2>${res.passed ? '🎉 Passed!' : '📚 Keep practicing!'}</h2>
          <p style="font-size:18px;margin:12px 0">Score: ${res.score}%</p>
          <p style="font-size:13px;color:#8a8075">${Object.entries(res.skill_scores || {}).map(([k,v]) => `${k}: ${v}%`).join(' · ')}</p>
          <button class="btn-primary" onclick="document.getElementById('exam-overlay').classList.add('hidden')">Close</button>
        </div>`;
      await loadDashboard();
    });
  } catch (e) {
    showToast('Error loading exam');
  }
}

async function recordAndScore(expected, onResult, phraseId = null) {
  if (state.recording && state.mediaRecorder) {
    state.mediaRecorder.stop();
    return;
  }
  try {
    const stream = await navigator.mediaDevices.getUserMedia({ audio: true });
    state.mediaRecorder = new MediaRecorder(stream);
    state.audioChunks = [];
    state.mediaRecorder.ondataavailable = e => state.audioChunks.push(e.data);
    state.mediaRecorder.onstop = async () => {
      state.recording = false;
      stream.getTracks().forEach(t => t.stop());
      const mimeType = state.mediaRecorder.mimeType || 'audio/webm';
      const audioBlob = new Blob(state.audioChunks, { type: mimeType });
      const fd = new FormData();
      fd.append('audio', audioBlob, mimeType.includes('ogg') ? 'recording.ogg' : 'recording.webm');
      fd.append('expected', expected);
      if (phraseId) fd.append('phrase_id', String(phraseId));

      try {
        const res = await fetchWithTimeout('/api/speak/pronounce', {
          method: 'POST',
          headers: { 'X-Telegram-Init-Data': getInitData() },
          body: fd,
        });
        const data = await res.json();
        if (!res.ok) throw new Error(data.detail || 'Ошибка распознавания речи');
        showToast(`Произношение: ${Math.round(data.score || 0)}%`);
        if (onResult) await onResult(data);
      } catch (e) {
        showToast(e.message || 'Не удалось распознать голос');
      }
    };
    state.mediaRecorder.start();
    state.recording = true;
    showToast('Запись идёт. Нажмите кнопку ещё раз, когда закончите.');
  } catch (e) {
    showToast('Нет доступа к микрофону. Разрешите его в настройках Telegram.');
  }
}

async function recordToText(onText) {
  if (state.recording && state.mediaRecorder) {
    state.mediaRecorder.stop();
    return;
  }
  try {
    const stream = await navigator.mediaDevices.getUserMedia({ audio: true });
    state.mediaRecorder = new MediaRecorder(stream);
    state.audioChunks = [];
    state.mediaRecorder.ondataavailable = event => state.audioChunks.push(event.data);
    state.mediaRecorder.onstop = async () => {
      state.recording = false;
      stream.getTracks().forEach(track => track.stop());
      const mimeType = state.mediaRecorder.mimeType || 'audio/webm';
      const form = new FormData();
      form.append('audio', new Blob(state.audioChunks, { type: mimeType }), 'answer.webm');
      try {
        const response = await fetchWithTimeout('/api/speak/transcribe', {
          method: 'POST', headers: { 'X-Telegram-Init-Data': getInitData() }, body: form,
        });
        const result = await response.json();
        if (!response.ok) throw new Error(result.detail || 'Voice recognition failed');
        if (onText) onText(result.text || '');
      } catch (error) {
        showToast(error.message || 'Не удалось распознать ответ');
      }
    };
    state.mediaRecorder.start();
    state.recording = true;
    showToast('Запись идёт. Нажмите ещё раз, когда закончите.');
  } catch (_) {
    showToast('Нет доступа к микрофону.');
  }
}

// ── App Init ──
async function init() {
  setupTabs();
  setupButtons();
  await loadDashboard();
  startActivityTracking();
  await loadLessons();
}

let activityTimer = null;

async function pingActivity() {
  if (document.visibilityState !== 'visible') return;
  try {
    const activity = await apiFetch('/activity/ping', { method: 'POST' });
    if (!state.dashboard) return;
    state.dashboard.minutes_today = activity.minutes_today;
    state.dashboard.streak_days = activity.streak_days;
    state.dashboard.longest_streak = activity.longest_streak;
    document.getElementById('streak-count').textContent = activity.streak_days;
    document.getElementById('stat-streak').textContent = activity.streak_days;
    document.getElementById('stat-best').textContent = activity.longest_streak;
    const isEn = state.dashboard.language_code === 'en';
    document.getElementById('daily-goal-text').textContent = isEn
      ? `${activity.minutes_today} / ${state.dashboard.daily_goal} active min`
      : `${activity.minutes_today} / ${state.dashboard.daily_goal} активных мин`;
  } catch (error) {
    console.warn('Activity heartbeat failed:', error);
  }
}

function startActivityTracking() {
  pingActivity();
  if (activityTimer) clearInterval(activityTimer);
  activityTimer = setInterval(pingActivity, 30000);
  document.addEventListener('visibilitychange', () => {
    if (document.visibilityState === 'visible') pingActivity();
  });
}

document.addEventListener('DOMContentLoaded', init);
