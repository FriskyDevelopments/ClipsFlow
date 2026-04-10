const fs = require('fs');

let content = fs.readFileSync('IntakePage.tsx', 'utf8');

// Add AccessDenied import
content = content.replace(
  'import { motion } from "framer-motion"',
  'import { motion } from "framer-motion"\nimport { AccessDenied } from "./AccessDenied"'
);

// Add useSearchParams
content = content.replace(
  'import { useNavigate } from "react-router-dom"',
  'import { useNavigate, useSearchParams } from "react-router-dom"'
);

// Add useSearchParams to component
content = content.replace(
  'const navigate = useNavigate()',
  'const navigate = useNavigate()\n  const [searchParams] = useSearchParams()'
);

// Add isProUser check
content = content.replace(
  '  return (\n    <div className="min-h-screen bg-background">',
  '  const isProUser = searchParams.has("session_id")\n\n  return (\n    <div className="min-h-screen bg-background">'
);

// Replace GlassPanel with condition
const glassPanelStart = '<GlassPanel>';
const glassPanelEnd = '</GlassPanel>';

const conditionStart = '{!isProUser ? (\n          <AccessDenied />\n        ) : (\n          <GlassPanel>';
const conditionEnd = '</GlassPanel>\n        )}';

content = content.replace(glassPanelStart, conditionStart);
content = content.replace(glassPanelEnd, conditionEnd);

fs.writeFileSync('IntakePage.tsx', content);
