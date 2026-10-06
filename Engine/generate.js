const pptxgen = require('pptxgenjs');
const fs = require('fs');

const data = JSON.parse(fs.readFileSync(process.argv[2], 'utf8'));
const logo = process.argv[3];
const out = process.argv[4];

const p = new pptxgen();
p.layout = 'LAYOUT_WIDE';
p.author = 'SeaTech';
p.subject = 'Évaluation pédagogique';
p.title = data.context.course;
p.lang = 'fr-FR';

const profile = data.report_profile || {};
const brand = profile.brand || {};
const chartOptions = profile.charts || {};

const C = {
  navy: brand.primary || '17365D',
  blue: brand.secondary || '2F6CAF',
  green: brand.accent || 'A8D431',
  bg: 'F4F7FA',
  white: 'FFFFFF',
  ink: '243447',
  muted: '66788A',
  grid: 'D9E2EC',
  low: 'B85042',
  medium: 'D89B32',
  high: '4C956C'
};

// Palette qualitative SeaTech inspiree de seaborn / ColorBrewer Accent.
// La premiere couleur est remplacee par le vert SeaTech, puis les teintes
// Accent sont conservees dans leur ordre. Les deux dernieres couleurs
// prolongent la palette jusqu'au maximum de 10 categories accepte par l'app.
const SEATECH_ACCENT_PALETTE = [
  C.green,   // Vert SeaTech
  'BEAED4',  // Lavande Accent
  'FDC086',  // Orange clair Accent
  "1B9E77",  // Bleu-vert soutenu
  '386CB0',  // Bleu Accent
  'F0027F',  // Magenta Accent
  'BF5B17',  // Brun-orange Accent
  '666666',  // Gris Accent
  C.blue,    // Bleu SeaTech, extension pour la 9e categorie
  C.navy     // Bleu marine SeaTech, extension pour la 10e categorie
];

function categoryColor(index) {
  return SEATECH_ACCENT_PALETTE[index % SEATECH_ACCENT_PALETTE.length];
}

const reportFont = brand.font || 'Arial';
const showBinaryGauge = chartOptions.binary_gauge !== false;
const showConnectors = chartOptions.show_connectors !== false;
const showConfidenceIntervals = chartOptions.show_confidence_intervals !== false;
const maximumCategories = Math.max(3, Math.min(10, Number(chartOptions.maximum_categories || 8)));
const ciTransparency = Math.max(0, Math.min(90, Number(chartOptions.ci_transparency ?? 62)));
const responseRate = Number(data.statistics.response_rate || 0);
const confidenceLevel = Number(data.statistics.confidence || 0.95);
const confidenceZ = confidenceLevel >= 0.985 ? 2.5758 : (confidenceLevel >= 0.925 ? 1.96 : 1.6449);
const ciLabel = `IC${Math.round(confidenceLevel * 100)} %`;

p.theme = { headFontFace: reportFont, bodyFontFace: reportFont, lang: 'fr-FR' };

function responseTier(rate) {
  if (rate < 0.30) {
    return {
      key: 'faible', label: 'Taux de réponse faible', color: C.low,
      scope: 'Résultats indicatifs parmi les répondants. Ne pas généraliser à toute la promotion.',
      interpretation: 'Les constats et recommandations doivent être formulés comme des signaux issus des réponses recueillies.'
    };
  }
  if (rate <= 0.70) {
    return {
      key: 'intermédiaire', label: 'Taux de réponse intermédiaire', color: C.medium,
      scope: 'Tendances utiles, à interpréter avec prudence en raison d’une non-réponse encore substantielle.',
      interpretation: 'Les résultats permettent d’orienter l’analyse, sans garantir une représentativité complète.'
    };
  }
  return {
    key: 'fort', label: 'Taux de réponse fort', color: C.high,
    scope: 'Base de réponses solide pour décrire la promotion, sous réserve d’éventuels biais de non-réponse.',
    interpretation: 'Les tendances sont plus robustes, mais une association observée ne constitue pas une causalité.'
  };
}

const tier = responseTier(responseRate);

function formatPercent(value) {
  return `${(100 * Number(value || 0)).toFixed(1).replace('.', ',')} %`;
}

function formatInterval(low, high) {
  return `[${formatPercent(low)} ; ${formatPercent(high)}]`;
}

function normalizeToken(value) {
  return String(value || '')
    .trim().toLowerCase().normalize('NFD')
    .replace(/[\u0300-\u036f]/g, '')
    .replace(/[’']/g, ' ')
    .replace(/[^a-z0-9]+/g, ' ')
    .trim();
}

function isYesToken(value) {
  const token = normalizeToken(value);
  return token === 'oui' || token === 'yes' || token.startsWith('oui ');
}

function isNoToken(value) {
  const token = normalizeToken(value);
  return token === 'non' || token === 'no' || token.startsWith('non ');
}

function getBinaryDefinition(rows) {
  if (!rows.length || rows.length > 2) return null;
  const yesRow = rows.find(row => isYesToken(row.label));
  const noRow = rows.find(row => isNoToken(row.label));
  const onlyYesNo = rows.every(row => isYesToken(row.label) || isNoToken(row.label));
  if (onlyYesNo && (yesRow || noRow)) {
    return { leftLabel: 'Non', rightLabel: 'Oui', leftRow: noRow || null, rightRow: yesRow || null };
  }
  if (rows.length === 2) {
    return {
      leftLabel: String(rows[0].label), rightLabel: String(rows[1].label),
      leftRow: rows[0], rightRow: rows[1]
    };
  }
  return null;
}

function wilsonInterval(count, total) {
  if (!total) return { low: 0, high: 0 };
  const z = confidenceZ;
  const proportion = count / total;
  const denominator = 1 + z * z / total;
  const center = (proportion + z * z / (2 * total)) / denominator;
  const margin = z * Math.sqrt(
    proportion * (1 - proportion) / total + z * z / (4 * total * total)
  ) / denominator;
  return { low: Math.max(0, center - margin), high: Math.min(1, center + margin) };
}

function base(title) {
  const slide = p.addSlide();
  slide.background = { color: C.bg };
  slide.addShape(p.ShapeType.rect, {
    x: 0, y: 0, w: 13.333, h: 0.12,
    fill: { color: C.green }, line: { color: C.green }
  });
  slide.addText(title, {
    x: 0.65, y: 0.38, w: 11.5, h: 0.45,
    fontSize: 24, bold: true, color: C.navy, margin: 0, fit: 'shrink'
  });
  slide.addImage({ path: logo, x: 11.68, y: 6.84, w: 1.0, h: 0.36 });
  return slide;
}

function card(slide, x, y, w, h, title, body, color = C.blue) {
  slide.addShape(p.ShapeType.roundRect, {
    x, y, w, h, fill: { color: C.white }, line: { color: C.grid }
  });
  slide.addText(title, {
    x: x + 0.22, y: y + 0.18, w: w - 0.44, h: 0.3,
    fontSize: 15, bold: true, color, margin: 0, fit: 'shrink'
  });
  slide.addText(body, {
    x: x + 0.22, y: y + 0.65, w: w - 0.44, h: h - 0.82,
    fontSize: 11.5, color: C.ink, margin: 0.03, valign: 'top', fit: 'shrink'
  });
}

function polarPoint(cx, cy, r, angleDeg) {
  const rad = (Math.PI / 180) * angleDeg;
  return { x: cx + r * Math.cos(rad), y: cy + r * Math.sin(rad) };
}

// Anneau annoté : arc de fond, arc de proportion, arc fin d'IC en surcouche,
// pourcentage au centre, erreur (demi-largeur de l'IC) juste en dessous.
function xmlEscape(value) {
  return String(value).replace(/[&<>"']/g, character => ({
    '&': '&amp;', '<': '&lt;', '>': '&gt;', '"': '&quot;', "'": '&apos;'
  }[character]));
}

function clamp01(value) {
  const numeric = Number(value);
  if (!Number.isFinite(numeric)) return 0;
  return Math.max(0, Math.min(1, numeric));
}

function svgPolarPoint(cx, cy, radius, proportion) {
  const angle = -90 + 360 * clamp01(proportion);
  const rad = angle * Math.PI / 180;
  return {
    x: cx + radius * Math.cos(rad),
    y: cy + radius * Math.sin(rad)
  };
}

function svgArcPath(cx, cy, radius, startProportion, endProportion) {
  const start = clamp01(startProportion);
  const end = Math.max(start, clamp01(endProportion));
  const span = end - start;
  if (span <= 0) return '';
  const safeEnd = span >= 0.999999 ? start + 0.999999 : end;
  const startPoint = svgPolarPoint(cx, cy, radius, start);
  const endPoint = svgPolarPoint(cx, cy, radius, safeEnd);
  const largeArcFlag = safeEnd - start > 0.5 ? 1 : 0;
  return `M ${startPoint.x} ${startPoint.y} A ${radius} ${radius} 0 ${largeArcFlag} 1 ${endPoint.x} ${endPoint.y}`;
}

function donutSvgData(proportion, ciLow, ciHigh, color) {
  const pValue = clamp01(proportion);
  const low = clamp01(ciLow);
  const high = Math.max(low, clamp01(ciHigh));
  const radius = 64;
  const innerRadius = 50.5;
  const outerRadius = 77.5;
  const ciRadius = 82;

  // Repere commun : 0 % au nord, progression horaire pour le remplissage,
  // l'IC, les graduations et les annotations.
  const valuePath = svgArcPath(100, 100, radius, 0, pValue);
  const valueArc = valuePath
    ? `<path d="${valuePath}" fill="none" stroke="#${xmlEscape(color)}" stroke-width="27" stroke-linecap="butt"/>`
    : '';

  const ciPath = svgArcPath(100, 100, ciRadius, low, high);
  const ciArc = showConfidenceIntervals && ciPath
    ? `<path d="${ciPath}" fill="none" stroke="#${xmlEscape(color)}" stroke-opacity="${Math.max(0, Math.min(1, 1 - ciTransparency / 100))}" stroke-width="7" stroke-linecap="round"/>`
    : '';

  const graduationLines = Array.from({ length: 10 }, (_, index) => {
    const tick = index / 10;
    const inner = svgPolarPoint(100, 100, innerRadius, tick);
    const outer = svgPolarPoint(100, 100, outerRadius, tick);
    return `<line x1="${inner.x}" y1="${inner.y}" x2="${outer.x}" y2="${outer.y}" stroke="#000000" stroke-width="1.15" stroke-dasharray="1.5 2.2" stroke-linecap="round"/>`;
  }).join('');

  const svg = `<svg xmlns="http://www.w3.org/2000/svg" width="200" height="200" viewBox="0 0 200 200"><circle cx="100" cy="100" r="${radius}" fill="none" stroke="#${C.grid}" stroke-opacity="0.85" stroke-width="27"/>${valueArc}${graduationLines}${ciArc}</svg>`;
  return `data:image/svg+xml;base64,${Buffer.from(svg, 'utf8').toString('base64')}`;
}

function confidenceBoundaryLabel(value) {
  return `${(100 * clamp01(value)).toFixed(1).replace('.', ',')} %`;
}

function estimateLabelSize(text, fontSizePt) {
  const width = Math.max(0.32, text.length * fontSizePt * 0.50 / 72 + 0.025);
  const height = Math.max(0.12, fontSizePt * 1.12 / 72);
  return { width, height };
}

function boundaryLabelPlacement(centerX, centerY, arcRadius, angleDeg, textWidth, textHeight) {
  const rad = angleDeg * Math.PI / 180;
  const cos = Math.cos(rad);
  const sin = Math.sin(rad);

  // Ecart tres court entre l'extremite de l'arc et le texte.
  const radialGap = 0.012;
  const anchorX = centerX + (arcRadius + radialGap) * cos;
  const anchorY = centerY + (arcRadius + radialGap) * sin;

  let x;
  let y;
  let align;
  if (cos > 0.30) {
    x = anchorX;
    align = 'left';
  } else if (cos < -0.30) {
    x = anchorX - textWidth;
    align = 'right';
  } else {
    x = anchorX - textWidth / 2;
    align = 'center';
  }

  if (sin > 0.30) {
    y = anchorY;
  } else if (sin < -0.30) {
    y = anchorY - textHeight;
  } else {
    y = anchorY - textHeight / 2;
  }
  return { x, y, align };
}

function addConfidenceBoundaryLabels(slide, centerX, centerY, diameter, ciLow, ciHigh, color, fontScale = 1) {
  if (!showConfidenceIntervals || !Number.isFinite(Number(ciLow)) || !Number.isFinite(Number(ciHigh))) return;
  const low = clamp01(ciLow);
  const high = Math.max(low, clamp01(ciHigh));
  const fontSize = Math.max(5.2, Math.min(7.0, 6.6 * fontScale));

  // Dans le SVG, l'IC est a r=82 sur un viewBox de 200. Sur la diapositive,
  // cela correspond exactement a 0,41 * diameter depuis le centre.
  const arcRadius = diameter * 0.41;

  [
    { value: low, text: confidenceBoundaryLabel(low) },
    { value: high, text: confidenceBoundaryLabel(high) }
  ].forEach(({ value, text }) => {
    const angle = -90 + 360 * value;
    const measured = estimateLabelSize(text, fontSize);
    const placement = boundaryLabelPlacement(
      centerX, centerY, arcRadius, angle, measured.width, measured.height
    );
    slide.addText(text, {
      x: placement.x, y: placement.y,
      w: measured.width, h: measured.height,
      fontFace: reportFont, fontSize, bold: true, color,
      margin: 0, align: placement.align, valign: 'mid', fit: 'shrink',
      fill: { color: C.white, transparency: 100 },
      line: { color: C.white, transparency: 100, width: 0 }
    });
  });
}

// Anneau SVG proportionnel avec IC extérieur et bornes annotées.
// Les bornes sont systématiquement ramenées dans l'intervalle [0 % ; 100 %].
function drawAnnotatedDonut(slide, {
  centerX, centerY, diameter, proportion, ciLow, ciHigh,
  color = C.blue, label = '', caption = '', labelBelow = true, fontScale = 1,
  labelHeight = 0.42
}) {
  const r = diameter / 2;
  const x = centerX - r;
  const y = centerY - r;
  const boundedLow = clamp01(ciLow);
  const boundedHigh = Math.max(boundedLow, clamp01(ciHigh));

  slide.addImage({
    data: donutSvgData(proportion, boundedLow, boundedHigh, color),
    x, y, w: diameter, h: diameter
  });
  addConfidenceBoundaryLabels(
    slide, centerX, centerY, diameter,
    boundedLow, boundedHigh, color, fontScale
  );

  slide.addText(formatPercent(clamp01(proportion)), {
    x, y: centerY - r * 0.34, w: diameter, h: r * 0.5,
    fontSize: 15.5 * fontScale, bold: true, color: C.navy,
    align: 'center', valign: 'mid', margin: 0, fit: 'shrink'
  });
  const halfWidth = (boundedHigh - boundedLow) / 2;
  slide.addText(`± ${(100 * halfWidth).toFixed(1).replace('.', ',')} pts`, {
    x, y: centerY + r * 0.06, w: diameter, h: r * 0.34,
    fontSize: 8.4 * fontScale, color: C.muted,
    align: 'center', valign: 'top', margin: 0, fit: 'shrink'
  });

  if (label && labelBelow) {
    slide.addText(label, {
      x: centerX - Math.max(diameter * 0.85, 0.75),
      y: y + diameter + 0.03,
      w: Math.max(diameter * 1.7, 1.5), h: labelHeight,
      fontSize: 8.6 * fontScale, color: C.ink,
      align: 'center', valign: 'top', margin: 0, fit: 'shrink'
    });
  }
  if (caption) {
    slide.addText(caption, {
      x: centerX - Math.max(diameter * 0.85, 0.75),
      y: y + diameter + (label ? labelHeight + 0.04 : 0.03),
      w: Math.max(diameter * 1.7, 1.5), h: 0.30,
      fontSize: 7.4 * fontScale, italic: true, color: C.muted,
      align: 'center', valign: 'top', margin: 0, fit: 'shrink'
    });
  }
}

function addBinaryGauge(slide, rows, definition, cardX, cardY, cardWidth) {
  const rightRow = definition.rightRow;
  const leftRow = definition.leftRow;
  const observedN = Number((rows[0] && rows[0].n) || 0);
  const rightCount = rightRow
    ? Number(rightRow.count)
    : Math.max(0, observedN - Number((leftRow && leftRow.count) || 0));
  const rightProportion = observedN > 0 ? rightCount / observedN : 0;
  const interval = rightRow
    ? { low: Number(rightRow.ci_low), high: Number(rightRow.ci_high) }
    : wilsonInterval(rightCount, observedN);

  const diameter = 1.62;
  const centerX = cardX + 2.05;
  const centerY = cardY + 1.58;

  drawAnnotatedDonut(slide, {
    centerX, centerY, diameter,
    proportion: rightProportion, ciLow: interval.low, ciHigh: interval.high,
    color: C.green, label: `« ${definition.rightLabel} »`
  });

  slide.addText(`${rightCount} « ${definition.rightLabel} » sur ${observedN} répondant(s)`, {
    x: cardX + 3.35, y: cardY + 1.02, w: cardWidth - 3.6, h: 0.32,
    fontSize: 12, bold: true, color: C.ink, margin: 0, fit: 'shrink'
  });
  slide.addText(`« ${definition.leftLabel} » : ${observedN - rightCount} répondant(s) · ${ciLabel} du « ${definition.rightLabel} » ${formatInterval(interval.low, interval.high)}`, {
    x: cardX + 3.35, y: cardY + 1.42, w: cardWidth - 3.6, h: 0.5,
    fontSize: 9.5, color: C.muted, margin: 0, fit: 'shrink'
  });
}

function addCategoricalBars(slide, rows, cardX, cardY, cardWidth) {
  const shownRows = rows.slice(0, maximumCategories);
  const count = shownRows.length;
  if (!count) return;
  const columns = count;
  const horizontalPadding = 0.28;
  const colWidth = (cardWidth - 2 * horizontalPadding) / columns;
  const diameter = Math.max(0.68, Math.min(1.02, colWidth * 0.44));
  const centerY = cardY + 1.35;
  const labelHeight = Math.max(0.34, cardY + 2.38 - (centerY + diameter / 2 + 0.03));
  const fontScale = count >= 6 ? 0.72 : count === 5 ? 0.80 : 0.92;

  shownRows.forEach((row, index) => {
    const centerX = cardX + horizontalPadding + colWidth * (index + 0.5);
    drawAnnotatedDonut(slide, {
      centerX, centerY, diameter,
      proportion: Number(row.proportion || 0),
      ciLow: Number(row.ci_low), ciHigh: Number(row.ci_high),
      color: categoryColor(index),
      label: `${row.label} (${row.count}/${row.n})`,
      fontScale, labelHeight
    });
  });
}

let slide = p.addSlide();
slide.background = { color: C.navy };
slide.addText(data.context.course, {
  x: 0.85, y: 1.10, w: 8.2, h: 0.72,
  fontSize: 30, bold: true, color: C.white, margin: 0, fit: 'shrink'
});
slide.addText('Rapport d’évaluation pédagogique', {
  x: 0.85, y: 2.04, w: 8.5, h: 0.45,
  fontSize: 19, color: 'DCE6F1', margin: 0
});
const coverContext = [data.context.cohort, data.context.academic_year].filter(Boolean).join(' · ');
if (coverContext) {
  slide.addText(coverContext, {
    x: 0.85, y: 2.62, w: 7.8, h: 0.30,
    fontSize: 13.5, bold: true, color: C.white, transparency: 8, margin: 0, fit: 'shrink'
  });
}
slide.addText(`${data.statistics.respondents}/${data.statistics.invited} réponses · ${formatPercent(responseRate)}`, {
  x: 0.85, y: 3.12, w: 4.30, h: 0.35,
  fontSize: 15, bold: true, color: tier.color, margin: 0
});
slide.addShape(p.ShapeType.roundRect, {
  x: 5.30, y: 3.02, w: 2.50, h: 0.47,
  fill: { color: tier.color, transparency: 12 }, line: { color: tier.color, transparency: 100 }
});
slide.addText(tier.label, {
  x: 5.40, y: 3.13, w: 2.30, h: 0.20,
  fontSize: 10.5, bold: true, color: C.white, align: 'center', margin: 0
});
slide.addText(tier.scope, {
  x: 0.85, y: 3.73, w: 7.20, h: 0.70,
  fontSize: 11, color: 'E8EEF4', margin: 0.02, fit: 'shrink'
});
slide.addImage({ path: logo, x: 9.5, y: 1.4, w: 2.7, h: 0.98 });

slide = base('Méthode et portée');
card(slide, 0.7, 1.4, 3.8, 2.2, 'Calculs', 'Taux de réponse\nIntervalles de Wilson\nAnalyses descriptives', C.blue);
const aiTrace = data.ai_trace || {};
const aiLabel = !aiTrace.enabled
  ? 'Désactivée'
  : (aiTrace.provider === 'ollama' ? `Ollama local\n${aiTrace.model || ''}` : 'Albert API');
const interpretationProfileLabel = aiTrace.interpretation_profile_name || 'Institutionnel prudent';
card(slide, 4.77, 1.4, 3.8, 2.2, 'IA', `Interprétation : ${aiLabel}\nProfil : ${interpretationProfileLabel}\nStatistiques immuables`, C.green);
card(slide, 8.84, 1.4, 3.8, 2.2, tier.label, `${tier.scope}\n\n${tier.interpretation}`, tier.color);
card(slide, 0.7, 4.05, 11.94, 1.55, 'Synthèse', data.analysis.summary, C.navy);

const closedQuestions = Array.isArray(data.statistics.closed_questions)
  ? data.statistics.closed_questions
  : [];
const questionsPerSlide = 2;
const statisticsSlideCount = Math.max(1, Math.ceil(closedQuestions.length / questionsPerSlide));

for (let pageIndex = 0; pageIndex < statisticsSlideCount; pageIndex += 1) {
  const pageQuestions = closedQuestions.slice(
    pageIndex * questionsPerSlide,
    pageIndex * questionsPerSlide + questionsPerSlide
  );
  slide = base(`Questions fermées et intervalles de confiance ${pageIndex + 1}/${statisticsSlideCount}`);

  pageQuestions.forEach((question, questionIndex) => {
    const cardX = 0.68;
    const cardY = questionIndex === 0 ? 1.27 : 4.10;
    const cardWidth = 11.98;
    const cardHeight = 2.50;
    const rows = Array.isArray(question.rows) ? question.rows : [];
    const isMultiSelect = /plusieurs r[ée]ponses?/i.test(String(question.question || ''));
    const binaryDefinition = (showBinaryGauge && !isMultiSelect) ? getBinaryDefinition(rows) : null;
    const binary = Boolean(binaryDefinition);
    const categorical = rows.length >= 3;

    slide.addShape(p.ShapeType.roundRect, {
      x: cardX, y: cardY, w: cardWidth, h: cardHeight,
      fill: { color: C.white }, line: { color: C.grid, width: 0.8 }
    });
    slide.addShape(p.ShapeType.rect, {
      x: cardX, y: cardY, w: 0.07, h: cardHeight,
      fill: { color: binary ? C.green : C.blue },
      line: { color: binary ? C.green : C.blue }
    });
    slide.addText(question.question, {
      x: cardX + 0.24, y: cardY + 0.15, w: cardWidth - 0.48, h: 0.43,
      fontSize: 13.5, bold: true, color: C.navy, margin: 0, fit: 'shrink'
    });

    if (binary) {
      addBinaryGauge(slide, rows, binaryDefinition, cardX, cardY, cardWidth);
    } else if (categorical) {
      addCategoricalBars(slide, rows, cardX, cardY, cardWidth);
    } else {
      const text = rows.map(row =>
        `${row.label} : ${row.count}/${row.n} · ${formatPercent(row.proportion)} · ${ciLabel} ${formatInterval(row.ci_low, row.ci_high)}`
      ).join('\n\n');
      slide.addText(text || 'Aucune modalité exploitable.', {
        x: cardX + 0.24, y: cardY + 0.72, w: cardWidth - 0.48, h: 1.50,
        fontSize: 10, color: C.ink, margin: 0.02, valign: 'mid', fit: 'shrink'
      });
    }
  });
}

slide = base('Questions ouvertes et thèmes');
const themes = data.analysis.themes || [];
slide.addText(tier.interpretation, {
  x: 0.75, y: 1.03, w: 11.80, h: 0.25,
  fontSize: 8.5, italic: true, color: tier.color, align: 'center', margin: 0, fit: 'shrink'
});
if (!themes.length) {
  card(slide, 0.7, 1.45, 11.95, 2.0, 'Analyse non générée', 'Activez Albert API pour obtenir une synthèse thématique des questions ouvertes.', C.blue);
} else {
  themes.slice(0, 4).forEach((theme, index) => {
    const x = 0.7 + (index % 2) * 6.05;
    const y = 1.4 + Math.floor(index / 2) * 2.4;
    const themeBody = tier.key === 'faible' ? `Parmi les répondants : ${theme.summary}` : (tier.key === 'intermédiaire' ? `Tendance observée : ${theme.summary}` : theme.summary);
    card(slide, x, y, 5.75, 2.0, theme.title, themeBody, C.blue);
  });
}

slide = base('Plan d’amélioration continue');
const recommendations = data.analysis.recommendations || [];
slide.addText(tier.interpretation, {
  x: 0.75, y: 1.03, w: 11.80, h: 0.25,
  fontSize: 8.5, italic: true, color: tier.color, align: 'center', margin: 0, fit: 'shrink'
});
if (!recommendations.length) {
  card(slide, 0.7, 1.45, 11.95, 2.0, 'Validation requise', 'Aucune recommandation IA n’a été demandée. Utilisez les statistiques et la lecture humaine pour construire le plan.', C.blue);
} else {
  recommendations.slice(0, 6).forEach((recommendation, index) => {
    const x = 0.7 + (index % 3) * 4.06;
    const y = 1.35 + Math.floor(index / 3) * 2.6;
    const priority = String(recommendation.priority || '').toLowerCase();
    const priorityColor = priority === 'haute' ? C.low : (priority === 'moyenne' ? C.medium : C.blue);
    card(
      slide, x, y, 3.78, 2.2,
      `${priority.toUpperCase()} · ${recommendation.title}`,
      `${tier.key === 'faible' ? 'Signal parmi les répondants : ' : (tier.key === 'intermédiaire' ? 'Tendance observée : ' : '')}${recommendation.evidence}\n\nAction : ${recommendation.action}`,
      priorityColor
    );
  });
}

slide = base('Limites et validation');
const tierLimitation = `${tier.label} (${formatPercent(responseRate)}). ${tier.scope}`;
const sampleSizeNote = Number(data.statistics.respondents || 0) < 30 ? `Effectif de répondants limité (n = ${data.statistics.respondents}) : les intervalles de confiance restent larges, même avec un taux de réponse élevé.` : null;
const rawLimitations = (data.analysis.limitations || []).filter(item => !(tier.key === 'fort' && normalizeToken(item).includes('faible taux de reponse')));
const limitations = [tierLimitation, sampleSizeNote, ...rawLimitations].filter(Boolean);
card(slide, 0.7, 1.45, 5.75, 3.8, 'Limites', limitations.join('\n\n'), tier.color);
card(slide, 6.75, 1.45, 5.9, 3.8, 'Avant diffusion', 'Relire les interprétations\nVérifier les verbatims\nContrôler les petits sous-groupes\nValider les recommandations\nArchiver selon la politique de conservation', C.green);

p.writeFile({ fileName: out });
