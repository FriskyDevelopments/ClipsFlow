# STIX MΛGIC Runic System for ClipsFlow

ClipsFlow is modeled as a runic signal machine:

`INPUT → FLOW → Λ TRANSFORM → OUTPUT`

## 1) Rune definitions (state + transformation + signal)

| Rune | Name | Meaning | Shape logic |
|---|---|---|---|
| `⟪` | INPUT | Incoming source/signal detected | Dual opening chevrons that admit signal into the pipeline |
| `→` | FLOW | Pipeline movement is active | Forward shaft + hard arrow head |
| `Λ` | TRANSFORM (CORE) | Conversion/alchemy stage | Apex triangle; all processing converges through Λ |
| `⫶` | SPLIT | Branching/multiplex paths | Single trunk diverges into dual exits |
| `◫` | OUTPUT | Result stabilized/generated | Closed rectangular enclosure |
| `✕` | DISRUPTION | Error/instability detected | Fractured cross segments |
| `⟐` | LOCK | Validation/secure acceptance | Sealed diamond with center node |

Reference implementation lives in `core/runes.py`.

## 2) SVG implementations

Every rune is generated as sharp-line SVG (no decorative curves). See:

- `core/runes.py` (`RUNES[...].svg`) for code-embedded SVG symbols.
- `assets/miniapp/runes_demo.html` for rendered neon runes on dark background.

## 3) Usage in UI + CLI/logs

### Telegram loading and processing state

Bot loading message now renders symbolic progression instead of generic spinner:

```
[⟪] SOURCE LOCKED
[→] FLOW ACTIVE
[Λ] Λ CORE TRANSFORMING
```

### Pipeline and disruption logging

The processing pipeline now emits runic logs such as:

```
[⟪] INPUT SIGNAL ACCEPTED url=<redacted>
[→] FLOW ACTIVE
[✕] Λ TRANSFORMATION FAILURE url=<redacted> reason=<error>
[◫] OUTPUT MATERIALIZED url=<redacted>
```

## 4) Animation behavior (mini app)

`assets/miniapp/runes_demo.html` demonstrates the motion model:

- **Draw-in:** stroke-dash animation traces rune geometry into existence.
- **Flow pulse:** sequential intensity pulse along INPUT → FLOW → Λ → OUTPUT.
- **State switch:** lock and error runes can be toggled; disruption flashes as fracture alert.
- **Style:** dark surface, high-contrast cyan/purple neon edges, no blur-heavy effects.

This matches the system goal: users perceive **activation of a machine**, not a static SaaS spinner.
