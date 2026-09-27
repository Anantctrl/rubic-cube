// CubeSimulation -- browser-side visual-state controller for the 2x2x2 solver.
//
// The controller knows nothing about BFS/IDA* internals.  It receives the
// scramble, the solution and solver metadata and drives the cubing.js
// <twisty-player> so that EVERY move is visibly performed on the 3D cube.
//
// cubing.js version reality check (v0.63.x):
//  - There is NO ``player.timeline`` / ``scrubTo`` / ``timeInMoves()`` /
//    ``isPlaying`` -- those existed on old experimental builds. The modern,
//    scrubber-buttons-everything-internal API is:
//      * ``player.play()`` / ``player.pause()`` / ``player.tempoScale``
//      * ``player.experimentalModel.timestampRequest.set(ms)``  <- scrub
//      * ``player.experimentalModel.detailedTimelineInfo.get()`` (async,
//        ``{ timestamp, timeRange: { start, end }, atStart, atEnd }``)
//      * ``player.experimentalModel.coarseTimelineInfo.get()`` (async,
//        ``{ atStart, atEnd, playing }``)
//  - Setting ``player.alg = "..."`` replaces the timeline, resets the
//    timestamp to the START (solved) and renders the state at the START of
//    that alg. Setting the prefix alg = exact-state guarantee as a fallback.
//
// Two guarantees make this independent of API drift:
//  1. STEPPING (jump/next/prev/chip-click) always ends on an exactly correct
//     state -- via scrub when the timeline API works, else prefix rebuild.
//  2. Playback animates the full sequence via ``player.play()``; a poll on
//     ``coarseTimelineInfo`` detects the end and a safety timeout guarantees
//     the chain (scramble -> auto-solve) never hangs.

export class CubeSimulation {
  constructor(player) {
    this.player = player;
    this.scramble = [];
    this.solution = [];
    this.stepIndex = 0;
    this.playing = false;
    this.speed = 1;
    this.onStateChange = null;
    this._pollTimer = null;
    this._fallbackTimer = null;
    this._safetyTimer = null;
    this._afterPlaying = null;
    this._lastAlgString = null;
    this._op = null;
    this._stopAtStep = null;
    this._model = null;
    this._fallbackOnly = false;
    this._gen = 0;
    this.animating = false;
    this._emit();
    this.ready = this._initModel();
  }

  whenReady() { return this.ready; }

  async _initModel() {
    let model = null;
    for (let i = 0; i < 400 && !model; i++) {
      const m = this.player.experimentalModel;
      if (m && typeof m.timestampRequest?.set === "function" &&
          typeof m.detailedTimelineInfo?.get === "function" &&
          typeof this.player.play === "function") {
        model = m;
      } else {
        await new Promise((r) => setTimeout(r, 50));
      }
    }
    this._model = model;
    this._fallbackOnly = !model;
    // First timeline read also warms the puzzle / puzzleLoader chain.
    try {
      if (model) await model.detailedTimelineInfo.get();
    } catch (_) { /* fallback below */ }
    if (this._fallbackOnly) {
      // Still render the initial solved state via the plain ``alg`` setter.
      this.player.alg = "";
      this._lastAlgString = "";
    }
    return !this._fallbackOnly;
  }

  _fullSequence() { return this.scramble.concat(this.solution); }

  // -- synchronous state mutation + async re-render -----------------------
  // Every render/replay op is serialized on this._op so that a scrub can never
  // land while the cubing timeline is playing (that used to pause the player
  // and rewind it to the timeline start right after play() began).
  _chain(fn) {
    const next = (this._op || Promise.resolve()).then(fn).catch(() => {});
    this._op = next;
    return next;
  }

  _setState(step) {
    this._gen++;
    this.stepIndex = Math.max(0, Math.min(step, this._fullSequence().length));
    this._chain(() => this._scrub());
    this._emit();
  }

  // -- rendering -----------------------------------------------------------
  async _scrub() {
    if (this._fallbackOnly) { this._renderPrefix(); return; }
    try {
      const m = this._model;
      this._setAlg(this._fullSequence().join(" "));
      m.playingInfo.set({ playing: false });
      const info = await m.detailedTimelineInfo.get();
      const { start, end } = info.timeRange || { start: 0, end: 0 };
      const total = this._fullSequence().length;
      const frac = total > 0 ? this.stepIndex / total : 0;
      const ts = Math.round(start + (end - start) * frac);
      m.timestampRequest.set(ts);
    } catch (_) {
      this._renderPrefix();
    }
  }

  _setAlg(algString) {
    if (algString === this._lastAlgString) return;
    this.player.alg = algString;
    this._lastAlgString = algString;
  }

  _renderPrefix() {
    this._setAlg(this._fullSequence().slice(0, this.stepIndex).join(" "));
  }

  // -- public interface (as specified in the plan) --------------------------
  setScramble(moves) {
    this.scramble = Array.from(moves || []);
    this.solution = [];
    this._setState(0);
    return this;
  }

  setSolution(moves) {
    this.solution = Array.from(moves || []);
    this._setState(this.scramble.length);
    return this;
  }

  // Load contest and solution together and render the starting (solved) pose.
  // The full timeline (scramble + solution) is then set exactly once, so the
  // scramble -> solve handoff never re-builds the timeline (which made cubing
  // flash the start of the alg -- a "blink" -- before seeking back).
  load(scramble, solution, startStep = 0) {
    this.scramble = Array.from(scramble || []);
    this.solution = Array.from(solution || []);
    this._setState(startStep);
    return this;
  }

  reset() { this._setState(0); return this; }

  play() {
    if (this.stepIndex >= this._fullSequence().length) return this;
    const self = this;
    const gen = this._gen;
    this.animating = true;
    this._chain(async () => {
      if (gen !== self._gen) { self.animating = false; return; }
      if (self.stepIndex >= self._fullSequence().length) return;
      if (self._fallbackOnly) { self._startFallback(); return; }
      try {
        self.playing = true;
        // The synchronous emit from play() above reports playing=false (the
        // flag flips inside this queued task); re-emit now so the UI reflects
        // "SCRAMBLING…" / "SOLVING…" for the whole animation, not a stale
        // paused label ("press SOLVE…") that invites a redundant Solve press.
        self._emit();
        await self._playTimeline();
        if (gen !== self._gen) {
          // A pause()/load()/reset() landed while the timeline was starting;
          // drop this stale playback instead of animating a dead sequence.
          self.playing = false;
          self.animating = false;
          return;
        }
        self._startPoll();
        self._startSafety();
      } catch (_) { self.playing = false; }
    });
    this._emit();
    return this;
  }

  pause() {
    this._gen++;
    this.playing = false;
    this.animating = false;
    if (!this._fallbackOnly) {
      try { this.player.pause(); } catch (_) {}
      try { this._model.playingInfo.set({ playing: false }); } catch (_) {}
    }
    this._stopPoll();
    this._stopFallback();
    this._stopSafety();
    this._emit();
    return this;
  }

  next() {
    if (this.stepIndex < this._fullSequence().length) this._setState(this.stepIndex + 1);
    return this;
  }

  previous() {
    if (this.stepIndex > 0) this._setState(this.stepIndex - 1);
    return this;
  }

  goToStep(step) {
    this.pause();
    this._stopAtStep = null;
    this._setState(step);
    return this;
  }

  // Play only up to `stopAtStep` (e.g. the end of the scramble), then pause so
  // the cube remains scrambled until the user acts (e.g. presses Solve).
  // Falls forward to the timeline end if `stopAtStep` is not within the
  // sequence or the timeline API never reports a crossing.
  playScramble(stopAtStep) {
    if (!this.scramble.length) { this._emit(); return this; }
    this.goToStep(0);
    const stop = typeof stopAtStep === "number" ? stopAtStep : this.scramble.length;
    this._stopAtStep = Math.min(stop, this._fullSequence().length);
    this.play();
    return this;
  }

  playSolution() {
    if (!this.solution.length) {
      this.goToStep(this._fullSequence().length);
      this._emit();
      return this;
    }
    this.goToStep(this.scramble.length);
    this.play();
    return this;
  }

  setSpeed(value) {
    this.speed = value;
    if (!this._fallbackOnly) {
      try { this.player.tempoScale = this.speed; } catch (_) {}
    }
    this._emit();
    return this;
  }

  getCurrentMove() { return this.currentMove(); }
  getCurrentStep() { return this.stepIndex; }
  getTotalSteps() { return this._fullSequence().length; }
  isAnimating() { return this.animating || this.playing; }

  // Callbacks fire once after a completed play/playScramble/playSolution
  // animation (used to chain "scramble -> then solve" without cooking
  // wall-clock timings). Multiple continuations are allowed (e.g. Random's
  // prefetch may register a late-solution attach AND the user may have
  // deferred a Solve). Pass null to clear all pending continuations.
  onDone(next) {
    if (next === null) { this._afterPlaying = []; return this; }
    if (!Array.isArray(this._afterPlaying)) this._afterPlaying = [];
    this._afterPlaying.push(next);
    return this;
  }

  // -- state accessors ------------------------------------------------------
  currentMove() {
    if (this.stepIndex === 0) return null;
    return this._fullSequence()[this.stepIndex - 1] ?? null;
  }

  phase() {
    const total = this._fullSequence().length;
    if (this.stepIndex === 0) return "solved";
    if (this.stepIndex <= this.scramble.length) return "scramble";
    if (this.stepIndex >= total) return "solved";
    return "solution";
  }

  // -- playback drivers ------------------------------------------------------
  async _playTimeline() {
    const m = this._model;
    this._setAlg(this._fullSequence().join(" ")); // no-op if unchanged
    try {
      m.playingInfo.set({ playing: false });
      await this._scrub();
      this.player.play();
    } catch (_) {
      this._startFallback();
    }
  }

  _startPoll() {
    this._stopPoll();
    this._pollTimer = setInterval(() => this._poll(), 150);
  }

  _stopPoll() { if (this._pollTimer) { clearInterval(this._pollTimer); this._pollTimer = null; } }

  async _poll() {
    if (!this.playing || this._fallbackOnly) return;
    try {
      // NOTE: detailedTimelineInfo has NO ``playing`` field (that is only on
      // coarseTimelineInfo).  Everything here is derived from the timestamp +
      // atStart/atEnd + timeRange, so playback progress is tracked even when
      // the model omits the flag.
      const dtl = await this._model.detailedTimelineInfo.get();
      const { start, end } = dtl.timeRange || { start: 0, end: 0 };
      const total = this._fullSequence().length;
      const ts = dtl.timestamp ?? 0;

      // Live step tracking: while the cubing timeline animates, advance the
      // wrapper's stepIndex from the timestamp fraction so the counter/chips
      // move in real time instead of freezing at the last scrubbed pose
      // (the "cube lags / nothing happens" look).
      if (total > 0 && end > start) {
        const frac = Math.min(1, Math.max(0, (ts - start) / (end - start)));
        const liveStep = Math.round(frac * total);
        if (liveStep !== this.stepIndex) {
          this.stepIndex = liveStep;
          this._emit();
        }
      }

      // Stop-at-step (e.g. end of the scramble phase): pause when the target
      // timestamp is reached so the cube stays scrambled and waits for the user.
      // The playScramble animation is considered complete here, so the pending
      // onDone continuations (a deferred Solve attach, Random's late solution
      // attach) must run exactly as if the timeline had ended naturally --
      // otherwise a Solve pressed mid-scramble is silently dropped.
      if (this._stopAtStep !== null && total > 0 && end > start) {
        const targetTs = start + (end - start) * (this._stopAtStep / total);
        if (ts >= targetTs) {
          const stop = this._stopAtStep;
          this._stopAtStep = null;
          this.pause();
          this._setState(stop);
          this._fireAfterPlaying();
        }
        return;
      }

      // Natural end: the timestamp reached (or passed) the timeline end.
      if (dtl.atEnd || (end > start && ts >= end) || this.stepIndex >= total) {
        this._playingEnded();
      }
    } catch (_) {}
  }

  _playingEnded() {
    this._gen++;
    this.playing = false;
    this.animating = false;
    this._stopAtStep = null;
    this.stepIndex = this._fullSequence().length;
    this._stopPoll();
    this._stopSafety();
    this._emit();
    this._fireAfterPlaying();
  }

  // Run all queued playback-end continuations once.  Used both at the natural
  // timeline end and at the stop-at-step pause (the end of a playScramble).
  _fireAfterPlaying() {
    const cbs = this._afterPlaying || [];
    this._afterPlaying = [];
    for (const cb of cbs) {
      try { cb.call(this); } catch (_) {}
    }
  }

  _startFallback() {
    this.playing = true;
    this._stopFallback();
    this._fallbackTimer = setInterval(() => {
      if (!this.playing) return;
      if (this.stepIndex >= this._fullSequence().length) { this._playingEnded(); return; }
      this.stepIndex += 1;
      this._renderPrefix();
      this._emit(false);
    }, 650 / this.speed);
  }

  _stopFallback() { if (this._fallbackTimer) { clearInterval(this._fallbackTimer); this._fallbackTimer = null; } }

  _startSafety() {
    this._stopSafety();
    const total = this._fullSequence().length;
    // Measured ~725ms/move at 1x (cubing.js can run slower under load); keep a
    // generous ceiling so the make-shift "physics rate" never fires mid-solve.
    const expect = (total - this.stepIndex) * 900 / this.speed + 3500;
    this._safetyTimer = setTimeout(() => {
      if (this.playing) { this._playingEnded(); }
    }, Math.max(800, expect));
  }

  _stopSafety() { if (this._safetyTimer) { clearTimeout(this._safetyTimer); this._safetyTimer = null; } }

  // -- state broadcast -------------------------------------------------------

  _emit() {
    if (!this.onStateChange) return;
    const seq = this._fullSequence();
    this.onStateChange({
      step: this.stepIndex,
      total: seq.length,
      currentMove: this.currentMove(),
      phase: this.phase(),
      playing: this.playing,
      seq,
      scrambleLength: this.scramble.length,
      solutionLength: this.solution.length,
    });
  }
}