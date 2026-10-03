# Make Jingle the App Friends Open Daily

Jingle's mobile app should be built around one promise that Spotify, Instagram and Airbuds cannot fully keep for an Indian 18–25 audience: **see what your own people are really playing, across every service including YouTube Music, and do something small together about it every day and every Monday.** The research shows the category is proven (Airbuds reached **15M+ downloads, 5M MAU and 1.5M DAU** with a "connect, add friends, widget" loop) ([TechCrunch](https://techcrunch.com/2025/09/17/airbuds-is-the-music-social-network-apple-and-spotify-wish-they-had-built/)) but also that the easy differentiator is gone: Spotify shipped mobile Listening Activity and Request to Jam in January 2026 ([TechCrunch](https://techcrunch.com/2026/01/07/spotify-now-lets-you-share-what-youre-streaming-in-real-time-with-friends)), and Spotify's Development Mode now caps an app at **5 users**, with extended quota reserved for registered businesses with **250k MAU** ([TechCrunch](https://techcrunch.com/2026/02/06/spotify-changes-developer-mode-api-to-require-premium-accounts-limits-test-users/)). The plan below therefore makes **Android the hero platform** (it alone can legally read YouTube Music and Amazon Music playback on the phone), makes Last.fm, Apple Music and the Android listener the launch data sources, and treats Spotify as a later upgrade. It recommends an **Expo / React Native New Architecture** app that shares types, API client, query hooks and tokens with the existing Next.js web app, with custom Kotlin modules for the notification listener and Android widgets, and Expo's now-stable iOS widgets and Live Activities ([Expo](https://expo.dev/blog/ios-widgets-and-live-activities-in-expo)). The activation target is a first real friend card in the first session, the retention engine is the daily Drop plus the Monday reveal (no punishing streaks), and the design pipeline runs from `/design-sync` of Night Studio into Claude Design, through two rounds of five-user prototype tests, into a Claude Code hand-off. The biggest open risks are Google Play's treatment of notification access, iOS's inability to show Live for YouTube Music or Amazon Music, and the empty-network problem for users who arrive without friends.

**How to read this plan.** A sentence with an inline source link is a researched fact from the notes. Text labelled **Recommendation** or **Inference** is this report's judgement, built on those facts. "**Given**" marks the founder's product context, which is treated as true without a source. "**Repo**" marks something read directly from the Jingle codebase (`packages/design-tokens`, `docs/ux/UX_SPEC.md`). Where a source is a vendor blog, aggregator or anecdote, the plan says so. Nothing here is to be implemented yet.

---

## 1. Spotify closed the easy gap, so Jingle must win on cross-service circles

### What the competitors now do

Airbuds is the direct analogue. Its core is a home-screen widget showing friends' live listening, plus reactions (emoji, stickers, selfies), Ghost Mode, DMs, a Sunday Weekly Recap, a customisable profile and a school feature; it connects seven services including Spotify, Apple Music, Amazon Music, SoundCloud and Deezer, and **about 30% of users use features beyond basic friend-listening** ([TechCrunch](https://techcrunch.com/2025/09/17/airbuds-is-the-music-social-network-apple-and-spotify-wish-they-had-built/)). Its growth levers are invite-gated features (you see only your top 3 artists in the recap until you invite friends) and a college ambassador programme ([TechCrunch](https://techcrunch.com/2025/09/17/airbuds-is-the-music-social-network-apple-and-spotify-wish-they-had-built/); [Consumer App Lab](https://consumerapplab.substack.com/p/inside-airbuds-the-app-that-grew)). Its App Store privacy label lists data "used to track you" ([Consumer App Lab](https://consumerapplab.substack.com/p/inside-airbuds-the-app-that-grew)), and its DAU/MAU of **about 30%** is the best public engagement benchmark in the category.

Spotify has moved deliberately but conservatively. Messages launched in August 2025 for users 16+, limited to people you have already interacted with ([Variety](https://variety.com/2025/digital/news/spotify-launches-in-app-messaging-1236497588/)); mobile Listening Activity followed in January 2026 as an opt-in setting shown only at the top of existing chats, with Request to Jam for Premium users ([TechCrunch](https://techcrunch.com/2026/01/07/spotify-now-lets-you-share-what-youre-streaming-in-real-time-with-friends)). Instagram Notes now update automatically with what you play on Spotify ([Spotify Newsroom](https://newsroom.spotify.com/2025-08-21/spotify-takes-instagram-sharing-to-the-next-level-with-audio-previews-and-real-time-listening-notes/)). Spotify also owns the recap genre: Wrapped 2025 reached **300M+ engaged users and 630M+ shares** ([Hypebeast](https://hypebeast.com/2026/2/spotify-wrapped-drives-record-751-million-monthly-users)), and **70% of daylist users return week after week** ([Spotify Newsroom](https://newsroom.spotify.com/2024-09-04/daylist-new-languages-expanding-worldwide/)).

India changes the map. **YouTube is used by 82% of Indian music streamers versus 48% for Spotify** ([bestmediainfo](https://bestmediainfo.com/insights/youtube-spotify-india-music-streaming-platform-competition-ey-imi-12200559)), India added nearly 4M paid subscriptions in 2025 to reach 14.4M ([MBW](https://www.musicbusinessworldwide.com/india-added-nearly-4m-paid-music-streaming-subscriptions-in-2025-taking-its-total-to-14-4m-according-to-new-report/)), and Wynk, Resso and Hungama have shut down ([Music Ally](https://musically.com/2025/04/02/shut-downs-watching-vs-listening-and-future-growth-indias-dsp-market-today/)). A cautionary tale sits nearby: Musicboard's outages, offline website and Play removal triggered a "save Musicboard" campaign ([TechCrunch](https://techcrunch.com/2026/02/09/so-whats-going-on-with-musicboard/)) — reliability is a feature for community apps.

### Differentiation (Recommendation)

| Axis | Airbuds | Spotify social (2026) | Jingle mobile position |
|---|---|---|---|
| Who you see | All friends, flat list | Only existing Spotify contacts, inside DMs | **Circles** (small named groups) first, friends second |
| Services | 7, Spotify-centred, US-first | Spotify only | **YouTube Music and Amazon via Android listener**, Apple Music, Last.fm, Spotify when quota allows |
| Honesty | Not stated | Not stated | **"Live" only under 90 s** (Given); Recent and Top states labelled with freshness |
| Rituals | Sunday recap | Wrapped yearly, daylist | **Daily Drop + Monday "Your people's Song/Artist of the Week" + circle battles + monthly recap** |
| Group action | Reactions, DMs | Jam (Premium host) | **Circle shared playlist with credits, "Play in order in your app" export, listen-together** |
| Privacy | Tracking label | Opt-in, 16+ | **No-tracking label, Ghost/visibility controls one tap away, DPDP-ready** |
| Market | US Gen Z | Global | **India-first 18+, Hindi/Hinglish copy, low/mid-range Android** |

**Inference:** the wedge is "Airbuds for India, organised around circles." Spotify's own feature removes "see what Spotify friends play" as a reason to install, but it does nothing for the majority of Indian listeners on YouTube Music, nothing across services, and nothing for groups. The Monday reveal should be positioned as a recurring viral artifact — the Receiptify/Instafest spike (Instafest peaked at 6M users a day ([Vercel](https://vercel.com/blog/from-idea-to-100-million-views-instafest-music-festival-application))) delivered every week to a small group, rather than once a year.

### The Spotify constraint changes the launch plan

The 5-user Development Mode cap applies to existing apps from 9 March 2026, and extended quota needs a registered business, 250k MAU, presence in key Spotify markets and a launched service ([TechCrunch](https://techcrunch.com/2026/02/06/spotify-changes-developer-mode-api-to-require-premium-accounts-limits-test-users/)). **Recommendation:** at launch, the "Spotify" button in onboarding routes everyone except allowlisted testers to "Connect Last.fm (works with Spotify)" with a one-screen explanation of enabling Spotify scrobbling, and Jingle never promises Spotify-native Live in marketing until quota is granted. The idea of "Continue with Spotify" as account creation (an inference in the onboarding research) is not viable at launch for the same reason. All existing Spotify rules (display-only, attributed, no ML, deleted within 24 h of unlinking) stay in force (Given).

---

## 2. The magic moment is a real friend's card in the first session

Classic activation metrics measure network density: Facebook's "7 friends in 10 days" ([Mode](https://mode.com/blog/facebook-aha-moment-simpler-than-you-think/)), Slack's 2,000 messages ([Adam Arant](https://adamarant.com/en/blog/saas-activation-metric-the-one-number-that-predicts-retention)). Andrew Chen's "atomic network" sizes run from 2–3 people (Zoom) to 5–10 (Slack) ([Andrew Clark summary](https://andrewclark.co.uk/product-book-summaries/the-cold-start-problem)). Airbuds' co-founder says the app "only really works if you add your friends" ([TechCrunch](https://techcrunch.com/2025/09/17/airbuds-is-the-music-social-network-apple-and-spotify-wish-they-had-built/)), and Nikita Bier's rule is that an app must show value "in the first three seconds" ([Podcast Notes](https://podcastnotes.org/lennys-podcast-with-lenny-rachitsky/nikita-bier-how-to-consistently-go-viral-the-playbook-for-winning-at-consumer-apps-lennys-podcast/)). At the median product, more than 98% of new users are inactive within two weeks, and day-7 performance predicts 3-month performance for 69% of top products ([Amplitude](https://info.amplitude.com/rs/138-CDN-550/images/the-product-benchmark-report.pdf)).

**Recommendation — magic moment (two beats).** Beat one, seconds after connecting: **"You, now playing"** — the user's own card appears with the real track, proving the connection works even with zero friends. Beat two, within the first session: **a real friend's card** (Live if their signal is under 90 s old, otherwise Recent with an honest freshness label) followed by one tap to react or Tune in. Seeded or demo content may fill the screen but is visibly labelled "Demo" and never shows Live (Given: no false Live).

**Recommendation — activation metric (hypothesis to validate in beta):** *a listening source connected, plus at least 3 accepted friends or membership of 1 circle with at least 3 members, plus at least 1 social action (react, send a song, or add to a circle playlist), all within 7 days.* Track two leading indicators daily: time-to-first-own-card (target under 60 s from install for Android listener and Last.fm users) and time-to-first-friend-card.

**Recommendation — solo value ladder for empty networks**, in this order on Home: your own card and "your week so far"; today's Drop; a starter weekly recap with the full group view unlocked by inviting (the Airbuds gating pattern, applied only to the *group* reveal, never basic features); taste-matched people and circles; clearly labelled demo circles.

---

## 3. Four noun tabs and a persistent listening accessory

### Navigation evidence

Tab bars should hold 3–5 peer destinations and "tabs are nouns, not verbs" ([Design Bootcamp](https://medium.com/design-bootcamp/dont-design-junk-in-the-new-ios-26-tab-bar-4de8e842da89), secondary summary of HIG). Spotify's "Create" action tab was disliked enough that users could turn it off from July 2025 ([9to5Google](https://9to5google.com/2025/08/01/spotify-update-remove-create-button/)). Snapchat's 3-tab simplification was scrapped after losing about 1M North American users ([Influencer Marketing Hub](https://influencermarketinghub.com/snapchat-redesign/)), and Discord partly reverted a 2023 tab split because it broke the mental model shared with desktop ([Discord](https://discord.com/blog/improving-our-mobile-experience)). Instagram reorganised around "what people use the app for most" ([Dataconomy](https://dataconomy.com/2025/10/13/instagram-tests-reels-first-redesign-with-dms-at-the-center/)).

On iOS 26, Liquid Glass made controls a functional layer over content and tab bars shrink on scroll ([Apple Newsroom](https://www.apple.com/newsroom/2025/06/apple-introduces-a-delightful-and-elegant-new-software-design/)); `.tabViewBottomAccessory` hosts an app-wide accessory such as music controls above the tab bar ([Donny Wals](https://www.donnywals.com/exploring-tab-bars-on-ios-26-with-liquid-glass/)). iOS 27 (WWDC June 2026) reduced default transparency, added a graduated transparency slider and put search back among the tabs, because iOS 26 translucency dropped contrast below thresholds for some users ([TechTimes](https://www.techtimes.com/articles/317975/20260608/apple-liquid-glass-ios-27-wwdc-2026-brings-refinements-developers-must-adopt-today.htm); [Neowin](https://www.neowin.net/news/apple-finally-brings-the-slider-for-liquid-glass-and-many-other-changes/)). On Android, Material 3 Expressive replaced the navigation bar with a shorter "flexible navigation bar", and Google says to show the nav bar on primary pages and toolbars on subsequent pages ([9to5Google](https://9to5google.com/2025/05/14/material-3-expressive-navigation/); [9to5Google](https://9to5google.com/2025/05/18/material-3-expressive-toolbars/)). M3 Expressive was backed by 46 studies with 18,000+ participants and was preferred by up to 87% of 18–24-year-olds ([Google Design](https://design.google/library/expressive-material-design-google-research)).

### Recommended tab bar

| Tab (noun) | Purpose | Mirrors web | Badge |
|---|---|---|---|
| **Home** | Now stage (friends Live/Recent), Drop, Sent-to-you strip, reveal banner on Mondays | Home | Coral dot only when ≥1 friend is truly Live |
| **Circles** | Your circles, shared playlists, rituals/battles, Blends, suggested circles | Circles/Library | Count of unseen circle activity (neutral colour) |
| **Inbox** | Songs sent to you, reactions, requests, notifications history | Sent to you + notifications | Unread count |
| **You** | Profile, weekly/monthly recap, connections, privacy, settings | Profile/Settings | Connection-health warning dot |

**Search** is a top-right control on Home and Circles on Android; on iOS 27 it can be a search-role tab if Apple's re-integrated layout makes that natural, otherwise a top-bar button. **Send a song** and **Start listening together** are contextual actions (floating toolbar on Android sub-pages, top-right button on iOS), never tabs. A **listening accessory** sits above the tab bar on both platforms: your own now-playing state (with Ghost toggle) or, during a session, "Listening together with Riya · 3". **Recommendation:** do not use scroll-minimise for core tab switching (iOS 27's correction) and do not use swipe-between-tabs (it collides with horizontal shelves).

### IA map: every screen and its key states

All screens share six state patterns (Recommendation): **Loading** = ThumbHash/skeleton of the final layout, never a spinner on first paint; **Empty** = Blip pose plus one primary action; **Error** = plain-language cause plus retry, cached data kept on screen; **Offline** = cached content with a "Last updated 14:02" chip and disabled send/react queued for retry; **Degraded** = source connected but stale or revoked, shown as a neutral warning with a "Fix connection" action; **Live vs Recent** = coral LiveBadge only when the signal is under 90 s old, otherwise a muted freshness label ("12 min ago on YouTube Music").

| Area | Screen | Key content | Critical states |
|---|---|---|---|
| Onboarding | Welcome | Cassette mark, Blip, one-line promise, sign-in buttons | Invite context banner if arrived via link |
| | Sign in | Apple / Google / phone (Truecaller on Android, SMS OTP fallback) | OTP delay, wrong code, account exists |
| | Age and name | DOB (18+ gate), display name, username suggestion | Under-18 block screen |
| | Connect | Platform-specific source list (see §4) | Per-source connecting / success / failed / unsupported |
| | Android: notification-access guide | Explainer, animation, Settings deep link, return detection | Not granted, granted, listener disconnected |
| | Android: battery and autostart guide | OEM-specific checklist | Skipped, done, unknown OEM |
| | Proof | "You're Live" own card | No music playing: "Play any song to see it here" |
| | Find friends | Invite link share, username/QR, Contact Access button, suggestions | Limited contacts, no matches, all invited |
| | Notifications primer | Contextual full-screen primer | Denied: settings path shown later |
| | Widget prompt | Preview of widget and add instructions | Skipped |
| Home | Home | Now stage, Drop card, Sent-to-you strip, reveal banner, suggestions | Zero friends, all friends Recent, Ghost on, source degraded |
| | Friend now-playing sheet | Track, artwork, freshness, Tune in, react, send back | Live expires to Recent while open |
| | Daily Drop | Song of the day, why, reactions, add to circle | Before release (countdown), released, missed |
| | Weekly reveal (Mondays) | Countdown, story-format top-5 Song and Artist, share card | Not enough data, partial (invite to unlock group), seen |
| | Tune in | Deep link to the user's own app at that track | App not installed, not available on service |
| Circles | Circles list | Circle tiles with "n live now", ritual chips | No circles: create/join/suggested |
| | Circle home | Members, Live row, playlist entry, rituals, chat-lite reactions | Muted member, admin, blocked users hidden |
| | Circle playlist | Credited songs, add, remove, "Play in order in your app" | Empty, export in progress, export stale (Apple append-only note) |
| | Add a song | Catalogue search, optional note | No results, duplicate across apps |
| | Ritual / battle | Nominate, vote, results | Vote open, closed, tie |
| | Blend | Two-person or group blend, compatibility | Not enough data |
| | Listen-together session | Host, queue, members, join in own app | Host left, reconnecting, versioned queue conflict |
| | Create / join circle | Name, cover, invite link | Invalid or expired code |
| Inbox | Inbox | Sent songs, reactions, requests, system notices | Empty, unread, offline queue |
| | Song detail | Track, sender note, reply, react, open in app | Unresolved track |
| You | Profile | Avatar, now-playing, top artists, circles, recap entries | Own vs others', private, blocked |
| | Monthly recap | 9:16 story cards, share | Not enough listening |
| | Connections | Each source with health, last signal time, unlink | Degraded, revoked, Spotify unlinked (24 h deletion notice) |
| | Privacy | Visibility, Ghost/hide until time, per-circle visibility, blocked list | Ghost active (persistent indicator) |
| | Notifications settings | Per-type toggles, quiet hours, caps | OS-level denied |
| | Account and data | Export, delete account (in app), consent log | Deletion pending |
| Global | Search | People, circles, songs | No results, offline |
| | Share sheet / invite | WhatsApp, Instagram Stories, copy link, QR | Instagram not installed |
| | Deep-link landing | Circle, Drop, reveal, profile | Logged out, link expired |

### Per-platform adaptation (Recommendation)

| Element | iOS 26/27 | Android 16 (Material 3 Expressive) |
|---|---|---|
| Tab bar | Native Liquid Glass tab bar; labels always on | Flexible (short) navigation bar; no glass imitation (glass nav on Android was called "tacky" anecdotally ([X](https://x.com/Maksiu129479/status/2007366421953863996))) |
| Listening accessory | `tabViewBottomAccessory` | Docked surface above nav bar |
| Sub-page actions | Top-right toolbar buttons | Floating toolbar (playlist actions, send) |
| Sheets | Native detented sheets, interruptible drag | Modal bottom sheets with spatial springs |
| Glass | Only on chrome; never over artwork ([LiquidGlassReference](https://github.com/conorluddy/LiquidGlassReference)) | None on content; tonal surfaces |
| Motion | Native springs | Spatial springs for movement, effects springs for colour/opacity ([M3 Motion](https://m3.material.io/styles/motion/overview/how-it-works)) |
| App icon | Layered cassette mark via Icon Composer with light/dark/tinted/clear ([Apple Newsroom](https://www.apple.com/newsroom/2025/06/apple-introduces-a-delightful-and-elegant-new-software-design/)) | Adaptive + themed monochrome icon |
| Testing | Reduce Transparency on, iOS 27 slider at both ends | Font scale 200%, dark/light |

---

## 4. Onboarding takes three steps and earns every permission

### Patterns that work

The fastest-growing social apps reuse an existing identity or graph and ask for one core setup action: Threads imported Instagram profiles and follows in about 30 seconds and hit 100M sign-ups in 5 days ([TechCrunch](https://techcrunch.com/2023/07/10/instagrams-threads-app-reaches-100-million-users-in-just-five-days/)); Airbuds is "connect your Spotify" then friends ([TechCrunch](https://techcrunch.com/2025/09/17/airbuds-is-the-music-social-network-apple-and-spotify-wish-they-had-built/)). Duolingo gained about **20% DAU/next-day retention** by moving sign-up after the first lesson and uses soft walls with "Later" ([Taplytics](https://taplytics.com/blog/duolingo-ab-test-onboarding/)). BeReal's 9-step phone-first flow asks for contacts before value, which is widely critiqued ([Tear Them Down](https://tearthemdown.substack.com/p/bereal-product-case-study)). Bluesky starter packs drove up to **43% of new follows** during migration waves ([Lancaster University](https://www.lancaster.ac.uk/news/starter-packs-have-played-a-central-role-in-blueskys-rapid-growth-new-study-shows)) — the analogue for Jingle is "join the circle you were invited to and follow everyone in it with one tap."

Permission facts: push opt-in medians vary by vendor (Airship 2025: 48.85% iOS, 53.3% Android; social apps 63.59% iOS and 76.28% Android) ([Airship](https://growth.airship.com/rs/313-QPJ-195/images/Airship-2025-Push-Notification-Benchmarks-EN.pdf?version=0)), and Android's median fell from 71.3% (2023) to 53.3% (2025) after Android 13's runtime prompt. Priming lifts are vendor-reported only ([Plotline](https://www.plotline.so/blog/how-to-improve-push-notification-opt-in-rates)). iOS 18 introduced Limited contacts access and `ContactAccessButton` ([WWDC24](https://developer.apple.com/videos/play/wwdc2024/10121/)); Bier advised that anyone betting on contact sync should "start thinking about plan B" ([Podcast Notes](https://podcastnotes.org/lennys-podcast-with-lenny-rachitsky/nikita-bier-how-to-consistently-go-viral-the-playbook-for-winning-at-consumer-apps-lennys-podcast/)). Android notification access is granted only on a system Settings page, not via a dialog ([ACM](https://dl.acm.org/doi/10.1145/3728898)), and that page warns the app can read all notifications, including OTPs ([AOSP](https://source.android.com/docs/automotive/hmi/notifications/notification-access)).

Sign-in facts: passkeys show **93% login success versus 63%** for other methods ([FIDO Passkey Index](https://fidoalliance.org/wp-content/uploads/2025/10/FIDO-Passkey-Index-October-2025.pdf)); Truecaller's one-tap verification avoids SMS (vendor claims of 180M+ Indian users and lower costs) ([NamoID](https://namoid.in/blog/truecaller-verification-sdk-integration)). Apple guideline 4.8 requires an equivalent privacy-preserving login option whenever a third-party social login is offered, and 5.1.1(v) requires in-app account deletion ([App Store Review Guidelines](https://developer.apple.com/app-store/review/guidelines/)).

### Android onboarding, screen by screen (Recommendation)

Progress dots show **Connect → Friends → Notifications**; every step after Connect is skippable.

| # | Screen | Copy direction | Action and logic |
|---|---|---|---|
| 0 | Invite landing (if deep link) | "Riya invited you to *Hostel 4B* — 6 people, 23 songs" | Carries invite token through install (Play Install Referrer) |
| 1 | Welcome | Blip waves; "See what your people are playing. Every app." | Continue with Google (one tap) · Phone (Truecaller one-tap, SMS OTP fallback) |
| 2 | About you | DOB (18+), name, username prefilled | Under 18 → polite block, no data stored beyond the check |
| 3 | Where do you listen? | Tiles: YouTube Music, Spotify, JioSaavn/others, Apple Music, Amazon Music | Multi-select; drives the route below |
| 4a | Phone listener explainer (YT Music, Amazon, others) | "Jingle reads only the song your music app is playing — never messages or OTPs. You can turn it off any time." 3-frame animation of the Settings toggle | "Open settings" → `ACTION_NOTIFICATION_LISTENER_SETTINGS`; "Use another way" → Last.fm |
| 4b | Return detection | On resume, check grant | Granted → step 5; not granted → gentle retry plus alternatives |
| 4c | Spotify route | "Spotify connects through Last.fm for now" | Last.fm login; allowlisted testers see native Spotify |
| 4d | Apple Music route | MusicKit sign-in | Recent/Top only on Android unless listener also enabled |
| 5 | **Proof** | "You're Live" own card with the current track | If nothing playing: "Play any song — we'll wait" with live detection |
| 6 | Keep Jingle connected (OEM) | Detect manufacturer; show 2–4 tailored steps | Skippable; resurfaced if listener disconnects |
| 7 | Friends | Invite via WhatsApp (primary), Instagram, copy link, QR; username search; optional contacts | If arrived by invite: auto-joined circle, inviter auto-friended, "Follow all members" one tap |
| 8 | First friend card | Real friend card or labelled demo circle | React / Tune in coach mark |
| 9 | Notifications primer (contextual) | "Get a ping when Riya goes Live" / "Know when the Drop lands" | Full-screen primer; OS `POST_NOTIFICATIONS` prompt only on "Yes" |
| 10 | Widget offer | Live preview of the "Friends Live" widget | Pin-widget request where supported |

**OEM battery guidance (Recommendation, built on [dontkillmyapp](https://dontkillmyapp.com/xiaomi) facts):** Xiaomi/HyperOS needs "Autostart" on and battery saver set to "No restrictions", and its settings can reset after reboot, so the app re-checks after boot. Vivo needs manual autostart and "High background power consumption" allowed. Oppo/Realme ColorOS "background freeze" kills services when the screen is off, so add Jingle to the startup manager and disable battery optimisation ([dontkillmyapp Oppo](https://dontkillmyapp.com/oppo)). Samsung and stock Android get the generic "battery optimisation: not optimised" step. The listener should detect disconnection (`onListenerDisconnected` → `requestRebind`) and show a non-nagging "Jingle lost your music signal — fix in 2 taps" card on Home (Inference from the tech notes).

**Distribution fact that shapes this flow:** Android 13+ Restricted Settings blocks enabling notification access for sideloaded apps, and Android 15 extends this to non-store session installers ([XDA](https://www.xda-developers.com/android-13-restricted-setting-notification-listener/); [Android Authority](https://www.androidauthority.com/android-15-restricted-settings-sideloading-3481098/)) — so Jingle must ship through Google Play, never as a direct APK.

### iOS onboarding, screen by screen (Recommendation)

iOS cannot read other apps' playback through any public API; Apple says there is no API for cross-app history ([Apple forum](https://developer.apple.com/forums/thread/809554)), and background execution is limited to declared purposes (guideline 2.5.4) ([App Store Review Guidelines](https://developer.apple.com/app-store/review/guidelines/)). Live on iOS therefore comes from server-side sources (Last.fm now-playing; Spotify Web API for allowlisted users) and from MusicKit while Jingle is in the foreground; Apple's recently-played data supports Recent and Top, not Live (Inference from tech notes). The iOS flow must say this honestly.

| # | Screen | Copy direction | Action and logic |
|---|---|---|---|
| 0 | Invite landing | Same as Android | Universal Link; deferred via clipboard code or vendor |
| 1 | Welcome | Same | Sign in with Apple (first), Google, phone |
| 2 | About you | DOB 18+, name, username | — |
| 3 | Where do you listen? | Same tiles | Routes below |
| 4a | Apple Music | MusicKit sign-in | Shows Recent immediately; "Live while Jingle is open" note |
| 4b | Spotify / any scrobbling app | Last.fm login | Live from Last.fm now-playing when fresh |
| 4c | YouTube Music / Amazon | "On iPhone, Jingle can't see these apps. Connect them from your laptop with the Jingle Companion, or from an Android phone." | Email/QR handoff to desktop extension; Top/Recent from other routes |
| 5 | Proof | Own card (Live or Recent, honestly labelled) | — |
| 6 | Friends | Invite sheet first; `ContactAccessButton` inline in search; username/QR | Designed for Limited access by default |
| 7 | First friend card | Same as Android | — |
| 8 | Notifications primer | Contextual | OS prompt on "Yes" only |
| 9 | Widget and Lock Screen offer | Short animation of adding the widget | Skippable |

**Recommendation:** offer passkey enrolment after the first successful week, not at sign-up (passkey benefits are for returning logins). Do not ask for contacts, notifications or widgets before the Proof screen.

### Invite and deferred deep-link flow (Recommendation)

Firebase Dynamic Links shut down on 25 August 2025 and all links now return 404 ([Firebase FAQ](https://firebase.google.com/support/dynamic-links-faq)); native Universal Links and App Links do not provide deferred deep linking ([Airbridge](https://www.airbridge.io/en/blog/firebase-dynamic-links-alternatives)). Partiful shows the power of making a link useful before install: guests RSVP from the web with no app ([Partiful Help](https://help.partiful.com/hc/en-us/articles/27354346663963-Do-my-guests-need-to-download-the-app)). The Jingle invite loop is: share a circle link (`jingle.<domain>/c/<code>`) via WhatsApp or Instagram; the recipient sees a **web preview** (circle name, member faces, the shared playlist with tappable songs, today's Drop); they install; the invite token survives install via Play Install Referrer on Android and a "Have an invite? Paste" clipboard step or Branch's free tier on iOS; one-tap sign-in lands them already in the circle with the inviter friended; Connect is framed as "so Riya and the circle see what you play." No published conversion data compares deferred and plain store links, so measure both.

---

## 5. Daily Drop and Monday reveal drive habit without punishing streaks

### Evidence for forgiving rituals

Duolingo learners with a 7-day streak are 2.4x more likely to return the next day (aggregator, primary unverified) ([sqmagazine](https://sqmagazine.co.uk/duolingo-statistics/)), and Duolingo's Weekend Amulet made users **4% more likely to return a week later and 5% less likely to lose a streak** — "by giving learners the option to take a break, they're actually more likely to do more in the long run" ([Duolingo blog](https://blog.duolingo.com/how-streaks-keep-duolingo-learners-committed-to-their-language-goals/), 2017). Snapchat streaks generate documented teen anxiety and monetised restores ([Screenwise](https://screenwiseapp.com/guides/snapchat-streaks-and-social-anxiety)), and Snapchat switched off its Solar System ranking by default after backlash ([TechCrunch](https://techcrunch.com/2024/04/05/snapchat-turns-off-controversial-solar-system-feature-by-default-after-bad-press)). Weekly cadences work: Locket's weekly Rollcall draws **more than a quarter of active users** ([TechCrunch](https://techcrunch.com/2025/08/06/photo-sharing-app-locket-is-banking-on-a-new-celebrity-focused-feature-to-fuel-its-growth)), Apple Replay updates every Sunday ([MacRumors](https://www.macrumors.com/2025/02/03/apple-music-replay-2025-now-available/)), and Wrapped 2025 added group mechanics (Clubs, Wrapped Party) ([TechBuzz](https://www.techbuzz.ai/articles/spotify-wrapped-2025-hits-200m-users-in-24-hours-after-last-year-s-ai-flop)).

### The ritual calendar (Recommendation)

| Cadence | Ritual | Mechanic | Guardrail |
|---|---|---|---|
| Ambient | Now stage + widget | Friends Live/Recent | Live only under 90 s |
| Daily, 9 pm IST default | **Daily Drop** | One song; react, add to circle, send | No "you missed it" shaming; archive stays browsable |
| Daily (opt-in) | Circle streak | Circle-level: any member adds or reacts keeps it alive | **2 freezes per week auto-applied; exam/travel pass; no paid restore; no individual leaderboard** |
| Weekly, Monday | **Your people's Song/Artist of the Week** top-5 reveal | Sunday-night countdown, story-format reveal, 9:16 share card, group variant | Partial view unlocked by inviting only for the *group* card |
| Weekly | Circle battle/ritual | Nominate → vote → results | Rankings visible only if the circle opts in |
| Monthly | Monthly recap | Story cards, share | Hidden if too little data |
| Event | Listen-together | Live session | Session ends cleanly; no FOMO pings after it ends |

Variable reward should come from real social content — who reacted, what the circle picked — not artificial loot (Inference from retention notes).

### Widgets and Live Activities

Widget-native social apps are among the largest youth successes of the period: Locket at about **9M DAU** and Airbuds, whose "core functionality remains the widget" ([TechCrunch](https://techcrunch.com/2025/08/06/photo-sharing-app-locket-is-banking-on-a-new-celebrity-focused-feature-to-fuel-its-growth); [TechCrunch](https://techcrunch.com/2025/09/17/airbuds-is-the-music-social-network-apple-and-spotify-wish-they-had-built/)). Expo's `expo-widgets` (stable in SDK 56) builds iOS widgets and Live Activities as React components, with Lock Screen, Dynamic Island compact/minimal/expanded slots, interactive buttons and push-to-start tokens ([Expo docs](https://docs.expo.dev/versions/latest/sdk/widgets/)). No public data exists on Live Activity effects for social apps, and Apple's Live Activity duration and update limits were not verified.

| Surface | Content | Platform | Phase |
|---|---|---|---|
| **Friends Live widget** (small/medium) | 1–4 friend cards, coral only when truly Live, freshness otherwise | iOS WidgetKit (expo-widgets); Android Glance (custom Kotlin) | Launch (must-have) |
| Drop widget / Lock Screen | Today's Drop artwork + title | iOS Lock Screen, Android small | Launch |
| Circle widget | One circle's Live row and latest playlist add | Both | Post-launch |
| Live Activity: Listening together | Host, current track, member count, Leave | iOS | Post-launch v1.1 |
| Live Activity: Monday countdown | Countdown to reveal, then "Your reveal is ready" | iOS | Post-launch v1.1 (verify Apple limits) |
| Android ongoing notification for sessions | Same as above | Android | v1.1 |

Widget rules (Recommendation): artwork shown uncropped at its own aspect, radius 4/8 px, no text over art; widgets use cached data and never imply Live from a stale cache — if the last refresh is older than 90 s, the widget shows Recent.

### Notification taxonomy, caps and quiet hours (Recommendation)

Duolingo's bandit research found that rotating templates while modelling novelty decay produced **+0.5% DAU and +2% new-user retention** ([Duolingo Research](https://research.duolingo.com/papers/yancey.kdd20.pdf)). No sourced data exists on ideal caps or Indian tolerance, so these are starting values to tune.

| Type (Android channel) | Trigger | Default | Cap | Priority |
|---|---|---|---|---|
| Sent to you | Friend sends a song | On | None (human-generated) | High |
| Reactions | Reaction to your card or add | On, bundled | Bundle into 1 per 30 min | Medium |
| Friend Live | Close friend goes Live (user picks friends) | Off until chosen | 1 per friend per 6 h; 3/day total | Medium |
| Circle activity | Song added, ritual opened, vote closing | On, digest | 1 digest per circle per day | Medium |
| Daily Drop | Drop released | On | 1/day | Medium |
| Weekly reveal | Monday reveal ready | On | 1/week | High |
| Session invite | Listen-together invite | On | Human-generated | High |
| Connection health | Source degraded/revoked | On | 1 per 3 days | Medium |
| Recap/monthly | Recap ready | On | 1/month | Low |
| Account/security | Login, deletion, export | Always | — | High |

Global rules: **quiet hours 23:00–08:00 local by default** (editable); a total cap of 6 non-human-generated notifications per day; marketing-style nudges at most 2 per week and never during quiet hours; no notifications that reference someone's absence ("Riya hasn't heard from you"); rotate templates per Duolingo's approach. Socket.IO connections drop when an iOS app backgrounds, so out-of-app events go through APNs/FCM and the app reconnects and refetches versioned state on foreground (Inference from tech notes).

### Shareability and invite loops (Recommendation)

Music identity cards are among the most shared formats online (Wrapped 2025: 500M+ shares on day one ([IBTimes](https://www.ibtimes.co.uk/record-breaking-spotify-wrapped-2025-sees-200m-engage-500m-shares-day-1760640))). Instagram Stories sharing requires writing the asset to the pasteboard with a registered **Meta App ID** as `source_application`; shares without one are rejected ([Medium](https://medium.com/@burakekmen/story-sharing-on-facebook-instagram-in-ios-apps-2df2a82ebf96); [react-native-share #1304](https://github.com/react-native-share/react-native-share/issues/1304)). Share artifacts: the Monday top-5 card (individual and circle variants, 9:16, deep link back), the Drop card, a circle playlist card (WhatsApp-first, with web preview), the monthly recap, and a "My Jingle" profile QR. Every shared link opens a useful web page first (Partiful pattern), and every share card shows real artwork untouched, framed by cassette/mixtape texture rather than overlaid.

---

## 6. Night Studio for phones: tokens, type, motion, haptics and access

### What "premium" means in the evidence

Premium feel comes from fast, interruptible, physically plausible motion. Emil Kowalski's standards: no animation for actions done 100+ times a day, reduced animation for tens a day, standard for occasional actions, delight only for rare ones; ease-out `cubic-bezier(0.23,1,0.32,1)`; press 100–160 ms, popover 125–200 ms, modal/drawer 200–500 ms, most UI under 300 ms; press scale 0.95–0.98; never scale from 0; springs around `{duration: 0.5, bounce: 0.2}` with bounce 0.1–0.3; stagger 30–80 ms; animate only transform and opacity; reduced motion keeps opacity/colour and drops movement ([emilkowalski/skills](https://github.com/emilkowalski/skills/blob/main/skills/review-animations/STANDARDS.md)). Spotify Wrapped 2025 used a mixtape/burned-CD analogue aesthetic built in Rive with data binding ([Spotify design](https://spotifynews.substack.com/p/designing-2025-wrapped-turning-a); [Rive](https://rive.app/blog/spotify-used-rive-for-spotify-wrapped-2025)) — directly on-brand for a cassette logo. Known "AI slop" tells include overused Inter, purple gradients, gradient text, glowing dark mode and decorative glassmorphism ([impeccable.style](https://impeccable.style/slop/)).

### Tokens: reuse the web source of truth

**Repo:** `packages/design-tokens` already defines dark and light themes with a WCAG AA contrast test: dark `bg #0A090C`, surfaces `#131116 / #1B181F / #252129`, text `#F6F3EF`, `live #FF6B5E` (coral) with `on-live #1A0705`, brand violet `#8B6BFF` → cyan `#3FE7D8` gradient, artwork radii 4/8 px, UI radii 8/12/20, a 4 px spacing grid, and durations 120/200/320 ms. **Recommendation:** migrate this to DTCG 2025.10 JSON (`*.tokens.json`), the first stable W3C spec, which supports theming via `$extends` and OKLCH/P3 colour ([W3C DTCG](https://www.w3.org/community/design-tokens/2025/10/28/design-tokens-specification-reaches-first-stable-version/)), and build it with Style Dictionary (DTCG-native since v4) ([Style Dictionary](https://styledictionary.com/info/dtcg/)) into Tailwind v4 CSS for web, `tokens.ts` with hex/rgba numbers for React Native (convert any OKLCH at build time), and DESIGN.md front matter. A CI check fails on drift.

| Token group | Mobile additions (Recommendation) |
|---|---|
| Colour | Keep all web roles; add `surface-chrome` for non-glass Android bars; add `live-on-glass` checked against translucent bars at both ends of the iOS 27 slider |
| Brand gradient | Max 3 moments per screen (Given); allowed on reveal hero, primary CTA, Blip glow — never text, never chrome, never over artwork |
| Artwork | `r-art-sm 4`, `r-art-lg 8` only; no blur-art backgrounds behind Spotify artwork; dynamic colour from artwork allowed for non-Spotify now-playing backgrounds but **coral is never derived** |
| Spacing | 4 px grid; screen margin 16; card gutter 12 |
| Touch | Minimum hit area 44 pt (iOS) / 48 dp (Android) |
| Elevation | Dark: tonal steps over shadows; light: existing shadows |
| Motion | See table below |

**Repo finding to reconcile:** `UX_SPEC.md` §4 sets FeedCard artwork radius to `--r-md` (12 px) at shelf sizes, while the token file and Spotify's guidelines cap artwork at 4 px (small/medium devices) and 8 px (large) ([Spotify Design Guidelines](https://developer.spotify.com/documentation/design)). Mobile should use 4/8 px for all third-party artwork.

### Typography (Recommendation)

**Repo:** the web uses Bricolage (display), Inter (UI) and JetBrains Mono (freshness labels). Bricolage is distinctive and should stay as the display face for reveals, recaps and section titles. Inter is on the slop list ([impeccable.style](https://impeccable.style/slop/)); on mobile, the stronger choice is the **platform system font for body text** (SF Pro on iOS, the Android system sans) because it gets Dynamic Type and font scaling for free, with Bricolage for display and a mono for freshness/data labels. Hindi/Hinglish support needs a Devanagari-capable fallback (for example Noto Sans Devanagari) — verify glyph coverage of every chosen face. All text styles scale with Dynamic Type / Android font scale up to at least 200%, song titles wrap to two lines before truncating, and truncated titles expose the full title to screen readers.

### Motion spec (Recommendation built on cited standards)

| Interaction | Frequency class | Spec | Reduced motion |
|---|---|---|---|
| Tab switch | 100+/day | No transition beyond native; selection haptic only | Same |
| Card press | Many/day | Scale 0.97, 120 ms ease-out | Opacity 0.8 |
| Live card update (track changes) | Tens/day | Cross-fade 160 ms, effects spring (no overshoot); artwork swaps, never animates | Instant swap |
| LiveBadge equaliser | Ambient | Existing bars; paused off-screen and when app inactive | Static bars |
| Sheet open/close | Occasional | Native sheet / spatial spring ≈ `{duration 0.45, bounce 0.15}`, fully interruptible by drag | Fade 200 ms |
| Mini-player → now-playing | Occasional | Shared-element move of the artwork *frame* (geometry only); fallback cross-fade because Reanimated shared transitions are still flagged experimental ([Software Mansion](https://swmansion.com/blog/introducing-reanimated-4-2-0-71eea21ca861/)) | Cross-fade |
| Reaction picker | Tens/day | Pop from 0.9 + opacity, 150 ms; stagger 30 ms | Fade |
| Send song success | Occasional | Check morph 250 ms + success haptic | Fade + haptic |
| Daily Drop open | Daily | Cassette "insert" Rive animation ≤ 900 ms, skippable by tap | Static card |
| Monday reveal | Weekly (rare) | Story sequence; per-rank spring `{0.5, 0.25}`, 60 ms stagger; Rive Blip celebration; custom haptic synced to a short sound | Fades, no movement, haptic kept optional |
| List entry | Per screen | Stagger 40 ms, never blocks interaction | None |

Only transform and opacity animate. Springs follow M3's two families on Android: spatial springs may overshoot; effects springs never do ([M3 Motion](https://m3.material.io/styles/motion/overview/how-it-works)). **Inference:** artwork-frame movement between mini-player and full player is a geometry change, not animating the artwork — confirm this reading of the "never animated" rule with the founder.

### Haptics map (Recommendation)

Android guidance prefers crisp "clear" haptics and the semantic `HapticFeedbackConstants` such as CONFIRM and REJECT ([Android haptics principles](https://developer.android.com/develop/ui/views/haptics/haptics-principles); [HapticFeedbackConstants](https://developer.android.com/reference/android/view/HapticFeedbackConstants)); iOS offers Impact, Selection and Notification generators plus Core Haptics for audio-synced patterns ([Eidinger](https://blog.eidinger.info/haptics-on-apple-platforms)).

| Event | iOS | Android |
|---|---|---|
| Tab change, scrubbing reaction picker, vote selection | Selection | Selection/tick constant (verify per API level) |
| Send song, add to playlist, join circle | Notification `.success` | `CONFIRM` |
| Failure (send failed, invalid code) | Notification `.error` | `REJECT` |
| Pull to refresh threshold | Impact light | Gesture threshold constant (verify) |
| Monday reveal #1 | Core Haptics custom pattern synced to sound | Composed vibration (rich), short |
| Passive Live updates, incoming feed items | **None** | **None** |

A global "Haptics" toggle lives in settings, and system haptic settings are always respected.

### Accessibility bar (WCAG 2.2 AA, Given)

The evidence that polish must survive accessibility settings is direct: iOS 26 glass pushed contrast below thresholds ([TechTimes](https://www.techtimes.com/articles/317975/20260608/apple-liquid-glass-ios-27-wwdc-2026-brings-refinements-developers-must-adopt-today.htm)), and M3 Expressive's research found expressive sizing let users 45+ perform on par with younger users ([Google Design](https://design.google/library/expressive-material-design-google-research)). **Recommendation — release checklist:** every text/surface pair passes 4.5:1 (existing token test extended to mobile surfaces and coral-on-glass); Live is never conveyed by colour alone (badge text "LIVE" plus VoiceOver/TalkBack label "Live now on YouTube Music"); full VoiceOver and TalkBack passes on every screen in §3; Dynamic Type/font scale 200% without clipping; Reduce Motion, Reduce Transparency, iOS 27 transparency slider and Android "Remove animations" all tested; 44 pt / 48 dp targets; reveal stories pausable and navigable without timing; captions or text equivalents for any audio cue; Blip animations decorative and hidden from assistive tech.

### Performance as perceived quality

Android vitals flags excessive launch at **cold ≥5 s, warm ≥2 s, hot ≥1.5 s** time-to-initial-display ([Android Developers](https://developer.android.com/google/play/vitals/launch-time)). ThumbHash encodes more detail and colour than BlurHash and expo-image supports it as a placeholder ([ThumbHash](https://evanw.github.io/thumbhash/); [Expo Image](https://docs.expo.dev/versions/latest/sdk/image/)). Older Expo issues reported expo-image and module start-up stalls on low-end Android ([expo#25201](https://github.com/expo/expo/issues/25201)) — verify on the current SDK. **Recommendation — budgets:** cold-start TTID under 2 s on a mid-range Android (₹15–20k class) and under 3 s on a 3 GB device; 60 fps scroll on Home with FlashList v2; the API returns a ThumbHash with every artwork URL; the install size is kept small (an agency blog suggests a 25 MB target for India ([vMobify](https://vmobify.com/blog/app-install-cost-india)), low confidence).

---

## 7. Blip and every asset start with a human hand

AI-only images are not copyrightable in the US; human selection, arrangement or modification can be, case by case ([US Copyright Office via LoC](https://newsroom.loc.gov/news/copyright-office-releases-part-2-of-artificial-intelligence-report/s/f3959c36-d616-498d-b8f9-67641fd18bab)). Airbnb's in-house team spent **two years** on its 3D icon set ([Design Bootcamp](https://medium.com/design-bootcamp/airbnb-summer-2025-update-heres-what-s-new-and-why-it-matters-0ced2338b921)). Duolingo animates characters in Rive with state machines for idle, speaking, blinking and reacting ([Duolingo blog](https://blog.duolingo.com/world-character-visemes)); Callstack measured Rive at about 60 FPS against Lottie's 17 FPS in one mobile test ([Callstack](https://www.callstack.com/blog/lottie-vs-rive-optimizing-mobile-app-animation)), and common guidance is Rive for stateful interaction, Lottie for simple linear playback ([PkgPulse](https://www.pkgpulse.com/guides/lottie-vs-rive-vs-css-animations-web-animation-formats-2026)).

**Recommendation — pipeline in six stages.** First, a human illustrator (commissioned, ideally Indian, with full IP assignment) draws Blip's canonical model sheet: turnarounds, 12 expressions, line weight, palette from Night Studio tokens. Second, write the **asset prompt plan**: one reusable style block (palette hexes, line weight, lighting, camera, texture: cassette, photocopy, sticker), a do-not list (no purple glow, no glass, no gradient text, no fake album art, no real artists' likenesses), and per-asset prompts. Third, use image-generation tools (via an image MCP if available; Higgsfield's MCP was not verified) only to explore poses, backgrounds and empty-state scenes in batches; curate hard and have the illustrator redraw or materially edit every keeper. Fourth, rig Blip in Rive with a state machine: `idle`, `listening` (bobs to a beat input), `reacting`, `celebrating` (reveal), `sleeping` (quiet hours / empty), `confused` (error), `connecting`. Fifth, produce static exports for widgets, notifications and store screenshots, plus Lottie only for trivial loops. Sixth, log provenance (human source file, AI-assisted steps) per asset. Album artwork is never generated, altered, cropped or overlaid (Given); where no artwork exists, use the existing GenerativeCover pattern (Repo, `UX_SPEC.md`) clearly distinct from real covers.

| Asset | Owner | Format | Used in |
|---|---|---|---|
| Blip master + states | Illustrator + Rive animator | `.riv` | Onboarding, empty states, reveal, errors |
| Empty-state scenes (≈12) | Illustrator, AI-explored | PNG/WebP @3x | Every empty state in §3 |
| App icon | Designer | Icon Composer layers / adaptive icon | Stores, home screen |
| Reveal and recap templates | Designer in Rive with data binding | `.riv` | Monday reveal, monthly recap, share cards |
| Share card frames | Designer | Rendered from RN view → PNG | WhatsApp/Instagram |
| Store screenshots and preview video | Designer | PNG/MP4 | Listings |

---

## 8. Expo React Native, native capture modules and store-safe architecture

### Stack (Recommendation built on cited facts)

Expo SDK 54 was the last with the Legacy Architecture, and Reanimated 4 and FlashList v2 are New-Architecture-only ([Expo SDK 54](https://expo.dev/changelog/sdk-54)); React Native 0.82 removed the Legacy Architecture ([Callstack](https://www.callstack.com/blog/react-native-wrapped-2025-a-month-by-month-recap-of-the-year)). Expo SDK 57 (30 June 2026) ships RN 0.86, React 19.2, Reanimated 4.5, an opt-in scene lifecycle for the iOS 27 SDK, and Hermes regression fixes in 57.0.9 and 57.0.17 ([Expo SDK 57](https://expo.dev/changelog/sdk-57)). Shopify moved its apps to the New Architecture while keeping weekly releases ([Shopify Engineering](https://shopify.engineering/react-native-new-architecture)).

| Layer | Choice | Basis |
|---|---|---|
| App framework | Expo SDK 57+ (≥57.0.17), RN 0.86, New Architecture, Hermes, expo-router | Fact (SDK) / Rec |
| Shared code with web | TS types, generated OpenAPI client, TanStack Query hooks, Zod schemas, Socket.IO client logic, tokens | Inference |
| Lists and images | FlashList v2; expo-image with ThumbHash and cache seeding | Fact (capabilities) / Rec |
| Animation | Reanimated 4 + worklets, Gesture Handler, Skia for Pulse/visualisers, Rive runtime | Rec |
| iOS widgets + Live Activities | `expo-widgets` (stable SDK 56), App Group shared cache, APNs updates | Fact |
| Android widgets | Custom Expo Module with Jetpack Glance (no first-party Expo solution confirmed) | Inference |
| Android capture | Expo Module porting the existing Kotlin `NotificationListenerService` + `MediaSessionManager.getActiveSessions()`; package allowlist of music apps; metadata only, never notification text; WorkManager expedited batched pushes to `/ingest/1/submit-listens`; **no foreground service** | Inference from [Android 15 FGS limits](https://developer.android.com/about/versions/15/behavior-changes-15) |
| iOS capture | MusicKit (foreground), server-side Last.fm/Spotify polling; Spotify App Remote optional only (guideline 4.2.3(i)) | Fact / Inference |
| Auth | Sign in with Apple, Google, phone OTP (Truecaller Android), passkeys later; tokens in Keychain/Keystore via SecureStore | Rec |
| Realtime | Socket.IO foreground only; reconnect with versioned state; APNs/FCM for background events | Inference |
| Offline | TanStack Query cache persisted to MMKV; outbox queue for sends/reactions | Inference |
| Push | expo-notifications (APNs/FCM), Android channels per §5 taxonomy (verify current feature set) | Rec, unverified |
| Deep links | Universal Links / App Links on a Jingle domain; Play Install Referrer; Branch free tier or clipboard code on iOS | Fact ([AppsFlyer](https://www.appsflyer.com/blog/mobile-marketing/fdl-deprecation-deep-linking/)) / Rec |
| OTA | EAS Update for JS/assets only — allowed under DPLA 3.3.1(B) if purpose unchanged; native changes need store builds ([Bitrise](https://bitrise.io/resources/compare/bitrise-codepush-vs-expo-eas-update)) | Fact (secondary) |
| Builds and release | EAS Build/Submit with Continuous Native Generation; config plugins for native targets | Rec |
| Observability | Crash and performance (e.g. Sentry), product analytics and flags (e.g. PostHog, self-hostable) — not verified in research | Rec, unverified |
| Testing | Unit (Jest), component, E2E (Maestro or Detox — status unverified), native module tests in Kotlin/Swift, axe-equivalent a11y audits, device lab (Xiaomi, Vivo, Oppo, Samsung, Pixel, iPhone SE/15) | Rec |
| CI/CD | GitHub Actions → EAS; token drift check; bundle-size and cold-start regression gates | Rec |

EAS Update pricing from a third-party summary is free to 1,000 MAU, $19/month to 3,000, $199/month to 50,000 ([Stallion](https://stalliontech.io/expo-eas-update-pricing)) — confirm on Expo's site. **Alternatives considered:** native SwiftUI + Compose gives the best per-platform polish but means two codebases plus web for a small team; Flutter shares nothing with the existing TypeScript stack (Inference).

### The current WebView wrapper must not ship

Guideline 4.2 asks apps to rise "beyond a repackaged website", and practitioner reports call it the most common rejection reason ([App Store Review Guidelines](https://developer.apple.com/app-store/review/guidelines/); [MobiLoud](https://www.mobiloud.com/blog/app-store-review-guidelines-webview-wrapper/)); Google Play's minimum-functionality and spam rules cover low-content and webview apps ([Play Spam policy](https://support.google.com/googleplay/android-developer/answer/9899034)). **Recommendation:** replace `apps/android` with the native-UI Expo app; keep its Kotlin listener code as the seed of the Expo Module.

### Store compliance checklist

| Rule | Requirement | Jingle action |
|---|---|---|
| Apple 4.2 / Play minimum functionality | Native value beyond a website | Native UI, widgets, push, offline, share |
| Apple 4.2.3(i) | Works without another app | Jingle useful without Spotify/Apple Music installed |
| Apple 2.5.4 | Background modes only for intended uses | No fake audio background mode |
| Apple 2.5.2 / DPLA 3.3.1(B) | OTA can't change purpose or add features | EAS Update for fixes and content only |
| Apple 4.8 | Privacy-preserving login alongside social login | Sign in with Apple |
| Apple 5.1.1(v) | In-app account deletion | You → Account and data → Delete |
| Apple 5.1.2(i) ATT | Only if tracking | No tracking → no ATT prompt; "no tracking" label as a marketing point |
| Play target API | New apps/updates target API 36 since 31 Aug 2026 ([Play](https://support.google.com/googleplay/android-developer/answer/11926878?hl=en)) | Target 36 from day one |
| Play notification-listener policy | Reported as restricted with allowed uses incl. widgets — **unverified** ([Play Console Help](https://support.google.com/googleplay/android-developer/answer/16558241)) | Prominent in-app disclosure, minimal use, declaration if required; verify in Play Console before beta |
| Android Restricted Settings | Sideloaded apps blocked from notification access | Play-only distribution |
| Android FGS limits | dataSync capped 6 h/24 h on Android 15 | No FGS; WorkManager |
| Spotify branding | Logo with any Spotify data (icon ≥21 px), no crop/overlay, radius 4/8 px ([Spotify](https://developer.spotify.com/documentation/design)) | Attribution row on Spotify cards |
| Instagram Stories | Registered Meta App ID | Register before share-card launch |
| Apple Music / YouTube / store badges | Not researched | Fetch brand guidelines before listing design |

### Privacy and DPDP checklist

The DPDP Rules were notified on 13 November 2025; the Consent Manager framework applies from 13 November 2026 and most obligations (notice, security, breach, retention, children's data) from **13 May 2027** ([Wikipedia](https://en.wikipedia.org/wiki/Digital_Personal_Data_Protection_Rules,_2025); [Lexology](https://www.lexology.com/library/detail.aspx?g=bbd416e3-04a5-4f77-a83b-76a01aeda951)). **Recommendation:** build to the 2027 standard now.

| Area | Control |
|---|---|
| Notice and consent | Plain-language notice at sign-up (English + Hindi); granular consent for listening capture, contacts, notifications, analytics; consent log viewable in app |
| Age | 18+ gate at DOB; no data retained from blocked minors beyond the check |
| Minimisation | Android listener reads only MediaSession metadata from an allowlist; never notification text; contacts matched by hash and never stored raw |
| Visibility | Default "Friends" visibility; Ghost/hide-until; per-circle visibility; blocked users invisible everywhere |
| Spotify data | Display-only, attributed, never used for ML, deleted within 24 h of unlinking (Given) |
| Rights | In-app export and deletion; deletion cascades to widgets' App Group cache and push tokens |
| Security | Tokens encrypted at rest; device secrets in Keychain/Keystore; certificate pinning considered |
| Breach | Runbook and notification path aligned with DPDP breach rules |
| Store labels | Apple: listening history, user content, identifiers, usage data linked to user, none for tracking; Play Data safety: music activity collected and shared with friends; deletion URL |
| Third parties | Analytics self-hosted or DPA-covered; no ad SDKs |

---

## 9. Claude Design runs Define, Design, Build before any code

### What Claude Design is and is not

Claude Design launched on 17 April 2026 from Anthropic Labs as a research preview for Pro, Max, Team and Enterprise, running on Claude Opus 4.7; it builds a design system "by reading your codebase and design files", takes prompts, images, documents and web captures, supports inline comments, direct edits and adjustment knobs, and exports to share links, PDF, PPTX, standalone HTML or a "handoff bundle" to Claude Code ([Anthropic](https://www.anthropic.com/news/claude-design-anthropic-labs)). It is reachable from chat, the Artifacts tab, `/design` commands in Claude Code and claude.ai/design; branching works with "Save what we have and try a completely different approach"; if comments aren't picked up, paste the feedback into chat ([Help center](https://support.claude.com/en/articles/14604416-get-started-with-claude-design)). Since 17 June 2026, `/design-sync` syncs design systems and built work both ways with Claude Code ([ClaudeDevs](https://x.com/ClaudeDevs/status/2067391951725629941)); it needs `.design-sync/config.json`, uses a `conventions.md`, grades Storybook stories against previews, and silently drops components not exported from the entry file ([Nitay Neeman](https://nitayneeman.com/blog/how-to-sync-a-design-system-with-claude-design/)). Limits: no Figma export ([UX Pilot](https://uxpilot.ai/blogs/claude-design-review)), usage comes from normal Claude limits, and one reviewer found Pro allowed "one or two meaningful iterations" a week while Max was workable ([Yiannis Antoniou](https://yiannisantoniou.substack.com/p/claude-design-redux-impressive-but)). No official native-mobile export or device-frame presets were found, and `/design-sync` support for React Native libraries is undocumented. DESIGN.md, open-sourced by Google Labs in April 2026, pairs YAML token front matter with prose rationale that coding agents follow ([google-labs-code/design.md](https://github.com/google-labs-code/design.md)).

**Inference:** Claude Design outputs HTML/React prototypes. For an Expo app they define intent, layout, states and copy; Claude Code translates them to React Native primitives. Plan for Max or Team during the design sprint.

### The workflow, merging the founder's three inspirations (Recommendation)

| Step | Where | Output | Inspiration |
|---|---|---|---|
| 1. Define: answer six business questions | Chat / doc | One-page brief | Define-Design-Build |
| 2. Fix magic moment and activation metric | Brief | §2 of this plan | Define-Design-Build |
| 3. Sync Night Studio | Claude Code `/design-sync` on `packages/design-tokens` + `apps/web/src/components/ds`, with `conventions.md` stating mobile rules | Design system in Claude Design | Anthropic designer (connect repo) |
| 4. Write DESIGN.md + design.html | Claude Code with the `jingle-design-system` skill | `docs/ux/mobile/DESIGN.md`, generated preview page | Define-Design-Build (design-system skill) |
| 5. Collect references | Mobbin (paid), own screenshots of Airbuds, Locket, Apple Music, Spotify Wrapped 2025 | 3–5 refs per flow, each with "borrow this, not that" | Premium craft |
| 6. Asset prompt plan + image MCP exploration | Claude Code + image MCP | Moodboards, Blip explorations (never final) | Define-Design-Build; premium craft |
| 7. New design: three divergent directions per hero flow | Claude Design | Options with rationale | Anthropic designer (options) |
| 8. Converge: comments, knobs, own direct edits | Claude Design | One direction per flow | Anthropic designer (comments, own edits) |
| 9. Every state | Claude Design | Empty/loading/error/offline/Live/Recent per screen | Claude Academy |
| 10. Self-critique pass | Claude Design chat | Critique vs UX spec, WCAG 2.2, slop list | Inference |
| 11. Click-through prototype of 5 core flows | Claude Design share link | Prototype | Anthropic designer |
| 12. Two rounds of 5-user tests on real phones | Moderated sessions | Issue log | [Maze](https://maze.co/blog/user-testing-how-many-users/) |
| 13. Motion and haptics spec + Rive files | Claude Design + Rive | Motion table, `.riv` | Premium craft (levels of feedback) |
| 14. "Build it": hand off to Claude Code | Export → Hand off to Claude Code | Handoff bundle + ticket list | Anthropic designer |
| 15. Expo "feel prototype" of 2 hero interactions | Claude Code, dev build | Live card + reveal on device | Inference (haptics/60 fps can't be judged in HTML) |
| 16. Push built screens back | `/design-sync` push | Canvas matches code | Two-way sync |

**Six business questions for step 1 (Recommendation):** Who exactly is the first user (18–24, which cities, which service)? What job do they hire Jingle for that Spotify/Instagram doesn't do? What is the single magic moment, and how fast must it happen? What does a retained user do daily, weekly, monthly? How does one user bring the next (the loop)? What must Jingle never do (Live honesty, Spotify rules, no tracking, no shaming)?

### Example prompts

**Step 3 — `conventions.md` excerpt for `/design-sync`:**

```text
Night Studio mobile conventions.
- Dark-first; light theme must pass the same contrast tests.
- Coral (--live) is used ONLY for a Live signal younger than 90 seconds. Never decorative.
- At most 3 brand-gradient moments per screen; never on text, chrome or over artwork.
- Album artwork: real only, square, uncropped, no overlays, radius 4px (small) / 8px (large).
  Spotify-sourced items always show the Spotify icon (>=21px) and "Data from Spotify".
- Glass only on navigation chrome (iOS). No glass on Android, none on content.
- Body text uses the platform system font; display uses Bricolage; data labels use mono.
- Every screen ships empty, loading (skeleton), error, offline and degraded states.
- Blip is decorative, never carries information alone.
```

**Step 7 — first direction prompt (Home):**

```text
Design the Jingle mobile Home screen for Android (412x915) and iOS (390x844), dark theme,
using only the Night Studio design system.
User: 20-year-old in Pune, listens on YouTube Music, has 4 friends on Jingle, 1 is Live.
Magic moment: they see Riya's card LIVE (song under 90s old) and tap "Tune in" within 3 seconds.
Content order: listening accessory above the tab bar; Now stage (friends Live first, then Recent
with freshness like "12 min ago on YouTube Music"); today's Drop; Sent to you strip;
Monday reveal banner (show both Monday and non-Monday variants).
Tabs: Home, Circles, Inbox, You. Search top-right. No action tab.
Platform: iOS uses a Liquid Glass tab bar with labels always visible; Android uses the
Material 3 Expressive short navigation bar, no glass.
References attached: Airbuds widget (borrow density of friend cards, not its colours);
Apple Music mini-player accessory (borrow placement); Wrapped 2025 (borrow cassette/sticker
texture only for the reveal banner).
Anti-goals: no purple glow, no gradient text, no glassmorphism on cards, no fake Live,
no text over artwork.
Give me three genuinely different directions (e.g. stacked cards, horizontal shelves,
circle-grouped feed), each with a one-line rationale, then all states: zero friends,
all friends Recent, Ghost mode on, source degraded, offline, loading.
```

**Step 7 — Android notification-access guide:**

```text
Design a 3-screen guided flow that asks an Android user to enable Notification access for
Jingle. Tone: calm, specific, trustworthy, Hinglish-friendly English.
Screen 1 explains: Jingle reads only the song your music app is playing, never messages or
OTPs, and you can turn it off anytime. Include a 3-frame illustration of the system Settings
toggle. Primary: "Open settings". Secondary: "Use Last.fm instead".
Screen 2 is the return state: detecting... then success = the user's own card
"You're Live" with the current song (real artwork placeholder, square, uncropped).
Screen 3 is the OEM step for Xiaomi, Vivo, Oppo: 2-4 manufacturer-specific steps
with a "Done" checklist and "Skip for now".
Also show the failure state (not granted) and the later "Jingle lost your music signal" Home card.
```

**Step 10 — critique prompt:**

```text
Critique this direction before we iterate. Check against: (1) the Night Studio conventions,
(2) WCAG 2.2 AA including 200% text and Reduce Transparency, (3) the coral-only-for-Live rule
and the 3-gradient budget, (4) the AI-slop list (Inter everywhere, purple gradients, glow,
decorative glass, generic copy), (5) 44pt/48dp targets and thumb reach.
List violations with the element, the rule, and a fix. Then apply the fixes.
```

**Step 13 — motion spec prompt:**

```text
For the Monday reveal flow, write a motion and haptics spec table: trigger, frequency class
(rare/occasional/frequent/100+ a day), property animated (transform/opacity only),
duration or spring (bounce 0.1-0.3), stagger, haptic (iOS generator / Android constant),
and the Reduce Motion fallback. Artwork may move as a frame but is never animated,
cropped or overlaid.
```

**Step 14 — hand-off instruction to Claude Code:**

```text
Hand off the Home, Onboarding (Android + iOS), Circle, Weekly reveal and Daily Drop flows.
Target: Expo SDK 57 app in apps/mobile using expo-router, Reanimated 4, FlashList v2,
expo-image with ThumbHash, tokens from packages/design-tokens (generated tokens.ts).
Translate HTML to React Native primitives; do not copy DOM components.
Create one ticket per screen with: states list, data contract (OpenAPI operation ids),
motion rows, haptics rows, accessibility labels, and the Gherkin acceptance criteria.
Flag anything that needs a native module (Android listener, Glance widget, expo-widgets).
```

### Avoiding slop in practice (Recommendation)

Ground every prompt in the synced system; ask for three divergent directions and kill two; attach references with an explicit "borrow / don't borrow" note; demand every state; run the critique prompt each round; keep a "taste log" of what was rejected and why so the next prompt inherits it; and never let generated imagery stand in for Blip or for real artwork. One Brilliant customer reported complex pages needing 2 prompts in Claude Design versus 20+ elsewhere ([Anthropic](https://www.anthropic.com/news/claude-design-anthropic-labs)) — vendor-reported, but consistent with the value of grounding.

---

## 10. Roadmap, quality bars and KPIs

Durations are estimates for a small team (Recommendation); gates are what matters.

| Phase | Weeks (est.) | Milestones | Quality bar to exit |
|---|---|---|---|
| 0. Define | 1–2 | Six answers, magic moment, activation metric, Play notification-listener policy confirmed in Play Console, Meta App ID, deep-link domain | Founder sign-off on §11 decisions |
| 1. Design | 3–5 | `/design-sync`, DESIGN.md, 5 core flows in Claude Design with all states, two 5-user rounds, motion/haptics spec, Blip model sheet commissioned | ≥4/5 users reach a friend card unaided; no critical a11y issues |
| 2. Foundations | 4–6 | Expo app shell, auth (Apple/Google/phone), tokens.ts, Home/Inbox/You read paths, offline cache, push, deep links, CI/CD, observability | Cold start <2 s mid-range Android; crash-free sessions ≥99.5% internal |
| 3. Capture + widgets | 4–6 | Android listener module + OEM guide, Last.fm/Apple routes, Live honesty enforcement, Friends Live widget (iOS + Android), Drop widget | Live accuracy: 0 false-Live in audit; listener survival ≥24 h on Xiaomi/Vivo/Oppo test devices |
| 4. Circles + rituals | 4–6 | Circles, playlists + export, Daily Drop, Monday reveal (Rive), share cards, invite loop with web preview | Reveal share flow under 3 taps; WCAG 2.2 AA audit passed |
| 5. Closed beta (India) | 4–6 | Play closed testing + TestFlight, 3–5 college/city circles, ambassador seeding | Activation ≥35% of installs; D7 ≥20% |
| 6. Public launch | — | Play first (hero platform), App Store same window | Crash-free ≥99.8%; ANR below Play bad-behaviour thresholds; store ratings ≥4.5 in beta |
| 7. v1.1+ | ongoing | Live Activities (sessions, countdown), circle widget, listen-together polish, passkeys, Hindi UI, Spotify extended quota application at scale | KPI-driven |

**KPIs (Recommendation; benchmarks are aggregator-level and conflict).** UXCam puts social-app medians at 40% D1, 18% D7, 12% D30, with over 15% D30 "excellent" ([UXCam](https://uxcam.com/blog/mobile-app-retention-benchmarks/)), while Business of Apps reports a far lower 26.3/9.3/3.9 ([Business of Apps](https://www.businessofapps.com/guide/mobile-app-retention/)); Amplitude places a product in the top quartile at 7% day-7 return ([Amplitude](https://amplitude.com/blog/7-percent-retention-rule)). Jingle targets: **D1 ≥40%, D7 ≥20%, D30 ≥15%, DAU/MAU ≥30%** (Airbuds parity); activation (§2) ≥40% of installs within 7 days; median time-to-own-card <60 s; ≥50% of activated users with a widget installed; push opt-in ≥60% Android / ≥55% iOS; Monday reveal open rate ≥50% of WAU and share rate ≥10% of openers; invites sent per activated user ≥2; false-Live incidents = 0; notification disable rate <5% per month.

---

## 11. Risks and open decisions for the founder

| # | Risk or decision | Why it matters | Recommendation |
|---|---|---|---|
| 1 | Play policy for notification access is unverified | It is the core Android capture path | Confirm in Play Console in Phase 0; prepare declaration and disclosure video |
| 2 | iOS can't show Live for YouTube Music/Amazon | iOS users in India mostly on YT Music get a weaker product | Be explicit in onboarding; lean on Last.fm and the desktop extension; market Android as the hero |
| 3 | Spotify 5-user cap | Spotify-native Live unavailable at launch | Last.fm route; apply for extended quota only after 250k MAU |
| 4 | Empty network / cold start | Airbuds says the product is empty without friends | Launch circle-by-circle in colleges/cities; invite-first onboarding; labelled demo circles |
| 5 | Brand gradient is violet→cyan; body font is Inter | Both appear on the "AI slop" list | Decide: keep gradient but enforce the 3-moment budget and test a warmer variant; move body text to system fonts |
| 6 | Artwork radius conflict (UX spec 12 px vs 4/8 px) | Spotify guideline breach risk | Adopt 4/8 px everywhere on mobile |
| 7 | Is a moving artwork frame "animated artwork"? | Brand rule interpretation | Founder ruling needed |
| 8 | OEM battery killers | Listener dies silently | Guided OEM setup, disconnection detection, honest Degraded state |
| 9 | Notification fatigue in India | No sourced tolerance data | Start conservative caps; measure disable rate weekly |
| 10 | Streaks causing anxiety | Snapchat backlash precedent | Circle-level, opt-in, freezes, no paid restore — or no streaks at all (decision) |
| 11 | Deferred deep-link reliability on iOS | Invite context lost on install | Clipboard code fallback; measure; Branch if needed |
| 12 | Claude Design limits and RN gap | Design sprint stalls; HTML ≠ RN | Max/Team plan for the sprint; Expo feel-prototype step |
| 13 | AI-generated assets not ownable | IP risk for Blip | Human-authored master, provenance log |
| 14 | DPDP May 2027 obligations | Compliance by default | Build the §8 checklist into Phase 2 |
| 15 | Hindi/Hinglish localisation not researched | India-first promise | Commission copy research; Devanagari font check |
| 16 | Which platform launches first | Resource focus | Recommend Android-first public launch with iOS in the same quarter |
| 17 | Monetisation not researched | Airbuds testing subscriptions; Locket profitable with 100K+ payers ([TechCrunch](https://techcrunch.com/2025/08/06/photo-sharing-app-locket-is-banking-on-a-new-celebrity-focused-feature-to-fuel-its-growth)) | Defer; never paywall Live honesty, privacy or streak recovery |

**Research gaps that remain:** no first-party retention data from any competitor; no Airbuds or Locket screen-by-screen captures; no verified Live Activity limits, Glance, App Intents or share-extension specifics; no primary Play notification-listener text; Sentry, PostHog, Maestro/Detox and Expo Notifications features not verified; Apple Music, YouTube Music and store-badge brand rules not fetched; no India-specific push, OTP or language data.

---

## Conclusion

The research reframes Jingle's mobile app from "the web app on a phone" to **an Android-first ambient social layer whose honesty is the product**. Spotify's 2026 moves and its 5-user API cap remove the obvious Spotify-centred path, but they leave open exactly what Indian young adults need: YouTube Music visibility, small circles and weekly shared moments — and only Android can deliver the first legally on the phone. That makes the notification-access screen, the OEM guide and the widget more important to Jingle's success than any visual flourish, and it makes Play policy confirmation the first task, not the last.

The second shift is that "premium" is mostly restraint backed by craft: no motion on frequent actions, springs only where earned, coral only when true, artwork untouched, and one rare, beautifully choreographed Monday moment that people want to share. Claude Design is well suited to reaching that bar quickly if it starts from the synced Night Studio system, is forced through divergent options, full state coverage and real-user rounds, and hands off to an Expo build that is judged on a device, where haptics and 60 fps feel can actually be tested.
