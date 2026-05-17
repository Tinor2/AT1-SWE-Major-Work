/**
 * Pomodoro Timer — clean rewrite.
 *
 * Architecture
 * ============
 * The SERVER is the source of truth for all state.
 * The CLIENT only:
 *   1. Displays the countdown (ticking locally for smoothness).
 *   2. Sends explicit user actions (start / pause / reset / skip / reset-sets).
 *   3. Periodically re-syncs with the server to correct drift.
 *
 * Key invariants that prevent the "skip on refresh" bug:
 *   - startCountdown() is ONLY called when the server tells us the timer is
 *     actively running (state === 'session' | 'short_break' | 'long_break').
 *   - handleCompletion() only auto-advances when the timer naturally reaches
 *     zero WHILE the page has been open and the countdown was already running.
 *     It is NOT called when loading a state that already has remaining === 0.
 *   - After completion the server lands in 'paused', so on the next refresh
 *     nothing auto-starts.
 */

'use strict';

class PomodoroTimer {

    // -----------------------------------------------------------------------
    // Construction & initialisation
    // -----------------------------------------------------------------------

    constructor() {
        // DOM refs — all optional (page may not have them)
        this.elContainer    = document.getElementById('timerContainer');
        this.elDisplay      = document.getElementById('timerDisplay');
        this.elPhase        = document.getElementById('timerPhase');
        this.elPausedBadge  = document.getElementById('timerPausedStatus');
        this.elProgressBar  = document.getElementById('progressBar');
        this.elStartPause   = document.getElementById('startPauseBtn');
        this.elReset        = document.getElementById('resetBtn');
        this.elSkip         = document.getElementById('skipBtn');
        this.elResetSets    = document.getElementById('resetSetsBtn');
        this.elSessionCount = document.getElementById('sessionCounter');

        // Local state — mirrors server
        this.state = {
            timer_state:        'idle',
            current_phase:      null,
            timer_remaining:    0,
            sessions_completed: 0,
            pomo_session:       25,
            pomo_short_break:   5,
            pomo_long_break:    15,
            timer_started_at:   null,
            timer_last_updated: null,
        };

        // Countdown bookkeeping
        this._tickInterval  = null;   // setInterval handle for local tick
        this._syncInterval  = null;   // setInterval handle for server sync
        this._lastKnownTime = Date.now();  // sleep detection

        // Flag: set to true only AFTER the initial loadState() completes.
        // handleCompletion will not fire before this is true.
        this._ready = false;

        // Human-readable phase names
        this._phaseNames = {
            session:     'Focus Session',
            short_break: 'Short Break',
            long_break:  'Long Break',
        };

        this._init();
    }

    async _init() {
        this._bindButtons();
        await this._loadState();
        this._ready = true;

        // Sleep detection
        setInterval(() => this._detectSleep(), 30_000);
    }

    // -----------------------------------------------------------------------
    // Button wiring
    // -----------------------------------------------------------------------

    _bindButtons() {
        this.elStartPause?.addEventListener('click', () => this._onStartPause());
        this.elReset?.addEventListener('click',      () => this._onReset());
        this.elSkip?.addEventListener('click',       () => this._onSkip());
        this.elResetSets?.addEventListener('click',  () => this._onResetSets());

        document.addEventListener('visibilitychange', () => {
            if (document.hidden) {
                this._stopTick();
            } else {
                // Re-sync and resume if needed
                this._syncNow().then(() => {
                    if (this._isRunning()) this._startTick();
                });
            }
        });

        window.addEventListener('beforeunload', () => this._cleanup());

        // Notification permission on first click
        document.addEventListener('click', () => {
            if ('Notification' in window && Notification.permission === 'default') {
                Notification.requestPermission();
            }
        }, { once: true });
    }

    // -----------------------------------------------------------------------
    // Server communication — all timer actions go through here
    // -----------------------------------------------------------------------

    async _post(endpoint) {
        const res = await fetch(`/timer/${endpoint}`, {
            method: 'POST',
            headers: { 'Content-Type': 'application/json' },
            body: '{}',
        });
        if (!res.ok) throw new Error(`HTTP ${res.status}`);
        return res.json();
    }

    async _get(endpoint) {
        const res = await fetch(`/timer/${endpoint}`);
        if (!res.ok) throw new Error(`HTTP ${res.status}`);
        return res.json();
    }

    // -----------------------------------------------------------------------
    // Load initial state from server
    // -----------------------------------------------------------------------

    async _loadState() {
        try {
            const data = await this._get('status');
            if (!data.success) return;

            this._applyState(data);
            this._render();

            if (this._isRunning()) {
                this._startTick();
                this._startSync();
            }
        } catch (e) {
            console.error('Timer: failed to load state', e);
            this._render(); // show defaults
        }
    }

    // -----------------------------------------------------------------------
    // User actions
    // -----------------------------------------------------------------------

    async _onStartPause() {
        try {
            if (this._isRunning()) {
                const data = await this._post('pause');
                if (!data.success) return;
                this._stopTick();
                this._stopSync();
                this._applyState(data);
                this._render();
            } else {
                // idle or paused → start
                const data = await this._post('start');
                if (!data.success) return;
                this._applyState(data);
                this._render();
                this._startTick();
                this._startSync();
            }
        } catch (e) {
            console.error('Timer: start/pause failed', e);
        }
    }

    async _onReset() {
        try {
            const data = await this._post('reset');
            if (!data.success) return;
            this._stopTick();
            this._stopSync();
            this._applyState(data);
            this._render();
        } catch (e) {
            console.error('Timer: reset failed', e);
        }
    }

    async _onSkip() {
        try {
            const data = await this._post('skip');
            if (!data.success) return;
            this._stopTick();
            this._stopSync();
            this._applyState(data);
            this._render();
            // Server lands in 'paused' after skip — do NOT auto-start
        } catch (e) {
            console.error('Timer: skip failed', e);
        }
    }

    async _onResetSets() {
        // Show confirmation modal first
        const confirmed = await this._confirmResetSets();
        if (!confirmed) return;

        try {
            const data = await this._post('reset-sets');
            if (!data.success) return;
            this._stopTick();
            this._stopSync();
            this._applyState(data);
            this._render();
        } catch (e) {
            console.error('Timer: reset-sets failed', e);
        }
    }

    _confirmResetSets() {
        return new Promise(resolve => {
            const modal = document.getElementById('resetSetsModal');
            if (!modal) {
                resolve(window.confirm(
                    'Reset sets?\n\n• Set counter → 1\n• Return to first focus session\n• Timer reset to full'
                ));
                return;
            }

            modal.classList.add('show');

            const done = (result) => {
                modal.classList.remove('show');
                // Remove listeners so they don't stack up
                confirmBtn.removeEventListener('click', onConfirm);
                cancelBtn.removeEventListener('click', onCancel);
                closeBtn.removeEventListener('click', onCancel);
                backdrop.removeEventListener('click', onCancel);
                document.removeEventListener('keydown', onEsc);
                resolve(result);
            };

            const onConfirm = () => done(true);
            const onCancel  = () => done(false);
            const onEsc = (e) => { if (e.key === 'Escape') done(false); };

            const confirmBtn = modal.querySelector('.modal-confirm');
            const cancelBtn  = modal.querySelector('.modal-cancel');
            const closeBtn   = modal.querySelector('.modal-close');
            const backdrop   = modal.querySelector('.modal-backdrop');

            confirmBtn?.addEventListener('click', onConfirm);
            cancelBtn?.addEventListener('click',  onCancel);
            closeBtn?.addEventListener('click',   onCancel);
            backdrop?.addEventListener('click',   onCancel);
            document.addEventListener('keydown',  onEsc);
        });
    }

    // -----------------------------------------------------------------------
    // Local countdown tick
    // -----------------------------------------------------------------------

    _startTick() {
        this._stopTick();
        this._tickInterval = setInterval(() => this._tick(), 1000);
    }

    _stopTick() {
        if (this._tickInterval !== null) {
            clearInterval(this._tickInterval);
            this._tickInterval = null;
        }
    }

    _tick() {
        if (this.state.timer_remaining > 0) {
            this.state.timer_remaining--;
            this._render();
        } else {
            // Reached zero — only auto-advance if the timer was genuinely
            // running during this page session (i.e. _ready is true and
            // the tick interval was running, not just loaded from server).
            this._stopTick();
            if (this._ready) {
                this._handleCompletion();
            }
        }
    }

    async _handleCompletion() {
        // Visual flash
        this.elContainer?.classList.add('completed');
        setTimeout(() => this.elContainer?.classList.remove('completed'), 2000);

        // Browser notification
        if ('Notification' in window && Notification.permission === 'granted') {
            const phase = this._phaseName(this.state.current_phase || this.state.timer_state);
            new Notification('Pomodoro Timer', { body: `${phase} complete!` });
        }

        // Show popup modal
        this._showCompletionModal();

        // Skip to next phase on server — lands in 'paused'
        try {
            const data = await this._post('skip');
            if (data.success) {
                this._applyState(data);
                this._render();
                // Do NOT auto-start the next phase
            }
        } catch (e) {
            console.error('Timer: auto-skip after completion failed', e);
        }
    }

    _showCompletionModal() {
        const modal = document.getElementById('sessionCompleteModal');
        if (!modal) return;

        const messageEl = document.getElementById('sessionCompleteMessage');
        const titleEl = document.getElementById('sessionCompleteTitle');

        // Determine which phase just completed
        const phase = this.state.current_phase || this.state.timer_state;
        let message = '';
        let title = 'Session Complete!';

        if (phase === 'session') {
            message = 'The focus session is over. Time for a break!';
        } else if (phase === 'short_break') {
            message = 'The short break is over. Ready to focus again?';
        } else if (phase === 'long_break') {
            message = 'The long break is over. Ready to start a new set?';
        } else {
            message = 'The session is complete!';
        }

        if (messageEl) messageEl.textContent = message;
        if (titleEl) titleEl.textContent = title;

        // Show modal
        modal.classList.add('show');

        // Set up close handlers
        const closeBtn = modal.querySelector('.modal-close');
        const confirmBtn = modal.querySelector('.modal-confirm');
        const backdrop = modal.querySelector('.modal-backdrop');

        const closeModal = () => {
            modal.classList.remove('show');
            closeBtn?.removeEventListener('click', closeModal);
            confirmBtn?.removeEventListener('click', closeModal);
            backdrop?.removeEventListener('click', closeModal);
        };

        closeBtn?.addEventListener('click', closeModal);
        confirmBtn?.addEventListener('click', closeModal);
        backdrop?.addEventListener('click', closeModal);

        // Close on Escape key
        const onEsc = (e) => {
            if (e.key === 'Escape') {
                closeModal();
                document.removeEventListener('keydown', onEsc);
            }
        };
        document.addEventListener('keydown', onEsc);
    }

    // -----------------------------------------------------------------------
    // Server sync (drift correction)
    // -----------------------------------------------------------------------

    _startSync() {
        this._stopSync();
        this._syncInterval = setInterval(() => this._syncNow(), 30_000);
    }

    _stopSync() {
        if (this._syncInterval !== null) {
            clearInterval(this._syncInterval);
            this._syncInterval = null;
        }
    }

    async _syncNow() {
        try {
            const data = await this._get('status');
            if (!data.success) return;

            const serverState   = data.timer_state;
            const serverPhase   = data.current_phase;
            const localState    = this.state.timer_state;
            const localPhase    = this.state.current_phase;

            // If state or phase has changed from under us, adopt server state fully
            if (serverState !== localState || serverPhase !== localPhase) {
                this._stopTick();
                this._stopSync();
                this._applyState(data);
                this._render();
                if (this._isRunning()) {
                    this._startTick();
                    this._startSync();
                }
                return;
            }

            // Same state/phase — just correct the remaining time
            // Server knows the authoritative remaining; use it if drift > 3 s
            if (this._isRunning()) {
                const serverRemaining = data.timer_remaining;
                const drift = Math.abs(serverRemaining - this.state.timer_remaining);
                if (drift > 3) {
                    this.state.timer_remaining = serverRemaining;
                    this._render();
                }
            }
        } catch (e) {
            // Silent — don't disrupt the user
        }
    }

    _detectSleep() {
        const now  = Date.now();
        const diff = now - this._lastKnownTime;
        this._lastKnownTime = now;

        // If more than 90 s have elapsed since the last check, the device
        // probably slept. Re-sync immediately.
        if (diff > 90_000 && this._isRunning()) {
            this._syncNow();
        }
    }

    // -----------------------------------------------------------------------
    // State management
    // -----------------------------------------------------------------------

    _applyState(data) {
        // Merge all timer fields from server response into local state.
        // timer_remaining from the server is already computed (remaining at
        // time of response) so we use it directly.
        this.state.timer_state        = data.timer_state;
        this.state.current_phase      = data.current_phase;
        this.state.timer_remaining    = data.timer_remaining ?? this.state.timer_remaining;
        this.state.sessions_completed = data.sessions_completed ?? 0;
        this.state.pomo_session       = data.pomo_session       ?? 25;
        this.state.pomo_short_break   = data.pomo_short_break   ?? 5;
        this.state.pomo_long_break    = data.pomo_long_break    ?? 15;
        this.state.timer_started_at   = data.timer_started_at   ?? null;
        this.state.timer_last_updated = data.timer_last_updated ?? null;
    }

    _isRunning() {
        const s = this.state.timer_state;
        return s === 'session' || s === 'short_break' || s === 'long_break';
    }

    // -----------------------------------------------------------------------
    // Rendering
    // -----------------------------------------------------------------------

    _render() {
        this._renderDisplay();
        this._renderProgressBar();
        this._renderPhaseLabel();
        this._renderPausedBadge();
        this._renderSessionCounter();
        this._renderButtons();
        this._renderContainerClass();
    }

    _renderDisplay() {
        if (!this.elDisplay) return;
        let secs = this.state.timer_remaining;
        // If idle, show the full session duration rather than 0
        if (this.state.timer_state === 'idle') {
            secs = this.state.pomo_session * 60;
        }
        const m = Math.floor(secs / 60);
        const s = secs % 60;
        this.elDisplay.textContent =
            `${String(m).padStart(2, '0')}:${String(s).padStart(2, '0')}`;
    }

    _renderPhaseLabel() {
        if (!this.elPhase) return;
        const s = this.state;
        let phase;
        if (s.timer_state === 'idle') {
            phase = 'session';
        } else if (s.timer_state === 'paused') {
            phase = s.current_phase || 'session';
        } else {
            phase = s.timer_state;
        }
        this.elPhase.textContent = this._phaseName(phase);
    }

    _renderPausedBadge() {
        if (!this.elPausedBadge) return;
        this.elPausedBadge.style.display =
            this.state.timer_state === 'paused' ? 'block' : 'none';
    }

    _renderProgressBar() {
        if (!this.elProgressBar) return;

        const s = this.state;
        let totalSecs;
        let effectivePhase;

        if (s.timer_state === 'idle') {
            this.elProgressBar.style.width = '0%';
            return;
        } else if (s.timer_state === 'paused') {
            effectivePhase = s.current_phase || 'session';
        } else {
            effectivePhase = s.timer_state;
        }

        totalSecs = this._phaseDuration(effectivePhase);
        if (totalSecs <= 0) {
            this.elProgressBar.style.width = '0%';
            return;
        }

        const elapsed  = totalSecs - s.timer_remaining;
        const progress = Math.max(0, Math.min(100, (elapsed / totalSecs) * 100));
        this.elProgressBar.style.width = `${progress}%`;

        // Enable CSS transition after first render to prevent a jump on load
        if (!this.elProgressBar.classList.contains('transitions-enabled')) {
            // Small delay so the initial paint is instant
            setTimeout(() => {
                this.elProgressBar.classList.add('transitions-enabled');
            }, 100);
        }
    }

    _renderSessionCounter() {
        if (!this.elSessionCount) return;
        const completed = this.state.sessions_completed;
        const posInSet  = completed % 4;          // 0–3
        const setNum    = Math.floor(completed / 4) + 1;
        const state     = this.state.timer_state;

        let text;
        if (state === 'idle') {
            text = `Ready to start • Set ${setNum}`;
        } else if (state === 'session' || (state === 'paused' && this.state.current_phase === 'session')) {
            text = `Session ${posInSet + 1} of 4 • Set ${setNum}`;
        } else if (state === 'short_break' || (state === 'paused' && this.state.current_phase === 'short_break')) {
            text = `Short break • Set ${setNum}`;
        } else if (state === 'long_break' || (state === 'paused' && this.state.current_phase === 'long_break')) {
            text = `Long break • Set ${setNum}`;
        } else {
            text = `Set ${setNum}`;
        }
        this.elSessionCount.textContent = text;
    }

    _renderButtons() {
        if (!this.elStartPause) return;
        if (this._isRunning()) {
            this.elStartPause.textContent = 'Pause';
            this.elStartPause.className   = 'btn btn-warning';
        } else {
            this.elStartPause.textContent = 'Start';
            this.elStartPause.className   = 'btn btn-primary';
        }
    }

    _renderContainerClass() {
        if (!this.elContainer) return;
        const classes = ['session', 'short-break', 'long-break', 'paused', 'idle', 'completed'];
        this.elContainer.classList.remove(...classes);

        const s = this.state;
        if (s.timer_state === 'paused') {
            this.elContainer.classList.add('paused');
            if (s.current_phase) {
                this.elContainer.classList.add(s.current_phase.replace('_', '-'));
            }
        } else if (s.timer_state !== 'idle') {
            this.elContainer.classList.add(s.timer_state.replace('_', '-'));
        }
    }

    // -----------------------------------------------------------------------
    // Utilities
    // -----------------------------------------------------------------------

    _phaseName(phase) {
        return this._phaseNames[phase] || 'Focus Session';
    }

    _phaseDuration(phase) {
        const s = this.state;
        if (phase === 'session')     return s.pomo_session     * 60;
        if (phase === 'short_break') return s.pomo_short_break * 60;
        if (phase === 'long_break')  return s.pomo_long_break  * 60;
        return s.pomo_session * 60;
    }

    _cleanup() {
        this._stopTick();
        this._stopSync();
    }
}

// Boot when the DOM is ready and the timer container exists
document.addEventListener('DOMContentLoaded', () => {
    if (document.getElementById('timerContainer')) {
        window.pomodoroTimer = new PomodoroTimer();
    }
});