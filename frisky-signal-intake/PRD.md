# Frisky Developments Signal Intake System

A premium signal intake and operator console system that feels like proprietary Frisky Developments infrastructure for managing client requests without DMs.

**Experience Qualities**:
1. **Branded Internal Tooling** - Functions like high-bandwidth proprietary infrastructure with clear Frisky Developments identity and system-native terminology
2. **Premium Dark** - Sophisticated glass-morphic surfaces with carbon-like matte finishes, cinematic radial backgrounds, and subtle signal field aesthetics
3. **Supportive Yet Operational** - Technical language that balances human-centered support messaging with precise system-like communication patterns

**Complexity Level**: Complex Application (advanced functionality, likely with multiple views)
This is a dual-interface system with public intake and protected operator console, featuring real-time state management, Discord webhooks, system logging, CSV export, and comprehensive filtering/search capabilities.

## Essential Features

### Public Signal Submission
- **Functionality**: Anonymous form for submitting support/inquiry signals with structured fields (name, contact, type, project, message)
- **Purpose**: Official intake channel that replaces DM-based support requests
- **Trigger**: User navigates to public intake portal
- **Progression**: Land on intake form → Fill required fields → Submit → Receive unique Ticket ID (FRK-XXXX-X) → View confirmation with tracking instructions
- **Success criteria**: Signal stored with unique ID, Discord webhook fired, user can save Ticket ID for tracking

### Status Check Interface
- **Functionality**: Public page where users enter Ticket ID to view vertical progress timeline with system-style state labels
- **Purpose**: Self-service status tracking without operator contact
- **Trigger**: User enters Ticket ID on status check page
- **Progression**: Navigate to status page → Enter Ticket ID → View vertical timeline showing current state and history → See last update timestamp
- **Success criteria**: Accurate state display, clear visual hierarchy, system-inspired labels (SIGNAL_RECEIVED, OPERATOR_ASSIGNED, etc.)

### Operator Console Dashboard
- **Functionality**: Protected internal dashboard with dense signal queue, filtering, search, quick actions, and state management
- **Purpose**: High-bandwidth signal triage and management for staff
- **Trigger**: Operator navigates to /console route (protected)
- **Progression**: Login → View signal queue → Filter/search → Select signal → Quick update state OR open detail view → Add notes → Update status
- **Success criteria**: Fast filtering, visible new signal indicators, smooth state changes, CSV export functional

### Signal Detail View
- **Functionality**: Full signal information with system event log and internal notes interface
- **Purpose**: Deep context for complex signals requiring detailed operator attention
- **Trigger**: Operator clicks signal from queue
- **Progression**: Open detail → Review all fields and history → Add internal notes → Update state → View system log entries → Return to queue
- **Success criteria**: Complete signal context visible, notes persist, system log tracks all state changes

### Discord Webhook Integration
- **Functionality**: Rich embed notification sent to Discord channel on new signal submission
- **Purpose**: Real-time operator alerting outside the console
- **Trigger**: User submits new signal
- **Progression**: Signal submitted → Webhook payload constructed → Discord API called → Embed appears in channel
- **Success criteria**: Embed displays with #FF4500 accent, includes Ticket ID, type, contact, and snippet

### Telegram Bot Integration
- **Functionality**: Markdown-formatted message sent to Telegram channel/group via bot when new signal is submitted
- **Purpose**: Alternative real-time operator alerting through Telegram
- **Trigger**: User submits new signal
- **Progression**: Signal submitted → Bot token and chat ID retrieved → Telegram API called with formatted message → Message appears in configured chat
- **Success criteria**: Message displays with clear formatting, includes all signal details (Ticket ID, type, name, contact, project, message snippet), uses Telegram Markdown for readability

## Edge Case Handling

- **Duplicate Ticket IDs**: Retry logic generates new ID until unique (max 10 attempts)
- **Invalid Ticket ID Lookup**: Clean error state showing "Signal not found" with guidance to verify ID
- **Discord Webhook Failure**: Silent failure logged to console, doesn't block signal submission
- **Telegram Webhook Failure**: Silent failure logged to console, doesn't block signal submission
- **Empty Signal Queue**: Elegant empty state in operator console with "No active signals" message
- **Missing Optional Fields**: System handles nulls gracefully, displays "Not provided" in operator view
- **Webhook URL Not Configured**: Discord and Telegram webhook calls skipped if credentials not set in storage
- **Telegram Configuration Incomplete**: Both bot token and chat ID required; skips notification if either missing

## Design Direction

The design should evoke the feeling of high-grade proprietary infrastructure - a controlled, technical environment where signals are processed with precision. Think operator console, mission control, internal tooling for a product studio. The aesthetic is restrained technical luxury: dark carbon surfaces with subtle glass effects, precision typography, and purposeful motion. This is not a helpdesk - it's a signal processing system.

## Color Selection

**Dark Carbon Foundation with Restrained Orange Accents**

The palette creates a premium soft-dark environment that feels technical yet refined, like matte carbon fiber with subtle glass overlays.

- **Primary Color**: Muted Orange `oklch(0.68 0.15 45)` - Technical accent for CTAs, focus states, and status highlights. Conveys warmth without playfulness.
- **Secondary Colors**:
  - Deep Charcoal `oklch(0.12 0.005 270)` - Secondary surface backgrounds (#14161b region)
  - Glass Panel `oklch(0.98 0 0 / 0.03)` - Translucent white overlay for elevated surfaces
- **Accent Color**: Amber Alert `oklch(0.75 0.14 65)` - New signal indicators and active state highlights
- **Foreground/Background Pairings**:
  - Page Background `oklch(0.09 0.005 270)` (#101114): Pale Gray Text `oklch(0.85 0.01 270)` - Ratio 8.2:1 ✓
  - Glass Panel `oklch(0.98 0 0 / 0.03)` with backdrop blur: White Text `oklch(0.92 0.01 270)` - Ratio 7.5:1 ✓
  - Primary Orange `oklch(0.68 0.15 45)`: Dark Text `oklch(0.12 0.005 270)` - Ratio 5.1:1 ✓
  - Muted Element `oklch(0.45 0.01 270)`: On Dark Background - Ratio 4.6:1 ✓

## Font Selection

**Inter** - Selected for its technical precision, excellent legibility at small sizes (critical for dense operator tables), and neutral professional character that matches internal tooling aesthetics.

- **Typographic Hierarchy**:
  - H1 (Page Titles): Inter SemiBold / 32px / -0.02em tracking / line-height 1.2
  - H2 (Section Headers): Inter Medium / 20px / -0.01em tracking / line-height 1.3
  - H3 (Card Titles, Ticket IDs): Inter Medium / 16px / normal tracking / line-height 1.4
  - Body (Signal content): Inter Regular / 14px / normal tracking / line-height 1.6
  - Small (Timestamps, labels): Inter Medium / 12px / 0.01em tracking / uppercase / line-height 1.4
  - System Labels (Status codes): Inter Medium / 11px / 0.05em tracking / uppercase / line-height 1.3

## Animations

Animations serve precision and clarity - subtle fade-ups on page loads (300ms), smooth 200ms hover lifts on panels, and controlled 250ms state transitions. Focus states expand with soft 200ms ring animations. Nothing flashy, nothing sci-fi gimmicky - just refined motion that reinforces the sense of responsive, high-quality tooling.

## Component Selection

- **Components**:
  - Dialogs: `Dialog` for operator quick actions and confirmations
  - Cards: `Card` with heavy customization (glass backgrounds, soft shadows, border treatments)
  - Forms: `Form` + `Input` + `Label` + `Select` + `Textarea` with dark charcoal backgrounds
  - Tables: `Table` for operator signal queue with custom hover states
  - Badges: `Badge` for status indicators with custom variant styles
  - Buttons: `Button` with custom variants (ghost for secondary, default heavily styled for premium dark)
  - Scroll Areas: `ScrollArea` for signal detail logs
  - Separator: `Separator` for visual hierarchy

- **Customizations**:
  - Custom glass panel wrapper component with backdrop-blur and rgba borders
  - Custom status badge component with state-specific colors
  - Custom timeline component for vertical progress states
  - System log entry component with timestamp and event type styling

- **States**:
  - Buttons: Default dark with subtle border → Hover adds orange tint and slight lift → Active scales down 98% → Focus shows orange ring
  - Inputs: Dark charcoal background → Focus shows orange ring with smooth expansion → Filled shows subtle border brightening
  - Signal rows: Default muted → Hover shows glass panel effect → New signals have amber left border and subtle glow

- **Icon Selection**:
  - Phosphor icons: `PaperPlaneRight` (submit), `MagnifyingGlass` (search), `Funnel` (filter), `Note` (internal notes), `CheckCircle` (complete), `Clock` (pending), `Export` (CSV), `Eye` (view detail), `X` (close)

- **Spacing**: Consistent 4/8/12/16/24/32 scale - 16px default gap in forms, 24px between major sections, 32px page padding, 8px internal card padding

- **Mobile**:
  - Stack operator table to card list on <768px
  - Reduce page padding to 16px
  - Single column forms throughout
  - Fixed bottom action bar for primary CTAs
  - Status timeline remains vertical but with tighter spacing
  - Console switches to mobile-optimized card stack with swipe actions for quick state changes
