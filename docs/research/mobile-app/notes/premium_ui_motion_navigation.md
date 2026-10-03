# Premium Mobile UI, Motion and Navigation (2025–2026) — design-craft reference for Jingle mobile

Research date: 2026-10-03. Sources are 2025–2026 unless flagged. Where a source is a secondary blog, X post or community README rather than a primary vendor document, that is noted.

## 1. Platform design languages: iOS 26/27 Liquid Glass and Material 3 Expressive

### Takeaway
Both platforms moved navigation chrome into a distinct floating "control layer" above content (Liquid Glass on iOS; floating/docked toolbars and a shorter flexible nav bar on Android). iOS 26's collapsing tab bar and split-out Search tab drew criticism and Apple partly walked them back in iOS 27 (WWDC June 2026: reduced transparency, user transparency slider, search back in the tab bar). A cross-platform app should use native tab bars on each platform (glass on iOS, M3 flexible nav bar on Android), keep a persistent mini-player "accessory" above the tabs, and never put glass on content (album art).

### Cited Findings
**Apple / Liquid Glass (iOS 26, 2025)**
- Liquid Glass is a translucent material that "reflects and refracts its surroundings"; controls are "a distinct functional layer that sits above apps" and "give way to content"; tab bars "shrink to bring focus to the content" on scroll down and "fluidly expand" on scroll up — [Apple Newsroom, Jun 2025](https://www.apple.com/newsroom/2025/06/apple-introduces-a-delightful-and-elegant-new-software-design/)
- App icons are now built from multiple Liquid Glass layers via Icon Composer, rendering in light, dark, tinted or clear looks — [Apple Newsroom](https://www.apple.com/newsroom/2025/06/apple-introduces-a-delightful-and-elegant-new-software-design/) (relevant: Jingle's cassette mark needs a layered icon with tinted/clear variants)
- HIG (as summarised by practitioners): tab bars are for 3–5 top-level peer destinations; never use a tab to trigger an action ("tabs are nouns, not verbs") — [Medium / Design Bootcamp](https://medium.com/design-bootcamp/dont-design-junk-in-the-new-ios-26-tab-bar-4de8e842da89) (secondary; Apple HIG page could not be fetched — JS-rendered)
- Liquid Glass belongs to the navigation/control layer, never to content — [LiquidGlassReference (Conor Luddy)](https://github.com/conorluddy/LiquidGlassReference)
- SwiftUI APIs: `Tab(..., role: .search)` puts a separate search button bottom-right and is expected to present a full-screen view; `.tabBarMinimizeBehavior(.onScrollDown)` collapses the bar; `.tabViewBottomAccessory` adds an app-wide accessory above the tab bar which moves next to the minimised tab button (intended for things like music player controls, not per-view actions) — [Donny Wals](https://www.donnywals.com/exploring-tab-bars-on-ios-26-with-liquid-glass/)
- Apple Music/Podcasts use this accessory "shelf" for the mini-player and global status — [Medium / Design Bootcamp](https://medium.com/design-bootcamp/dont-design-junk-in-the-new-ios-26-tab-bar-4de8e842da89); WWDC25 UIKit session on adopting the new design — [Apple WWDC25 #284](https://developer.apple.com/videos/play/wwdc2025/284/)

**Backlash and iOS 27 correction (2026)**
- Criticism: the collapsing tab bar made tab switching take "two gestures instead of one" in Apple Music; it "prioritized the appearance of space over the function of navigation" (attributed to Mark Gurman / Bloomberg reporting, May 2026) — [AprenderHub](https://www.aprenderhub.com/2026/05/ios-27-tab-bar-fix-liquid-glass.html) (secondary, pre-WWDC rumour reporting)
- WWDC 2026 (confirmed): iOS 27 reduced default transparency, added a graduated Liquid Glass transparency slider (vs binary Reduce Transparency), improved layer separation so toolbar buttons stand out, uniform top toolbar — [Neowin](https://www.neowin.net/news/apple-finally-brings-the-slider-for-liquid-glass-and-many-other-changes/); [Tom's Guide](https://www.tomsguide.com/phones/iphones/ios-27-has-a-bunch-of-changes-including-a-refined-liquid-glass-design-but-how-much-has-changed-from-ios-26)
- iOS 27 re-integrates search with the other navigation tabs; apps with custom tab bars built for iOS 26's split-search layout need updating; iOS 26 translucency reduced contrast below thresholds for users with mild vision impairment; apps using system glass APIs inherit Apple's compositing fixes automatically — [TechTimes, Jun 8 2026](https://www.techtimes.com/articles/317975/20260608/apple-liquid-glass-ios-27-wwdc-2026-brings-refinements-developers-must-adopt-today.htm)

**Material 3 Expressive (Android 16, 2025)**
- Backed by 46 studies, 18,000+ participants; key UI elements spotted up to 4x faster; expressive designs preferred by up to 87% of 18–24-year-olds; users 45+ performed on par with younger users; caveat: works best when it keeps established UI patterns — [Google Design](https://design.google/library/expressive-material-design-google-research)
- Original navigation bar deprecated → "flexible navigation bar", shorter height, horizontal icon+label items on medium windows; bottom app bar deprecated → docked toolbar; navigation drawer deprecated → collapsible/expandable navigation rail — [9to5Google, May 2025](https://9to5google.com/2025/05/14/material-3-expressive-navigation/); Google Home and Phone apps shipped the short bar Dec 2025 — [9to5Google](https://9to5google.com/2025/12/12/google-home-bottom-bar/)
- Floating toolbar = contextual page actions, can pair with a FAB; Google says don't pair a toolbar with a navigation bar: "Show the navigation bar on primary pages, and toolbars on subsequent pages with actions"; no floating nav-bar component exists — [9to5Google](https://9to5google.com/2025/05/18/material-3-expressive-toolbars/); [M3 Toolbars](https://m3.material.io/components/toolbars/overview)
- Motion physics: spring tokens in two families — spatial (position, size, rotation, corners; may overshoot) and effects (colour, opacity; no overshoot), each in default/fast/slow; Expressive scheme (lower damping, visible bounce) is the recommended default for hero moments; effects spring constants identical across schemes — [M3 Motion](https://m3.material.io/styles/motion/overview/how-it-works); [Medium, M3E in Compose](https://navczydev.medium.com/express-yourself-designing-with-material-3-expressive-in-compose-215818c18e91)
- Apple itself ships a Liquid-Glass-styled Apple Music on Android (7.0 beta) — [Beebom](https://gadgets.beebom.com/news/apple-music-7-0-beta-brings-liquid-glass-to-android); and a user on X called Revolut's glass nav on Android "tacky" — [X post](https://x.com/Maksiu129479/status/2007366421953863996) (anecdotal)

### Inferences
- iOS: use the native glass tab bar + `tabViewBottomAccessory` for Jingle's mini-player / "Listening together" status. Given iOS 27's reversal, do not rely on scroll-minimise for core tab switching; keep tabs persistently visible (or minimise only on very long feeds).
- Android: use M3 Expressive flexible nav bar (short), not a glass imitation; use a floating toolbar on sub-pages (e.g. circle playlist actions) instead of the nav bar. Use spatial springs for card/sheet movement, effects springs for colour/opacity.
- Glass/blur must never sit over or tint album artwork (consistent with Jingle's artwork rule and Apple's "never on content" guidance). Coral "Live" indicator needs contrast checks against translucent bars; test with Reduce Transparency and the iOS 27 slider at both extremes.
- Brand-gradient budget (max 3 per screen) fits well: chrome stays neutral/system, gradients reserved for hero moments.

### Gaps
- Apple HIG Tab bars / Materials / Sheets pages and m3.material.io pages are JS-rendered and could not be fetched verbatim; HIG guidance above comes from secondary summaries.
- Exact iOS 27 HIG text on minimise behaviour (deprecated vs discouraged) not confirmed from a primary source.

## 2. Navigation/tab architecture of top apps

### Takeaway
Winners in 2025–26 use 4–5 noun tabs organised around what users do most, with a persistent mini-player in music apps; action buttons in the tab bar ("Create") are actively disliked; radically cutting tabs (Snapchat 3-tab, Discord split) caused measurable backlash and reversals.

### Cited Findings
- Spotify added a 4th "Create" tab (new playlist, collaborative playlist, Blend, AI playlist, Jam); widely disliked; from Jul 31 2025 users can turn it off in Settings › Content and display — [9to5Google](https://9to5google.com/2025/08/01/spotify-update-remove-create-button/); [Creative Bloq](https://www.creativebloq.com/web-design/ux-ui/spotifys-latest-ui-design-change-is-driving-people-crazy); [Spotify Community](https://community.spotify.com/t5/Implemented-Ideas/Mobile-Get-rid-of-Create-button-on-mobile-navigation-bar/idi-p/6453037/page/44)
- Instagram (test from Oct 2025): tabs Home, Reels, DMs, Search, Profile; Reels takes centre, DMs move to the bottom bar, Create moves to top-left; horizontal swipe between all tabs. Mosseri: "We're organizing the app around what people use the app for most, which has increasingly been reels and DMs" — [Dataconomy](https://dataconomy.com/2025/10/13/instagram-tests-reels-first-redesign-with-dms-at-the-center/); [Design Compass](https://designcompass.org/en/2025/10/01/instagram-testing-reels-focused-tab-layout/)
- Snapchat "Simple Snapchat" (Sep 2024) consolidated to 3 tabs (Chat, Camera, Spotlight), removing Map and Stories; power users found it harder; scrapped after losing ~1M North American users in Q1 2025; testing a refined 5-tab layout — [Influencer Marketing Hub](https://influencermarketinghub.com/snapchat-redesign/); [netinfluencer](https://www.netinfluencer.com/simple-snapchat-simplified-interface-snap-partner-summit/) (2024–25)
- Discord (Dec 2023 redesign, older): bottom tabs Servers, Messages, Notifications, You; backlash; May 2024 partly reverted (DMs back top-left above server list) because splitting servers and DMs broke the mental model shared with desktop — [Discord blog](https://discord.com/blog/improving-our-mobile-experience); [Engadget](https://www.engadget.com/discord-overhauls-its-mobile-app-with-new-tabs-messaging-features-and-more-170035917.html) (flag: 2023–24)
- Threads: Messages (envelope) and Activity in the bottom bar; rolling out Liquid Glass navigation in 2026 — [Threads](https://www.threads.com/@threads/post/DLkt0y0gH8v/once-you-have-dms-youll-see-the-icon-at-the-bottom-of-your-screen-tap-it-to-open); [SocialBee](https://socialbee.com/blog/threads-news/)
- Airbnb Summer 2025 release: app rebuilt into three pillars (Homes, Experiences, Services) with a rebuilt tech stack enabling modular, animated components — [It's Nice That](https://www.itsnicethat.com/articles/airbnb-app-redesign-140525); [Design Bootcamp](https://medium.com/design-bootcamp/airbnb-summer-2025-update-heres-what-s-new-and-why-it-matters-0ced2338b921)
- Revolut and Instagram collapse the tab bar on scroll but keep every icon visible (drop labels, shrink the pill) rather than Apple's single-button minimise — [X, @itsjustkevs](https://x.com/itsjustkevs/status/2083189713238626754); [expo-glass-tabs README](https://github.com/davidmokos/expo-glass-tabs) (anecdotal/community)
- Apple Music: tab bar + mini-player in the accessory shelf above tabs, persists across tabs — [Medium / Design Bootcamp](https://medium.com/design-bootcamp/dont-design-junk-in-the-new-ios-26-tab-bar-4de8e842da89)

### Inferences
- Jingle proposal: 4–5 noun tabs (e.g. Home/Live feed, Circles, Drop/Discover, Inbox (sent songs), You), with a persistent now-playing/listen-together accessory above the tab bar. Put "Send a song" / "Start listening together" as a contextual button (top-right or floating toolbar), not a tab — Spotify's Create tab is the cautionary tale.
- Organise around the most frequent jobs (Mosseri principle): seeing friends live and sending songs. Don't cut below what power users need (Snapchat lesson); keep the mobile and web mental models aligned (Discord lesson).
- Swipe-between-tabs (Instagram test) conflicts with horizontal carousels (circle rows, story-format reveal); use only if no top-level screen has horizontal gestures.

### Gaps
- No reliable 2025–26 primary sources found for TikTok, BeReal, Arc Search, Things 3, Linear mobile or Telegram tab structures within the tool budget; BeReal sources were only student case studies.
- No source found on Spotify's own design-blog rationale for the Create tab.

## 3. Motion and micro-interactions that create the premium feel

### Takeaway
Premium feel comes from fast, interruptible, physically plausible motion: ease-out or springs (bounce 0.1–0.3), sub-300 ms UI transitions, no animation on very frequent actions, only transform/opacity animated, and gesture-driven, interruptible sheets. Haptics should use the platform's semantic types (success/error, confirm/reject) sparingly and crisply.

### Cited Findings
- Emil Kowalski's animation standards (2025–26): frequency rule — 100+/day: no animation; tens/day: reduce; occasional (modals, drawers, toasts): standard; rare (onboarding, celebrations): delight. Easing: ease-out `cubic-bezier(0.23,1,0.32,1)`, in-out `cubic-bezier(0.77,0,0.175,1)`, iOS-like drawer `cubic-bezier(0.32,0.72,0,1)`; "never ease-in on UI". Durations: press 100–160 ms, popover 125–200 ms, dropdown 150–250 ms, modal/drawer 200–500 ms; UI animations under 300 ms. Press scale 0.95–0.98; never scale from 0 (start 0.9–0.97 + opacity 0). Animate only transform/opacity. Springs `{duration: 0.5, bounce: 0.2}`, bounce 0.1–0.3. Stagger 30–80 ms, never block interaction. Reduced motion: keep opacity/colour, drop position changes — [emilkowalski/skills STANDARDS.md](https://github.com/emilkowalski/skills/blob/main/skills/review-animations/STANDARDS.md)
- Springs have no fixed duration, are suited to drag with momentum, interruptible gestures and "alive" elements like Dynamic Island; CSS keyframes are not interruptible — [emilkowalski/skills SKILL.md](https://github.com/emilkowalski/skills/blob/main/skills/review-animations/SKILL.md)
- M3 Expressive: spatial springs overshoot; effects springs never overshoot — [M3 Motion](https://m3.material.io/styles/motion/overview/how-it-works)
- React Native: Reanimated 4 adds CSS-style animations/transitions on the worklet engine; Shared Element Transitions on the New Architecture since 4.2.0 (Dec 2025) but behind a feature flag and "not yet production-ready" — [Software Mansion](https://swmansion.com/blog/introducing-reanimated-4-2-0-71eea21ca861/); React Navigation 8 documents shared element transitions — [React Navigation](https://reactnavigation.org/docs/8.x/shared-element-transitions/)
- Airbnb 2025: 3D, Pixar-like animated icons (door pops open, porch light, bell rattles, balloon bounces), new transparent "Lava" media format for UI animation; two years of in-house design work — [Design Bootcamp](https://medium.com/design-bootcamp/airbnb-summer-2025-update-heres-what-s-new-and-why-it-matters-0ced2338b921); [Bloomberg](https://www.bloomberg.com/news/articles/2025-06-13/apple-airbnb-ditch-flat-app-icons-for-new-3d-ui-design)

**Haptics**
- Android: prefer "clear" (crisp, sharp) and "rich" haptics over "buzzy/mushy"; use action-oriented `HapticFeedbackConstants` (CONFIRM = short, light; REJECT = stronger) for system consistency, no fallback needed; be mindful of frequency and importance — [Android haptics principles](https://developer.android.com/develop/ui/views/haptics/haptics-principles); [HapticFeedbackConstants](https://developer.android.com/reference/android/view/HapticFeedbackConstants); [AOSP haptics UX](https://source.android.com/docs/core/interaction/haptics/haptics-ux-foundation)
- iOS: standard controls (switches, sliders, pickers) already play system haptics; UIKit offers Impact, Selection and Notification (success/warning/error) generators; Core Haptics supports custom patterns synchronised with audio — [Eidinger, Haptics on Apple Platforms](https://blog.eidinger.info/haptics-on-apple-platforms); [WWDC19 Core Haptics](https://developer.apple.com/videos/play/wwdc2019/520) (flag: 2019, still current API)
- Community Expo glass tab bar ships "finger scrubbing with haptics" across tabs (selection ticks) — [expo-glass-tabs](https://github.com/davidmokos/expo-glass-tabs) (community)

### Inferences
- Jingle motion budget: Live feed cards update in place with an opacity/effects spring only (seen tens of times a day → minimal motion); the weekly top-5 reveal and Drop are "rare" moments that earn richer, spring-driven choreography and a Core Haptics pattern synced to a short sound.
- Haptic map: selection tick on tab/scrub and reaction picker; success notification on "song sent", "added to circle playlist"; reject/error on failures; one custom pattern for the weekly reveal. No haptics on passive live updates.
- Artwork must not be animated (brand rule): shared-element transitions can move/scale the artwork frame between mini-player and now-playing (geometry change, not cropping or effects) — confirm this interpretation with brand owners. Treat Reanimated SET as experimental; have a fallback cross-fade.

### Gaps
- Apple HIG "Playing haptics" page text not retrieved verbatim.
- No 2025–26 sources found on skeleton vs shimmer, optimistic UI quantification, 120 Hz ProMotion specifics, or sound design in Family/Honk/Retro/Arc.

## 4. Music-specific UI patterns and story-format recaps

### Takeaway
Spotify Wrapped 2025 shows the current bar for recaps: a "visual mixtape" analogue aesthetic (mixtapes, burned CDs, stickers, photocopy textures, handwriting) built in Rive with data binding, which drove record engagement. This aligns closely with Jingle's cassette identity.

### Cited Findings
- Wrapped 2025 design was inspired by '80s–2000s mixtapes and burned CDs: doodles, photocopy textures, stickers, cutouts, handwriting; "reduced color palette and bold use of images" — [Spotify design Substack](https://spotifynews.substack.com/p/designing-2025-wrapped-turning-a); [Fast Company](https://www.fastcompany.com/91451332/spotify-wrapped-2025-goes-analog-in-the-age-of-ai)
- Wrapped is a year-long effort; design foundation set early so many teams can build on it — [Spotify design Substack](https://spotifynews.substack.com/p/designing-2025-wrapped-turning-a)
- Built in Rive: designers prototyped with dummy data, built final animation in Rive, engineers bound real user data without rebuilding; handled text variation, localisation, device constraints. Results per co-CEO Alex Norström: 300M+ users engaged (+20%), 630M+ shares (+42%), record single-day subscriber intake — [Rive blog](https://rive.app/blog/spotify-used-rive-for-spotify-wrapped-2025)
- Wrapped highlights backed by a dedicated archive pipeline — [Spotify Engineering, Mar 2026](https://engineering.atspotify.com/2026/3/inside-the-archive-2025-wrapped)

### Inferences
- Jingle's weekly top-5 reveal and Blends recap should be story-format (tap-through, share card export) with Rive-authored, data-bound templates. Cassette/mixtape texture is on-trend and on-brand; texture should frame the real album art, never overlay it.
- Artwork-derived colour (dynamic theming) for now-playing backgrounds is compatible with the brand as long as the artwork itself is untouched and the coral "Live" colour is never derived.

### Gaps
- No 2025–26 primary source found on Apple Music now-playing/lyrics design changes or artwork colour extraction guidance (Android `Palette`/Material You dynamic colour from media not researched within budget).

## 5. Typography, colour, dark mode and accessibility

### Takeaway
Liquid Glass's first year showed that translucency harms contrast; iOS 27 responded with less transparency and a user slider. Polish must survive Reduce Transparency, Reduce Motion and large text.

### Cited Findings
- iOS 26 translucent elements and blurred backgrounds reduced contrast below thresholds for users with mild vision impairment; iOS 27 adds graduated transparency control — [TechTimes](https://www.techtimes.com/articles/317975/20260608/apple-liquid-glass-ios-27-wwdc-2026-brings-refinements-developers-must-adopt-today.htm)
- M3 Expressive's research showed expressive size/colour/shape closed age gaps (45+ performing on par) — [Google Design](https://design.google/library/expressive-material-design-google-research)
- Reduced-motion approach: keep opacity/colour transitions, remove transform-based movement — [Kowalski STANDARDS.md](https://github.com/emilkowalski/skills/blob/main/skills/review-animations/STANDARDS.md)
- "AI slop" tells include overused Inter, purple gradients, gradient text, dark mode with glowing accents, glassmorphism as decoration — [impeccable.style/slop](https://impeccable.style/slop/)

### Inferences
- Dark-first with neutral, non-glowing surfaces; brand gradient as scarce hero accent; choose a distinctive type pairing over default Inter; support Dynamic Type/Android font scaling with layouts that reflow (no truncated song titles without a full-title accessible label).

### Gaps
- No primary 2025–26 Apple/Google typography guidance (SF / Google Sans Flex specifics) retrieved.

## 6. Illustration, mascot and brand craft (avoiding "AI slop")

### Takeaway
Top brands invest years of in-house craft (Airbnb's icons: two years) and use stateful animation runtimes (Rive) for characters; generic AI aesthetics are now a recognised negative signal.

### Cited Findings
- Airbnb's in-house team spent two years on a consistent 3D icon set — [Design Bootcamp](https://medium.com/design-bootcamp/airbnb-summer-2025-update-heres-what-s-new-and-why-it-matters-0ced2338b921)
- Duolingo animates its characters in Rive: state machines blend idle/speaking/blinking/reacting; lip sync maps phonemes to visemes; one runtime file handed to engineers — [Duolingo blog](https://blog.duolingo.com/world-character-visemes); [DEV (secondary)](https://dev.to/uianimation/how-duolingo-uses-rive-for-their-character-animation-and-how-you-can-build-a-similar-rive-mascot-5d19)
- Rive suits interactive, state-driven animation; Lottie suits linear, lightweight playback — [Polar Hedgehog](https://www.polarhedgehog.com/blog/rive-vs-interactive-lottie)
- Slop catalogue (typography, colour, glass, layout, copy) — [impeccable.style](https://impeccable.style/slop/)
- Hybrid workflow example: sketch concept and core poses by hand, use AI to polish/export, animate parts independently — [WisdomAI / Adam Lyttle](https://www.wisdomai.com/insights/adamlyttleapps/app-mascot-ai-design-swiftui-character-animation-54218ce5) (practitioner anecdote)

### Inferences
- Jingle's Blip mascot: author in Rive with a small state machine (idle, listening, reacting, celebrating) driven by app events; commission or hand-author key poses rather than relying on generated art.

### Gaps
- No transcripts/talks retrieved from Mobbin or named practitioners specifically on avoiding AI slop.

## 7. Performance as perceived quality

### Takeaway
Hard floors: Android vitals flags cold start ≥5 s, warm ≥2 s, hot ≥1.5 s (TTID). Use ThumbHash placeholders and cached images; be careful with Expo native-module startup cost on low-end Android.

### Cited Findings
- Android vitals excessive thresholds: cold ≥5 s, warm ≥2 s, hot ≥1.5 s, measured by Time to Initial Display — [Android Developers](https://developer.android.com/google/play/vitals/launch-time)
- ThumbHash encodes more detail, more accurate colour, alpha and aspect ratio vs BlurHash; expo-image supports both as `placeholder` and transitions between sources without flicker — [ThumbHash](https://evanw.github.io/thumbhash/); [Expo Image docs](https://docs.expo.dev/versions/latest/sdk/image/)
- Reported expo-image startup stall on low-end Android (~4.5 s; 8 s to first content on Galaxy A12) and expo-modules boot overhead of 2–2.5 s — [expo#25201](https://github.com/expo/expo/issues/25201); [expo#23189](https://github.com/expo/expo/issues/23189) (flag: 2023 issues; may be fixed — verify on current SDK)

### Inferences
- Set Jingle budgets well inside vitals: target cold start TTID < 2 s on a mid-range Android, profile on a low-end device, ship ThumbHash with every artwork URL from the API so cards render instantly.

### Gaps
- No 2025–26 sources retrieved on list virtualisation (FlashList v2), 120 Hz frame budgets, or offline-first patterns.
