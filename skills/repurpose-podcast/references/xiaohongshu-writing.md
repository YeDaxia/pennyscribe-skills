# Xiaohongshu writing and cards

Generate a native Xiaohongshu package: title options, caption, and a visual story of 4–8 portrait cards.

## Title and caption

- Write a new platform-native primary title instead of copying the episode title. Lead with a concrete tension, surprising conclusion, recognizable person, or reader benefit grounded in the transcript.
- Prefer a natural, specific title over vague labels such as “播客笔记” or inflated clickbait. Keep the primary title compact enough for mobile display.
- Format the caption as short paragraphs with breathing room. Open with a hook, follow with 3–5 scannable points, and close with a question or listening invitation.
- Do not include URLs in the title, caption, or card artwork. The publishing user can attach or mention the source separately when the platform supports it.

## Narrative

Use this sequence when it fits the episode:

1. Cover: one specific promise or tension. Make it visually distinct from every content card and optimize the hierarchy for feed-level recognition.
2. Context: why this episode matters.
3. Core insights: one idea per card.
4. Quote or counterintuitive point.
5. Practical takeaway.
6. Closing card with a takeaway, question, or listening invitation.

Avoid clickbait that overstates the transcript. Give each content card enough context to stand alone without turning it into a wall of text. Put longer nuance in the caption.

## Themes

The built-in themes translate twelve reusable design languages into static social cards. Use their principles rather than copying a reference layout pixel for pixel:

- `visual-hand-drawn`: grid paper, imperfect ink lines, pastel sticky notes, and hard paper shadows. Best for learning, creativity, and personal knowledge.
- `visual-neo-brutalism`: thick black outlines, saturated candy colors, and clearly offset shadows. Best for bold opinions, startups, and creator content.
- `visual-paper-cutout`: layered irregular paper shapes, warm pastel color, and soft downward shadows. Best for culture, education, and human stories.
- `retro-mid-century`: warm beige, orange, mustard, olive, organic geometry, and atomic-age motifs. Best for lifestyle, history, and optimistic narratives.
- `visual-accessibility`: maximum contrast, large readable type, explicit borders, and redundant numbered structure. Best for dense explainers and broad audiences.
- `visual-comic-book`: irregular panels, heavy black contours, halftone dots, action shapes, and dramatic display type. Best for energetic stories and surprising arguments.
- `retro-bauhaus`: primary colors, exact geometry, asymmetric balance, and functional sans-serif type. Best for design, systems, and conceptual content.
- `layout-magazine` (default): editorial grid, serif headline, rules, folios, warm paper, and one vermilion accent. Best for interviews, ideas, culture, and business analysis.
- `retro-futurism`: deep-space navy, cyan and magenta neon, perspective grids, and glowing wireframes. Best for AI, science, and future-facing topics.
- `core-flat-design`: pure color planes, simple geometry, no material texture, and hierarchy built with size, color, and whitespace. Best for frameworks and practical explainers.
- `white-collage`: white paper, a thin column frame, wide-tracked sans-serif column headers, one saturated accent color, and numbered body paragraphs. Best for personal product observations, design analysis, and evidence-style note series.
- `international-grid`: mathematical typographic grid, sans-serif scale jumps (cover 52px / content 40px, weight 700), black-on-white with hairline rules, black-circle paragraph numbers, a rotated edge label, and zero ornament. Cover keywords render as TOC-style lines — left edge aligned to the headline, gray 01/02/03 counters hanging right, spacing by whitespace only, no hairlines on the cover.

Choose one theme based on tone and keep it consistent within a set. `layout-magazine` is the safest content-first default for dense three-paragraph cards; `visual-accessibility` is the safest maximum-readability option. Do not use interaction-led UI styles for exported images. Use the episode cover only when it is available and legally exposed by the source page. Never imply AI-generated decoration is an original episode image.

## Card system

- Use a 3:4 canvas at 1080×1440 export resolution with generous safe margins.
- Give the cover oversized display type, a short supporting hook, stronger contrast, and a distinctive visual device. Do not make it look like content card 1.
- Give content cards a stable grid: sequence label, one concise idea, three visibly separated supporting paragraphs, and page number. Keep one idea per card.
- Write every non-cover card as exactly three short paragraphs totaling roughly 80–130 Chinese characters: lead with the conclusion, add transcript-grounded evidence or context, then explain the consequence, tension, or open question. Separate paragraphs with blank lines.
- Keep titles short enough to avoid dense line breaks. Prefer 2–4 lines on the cover and 2–3 lines on content cards.
- Do not show the podcast channel, show name, creator, URL, or generic watermark on card artwork.
- Use typography, rules, shapes, and whitespace intentionally. Avoid decorative clutter and tiny body text.
- Keep text inside a visually centered, approximately symmetric safe area. Reserve edge zones for theme decoration and never let decorative outlines, shadows, or shapes intersect the headline.
- Let headlines use the full safe-area width and wrap naturally by phrase. Scale short cover headlines down just enough to fill that width in one line; let longer titles wrap without artificial side columns. Avoid accidental orphans, forced equal-length lines, and auxiliary badges or color blocks beside the headline. Preserve at least 24px of visual separation between the headline and body block.
- Use no more than two large material/background layers. A cover supporting hook should be one clear container, not nested colored boxes.

## Grounding

Attach source paragraph IDs to insight and quote cards. Use quotation marks only for `verbatim` or `lightly_edited` text. Keep source URLs out of Xiaohongshu copy and artwork.
