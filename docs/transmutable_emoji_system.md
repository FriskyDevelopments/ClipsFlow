# ClipsFlow Transmutable Emoji System

This system defines six geometric symbols with four transmutation states each:

- **Base**: clean default form.
- **Idle**: dimmed, low-energy version.
- **Active**: subtle pulse + orbit shimmer for processing.
- **Premium**: filled form, smooth motion, and 5–10% glow.

## Symbol inventory

| Symbol | Semantic | Base | Idle | Active | Premium |
|---|---|---|---|---|---|
| Process | transformation in progress | `assets/emoji_system/process/base.svg` | `assets/emoji_system/process/idle.svg` | `assets/emoji_system/process/active.svg` | `assets/emoji_system/process/premium.svg` |
| Result | finished output | `assets/emoji_system/result/base.svg` | `assets/emoji_system/result/idle.svg` | `assets/emoji_system/result/active.svg` | `assets/emoji_system/result/premium.svg` |
| Unlock | access gained | `assets/emoji_system/unlock/base.svg` | `assets/emoji_system/unlock/idle.svg` | `assets/emoji_system/unlock/active.svg` | `assets/emoji_system/unlock/premium.svg` |
| Free | free-tier state | `assets/emoji_system/free/base.svg` | `assets/emoji_system/free/idle.svg` | `assets/emoji_system/free/active.svg` | `assets/emoji_system/free/premium.svg` |
| Flow | directional motion | `assets/emoji_system/flow/base.svg` | `assets/emoji_system/flow/idle.svg` | `assets/emoji_system/flow/active.svg` | `assets/emoji_system/flow/premium.svg` |
| Energy | intensity + charge | `assets/emoji_system/energy/base.svg` | `assets/emoji_system/energy/idle.svg` | `assets/emoji_system/energy/active.svg` | `assets/emoji_system/energy/premium.svg` |

## Motion + color rules

- **Palette**
  - Stroke/base: `#E8ECF4` / `#B8C0D0`
  - Indigo glow: `#8EA6FF`
  - Violet glow: `#B09AFF`
  - Soft cyan glow: `#8FF2FF`
- **Glow intensity**
  - Keep glow alpha between **0.05 and 0.10**.
- **Animation style**
  - Pulse: opacity cycle (`0.72 → 1.00 → 0.72`, `1.8s`)
  - Orbit: thin ring, slow 360° rotation (`8s` linear)
  - Premium shimmer: low-amplitude opacity breathe (`3s`)

## Optional shared CSS animation spec

```css
:root {
  --cf-ink: #e8ecf4;
  --cf-dim: #b8c0d0;
  --cf-indigo: rgba(142, 166, 255, 0.10);
  --cf-violet: rgba(176, 154, 255, 0.10);
  --cf-cyan: rgba(143, 242, 255, 0.10);
}

.cf-symbol {
  width: 20px;
  height: 20px;
}

.cf-symbol--idle {
  opacity: 0.78;
}

.cf-symbol--active {
  animation: cfPulse 1.8s ease-in-out infinite;
}

.cf-symbol--premium {
  filter: drop-shadow(0 0 8px var(--cf-violet));
  animation: cfBreathe 3s ease-in-out infinite;
}

@keyframes cfPulse {
  0%, 100% { opacity: 0.72; }
  50% { opacity: 1; }
}

@keyframes cfBreathe {
  0%, 100% { opacity: 0.88; }
  50% { opacity: 1; }
}
```

## Bonus: behavior mapping (same symbol, different UI contexts)

### 1) Button
- Default: **base** symbol with neutral stroke.
- Hover: move to **active** (very light pulse only).
- Premium CTA: use **premium** symbol with violet/cyan 8% glow.

### 2) Loading state
- Use **active** variant.
- Keep orbit ring visible at 10–14% stroke opacity max.
- Do not combine with extra spinner if symbol orbit exists.

### 3) Success state
- Transition `active → base` in 200ms.
- Fire one-time micro burst (scale `1.0 → 1.06 → 1.0`, 220ms).
- If premium account, end in **premium** variant for completion reinforcement.
