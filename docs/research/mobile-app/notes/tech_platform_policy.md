# Jingle Mobile Apps: Technical Stack, Platform Capabilities and Store Policy (researched 2026-10-03)

Scope note: about 20 search/fetch calls. Items marked "UNVERIFIED" or listed under Gaps were not confirmed against a primary source in this pass. Several facts in the brief are now out of date. See "CHANGED SINCE BRIEF" flags.

## Q1. Framework choice (Expo/React Native vs Flutter vs native vs KMP/CMP)

### Takeaway
For a small team that already ships React 19/TypeScript, Expo + React Native (New Architecture only) is the current low-risk default. As of mid-2026 Expo has stable first-party iOS widgets and Live Activities written as React components (SDK 56), React Native 0.86 / React 19.2 (SDK 57), and Reanimated 4.5. The Android Glance/widget story and the native modules Jingle needs (NotificationListenerService, MediaSession) will still be custom Kotlin, written as Expo Modules.

### Cited Findings
- Expo SDK 54 (10 Sep 2025, RN 0.81) was the last SDK with Legacy Architecture support. Reanimated v4 and FlashList v2 support only the New Architecture. Reanimated 4 needs the separate `react-native-worklets` package. Precompiled XCFrameworks cut clean iOS builds (RNTester) from about 120 s to about 10 s. — [Expo SDK 54 changelog](https://expo.dev/changelog/sdk-54); [expo/fyi reanimated note](https://github.com/expo/fyi/blob/main/expo-54-reanimated.md)
- React Native 0.82 (Oct 2025) removed the Legacy Architecture entirely. The 2025 State of RN survey reports more than 80% of developers on or moving to the New Architecture. — [Callstack RN Wrapped 2025](https://www.callstack.com/blog/react-native-wrapped-2025-a-month-by-month-recap-of-the-year) (secondary)
- Expo SDK 57 (30 Jun 2026): RN 0.86, React 19.2, reanimated 4.3→4.5, worklets 0.8→0.10, gesture-handler 2.32. expo-image gains cache seeding/reading. expo-router gets `Stack.Toolbar.Badge` on Android. Opt-in scene-based lifecycle for the iOS 27 SDK. Continuous Native Generation (CNG) now clears and regenerates native dirs by default. Hermes V1 memory regression fixed in 57.0.9 and startup regression in 57.0.17. Expo is moving to more frequent non-breaking SDKs. SDK 54 gets critical fixes until about Sep/Oct 2026. — [Expo SDK 57 changelog](https://expo.dev/changelog/sdk-57)
- `expo-widgets`: alpha in SDK 55, stable in SDK 56. It builds iOS home-screen widgets and Live Activities as React components via `@expo/ui`. The config plugin generates the Widget Extension target and App Group at prebuild. Live Activity layout slots: Lock Screen banner, Dynamic Island compact (leading and trailing), minimal, and expanded (leading, center, trailing, bottom). It also supports interactive buttons and toggles, configurable widgets, and listening for push-to-start tokens. Live Activities can be updated from the server via APNs or from the app. — [Expo blog: widgets stable in SDK 56](https://expo.dev/blog/ios-widgets-and-live-activities-in-expo); [Expo blog: widgets and Live Activities](https://expo.dev/blog/home-screen-widgets-and-live-activities-in-expo); [Expo Widgets docs](https://docs.expo.dev/versions/latest/sdk/widgets/); [Expo on X](https://x.com/expo/status/2029242117869191188)
- Shopify migrated Shopify Mobile and Shopify POS to the New Architecture while keeping weekly releases. — [Shopify Engineering](https://shopify.engineering/react-native-new-architecture)
- Meta runs Fabric and TurboModules in production. Vercel built its v0 iOS app with Expo and RN. — [Callstack / search summary via Shopify and Callstack results](https://www.callstack.com/blog/react-native-wrapped-2025-a-month-by-month-recap-of-the-year) (secondary)
- New Architecture guide (Expo). — [Expo docs](https://docs.expo.dev/guides/new-architecture/)

### Inferences
- Code sharing: with RN, Jingle can share TypeScript types, the generated OpenAPI client, TanStack Query hooks, Zod schemas, the Socket.IO client logic and design tokens (`packages/design-tokens`) with `apps/web`. It cannot share DOM components. Flutter and native would share none of this. KMP shares Kotlin logic but not the existing TS.
- Recommended shape: Expo (latest SDK, at least 56) + expo-router + Reanimated 4 + Skia (Pulse, visualisers) + expo-image + FlashList v2. Add custom Expo Modules for (a) the Android NotificationListener/MediaSession bridge, which ports the existing Kotlin code, and (b) Android Glance widgets. Keep a native escape hatch through CNG config plugins.
- Native SwiftUI + Compose gives the best per-platform polish but needs two codebases plus web. That is hard to justify for a small team. Flutter's Impeller is smooth but shares nothing with the TS stack.

### Gaps
- No verified 2025–2026 primary sources gathered for Flutter (Impeller status, widget/Live Activity packages) or Compose Multiplatform iOS stability. Discord's and Bluesky's RN engineering posts were not fetched. Treat named app examples beyond Shopify, Meta and Vercel as unverified.
- Android home-screen widgets in Expo: no first-party Expo solution was confirmed. The community `react-native-android-widget` and `expo-apple-targets` (Evan Bacon) were not verified in this pass.

## Q2. iOS: what can an app legally know about what the user is playing?

### Takeaway
On iOS there is no public API that reveals what Spotify, YouTube Music or Amazon Music is playing. `MPNowPlayingInfoCenter` only publishes your own app's now-playing info, and reading other apps' state needs private APIs, which the guidelines forbid. The legal iOS signals are: Apple Music via MusicKit (system player state plus the recently-played API), Spotify via the Web API (currently-playing / recently-played, server-side) or the iOS SDK App Remote (needs the Spotify app installed, playing and connected), Last.fm scrobbles, and ShazamKit (mic-based recognition only with explicit user action). This means "Live" on iOS for Spotify must come from server-side polling of the Spotify Web API, and on iOS it is impossible for YouTube Music and Amazon Music.

### Cited Findings
- The Spotify iOS SDK provides auth, shuffle playback for Free users, on-demand playback for Premium, and real-time player state updates through `SPTAppRemotePlayerStateDelegate`. Music must be playing when you connect, and iOS apps stay active in the background only for a few seconds unless they are doing navigation or audio. — [Spotify iOS SDK docs](https://developer.spotify.com/documentation/ios); [Getting started](https://developer.spotify.com/documentation/ios/getting-started); [spotify/ios-sdk GitHub](https://github.com/spotify/ios-sdk)
- The `app-remote-control` scope is limited to the iOS/Android SDKs. A Spotify community thread says remote playback via app-remote-control is not allowed for commercial apps under certain conditions. — [Spotify scopes](https://developer.spotify.com/documentation/web-api/concepts/scopes); [Spotify community thread](https://community.spotify.com/t5/Spotify-for-Developers/Remote-playback-SDK-and-commercial-SDA-question/td-p/6662045) (community, not policy text)
- **CHANGED SINCE BRIEF:** Spotify Development Mode now requires the developer to have Premium and allows only **5** users per app, down from 25. This applies to new apps from 11 Feb 2026 and existing apps from 9 Mar 2026. Extended quota (since Mar 2025) requires a registered business, 250k MAU, availability in key Spotify markets and a launched service. — [TechCrunch 2026-02-06](https://techcrunch.com/2026/02/06/spotify-changes-developer-mode-api-to-require-premium-accounts-limits-test-users/)
- Apps may use only public APIs. Public `MPNowPlayingInfoCenter` usage is for an app to manage its own now-playing info. — [Apple dev forums, media-player tag](https://developer.apple.com/forums/tags/media-player) (search summary; no explicit Apple statement found)
- Apple DTS says the "Recently Played" app list in system UI comes from SiriKit media intents and donated interactions. There is no API to read the cross-app history. — [Apple forum thread 809554](https://developer.apple.com/forums/thread/809554)
- Guideline 2.5.4: background services may be used only for their intended purposes (VoIP, audio playback, location, task completion, local notifications). Guideline 4.2.3(i): the app should work on its own without requiring another app. — [App Store Review Guidelines](https://developer.apple.com/app-store/review/guidelines/)

### Inferences
- iOS Jingle cannot run a background "listener". Live comes from server polling (Spotify Web API currently-playing, Last.fm `nowplaying`) and from MusicKit on-device while the app is foregrounded. Recently played (Apple Music API) only supports Recent and Top cards, not Live.
- Because of 4.2.3(i), App Remote features must be optional. Jingle must be useful without Spotify installed.
- The 5-user Development Mode cap makes Spotify effectively unusable for a public launch until Jingle qualifies for extended quota (250k MAU). Plan for Last.fm, the companion extension, the Android listener and Apple Music as primary sources.

### Gaps
- `MPMusicPlayerController.systemMusicPlayer` behaviour (nowPlayingItem visible only for Apple Music / the local library) and the MusicKit `recent/played` endpoint limits were not re-verified in this pass. ShazamKit policy was not fetched.

## Q3. Android: NotificationListenerService / MediaSession, background limits, OEM killers

### Takeaway
`MediaSessionManager.getActiveSessions()` with a NotificationListener component works legally on Android and is Jingle's only phone-side cross-app now-playing signal. Three constraints apply: (1) Play policy scrutiny of notification access (the details are not confirmed from a primary Play page), (2) Android 13+ "Restricted settings" blocks enabling notification access for sideloaded APKs, so distribute via Play, and (3) aggressive OEM killers (Xiaomi, Vivo, Oppo), which need in-app guided setup.

### Cited Findings
- Android 13 Restricted Settings stops users from easily enabling Accessibility or Notification Listener for sideloaded apps. Android 15 adds Enhanced Confirmation Mode, which also covers apps installed via session-based installers that are not stores. The covered roles and permissions include Notification listener and Usage access. — [XDA](https://www.xda-developers.com/android-13-restricted-setting-notification-listener/); [Android Authority](https://www.androidauthority.com/android-15-restricted-settings-sideloading-3481098/); [9to5Google](https://9to5google.com/2024/09/12/android-15-sideloaded-apps-restrictions/)
- Play notification-listener policy: a search summary says notification listener is "high-risk/restricted". It lists allowed uses (relaying to wearables, aggregating notifications, alternate UIs such as widgets and launchers) and disallowed uses (reading content without explicit consent, hiding other apps' notifications). **UNVERIFIED.** The fetched Play help page "Permissions and APIs that Access Sensitive Information" did not contain notification-listener text. — [Play Console Help 16558241](https://support.google.com/googleplay/android-developer/answer/16558241); [Play: restricted permissions with minimum-scope alternatives](https://support.google.com/googleplay/android-developer/answer/16935362); [AOSP notification access](https://source.android.com/docs/automotive/hmi/notifications/notification-access)
- Android 15 (API 35): dataSync FGS limited to 6 h per 24 h, after which `onTimeout()` is called. BOOT_COMPLETED receivers cannot start dataSync, mediaPlayback, camera, mic or phoneCall FGS. New `mediaProcessing` type (also 6 h per 24 h). Android 16: jobs started from an FGS must respect runtime quotas. Android 14 requires FGS types to be declared. — [Android 15 behavior changes](https://developer.android.com/about/versions/15/behavior-changes-15); [FGS timeouts](https://developer.android.com/develop/background-work/services/fgs/timeout); [FGS types required (A14)](https://developer.android.com/about/versions/14/changes/fgs-types-required); [FGS changes](https://developer.android.com/develop/background-work/services/fgs/changes)
- Play target API: since 31 Aug 2026, new apps and updates must target API 36 (Android 16). Extension requests were possible to 1 Nov 2026. Existing apps below API 35 become invisible to new users on newer devices. — [Play target API requirements](https://support.google.com/googleplay/android-developer/answer/11926878?hl=en)
- OEM killers: Xiaomi/MIUI/HyperOS settings ("Background autostart") can reset after reboot. Vivo needs manual autostart and "High background power consumption". Oppo/ColorOS "background freeze" kills services when the screen turns off, and the advice includes a startup-manager allowlist, disabling battery optimisation and a persistent notification. — [dontkillmyapp Xiaomi](https://dontkillmyapp.com/xiaomi); [dontkillmyapp Oppo](https://dontkillmyapp.com/oppo); [Biolovision per-brand guide](https://help.biolovision.net/Keep_Background_Services_Alive_on_Android_(by_Brand))

### Inferences
- A NotificationListenerService is bound by the system and does not need a foreground service. Do not add an FGS just to stay alive. Pushes to `/ingest/1/submit-listens` should use WorkManager (expedited) with batching, which avoids the dataSync 6 h cap and Android 16 job quotas.
- Detect when the listener is disconnected (`onListenerDisconnected` → `requestRebind`). Show an OEM-specific "Keep Jingle connected" checklist, which matters for India where these OEMs dominate. Show Live only when the last MediaSession update is under 90 s old.
- In the Play listing and the in-app prominent disclosure, describe the use as "show what you're playing to friends and in widgets". Read only MediaSession metadata from an allowlist of music packages and never read notification text.

### Gaps
- No primary Play policy text was found confirming whether a Permissions Declaration Form is required for `BIND_NOTIFICATION_LISTENER_SERVICE`. Verify in Play Console before launch.

## Q4. Store policies: 4.2 web wrappers, Play webview and spam rules, privacy labels, ATT, Data safety, DPDP

### Takeaway
The current WebView-wrapper Android app is a 4.2 / minimum-functionality risk on both stores. The production app needs native navigation, offline cache, push, widgets, share and native capture. India's DPDP Rules were notified 13 Nov 2025, with substantive obligations due 13 May 2027.

### Cited Findings
- Guideline 4.2 says the app should "elevate it beyond a repackaged website". 4.2.2 excludes web clippings, content aggregators and link collections. 5.1.1(v) requires in-app account deletion when account creation exists. 5.1.2(i) requires ATT permission to track. 4.8 says a third-party social login must be paired with an equivalent privacy-preserving login (name and email only, hide-my-email, no ad tracking). — [App Store Review Guidelines](https://developer.apple.com/app-store/review/guidelines/)
- Practitioner reports say Apple tightened 4.2 around 2021 and that it became the most common rejection reason by 2023–24. The recommended fix is wiring native capabilities (offline, widgets, notifications, share) into the core loop. — [MobiLoud](https://www.mobiloud.com/blog/app-store-review-guidelines-webview-wrapper/); [vp0](https://vp0.com/blogs/fix-app-store-rejection-4-2-minimum-functionality) (secondary)
- Google Play Spam policy bars apps whose primary purpose is a webview of a website without the owner's permission. Minimum-functionality rules bar static or very low-content apps. The policy was uplifted 17 Jul 2024. — [Play Spam policy](https://support.google.com/googleplay/android-developer/answer/9899034); [Play policy announcement Jul 2024](https://support.google.com/googleplay/android-developer/answer/14993590)
- DPDP Rules 2025 were notified 13 Nov 2025. Rules 1, 2 and 17–21 (Data Protection Board) applied immediately. The Consent Manager framework (Rule 4) applies from 13 Nov 2026. Most obligations (Rules 3, 5–16, 22, 23: notice, security, breach, retention, children's data, etc.) apply from 13 May 2027. — [Wikipedia: DPDP Rules 2025](https://en.wikipedia.org/wiki/Digital_Personal_Data_Protection_Rules,_2025); [Lexology](https://www.lexology.com/library/detail.aspx?g=bbd416e3-04a5-4f77-a83b-76a01aeda951)

### Inferences
- Jingle only loads its own domain, so the Play spam clause on webviews of other sites is not the issue. Minimum functionality is. Either way, ship a native-UI app rather than a wrapper.
- If Jingle collects no data for cross-app tracking, it does not need the ATT prompt. Its Apple privacy label still lists Contacts? (only if used), User Content, Identifiers and Usage Data (listening history) as linked to the user. On Play, declare that the Data safety listening/music-activity data is collected and shared with friends, plus account deletion URL.
- For DPDP: children's data rules (verifiable parental consent for under-18s) take effect May 2027, so the age gate design matters now.

### Gaps
- Apple privacy-label and Play Data-safety category definitions were not fetched. DPDP children's-data rule specifics and Significant Data Fiduciary thresholds were not verified.

## Q5. Widgets, Live Activities, App Intents, share and Instagram Stories, deep links

### Takeaway
iOS widgets and Live Activities are feasible inside Expo (expo-widgets, stable SDK 56). Instagram Stories sharing needs a registered Meta App ID passed as `source_application`. Firebase Dynamic Links is dead (links 404 since 25 Aug 2025), so use Universal Links/App Links on a Jingle domain plus a deferred deep-link vendor or a home-grown solution.

### Cited Findings
- expo-widgets: see Q1. Push-to-start tokens and APNs updates are supported. — [Expo Widgets docs](https://docs.expo.dev/versions/latest/sdk/widgets/)
- Instagram/Facebook Stories: the app writes the image or sticker to `UIPasteboard` (`com.instagram.sharedSticker.backgroundImage` etc.) with `source_application` set to the Meta App ID, then opens `instagram-stories://share?source_application=<id>`. Shares without a registered App ID are rejected ("The app you shared from doesn't currently support sharing to Stories"). Facebook validates the ID strictly. — [Medium: story sharing in iOS apps](https://medium.com/@burakekmen/story-sharing-on-facebook-instagram-in-ios-apps-2df2a82ebf96); [react-native-share issue #1304](https://github.com/react-native-share/react-native-share/issues/1304) (secondary; Meta's own doc not fetched)
- Firebase Dynamic Links shut down 25 Aug 2025. All FDL links (page.link and custom domains) return HTTP 404, and the APIs are gone. Firebase email-link auth needs SDK upgrades. — [Firebase FDL deprecation FAQ](https://firebase.google.com/support/dynamic-links-faq). Note: one vendor blog claims old links "continue to redirect", which contradicts Google's FAQ. Trust the FAQ. — [chottulink](https://chottulink.com/blog/firebase-dynamic-links-shut-down-5-best-alternatives-for-2026/)
- Google's recommended replacements: Adjust, Airbridge, AppsFlyer, Bitly, Branch, Kochava, Singular. Native Universal Links and App Links do not provide deferred deep linking. — [Airbridge](https://www.airbridge.io/en/blog/firebase-dynamic-links-alternatives); [AppsFlyer](https://www.appsflyer.com/blog/mobile-marketing/fdl-deprecation-deep-linking/); [Dub](https://dub.co/blog/firebase-alternative)

### Inferences
- For circle invites, use Universal Links/App Links on `jingle.<domain>/c/<code>`. The fallback web page should carry the invite code. A cheap, privacy-preserving deferred path: copy the invite code on tap (clipboard) or ask "Have an invite code?" in onboarding. On Android use the Play Install Referrer. A paid MMP is optional.
- Live Activity idea: a "Listening together" session or "friend is Live" activity updated via APNs. Respect Apple's limits on Live Activity duration and update frequency (not verified here).

### Gaps
- App Intents, Shortcuts, Glance (Android widgets) and share extension specifics were not researched in this pass. Meta's official Sharing to Stories doc was not fetched.

## Q6. Push, realtime, offline, images, OTA, crash and analytics, CI/CD, testing, costs

### Takeaway
EAS Update is App Store–compliant for JS/asset changes under DPLA 3.3.1(B) as long as the app's purpose does not change. Native changes still need store builds. EAS pricing starts free (1k MAU for updates). Most other items in this question were not researched in depth in this pass.

### Cited Findings
- DPLA 3.3.1(B) lets interpreted code be downloaded only if it does not change the app's primary purpose, does not bypass signing, sandbox or security, and does not create a storefront. EAS Update ships JS and assets, not native code. — [Medium summary of 2.5.2 / 3.3.1(B)](https://jackappdev.medium.com/does-apple-allow-ota-updates-on-ios-guideline-2-5-2-fc1030f07e20); [Bitrise compare](https://bitrise.io/resources/compare/bitrise-codepush-vs-expo-eas-update)
- Guideline 2.5.2 bars downloading code that "introduces or changes features or functionality". — [App Store Review Guidelines](https://developer.apple.com/app-store/review/guidelines/)
- EAS Update plans (third-party summary): Free with 1,000 MAU and 100 GiB bandwidth. Starter $19/mo with 3,000 MAU. Production $199/mo with 50,000 MAU. Enterprise is custom. Overage is $0.10/GiB bandwidth and $0.05/GiB storage. — [Stallion EAS pricing](https://stalliontech.io/expo-eas-update-pricing) (secondary; confirm on expo.dev/pricing)
- Microsoft App Center / CodePush retired (Mar 2025). Bitrise offers a CodePush-compatible replacement. — [Bitrise](https://bitrise.io/resources/compare/bitrise-codepush-vs-expo-eas-update) (secondary)

### Inferences
- Socket.IO on iOS drops when backgrounded. Use push (APNs/FCM) for out-of-app events. On foreground, reconnect and refetch versioned state (matches the existing gateway design). Persist the TanStack Query cache to MMKV for instant cold start.

### Gaps
- Not verified in this pass: Expo Notifications current features (rich and grouped notifications, Android channels), Sentry RN/Expo integration, PostHog RN SDK and feature flags, Maestro vs Detox status, EAS Build/Submit pricing, and the Fastlane role. These need a follow-up pass with primary docs.

## Q7. Brand and attribution rules (Spotify, Apple, Google)

### Takeaway
Spotify metadata and artwork must always carry Spotify branding. Artwork must not be cropped, overlaid or covered, and its corner radius is capped. Apple and Google badge rules were not fetched in this pass.

### Cited Findings
- Any Spotify metadata (artist, album or track names, artwork, playback) must be accompanied by the Spotify logo or icon. Use the full logo (icon + wordmark) in integrations, at a minimum of 70 px (icon alone at least 21 px). Artwork must not be cropped, have text or images overlaid, be covered by controls or carry your logo. Corner radius is 4 px on small and medium devices and 8 px on large ones. Your logo must not resemble Spotify's (green, circle, waves) or use Spotify trademarks in your name. — [Spotify Design & Branding Guidelines](https://developer.spotify.com/documentation/design)
- Spotify Developer Policy (ML-training ban, deletion obligations, attribution), from the brief. — [Spotify Developer Policy](https://developer.spotify.com/policy); [Compliance tips](https://developer.spotify.com/compliance-tips)

### Inferences
- Jingle cards that show Spotify artwork can't use blurred-artwork-with-overlay hero treatments. Keep Spotify content visually separated (the design-system rule already exists) and set card artwork radius to at most 8 px.

### Gaps
- Apple Music identity guidelines ("Listen on Apple Music" badge, artwork rules), "Download on the App Store" and "Get it on Google Play" badge rules, and YouTube Music branding were not fetched in this pass.
