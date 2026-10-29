import React from 'react';
import { AbsoluteFill, Composition, Img, Sequence, interpolate, registerRoot, staticFile, useCurrentFrame } from 'remotion';
import { Video } from '@remotion/media';

const FPS = 30;
const INTRO = 4 * FPS;
const DEMO = 734;
const OUTRO = 4 * FPS;
const colors = { background: '#100c1b', text: '#f8f1ff', muted: '#c2b5d1', accent: '#ffb96e' };
const base = { background: colors.background, color: colors.text, fontFamily: 'Arial, sans-serif' };

function Entrance({ children, style }) {
  const frame = useCurrentFrame();
  const opacity = interpolate(frame, [0, 12], [0, 1], { extrapolateRight: 'clamp' });
  const y = interpolate(frame, [0, 16], [15, 0], { extrapolateRight: 'clamp' });
  return <div style={{ ...style, opacity, transform: `translateY(${y}px)` }}>{children}</div>;
}

function Intro() {
  const frame = useCurrentFrame();
  return <AbsoluteFill style={base}>
    <Img src={staticFile('halloween-circuit.png')} style={{ position: 'absolute', right: -90, top: 0, width: 1080, height: 1080, opacity: .8, transform: `scale(${1 + frame * .0002})` }} />
    <AbsoluteFill style={{ background: 'linear-gradient(90deg, #100c1b 15%, #100c1be8 38%, transparent 85%)' }} />
    <Entrance style={{ position: 'absolute', left: 85, top: 300, width: 690 }}>
      <h1 style={{ fontSize: 80, lineHeight: 1.08, margin: '28px 0' }}>Conduce<br />con tu voz</h1>
    </Entrance>
  </AbsoluteFill>;
}

const explanations = [
  ['01 / HABLA', 'Whisper transcribe tu voz.', ''],
  ['02 / DECIDE', 'Kev evalúa la orden y elige una acción.', ''],
  ['03 / CONDUCE', 'El juego ejecuta la decisión.', 'Arrancar, girar, parar o dar marcha atrás.'],
  ['', 'Escena creada en Blender y animada con Three.js', ''],
];

function Demo() {
  const frame = useCurrentFrame();
  const step = Math.min(3, Math.floor(frame / 185));
  const [label, title, subtitle] = explanations[step];
  return <AbsoluteFill style={base}>
    <div style={{ position: 'absolute', left: 80, top: 34, color: colors.accent, fontSize: 19, letterSpacing: 2 }}>{label}</div>
    <div style={{ position: 'absolute', left: 80, top: 70, fontSize: 43, fontWeight: 700 }}>{title}</div>
    <div style={{ position: 'absolute', left: 80, top: 129, fontSize: 24, color: colors.muted }}>{subtitle}</div>
    <div style={{ position: 'absolute', left: 80, top: 194, width: 1280, height: 800, overflow: 'hidden', borderRadius: 16, border: '1px solid #493551' }}>
      <Video src={staticFile('demo.mp4')} muted style={{ width: '100%', height: '100%' }} />
    </div>
    <div style={{ position: 'absolute', bottom: 0, height: 4, width: `${frame / DEMO * 100}%`, background: colors.accent }} />
  </AbsoluteFill>;
}

function Outro() {
  const cards = [['Whisper', 'Transcribir'], ['Kev', 'Decidir'], ['Ejecutar decisión', null]];
  return <AbsoluteFill style={{ ...base, padding: '240px 100px' }}>
    <Entrance>
      <div style={{ display: 'flex', alignItems: 'center', gap: 20 }}>
        {cards.map(([title, action], index) => <React.Fragment key={title}>
          {index > 0 && <span style={{ fontSize: 38, color: colors.accent }}>→</span>}
          <div style={{ flex: 1, border: '1px solid #705178', borderRadius: 16, padding: '40px 28px' }}>
            <div style={{ fontSize: action ? 45 : 38, fontWeight: 700, color: colors.accent }}>{title}</div>
            {action && <div style={{ fontSize: 29, marginTop: 28 }}>{action}</div>}
          </div>
        </React.Fragment>)}
      </div>
      <p style={{ fontSize: 35, marginTop: 65 }}>Modelos integrados con <b style={{ color: colors.accent }}>RunOnWeb de midudev</b>.</p>
      <p style={{ fontSize: 25, color: colors.muted, lineHeight: 1.6 }}>Los pesos se descargan desde Hugging Face.<br />Voz y decisiones se procesan en el navegador del jugador.</p>
    </Entrance>
  </AbsoluteFill>;
}

function Explainer() {
  return <AbsoluteFill style={base}>
    <Sequence durationInFrames={INTRO}><Intro /></Sequence>
    <Sequence from={INTRO} durationInFrames={DEMO}><Demo /></Sequence>
    <Sequence from={INTRO + DEMO} durationInFrames={OUTRO}><Outro /></Sequence>
  </AbsoluteFill>;
}

registerRoot(() => <Composition id="HowToDrive" component={Explainer} width={1440} height={1080} fps={FPS} durationInFrames={INTRO + DEMO + OUTRO} />);
