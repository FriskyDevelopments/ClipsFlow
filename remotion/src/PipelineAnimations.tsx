import React from 'react';
import {
  AbsoluteFill,
  Easing,
  interpolate,
  Sequence,
  useCurrentFrame,
  useVideoConfig,
} from 'remotion';

type Stage = {
  label: string;
  detail: string;
  tone: 'idle' | 'active' | 'ok' | 'warn';
};

type PipelineSceneProps = {
  episode: string;
  title: string;
  subtitle: string;
  stages: Stage[];
  primaryCopy: string;
  secondaryCopy: string;
  footer: string;
  accent: string;
  pathMode: 'intake' | 'guardrails' | 'delivery';
};

const colors = {
  bg: '#0d1016',
  bg2: '#101720',
  ink: '#fffaf0',
  muted: '#a9b4af',
  line: '#253132',
  lime: '#d6ef7d',
  cyan: '#75cbbe',
  amber: '#f0c56b',
  rose: '#ee8d8d',
};

const ease = Easing.bezier(0.16, 1, 0.3, 1);

const clamp = {
  extrapolateLeft: 'clamp' as const,
  extrapolateRight: 'clamp' as const,
};

const fade = (frame: number, start: number, end: number) =>
  interpolate(frame, [start, end], [0, 1], {...clamp, easing: ease});

const pulse = (frame: number, start: number, length: number) => {
  const local = Math.max(frame - start, 0);
  return interpolate(local % length, [0, length / 2, length], [0.72, 1, 0.72], clamp);
};

const shell: React.CSSProperties = {
  background:
    'radial-gradient(circle at 18% 14%, rgba(214,239,125,0.10), transparent 24%), radial-gradient(circle at 82% 78%, rgba(117,203,190,0.10), transparent 28%), #0d1016',
  color: colors.ink,
  fontFamily:
    'Inter, ui-sans-serif, system-ui, -apple-system, BlinkMacSystemFont, "Segoe UI", sans-serif',
  padding: 72,
};

const smallCaps: React.CSSProperties = {
  color: colors.muted,
  fontSize: 24,
  letterSpacing: 7,
  textTransform: 'uppercase',
  fontWeight: 700,
};

const titleStyle: React.CSSProperties = {
  fontSize: 88,
  lineHeight: 0.92,
  fontWeight: 800,
  letterSpacing: 0,
  marginTop: 68,
  maxWidth: 760,
};

const subtitleStyle: React.CSSProperties = {
  color: '#c5cec8',
  fontSize: 34,
  lineHeight: 1.25,
  marginTop: 28,
  maxWidth: 790,
};

const toneColor = (tone: Stage['tone']) => {
  if (tone === 'ok') return colors.lime;
  if (tone === 'warn') return colors.amber;
  if (tone === 'active') return colors.cyan;
  return '#435052';
};

const Header = ({episode, title, subtitle}: Pick<PipelineSceneProps, 'episode' | 'title' | 'subtitle'>) => {
  const frame = useCurrentFrame();
  const headerIn = fade(frame, 0, 24);
  const titleIn = fade(frame, 12, 48);

  return (
    <div>
      <div style={{...smallCaps, opacity: headerIn}}>CLIPSFLOW PIPELINE / {episode}</div>
      <div
        style={{
          ...titleStyle,
          opacity: titleIn,
          transform: `translateY(${interpolate(titleIn, [0, 1], [28, 0])}px)`,
        }}
      >
        {title}
      </div>
      <div style={{...subtitleStyle, opacity: fade(frame, 30, 60)}}>{subtitle}</div>
    </div>
  );
};

const SignalCard = ({
  stages,
  accent,
  start,
}: {
  stages: Stage[];
  accent: string;
  start: number;
}) => {
  const frame = useCurrentFrame();
  const progress = fade(frame, start, start + 36);

  return (
    <div
      style={{
        position: 'absolute',
        left: 72,
        right: 72,
        bottom: 86,
        border: `2px solid ${colors.line}`,
        background: 'rgba(16,23,32,0.92)',
        borderRadius: 16,
        padding: 36,
        opacity: progress,
        transform: `translateY(${interpolate(progress, [0, 1], [30, 0])}px)`,
        boxShadow: '0 34px 120px rgba(0,0,0,0.34)',
      }}
    >
      <div
        style={{
          height: 2,
          background: `linear-gradient(90deg, transparent, ${accent}, transparent)`,
          margin: '-36px 0 34px',
        }}
      />
      <div style={{display: 'grid', gridTemplateColumns: `repeat(${stages.length}, 1fr)`, gap: 18}}>
        {stages.map((stage, index) => {
          const itemIn = fade(frame, start + index * 14, start + index * 14 + 28);
          const scale = stage.tone === 'active' ? pulse(frame, start + index * 10, 54) : 1;
          return (
            <div key={stage.label} style={{opacity: itemIn}}>
              <div style={{display: 'flex', alignItems: 'center', gap: 12}}>
                <div
                  style={{
                    width: 18,
                    height: 18,
                    borderRadius: 99,
                    background: toneColor(stage.tone),
                    transform: `scale(${scale})`,
                    boxShadow: `0 0 28px ${toneColor(stage.tone)}66`,
                  }}
                />
                <div style={{...smallCaps, fontSize: 18, letterSpacing: 4}}>{stage.label}</div>
              </div>
              <div style={{color: '#d4dbd6', fontSize: 24, lineHeight: 1.22, marginTop: 18}}>
                {stage.detail}
              </div>
            </div>
          );
        })}
      </div>
    </div>
  );
};

const IntakePath = ({accent}: {accent: string}) => {
  const frame = useCurrentFrame();
  const draw = fade(frame, 84, 170);
  const packet = interpolate(draw, [0, 1], [118, 780]);
  const packetY = 518 + Math.sin(draw * Math.PI) * -72;

  return (
    <div style={{position: 'absolute', inset: 0}}>
      <svg width="1080" height="1080" style={{position: 'absolute', inset: 0}}>
        <path
          d="M132 520 C310 390 470 660 646 522 S840 412 936 512"
          fill="none"
          stroke={colors.line}
          strokeWidth="4"
          strokeDasharray="12 18"
          opacity="0.85"
        />
        <path
          d="M132 520 C310 390 470 660 646 522 S840 412 936 512"
          fill="none"
          stroke={accent}
          strokeWidth="5"
          strokeLinecap="round"
          strokeDasharray={`${draw * 980} 980`}
        />
      </svg>
      <div style={{...nodeStyle(118, 486, accent), opacity: fade(frame, 58, 82)}}>URL</div>
      <div style={{...nodeStyle(430, 624, colors.cyan), opacity: fade(frame, 106, 132)}}>BOT</div>
      <div style={{...nodeStyle(768, 460, colors.lime), opacity: fade(frame, 150, 176)}}>MEDIA</div>
      <div
        style={{
          position: 'absolute',
          left: packet,
          top: packetY,
          width: 54,
          height: 54,
          borderRadius: 14,
          background: accent,
          boxShadow: `0 0 52px ${accent}88`,
          opacity: fade(frame, 82, 104),
          transform: 'rotate(12deg)',
        }}
      />
    </div>
  );
};

const GuardrailPath = ({accent}: {accent: string}) => {
  const frame = useCurrentFrame();
  const scan = fade(frame, 74, 190);
  const shield = fade(frame, 130, 170);
  const reject = fade(frame, 196, 232);

  return (
    <div style={{position: 'absolute', inset: 0}}>
      <div
        style={{
          position: 'absolute',
          left: 130,
          top: 472,
          width: 820,
          height: 188,
          borderRadius: 18,
          border: `2px solid ${colors.line}`,
          background:
            'linear-gradient(135deg, rgba(255,250,240,0.04) 25%, transparent 25% 50%, rgba(255,250,240,0.04) 50% 75%, transparent 75%)',
          backgroundSize: '28px 28px',
          overflow: 'hidden',
          opacity: fade(frame, 48, 78),
        }}
      >
        <div
          style={{
            position: 'absolute',
            top: 0,
            bottom: 0,
            left: interpolate(scan, [0, 1], [-220, 840]),
            width: 220,
            background: `linear-gradient(90deg, transparent, ${accent}55, transparent)`,
          }}
        />
        <div
          style={{
            position: 'absolute',
            left: 40,
            top: 54,
            fontSize: 36,
            fontWeight: 800,
          }}
        >
          Source: 20m00s / 2.1MB
        </div>
        <div style={{position: 'absolute', left: 42, top: 108, color: colors.muted, fontSize: 26}}>
          Duration wins over tiny file size.
        </div>
      </div>
      <div
        style={{
          position: 'absolute',
          right: 138,
          top: 444,
          width: 172,
          height: 172,
          borderRadius: 36,
          background: `linear-gradient(180deg, ${colors.amber}, #463a20)`,
          opacity: shield,
          transform: `scale(${interpolate(shield, [0, 1], [0.72, 1])})`,
          boxShadow: '0 30px 80px rgba(240,197,107,0.22)',
        }}
      />
      <div
        style={{
          position: 'absolute',
          right: 176,
          top: 482,
          color: '#1a160b',
          fontSize: 74,
          fontWeight: 900,
          opacity: shield,
        }}
      >
        !
      </div>
      <div
        style={{
          position: 'absolute',
          left: 156,
          top: 702,
          color: colors.amber,
          fontSize: 44,
          fontWeight: 900,
          opacity: reject,
          transform: `translateX(${interpolate(reject, [0, 1], [-24, 0])}px)`,
        }}
      >
        Reject before expensive processing.
      </div>
    </div>
  );
};

const DeliveryPath = ({accent}: {accent: string}) => {
  const frame = useCurrentFrame();
  const upload = fade(frame, 72, 178);
  const sent = fade(frame, 190, 240);
  const mark = fade(frame, 112, 154);

  return (
    <div style={{position: 'absolute', inset: 0}}>
      <div style={{...nodeStyle(124, 548, colors.cyan), opacity: fade(frame, 44, 72)}}>EXPORT</div>
      <div style={{...nodeStyle(748, 548, accent), opacity: fade(frame, 178, 206)}}>CHAT</div>
      <div
        style={{
          position: 'absolute',
          left: 300,
          top: 602,
          width: 470,
          height: 12,
          borderRadius: 99,
          background: colors.line,
          opacity: fade(frame, 62, 88),
        }}
      />
      <div
        style={{
          position: 'absolute',
          left: 300,
          top: 602,
          width: interpolate(upload, [0, 1], [0, 470]),
          height: 12,
          borderRadius: 99,
          background: `linear-gradient(90deg, ${colors.cyan}, ${accent})`,
          boxShadow: `0 0 34px ${accent}66`,
        }}
      />
      <div
        style={{
          position: 'absolute',
          left: 392,
          top: 490,
          border: `2px solid ${colors.line}`,
          borderRadius: 18,
          padding: '20px 26px',
          background: colors.bg2,
          color: colors.ink,
          fontSize: 28,
          fontWeight: 800,
          opacity: mark,
        }}
      >
        ClipFLOW Free
      </div>
      <div
        style={{
          position: 'absolute',
          left: 378,
          top: 672,
          color: sent ? colors.lime : colors.muted,
          fontSize: 42,
          fontWeight: 900,
          opacity: fade(frame, 188, 224),
        }}
      >
        Delivered only after Telegram confirms.
      </div>
    </div>
  );
};

const nodeStyle = (left: number, top: number, accent: string): React.CSSProperties => ({
  position: 'absolute',
  left,
  top,
  width: 182,
  height: 104,
  borderRadius: 22,
  border: `2px solid ${accent}66`,
  background: colors.bg2,
  color: colors.ink,
  display: 'flex',
  alignItems: 'center',
  justifyContent: 'center',
  fontSize: 30,
  fontWeight: 900,
  boxShadow: `0 24px 90px ${accent}1f`,
});

const PathLayer = ({mode, accent}: {mode: PipelineSceneProps['pathMode']; accent: string}) => {
  if (mode === 'guardrails') return <GuardrailPath accent={accent} />;
  if (mode === 'delivery') return <DeliveryPath accent={accent} />;
  return <IntakePath accent={accent} />;
};

const ClosingPanel = ({copy, footer, accent}: {copy: string; footer: string; accent: string}) => {
  const frame = useCurrentFrame();
  const {fps} = useVideoConfig();
  const start = 9.2 * fps;
  const entrance = fade(frame, start, start + 28);

  return (
    <div
      style={{
        position: 'absolute',
        left: 72,
        right: 72,
        top: 270,
        padding: 54,
        borderRadius: 22,
        background: 'rgba(13,16,22,0.94)',
        border: `2px solid ${accent}55`,
        opacity: entrance,
        transform: `translateY(${interpolate(entrance, [0, 1], [40, 0])}px)`,
        boxShadow: '0 40px 140px rgba(0,0,0,0.42)',
      }}
    >
      <div style={{fontSize: 66, lineHeight: 1, fontWeight: 900, maxWidth: 780}}>{copy}</div>
      <div style={{marginTop: 36, color: colors.muted, fontSize: 28, lineHeight: 1.25}}>{footer}</div>
    </div>
  );
};

const PipelineScene = ({
  episode,
  title,
  subtitle,
  stages,
  primaryCopy,
  secondaryCopy,
  footer,
  accent,
  pathMode,
}: PipelineSceneProps) => {
  const frame = useCurrentFrame();
  const {fps} = useVideoConfig();
  const stageBadge = pathMode === 'intake' ? 'INTAKE' : pathMode === 'guardrails' ? 'CHECK' : 'DELIVER';

  return (
    <AbsoluteFill style={shell}>
      <Header episode={episode} title={title} subtitle={subtitle} />
      <Sequence from={2.2 * fps}>
        <PathLayer mode={pathMode} accent={accent} />
      </Sequence>
      <SignalCard stages={stages} accent={accent} start={6.2 * fps} />
      <ClosingPanel copy={primaryCopy} footer={`${secondaryCopy} ${footer}`} accent={accent} />
      <div
        style={{
          position: 'absolute',
          right: 72,
          top: 72,
          color: colors.muted,
          fontSize: 24,
          letterSpacing: 5,
          opacity: fade(frame, 0, 20),
        }}
      >
        {stageBadge}
      </div>
    </AbsoluteFill>
  );
};

export const PipelineIntake = () => (
  <PipelineScene
    episode="01"
    title="From link to media signal"
    subtitle="A user drops a URL. ClipsFlow normalizes it, routes it, and resolves the source before any heavy work begins."
    accent={colors.lime}
    pathMode="intake"
    stages={[
      {label: 'Link', detail: 'Normalize and validate the incoming URL.', tone: 'ok'},
      {label: 'Route', detail: 'Pick the provider that owns the source.', tone: 'active'},
      {label: 'Resolve', detail: 'Pull the direct media candidate and metadata.', tone: 'idle'},
    ]}
    primaryCopy="The bot should feel calm because the system knows where the clip is going."
    secondaryCopy="No fake completion. No mystery queue."
    footer="The first promise is routing clarity."
  />
);

export const PipelineGuardrails = () => (
  <PipelineScene
    episode="02"
    title="Duration beats file size"
    subtitle="A 2MB export can still come from a 20-minute source. ClipsFlow checks duration before transcode, watermark, or upload."
    accent={colors.amber}
    pathMode="guardrails"
    stages={[
      {label: 'Probe', detail: 'ffprobe fills missing duration after download.', tone: 'active'},
      {label: 'Limit', detail: 'Trial clips stay inside the configured runway.', tone: 'warn'},
      {label: 'Reject', detail: 'Long sources stop before expensive processing.', tone: 'ok'},
    ]}
    primaryCopy="Small file does not mean cheap pipeline."
    secondaryCopy="The guardrail exists before the cost."
    footer="That is how the 20-minute trap gets closed."
  />
);

export const PipelineDelivery = () => (
  <PipelineScene
    episode="03"
    title="Delivery is a real step"
    subtitle="Free exports get watermarked, Pro can use clean cache, and Telegram delivery is only complete after the send resolves."
    accent={colors.cyan}
    pathMode="delivery"
    stages={[
      {label: 'Mark', detail: 'Free tier receives the ClipFLOW watermark.', tone: 'warn'},
      {label: 'Upload', detail: 'Telegram progress is real upload state.', tone: 'active'},
      {label: 'Confirm', detail: 'Only confirmed sends count as delivered.', tone: 'ok'},
    ]}
    primaryCopy="The user sees the export when Telegram actually has it."
    secondaryCopy="Not at ninety-nine. Not at almost."
    footer="Delivery is the finish line."
  />
);
