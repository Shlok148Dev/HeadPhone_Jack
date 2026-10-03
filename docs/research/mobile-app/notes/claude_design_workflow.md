# Claude Design and an AI-assisted design-to-production workflow for Jingle mobile (researched 2026-10-03)

## What is Claude Design, where does it live, and what can and can't it do?

### Takeaway
Claude Design is Anthropic Labs' visual-canvas design tool. It launched on 2026-04-17 as a research preview, runs on Claude Opus 4.7, and makes prototypes, mobile and responsive layouts, decks and one-pagers from prompts, uploads, web captures and your codebase. Since June 2026 it syncs both ways with Claude Code through `/design-sync`. Its weak spots are Figma interop (there is no Figma export), usage cost on the Pro plan, and reported bugs in fine editing and comments.

### Cited Findings
- Launch date was 2026-04-17, by Anthropic Labs. It is a research preview for Pro, Max, Team and Enterprise, powered by Claude Opus 4.7, which Anthropic calls "our most capable vision model". On Enterprise it is off by default until an admin enables it — [Anthropic news](https://www.anthropic.com/news/claude-design-anthropic-labs)
- Claude "builds a design system for your team by reading your codebase and design files" and applies its colours, type and components to every project. A team can keep more than one design system — [Anthropic news](https://www.anthropic.com/news/claude-design-anthropic-labs)
- Inputs are text prompts, image uploads, DOCX/PPTX/XLSX files, a codebase, and a web-capture tool that pulls elements from websites — [Anthropic news](https://www.anthropic.com/news/claude-design-anthropic-labs)
- You refine work with inline comments on specific elements, direct text edits, and "adjustment knobs to tweak spacing, color, and layout live". Claude carries changes across the whole design — [Anthropic news](https://www.anthropic.com/news/claude-design-anthropic-labs)
- Exports: an org-internal share URL, Canva, PDF, PPTX, standalone HTML, a folder save, and a "handoff bundle" to Claude Code from a single instruction. Teams use it for code-powered prototypes that include voice, video, shaders, 3D and built-in AI — [Anthropic news](https://www.anthropic.com/news/claude-design-anthropic-labs)
- Places you can use it now, per the help center:
  - In chat ("Output > Design")
  - The Artifacts tab, using a Design template
  - Claude Code on desktop or in the terminal, via `/design` commands
  - The mobile apps (you can view designs there, but editing needs web or desktop)
  - The standalone claude.ai/design, which has its own setting
  — [Help center: Get started](https://support.claude.com/en/articles/14604416-get-started-with-claude-design)
- New projects automatically inherit the org design system. A design system can be attached from a GitHub repo, design files, raw uploads, or a local codebase via `/design-sync` — [Help center](https://support.claude.com/en/articles/14604416-get-started-with-claude-design)
- It supports "mobile and responsive layouts", onboarding flows, dashboards, forms and landing pages — [Help center](https://support.claude.com/en/articles/14604416-get-started-with-claude-design)
- The help center lists three ways to refine:
  - Chat, for broad changes
  - Inline comments: click on the canvas to ask for a targeted change
  - Direct editing: "drag, resize, and align elements directly"
  It also says: "If your comments aren't being picked up, paste the feedback directly into the chat instead." — [Help center](https://support.claude.com/en/articles/14604416-get-started-with-claude-design)
- To branch a direction, you can say "Save what we have and try a completely different approach" — [Help center](https://support.claude.com/en/articles/14604416-get-started-with-claude-design)
- Usage comes out of normal Claude limits; there is no separate allowance. Big codebases use more, and when you hit the limit Design is unavailable until it resets — [Help center](https://support.claude.com/en/articles/14604416-get-started-with-claude-design)
- Handoff is Export, then "Hand off to Claude Code", to either a local agent or Claude Code Web — [Help center](https://support.claude.com/en/articles/14604416-get-started-with-claude-design)
- On 2026-06-17, "Claude Code and Claude Design now sync both ways." `/design-sync` pulls the design system into the repo, or pushes what was built back to the canvas — [ClaudeDevs on X](https://x.com/ClaudeDevs/status/2067391951725629941); [AI Catchup](https://aicatchup.com/news/claude-design-sync-claude-code-two-way)
- How `/design-sync` works in practice (practitioner write-up, 2026-09-28):
  - It needs `.design-sync/config.json` with these fields: entry, pkg, globalName, buildCmd, cssEntry, extraFonts, storybookConfigDir, readmeHeader.
  - It produces a compiled bundle (components, CSS, fonts, React), type definitions, a preview page and a usage guide per component, and prop/variant information.
  - If Storybook is present, it screenshots the stories (with Playwright) and grades each one match, close or mismatch against the generated previews.
  - A `.design-sync/conventions.md` file tells Claude how to use the components.
  - Pitfalls:
    - `url()` CSS imports break.
    - Fonts must be listed in `extraFonts`.
    - Layout utilities need Tailwind v4 `@source inline(...)`.
    - Components not exported from the entry file are silently dropped.
  - The mirror is a one-way snapshot that you re-run to refresh, and deleted components are not cleaned up.
  — [Nitay Neeman](https://nitayneeman.com/blog/how-to-sync-a-design-system-with-claude-design/)
- Anthropic Academy's prototype workflow has eight steps:
  1. A PM writes a detailed prompt.
  2. Claude generates a prototype with the org design system.
  3. A designer refines it with inline feedback.
  4. The link goes out for async stakeholder review.
  5. Claude produces alternatives for the weak sections.
  6. A design lead checks that real components were used.
  7. Code handoff.
  8. Engineers implement from the prototype.
  The Academy also suggests:
  - Asking for 3 layout variants, two flow versions, and empty, error, loading and data-volume states.
  - Linking specific packages instead of a whole monorepo, and excluding `.git` and `node_modules`.
  - Naming components clearly, recording the rationale in chat, and flagging edge cases before handoff.
  — [Claude Academy](https://academy.claude.com/tutorials/using-claude-design-for-prototypes-and-ux)
- Limitation: there is no direct Figma export. Editable Figma layers need screenshots or a round trip through Claude Code and the Figma MCP — [UX Pilot review](https://uxpilot.ai/blogs/claude-design-review); [Anima review](https://animaapp.com/blog/ai-design-en/claude-design-review-features-pros-cons-and-best-alternatives/)
- Early reviewers said the controls could not move elements around. This conflicts with the current help center, which describes drag, resize and align; the gap is probably the June WYSIWYG update. Reviewers also said animations cannot be exported as video — [UX Pilot](https://uxpilot.ai/blogs/claude-design-review); compare [Help center](https://support.claude.com/en/articles/14604416-get-started-with-claude-design)
- A May 2026 review found that design-system extraction "understood what a design system is". On the Pro plan it allowed "maybe one or two meaningful iterations before you are locked out for the week", Max was "workable" for a few projects a month, and there was no multi-user live editing. The reviewer called the tool best for founders, PMs and developers — [Yiannis Antoniou](https://yiannisantoniou.substack.com/p/claude-design-redux-impressive-but)
- Claude Design connects with Adobe, Canva, Gamma, Lovable, Miro, Replit, Vercel and Wix — [search summary of claude.com/product/design](https://claude.com/product/design); not independently verified

### Inferences
- The flow in video (1) matches the documented features: start from the Artifacts tab or `/design` in Claude Code, ask for options, comment and edit, request a click-through prototype, then "Hand off to Claude Code".
- For Jingle, the best order is to run `/design-sync` from the repo first, using the existing tokens package and web components. The mobile screens then start from Night Studio rather than generic styling.
- Claude Design outputs are HTML/React prototypes. For a React Native or Expo app they are a reference for intent and visuals, not code you can copy across. Expect the handoff to need translation into RN primitives.
- Use Max (or Team) during the design sprint. Pro limits are likely to stall a full mobile screen set.

### Gaps
- I found no official doc listing device-frame presets (iPhone/Android sizes) or native-mobile export. "Mobile layouts" are documented, but native output is not.
- It is unclear whether `/design-sync` supports React Native component libraries; the documented path assumes web React, Tailwind and Storybook.
- I found no official statement on Claude Design generating raster illustrations. It does not appear to be an image generator.

## Best practices for prompting AI design tools

### Takeaway
Across vendors and practitioners the same patterns lead to better output:
- Ground the tool in a real design system or tokens.
- Give it concrete references and a named aesthetic direction.
- Ask for several divergent options and then converge.
- Demand that every state is covered.
- Use targeted comments for local fixes and chat for global changes.
- Write down the rationale for handoff.

### Cited Findings
- Ask for variants explicitly, for example three layouts (card, sidebar, tabs) or two flow structures, and ask for empty, error, loading and data-volume states — [Claude Academy](https://academy.claude.com/tutorials/using-claude-design-for-prototypes-and-ux)
- Use chat for global changes, inline comments for local ones, and direct edits for nudges. To branch, say "save what we have and try a completely different approach" — [Help center](https://support.claude.com/en/articles/14604416-get-started-with-claude-design)
- Anthropic's frontend-design skill commits to a purpose, an audience and a specific aesthetic direction before coding. It avoids generic system fonts, "predictable purple gradients" and cookie-cutter components, and favours distinctive type pairings and intentional motion — [claude.com plugin page](https://claude.com/plugins/frontend-design); [ui-skills mirror](https://www.ui-skills.com/skills/anthropics/frontend-design)
- References and brand capture are first-class inputs: screenshots, competitor references, and a web-capture tool — [Anthropic news](https://www.anthropic.com/news/claude-design-anthropic-labs); [The New Stack](https://thenewstack.io/anthropic-claude-design-launch/)
- A customer at Brilliant reported that complex pages which took 20+ prompts elsewhere needed 2 in Claude Design — [Anthropic news](https://www.anthropic.com/news/claude-design-anthropic-labs)

### Inferences
- A prompt template that fits Jingle:
  - **Context:** product, user, the "magic moment" (for example, seeing a friend's live song and tapping Tune in).
  - **Platform:** iOS and Android, a 390x844 frame, safe areas, thumb zone, and 44pt/48dp touch targets.
  - **Design-system constraints:** use only Night Studio tokens and components.
  - **References:** 3–5 Mobbin screenshots, each with a note on *what* to borrow.
  - **Anti-goals:** no purple gradients, no generic glassmorphism.
  - **Deliverable:** three divergent directions with a one-line rationale each, plus every state.
- Critique loop: after each round, ask Claude to critique its own output against the UX spec and an accessibility checklist before the next iteration. Keep the winning direction and branch the rest.
- Not independently researched in this pass: vendor guides for Figma Make, v0, Lovable, Stitch and Magic Patterns. The patterns above are consistent with what they are known to recommend, but this note has no direct citations for them.

### Gaps
- I did not fetch first-party prompting guides from Figma Make, v0, Lovable, Google Stitch or Magic Patterns (tool-call budget).

## Design-system documentation formats coding agents follow, and one token source for web and mobile

### Takeaway
Use DTCG 2025.10 JSON tokens as the single source and build them with Style Dictionary into Tailwind v4 `@theme` CSS, TypeScript, and React Native style objects. Pair that with a DESIGN.md (YAML tokens plus prose rationale) and a `.design-sync/conventions.md` so that both Claude Design and coding agents follow the rules.

### Cited Findings
- The W3C Design Tokens Community Group spec reached its first stable version, 2025.10, on 2025-10-28. It adds:
  - theming and multi-brand support via `$extends` and group inheritance
  - P3, OKLCH and CSS Color 4 colour spaces
  - aliases written as `{token.name}` and JSON Pointer
  - `.tokens` / `.tokens.json` file extensions
  More than 40 organisations back it, including Adobe, Figma, Google, Microsoft and Shopify — [W3C DTCG](https://www.w3.org/community/design-tokens/2025/10/28/design-tokens-specification-reaches-first-stable-version/)
- Style Dictionary has had first-class DTCG support since v4. v5 is used as a DTCG build pipeline that emits web, TS, iOS and Android outputs and Tailwind v4 `@theme` CSS — [Style Dictionary DTCG](https://styledictionary.com/info/dtcg/); [tokens-studio/sd-tailwindv4](https://github.com/tokens-studio/sd-tailwindv4/); [example PR](https://github.com/hansenexus/design/pull/5)
- Terrazzo has no official React Native plugin yet; an open issue requests one. DTCG composites (border, shadow, typography) map to spreadable StyleSheet objects — [Terrazzo issue #856](https://github.com/terrazzoapp/terrazzo/issues/856)
- DESIGN.md is a Google Labs format, created in Stitch and open-sourced on 2026-04-21 under Apache 2.0. It has YAML front matter with exact token values (colours, type, spacing, component token refs) and a markdown body with rationale and do/don't guidance. It works with Claude Code, Cursor, Copilot and Codex — [google-labs-code/design.md](https://github.com/google-labs-code/design.md); [Autocomplete AI guide](https://acdigest.substack.com/p/designmd-the-complete-guide)
- `/design-sync` reads a conventions markdown file plus the compiled components and CSS. A Tailwind CLI build with tokens inlined is the recommended input — [Nitay Neeman](https://nitayneeman.com/blog/how-to-sync-a-design-system-with-claude-design/)

### Inferences
- Recommended layout for Jingle, assuming its existing `packages/design-tokens` (inferred from the repo's agent definitions):
  - `tokens/*.tokens.json` in DTCG format is the source.
  - Style Dictionary generates three outputs from it:
    - (a) `tailwind.css` with `@theme`, for the web
    - (b) `tokens.ts`, giving RN-safe numbers and hex/rgba, since RN does not support OKLCH, so convert at build time
    - (c) a generated `DESIGN.md` front matter
  - The hand-written prose lives in DESIGN.md and in the existing jingle-design-system skill.
- Video (2)'s "design.md + design.html" is the same idea. The html part maps to the per-component preview pages that `/design-sync` produces, or to a Storybook.
- Add a CI check that fails when generated outputs drift from the token JSON.

### Gaps
- I found no first-party Style Dictionary React Native preset documentation in this pass.

## Asset pipeline: illustration, mascot, animation, licensing, avoiding slop

### Takeaway
Use Rive for interactive, stateful mascot and micro-interaction animation, and Lottie (or dotLottie) for simple one-shot or looping illustrations. Keep a human-authored master mascot. AI-only images are not copyrightable in the US, so brand-critical assets need meaningful human authorship.

### Cited Findings
- Rive has state machines driven by boolean, number and trigger inputs, for example idle, pressed, success and error. Lottie is mostly play, pause and scrub, but dotLottie added state machines in late 2025 — [Unicorn Icons](https://unicornicons.com/learn/rive-vs-lottie)
- Callstack's mobile benchmark measured Rive at about 60 FPS against Lottie at about 17 FPS in their test case — [Callstack](https://www.callstack.com/blog/lottie-vs-rive-optimizing-mobile-app-animation)
- Common 2026 guidance is Lottie for designer illustrations, Rive for interactive stateful animation, and code animation for UI transitions. lottie-react-native is mature, and Rive's RN runtime takes more integration work — [PkgPulse](https://www.pkgpulse.com/guides/lottie-vs-rive-vs-css-animations-web-animation-formats-2026); [Unicorn Icons](https://unicornicons.com/learn/rive-vs-lottie)
- The US Copyright Office AI report, Part 2 (January 2025), says purely AI-generated material is not copyrightable. Prompts alone are not enough. Human selection, arrangement or material modification can be protected, decided case by case — [Library of Congress newsroom](https://newsroom.loc.gov/news/copyright-office-releases-part-2-of-artificial-intelligence-report/s/f3959c36-d616-498d-b8f9-67641fd18bab); [Jones Day](https://www.jonesday.com/en/insights/2025/02/copyrightability-of-ai-outputs-us-copyright-office-analyzes-human-authorship-requirement)

### Inferences
- Approach for Blip, the mascot:
  - A human illustrator draws the canonical model sheet (turnarounds and expressions), which gives ownable IP.
  - AI tools (Midjourney, Recraft, Higgsfield) are used only for exploring variants and backgrounds, then redrawn or edited by hand.
  - The final mascot is rigged in Rive with states for idle, listening, reveal-celebration and error.
- Write an "asset prompt plan": one style spec (palette from tokens, line weight, lighting, camera) reused in every image prompt, plus a do-not list. Generate in batches and curate hard.
- Album artwork must stay the platform's own content and must not be AI-altered (see the existing design-system Spotify separation rules).

### Gaps
- I did not verify current Midjourney, Recraft or Higgsfield commercial terms or plan tiers, Rive's pricing and licence, or whether Higgsfield's MCP officially exists.
- I did not cover laws outside the US, such as India, where Jingle's DPDP context suggests it is based.

## Prototype testing and validating "premium feel" before build

### Takeaway
Run small, frequent qualitative rounds: 3–5 users per round, observing task completion on a click-through prototype on a real phone. Treat "premium feel" as something to test separately, through motion and feedback timing on a coded prototype, not through static frames.

### Cited Findings
- Nielsen's guidance is that 5 users surface about 85% of usability issues in one qualitative round. It applies to one user segment and one set of tasks, not to surveys or benchmarks — [Maze](https://maze.co/blog/user-testing-how-many-users/); [UXArmy](https://uxarmy.com/blog/usability-testing-are-5-participants-enough/)
- Maze recommends 3–5 participants per round for iterative prototype testing — [Maze](https://maze.co/blog/user-testing-how-many-users/)
- Claude Design prototypes are clickable HTML with share links for async review, and can include voice, video, shaders and 3D — [Anthropic news](https://www.anthropic.com/news/claude-design-anthropic-labs); [Yiannis Antoniou](https://yiannisantoniou.substack.com/p/claude-design-redux-impressive-but)

### Inferences
- Suggested sequence:
  1. Claude Design click-through of the 5 core flows: onboarding/connect, live feed, circle and playlist, weekly reveal, daily drop.
  2. Five 30-minute moderated sessions, with the share link opened on participants' own phones.
  3. Fix the issues found.
  4. A second round of 5.
  5. Hand off to Claude Code.
  6. Build an Expo dev-build "feel prototype" of the 2 hero interactions (the live card Pulse and the reveal) and test those for perceived quality, since haptics and 60fps motion can't be judged in HTML.
- Maze or Useberry can run unmoderated tests on a hosted HTML URL. Whether either supports Claude Design links is unverified.

### Gaps
- I did not verify Maze or Useberry support for arbitrary HTML prototype URLs (versus Figma imports).
- I found no rigorous source on measuring "premium feel". Practitioner advice in video (3) is only available second-hand.
