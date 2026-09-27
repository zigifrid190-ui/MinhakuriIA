# Sleep / Suspended Mode Animation Fix (June 2026)

## Problem Summary
When the app entered "modo sono" / mic suspended mode (after 5 minutes of inactivity or when mic checks were suspended), the following happened:
- FPS correctly dropped (deep idle working).
- The custom sleepy avatar visual (low/closed eyes via ParamEyeLOpen/ROpen, head tilted down with slow sway, slow breathing) + ZZZ overlay would appear for only ~1 second.
- Then the avatar would revert to the normal "idle" animation.
- The "ZZZ" indicator would disappear.

This made sleep mode look broken even though the low-power logic was active.

## Root Causes
1. **Idle motion overriding manual parameters**: The Live2D "Idle" motion (started via animation_map or previous state) was blending or resetting the eye, angle, and breath parameters we were trying to force for the sleepy look.
2. **_reset_activity() clearing sleep state**: Any call to set_emotion(), set_speaking(), or set_state() would call _reset_activity(), which deleted `_sleep_params` and re-enabled normal FPS/mouse tracking.
3. **State not sticky in suspended mode**: The core would set `KuriState.SLEEPING` once, but subsequent ticks or other logic (or signal ordering) would allow the avatar to fall back to IDLE behavior.
4. **Parameter timing**: Setting parameters before `model.Update()` in paintGL allowed the motion system to override them on the next frame.
5. **No re-enforcement**: Once in `_mic_suspended`, the loop was doing long sleeps but not periodically re-applying the SLEEPING state to the avatar.

## Solution Applied (Key Changes)

### 1. gui/live2d_avatar.py
- **Special-case SLEEPING early** in `set_state()`:
  - Return immediately after applying sleep logic.
  - Never call `_reset_activity()` or the normal `_apply_state_animation()` for SLEEPING.
- **Aggressive motion stopping**:
  - Call `StopAllMotions()` on entry to SLEEPING.
  - Call it again inside `_on_tick()` and `paintGL()` while in SLEEPING.
- **Force parameters after Update()** (most important):
  - In `paintGL()`, after `self._model.Update()`, re-apply the sleepy params (eyes, angleY + sway, breath).
  - This overrides any blending the motion system did during Update().
- **Stronger sleep params**:
  - Eyes at 0.08 (very closed).
  - AngleY at -12 + slow sinusoidal sway.
  - Very slow breath rate.
- **Guard in _reset_activity()**:
  - If `self._current_state == KuriState.SLEEPING`, do nothing (prevent accidental wake from mouse movement, timers, etc.).
- **_apply_sleep_visual()** now also stops motions and resets expressions.

### 2. gui/kuri_core.py
- In the `_mic_suspended` branch of the main voice loop:
  - Periodically re-call `bridge.set_state(KuriState.SLEEPING)` + `set_emotion("neutral")`.
  - This re-triggers the avatar's sleep logic every ~30s, making the visual "stick" even if something tried to revert it.
- When hitting max mic attempts or consecutive silence:
  - Explicitly set both `_mic_suspended` and `_in_sleep`, then force SLEEPING + neutral.
- Time-based sleep (`_should_enter_sleep()`) also forces the state cleanly.

### 3. gui/widget.py
- The "💤 Zzz" overlay label is now strictly tied to receiving `KuriState.SLEEPING`.
- Re-forcing the state from core also re-shows the Zzz indicator.

## How to Search for This Fix Later
Use these keywords in the codebase:
- `SLEEP_ANIMATION_FIX`
- `SLEEP_VISUAL_PERSIST`
- `LIVE2D_SLEEP`
- `Mic suspenso`
- `_sleep_params`
- `StopAllMotions` + SLEEPING

## Prevention / Future Tips
- Always special-case SLEEPING (or any "low power" state) before generic state logic.
- Force visual/parameter changes **after** Live2D `Update()`.
- When you have a "suspended" path that avoids heavy work, periodically re-emit the desired state so downstream components (avatar, UI) stay in sync.
- Guard reset/wake functions with `if current_state == SLEEPING: return`.
- For overlays (like Zzz), drive visibility purely from the authoritative state enum.

This fix was validated by leaving the app idle >5 minutes and confirming the sleepy pose + Zzz stayed visible while FPS remained low.

Last updated: 2026-06 (see git blame on the changed functions for exact commits).
