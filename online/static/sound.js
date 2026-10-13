(function () {
  "use strict";

  const sources = {
    intro: "/media/audio/intro.mp3",
    question: "/media/audio/question_music.mp3",
    transition: "/media/audio/transition.mp3",
    correct: "/media/audio/correct.wav",
    incorrect: "/media/audio/incorrect.wav",
    lifeline: "/media/audio/lifeline.wav",
    call: "/media/audio/call.mp3",
    audience: "/media/audio/audience.wav",
  };

  const DEFAULT_MUSIC_VOLUME = 0.24;
  const DEFAULT_CUE_VOLUME = 0.72;
  const DEFAULT_EFFECT_VOLUME = 0.78;
  const DEFAULT_VOICE_VOLUME = 0.86;
  const QUESTION_CUE_FALLBACK_MS = 11650;

  class GameAudio {
    constructor(button, options = {}) {
      this.button = button;
      this.storageKey = options.storageKey || "desafio:sound";
      this.musicOnEnable = options.musicOnEnable || null;
      this.autoEnabled = Boolean(options.autoEnabled);
      this.enabled = this.autoEnabled || localStorage.getItem(this.storageKey) === "on";
      this.playbackBlocked = false;

      this.music = new Audio();
      this.music.loop = true;
      this.music.preload = "auto";
      this.music.volume = DEFAULT_MUSIC_VOLUME;

      this.cue = new Audio();
      this.cue.loop = false;
      this.cue.preload = "auto";
      this.cue.volume = DEFAULT_CUE_VOLUME;

      this.effect = new Audio();
      this.effect.preload = "auto";
      this.effect.volume = DEFAULT_EFFECT_VOLUME;

      this.voice = new Audio();
      this.voice.preload = "auto";
      this.voice.volume = DEFAULT_VOICE_VOLUME;

      this.musicName = null;
      this.cueName = null;
      this.fadeToken = 0;
      this.sequenceToken = 0;
      this.questionSequenceActive = false;
      this.questionSequenceTimer = null;
      this.preloads = [];

      this.updateButton();
      button?.addEventListener("click", () => {
        if (this.enabled) this.disable();
        else {
          const musicName = typeof this.musicOnEnable === "function"
            ? this.musicOnEnable()
            : this.musicOnEnable;
          this.enable(musicName);
        }
      });
    }

    updateButton() {
      if (!this.button) return;
      this.button.textContent = this.enabled ? "Silenciar" : "Activar sonido";
      this.button.setAttribute("aria-pressed", String(this.enabled));
    }

    preloadSources() {
      if (this.preloads.length) return;
      this.preloads = Object.values(sources).map((src) => {
        const audio = new Audio();
        audio.preload = "auto";
        audio.src = src;
        audio.load();
        return audio;
      });
    }

    async enable(musicName = null) {
      this.enabled = true;
      this.playbackBlocked = false;
      localStorage.setItem(this.storageKey, "on");
      this.updateButton();
      if (musicName) await this.startMusic(musicName);
    }

    disable() {
      this.enabled = false;
      localStorage.setItem(this.storageKey, "off");
      this.cancelQuestionSequence();
      this.fadeToken += 1;
      [this.music, this.cue, this.effect, this.voice].forEach((audio) => {
        audio.pause();
        try { audio.currentTime = 0; } catch { /* Fuente aún no disponible. */ }
      });
      this.musicName = null;
      this.cueName = null;
      this.updateButton();
    }

    async startMusic(name) {
      if (!this.enabled || !sources[name]) return;
      if (this.playbackBlocked) return;
      this.fadeToken += 1;
      if (this.musicName !== name) {
        this.music.pause();
        this.music.src = sources[name];
        this.music.currentTime = 0;
        this.musicName = name;
      }
      this.music.volume = DEFAULT_MUSIC_VOLUME;
      if (!this.music.paused) return;
      try {
        await this.music.play();
      } catch {
        if (this.autoEnabled) {
          this.playbackBlocked = true;
          return;
        }
        this.enabled = false;
        localStorage.setItem(this.storageKey, "off");
        this.updateButton();
      }
    }

    stopMusic(options = {}) {
      const fadeMs = Number(options.fadeMs || 0);
      if (!this.musicName && this.music.paused) return;
      const token = ++this.fadeToken;
      if (!fadeMs || this.music.paused) {
        this.music.pause();
        try { this.music.currentTime = 0; } catch { /* Fuente aún no disponible. */ }
        this.music.volume = DEFAULT_MUSIC_VOLUME;
        this.musicName = null;
        return;
      }
      const startVolume = this.music.volume;
      const started = performance.now();
      const fade = (now) => {
        if (token !== this.fadeToken) return;
        const progress = Math.min(1, (now - started) / fadeMs);
        this.music.volume = startVolume * (1 - progress);
        if (progress < 1) requestAnimationFrame(fade);
        else {
          this.music.pause();
          try { this.music.currentTime = 0; } catch { /* Fuente aún no disponible. */ }
          this.music.volume = DEFAULT_MUSIC_VOLUME;
          this.musicName = null;
        }
      };
      requestAnimationFrame(fade);
    }

    stopCue() {
      this.cue.pause();
      this.cue.onended = null;
      try { this.cue.currentTime = 0; } catch { /* Fuente aún no disponible. */ }
      this.cueName = null;
    }

    stopVoice() {
      this.voice.pause();
      try { this.voice.currentTime = 0; } catch { /* Fuente aún no disponible. */ }
    }

    stopEffect() {
      this.effect.pause();
      try { this.effect.currentTime = 0; } catch { /* Fuente aún no disponible. */ }
    }

    cancelQuestionSequence() {
      this.sequenceToken += 1;
      this.questionSequenceActive = false;
      if (this.questionSequenceTimer) {
        clearTimeout(this.questionSequenceTimer);
        this.questionSequenceTimer = null;
      }
      this.stopCue();
    }

    isQuestionSequenceActive() {
      return this.questionSequenceActive;
    }

    beginQuestionSequence(options = {}) {
      if (!this.enabled) return;
      const cueName = options.cue || "transition";
      const musicName = options.music || "question";
      const fallbackMs = Number(options.fallbackMs || QUESTION_CUE_FALLBACK_MS);
      if (!sources[cueName] || !sources[musicName]) return;

      this.cancelQuestionSequence();
      this.stopVoice();
      this.stopMusic();

      const token = ++this.sequenceToken;
      this.questionSequenceActive = true;
      this.cue.pause();
      this.cue.src = sources[cueName];
      this.cue.currentTime = 0;
      this.cue.volume = DEFAULT_CUE_VOLUME;
      this.cueName = cueName;

      let finished = false;
      const finish = () => {
        if (finished || token !== this.sequenceToken || !this.enabled) return;
        finished = true;
        this.questionSequenceActive = false;
        if (this.questionSequenceTimer) {
          clearTimeout(this.questionSequenceTimer);
          this.questionSequenceTimer = null;
        }
        this.cue.onended = null;
        this.cueName = null;
        this.startMusic(musicName);
      };

      this.cue.onended = finish;
      this.questionSequenceTimer = setTimeout(finish, Math.max(1000, fallbackMs));
      this.cue.play().catch(finish);
    }

    resumeQuestionMusic() {
      if (!this.enabled) return;
      this.cancelQuestionSequence();
      this.stopVoice();
      this.startMusic("question");
    }

    async play(name) {
      if (!this.enabled || !sources[name]) return;
      this.effect.pause();
      this.effect.src = sources[name];
      this.effect.currentTime = 0;
      this.effect.volume = DEFAULT_EFFECT_VOLUME;
      try { await this.effect.play(); } catch { /* El control visible permite reactivar. */ }
    }

    async playVoice(name) {
      if (!this.enabled || !sources[name]) return;
      this.voice.pause();
      this.voice.src = sources[name];
      this.voice.currentTime = 0;
      this.voice.volume = DEFAULT_VOICE_VOLUME;
      try { await this.voice.play(); } catch { /* El control visible permite reactivar. */ }
    }
  }

  GameAudio.sources = Object.freeze({ ...sources });
  GameAudio.QUESTION_CUE_FALLBACK_MS = QUESTION_CUE_FALLBACK_MS;
  window.GameAudio = GameAudio;
}());
