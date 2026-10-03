# Onboarding and activation patterns of popular consumer mobile apps (2024–2026), for Jingle's mobile app

Researched 2026-10-03. About 20 searches and fetches. Source quality is uneven. Primary or near-primary sources: TechCrunch, Apple WWDC, FIDO Alliance, Amplitude, the Lancaster University study, First Round Review. Some stats come from vendor or aggregator blogs (Pushwoosh, Airship, Batch, MobiLoud, relaunch.ai, social-login vendor blogs, India cost blogs). These are flagged inline. Treat them as directional, not authoritative.

## 1. How the named apps onboard (step counts, order, contacts, invites)

### Takeaway
The fastest-growing social apps of 2022–2025 (Airbuds, Locket, Gas, Threads, Partiful) share three traits:
- **One core setup action.** Airbuds: connect a streaming service, then add friends. Threads: log in with Instagram, then follow all. Locket: add friends, then add the widget.
- **Existing identity or graph data reused.** Instagram graph, phone contacts, school lists.
- **A built-in invite loop.** Features are gated on inviting, or the invite works without an install.

Content apps take a different route: TikTok and Duolingo show value before sign-up.

### Cited Findings
**Airbuds (closest analogue to Jingle: a real-time "what friends are streaming" widget)**
- Setup is "you just connect your Spotify, and then every time you're going to listen to something on Spotify, it's going to be shared on Airbuds in real time." — [TechCrunch, Sep 2025](https://techcrunch.com/2025/09/17/airbuds-is-the-music-social-network-apple-and-spotify-wish-they-had-built/)
- Supported sources: Spotify, Apple Music, SoundCloud, Musi, Deezer, Amazon Music, Audiomack. — [TechCrunch](https://techcrunch.com/2025/09/17/airbuds-is-the-music-social-network-apple-and-spotify-wish-they-had-built/)
- Scale: 15M+ downloads, 5M MAU, 1.5M DAU, 96% positive rating sentiment over 9,400+ ratings in 30 days. Core users are US high-school and college students. Secondary markets: UK, Australia, Brazil, Mexico. — [TechCrunch](https://techcrunch.com/2025/09/17/airbuds-is-the-music-social-network-apple-and-spotify-wish-they-had-built/); [Music Ally](https://musically.com/2025/09/18/social-music-app-airbuds-has-1-5m-daily-users-and-5m-of-funding/)
- **Invite gating:** users must invite friends to see more than their top 3 artists in the Weekly Recap. The co-founder says the app "only really works if you add your friends." — [TechCrunch](https://techcrunch.com/2025/09/17/airbuds-is-the-music-social-network-apple-and-spotify-wish-they-had-built/)
- About 30% of users engage with features beyond basic stream sharing: reactions with emoji, stickers or selfies, DMs, ghost mode, Weekly Recap, school-based top artists, customisable profiles. — [TechCrunch](https://techcrunch.com/2025/09/17/airbuds-is-the-music-social-network-apple-and-spotify-wish-they-had-built/)
- The widget is "featured prominently during onboarding." The Weekly Recap (every Sunday) is pitched as a "pocket-sized Spotify Wrapped." Growth came through a college ambassador program and student TikToks. — [Consumer App Lab](https://consumerapplab.substack.com/p/inside-airbuds-the-app-that-grew); [Airbuds Ambassadors](https://airbuds-fm.webflow.io/)
- A 2026 profile describes onboarding as centred on "link your streaming service and find friends. Without them, there is nothing to see." — [Techweez, Jun 2026](https://techweez.com/2026/06/12/airbuds-the-app-that-turns-your-music-into-a-social-feed/)

**Locket Widget**
- Requires contacts and camera access. A case study critiques full address-book access as not privacy-centric and suggests standalone invites instead. — [Medium case study](https://medium.com/@siddhisonwalkar1/locket-product-case-study-e79e0823070c)
- Growth came from TikTok: the founder's video got about 100k views in days. Locket then partnered with hundreds of creators for 100M+ to 250M views. The app reached 9M+ DAU. The founder's podcast argues onboarding "might not matter as much as you think (in the early days)." — [Retention podcast / Substack](https://saba.substack.com/p/from-a-gift-for-his-girlfriend-to-d24); [Shortimize](https://www.shortimize.com/blog/locketapps-tiktok-influencer-strategy-for-gaining-250m-views); [TechCrunch 2022 (older)](https://techcrunch.com/2022/01/11/locket-an-app-for-sharing-photos-to-friends-homescreens-hits-the-top-of-the-app-store)

**BeReal** (flow documented by Page Flows; date of capture unclear)
- 9 steps: splash → phone number → OTP verify → name → birthday → username → contact access (priming screen: contacts "only used to connect with friends") → add contacts → enable notifications. — [Page Flows](https://pageflows.com/post/ios/onboarding/bereal/); [Tear Them Down](https://tearthemdown.medium.com/6-product-lessons-from-bereal-including-user-education-36564408b9c6)
- Critique: BeReal asks for contacts right after account creation, before the user has seen any value. — [Tear Them Down](https://tearthemdown.substack.com/p/bereal-product-case-study)
- 23M DAU in Jan 2024. — [TechCrunch](https://techcrunch.com/2024/01/24/bereal-which-now-has-23m-daus-is-onboarding-brands-and-celebs)

**Threads (2023, older but the canonical "import your graph" case)**
- "Log in with Instagram" imports username, bio and photo. Setup takes about 30 seconds. One "follow all" tap re-follows your Instagram follows. Threads hit 100M sign-ups in 5 days. — [TechCrunch 2023](https://techcrunch.com/2023/07/10/instagrams-threads-app-reaches-100-million-users-in-just-five-days/); [Buffer](https://buffer.com/resources/instagram-threads-app/)

**TikTok**
- The feed plays on first open with no account. An interest picker is offered. Sign-up walls appear only on social actions such as following. — [Appcues GoodUX](https://goodux.appcues.com/blog/tiktok-user-onboarding); [Mobbin flow](https://mobbin.com/explore/flows/ff7d14f9-91bf-4ac5-87b6-a986d0824da4)

**Duolingo**
- Users take a lesson before sign-up. Moving sign-up after the first lesson gave about +20% DAU / next-day retention. "Soft walls" (sign-up with a "Later" option) come before a hard wall. — [Taplytics](https://taplytics.com/blog/duolingo-ab-test-onboarding/); [First Round Review](https://review.firstround.com/the-tenets-of-a-b-testing-from-duolingos-master-growth-hacker/)
- A 2026 teardown claims 7 A/B tests and a 9% conversion rate. This is unverified and the source is a vendor blog. — [relaunch.ai](https://relaunch.ai/blog/duolingo-onboarding-teardown-7-b-tests-behind-their-9-conver.html)

**Spotify**
- Flow: email → password → DOB → gender → name → notifications → pick artists (at least 3; some captures say 5). The picker fills Home so it is not empty on first visit. — [Page Flows](https://pageflows.com/post/ios/onboarding/spotify/); [Medium teardown](https://medium.com/@TheAhmadkabir/how-spotify-onboards-new-users-and-what-id-improve-as-a-pm-c05b4eb318df)

**Gas / tbh (Nikita Bier; 2016–2022, older)**
- Gas: pick your school and grade from a location-based list, then sync contacts. "Three-second onboarding that shows value instantly." Launched school by school to create FOMO.
- Results: tbh reached 40% of a pilot school in 48 hours. Gas reached 1M DAU and 30k sign-ups per hour at peak, and sold to Discord. — [Medium summary of Lenny's Podcast](https://medium.com/@illyism/how-to-build-successful-social-apps-lessons-from-nikita-bier-creator-of-tbh-and-gas-11c564ece467); [Wikipedia: Gas](https://en.wikipedia.org/wiki/Gas_(app))
- Bier: "If your app cannot demonstrate value in the first three seconds, it's so over." — [Podcast Notes, Lenny's Podcast](https://podcastnotes.org/lennys-podcast-with-lenny-rachitsky/nikita-bier-how-to-consistently-go-viral-the-playbook-for-winning-at-consumer-apps-lennys-podcast/)

**Partiful**
- Each invite link doubles as a landing page. Guests open it, enter a phone number, RSVP, see the guest list and get SMS reminders. No app install or account is needed. — [Sacra](https://sacra.com/chat/h/ca6c792b-7d6d-42a9-ae5f-0970a819c66c/); [Partiful Help](https://help.partiful.com/hc/en-us/articles/27354346663963-Do-my-guests-need-to-download-the-app)

**Bluesky starter packs**
- Starter packs (one tap follows a curated list) drove up to 43% of new follows during migration waves and about 20% of all follows overall. Only 6.25% of users were ever in a pack.
- Accounts in packs gained 85% more followers. — [Lancaster University study, 2025](https://www.lancaster.ac.uk/news/starter-packs-have-played-a-central-role-in-blueskys-rapid-growth-new-study-shows); [arXiv 2501.11605 via Pith](https://pith.science/paper/2501.11605)
- Caveat: packs get people in once; ongoing feeds are what bring them back. — [Lacuna](https://lacuna.tiptreesystems.com/work/bootstrapping-social-networks-lessons-from-bluesky-starter-packs/wrk_9f3098f2d9f2244814cad10b9f82a105)

### Inferences
- Airbuds is Jingle's direct competitor and has proven the loop: connect a source, add friends, widget on the home screen, weekly recap gated on inviting. Jingle's differences are circles, the daily Drop, listen-together and India focus. Onboarding should be at least as short as Airbuds': connect, then friends.
- The "Threads follow-all" and "Bluesky starter pack" patterns map onto Jingle as "join the circle you were invited to, and follow everyone in it with one tap."
- The "Partiful no-install" pattern maps onto a web landing page for a shared Drop or circle playlist link. People can tap songs and preview the circle before installing.

### Gaps
- No current (2025–26) screen-by-screen captures were retrievable for Airbuds, stats.fm, Lemon8, Arc Search, Instagram or Snapchat. Mobbin and Page Flows are behind login or paywalls, and the fetched pages gave no flows.
- No published step counts or funnel drop-off for Airbuds or Locket.

## 2. Magic moments, and the equivalent for social music

### Takeaway
Classic activation thresholds measure network density, not features. Examples: Facebook's 7 friends in 10 days and Slack's 2,000 messages. For Jingle, the likely equivalent is "the first time you see a friend Live, or get a reaction to your own listening." That needs at least a few connected friends, so cold-start tactics (seeding, invites, starter circles) are the onboarding.

### Cited Findings
- Facebook's activation metric was 7 friends in 10 days. — [Mode](https://mode.com/blog/facebook-aha-moment-simpler-than-you-think/)
- Slack's was 2,000 messages, cited as predicting 93% retention. — [Adam Arant blog](https://adamarant.com/en/blog/saas-activation-metric-the-one-number-that-predicts-retention)
- These are proxies for the real moment: a feed full of relevant friends' updates. — [Medium / Bootcamp](https://medium.com/design-bootcamp/a-simple-approach-to-discover-your-products-aha-moment-9cf5879b8ce7)
- Andrew Chen's "atomic network" is the smallest network where everyone sticks around. Sizes: Zoom 2–3 people, Slack 5–10, Tinder about 500 per campus. Invite-only launches (e.g., LinkedIn) seed dense, high-quality networks. — [Andrew Clark summary of The Cold Start Problem](https://andrewclark.co.uk/product-book-summaries/the-cold-start-problem); [Startup Archive](https://www.startuparchive.org/p/three-case-studies-from-andrew-chen-on-solving-the-cold-start-problem)
- Amplitude benchmark: median product day-1 activation is about 5%, versus about 21% for the top 10%. Getting 7% of a cohort back on day 7 puts a product in the top 25%. 69% of top day-7 performers were also top 3-month performers. — [Amplitude Product Benchmark Report](https://info.amplitude.com/rs/138-CDN-550/images/the-product-benchmark-report.pdf); [Amplitude: 7% rule](https://amplitude.com/blog/7-percent-retention-rule)
- Airbuds itself says the product is empty without friends. Its solo hook is the Weekly Recap. — [TechCrunch](https://techcrunch.com/2025/09/17/airbuds-is-the-music-social-network-apple-and-spotify-wish-they-had-built/)
- Spotify's artist picker exists so Home is not empty on first visit. — [Medium teardown](https://medium.com/@TheAhmadkabir/how-spotify-onboards-new-users-and-what-id-improve-as-a-pm-c05b4eb318df)

### Inferences
- **Proposed Jingle activation metric (hypothesis to validate):** source connected, at least 3 accepted friends or 1 circle with at least 3 members within 7 days, and at least 1 social action (react, send a song, or add to a circle playlist).
- **Proposed Jingle magic moment:** within the first session, the user sees a real friend's card (Live, or Recent if not Live). Separately, their own first track appears as "you, now playing" right after connecting. Showing your own Live card instantly proves the connection worked even with zero friends, much as Airbuds shows your stream in real time.
- **Solo value for an empty network (layered):**
  1. Your own Live card and "your week so far."
  2. A starter recap (Airbuds-style) with partial reveal gated on inviting.
  3. Today's Drop from Jingle or a seeded circle.
  4. Taste-matched suggested people and circles.
  5. Demo circles that are clearly labelled as demos.
- Respect the Live honesty rule: never fake Live for seeded content.

### Gaps
- No published activation thresholds for Airbuds, stats.fm or any social-music app.
- No data found on minimum friend count for retention in widget or ambient-social apps.

## 3. Permission priming on iOS and Android, with opt-in data

### Takeaway
Push opt-in medians are about 50–56% on iOS and about 53–75% on Android after Android 13. Benchmark vendors disagree. Priming before the system prompt and asking in context help, with vendor-reported lifts of 10% up to 2–3x. Contact sync is under structural threat: iOS 18 lets users share only some contacts. Android notification access is a buried Settings toggle, not a dialog, so it needs a dedicated guided screen.

### Cited Findings
**Push notifications**
- Pushwoosh 2025 (600+ apps): iOS about 56%, Android about 75%. — [Pushwoosh](https://www.pushwoosh.com/blog/push-notification-benchmarks/)
- Airship 2026 report: medians of 48.85% on iOS and 53.3% on Android. — [via MobiLoud](https://www.mobiloud.com/blog/push-notification-opt-in-rate/)
- Batch (Jul 2024–Jul 2025): Android 67%, iOS 56%. — [Batch](https://batch.com/ressources/etudes/benchmark-notifications-push-crm-mobile)
- These sources conflict. Android 13's explicit runtime prompt is narrowing the gap with iOS. — [Pushwoosh](https://www.pushwoosh.com/blog/push-notification-benchmarks/)
- Priming lifts (all vendor-reported, weak evidence):
  - "2–3x higher opt-in" with a custom pre-prompt. — [Plotline](https://www.plotline.so/blog/how-to-improve-push-notification-opt-in-rates)
  - +10% when asking after value slides versus at the start. — [ngrow](https://www.ngrow.ai/blog/push-notifications-how-to-maximize-opt-ins)
  - Full-screen primers beat modals. — [PushEngage](https://www.pushengage.com/ios-push-notification-permission/)

**Contacts**
- iOS 18 added Limited contacts access, a two-stage prompt where users choose a subset, and `ContactAccessButton`, which grants individual contacts inline from a search UI. — [Apple WWDC24 "Meet the Contact Access Button"](https://developer.apple.com/videos/play/wwdc2024/10121/)
- Nikita Bier called it "the end of the world" for friend-based social apps. — [Slashdot](https://apple.slashdot.org/story/24/10/02/1744216/did-apple-just-kill-social-apps); [Medium](https://medium.com/@aftab.h.alam/did-apple-just-sink-social-apps-the-ios-18-privacy-change-shakes-up-the-industry-5b88d43862a1)
- Bier cites about a 65% contact approval rate and says "if you are betting on contact sync… start thinking about plan B." — [Podcast Notes](https://podcastnotes.org/lennys-podcast-with-lenny-rachitsky/nikita-bier-how-to-consistently-go-viral-the-playbook-for-winning-at-consumer-apps-lennys-podcast/)
- BeReal's contact primer promises contacts are "only used to connect with friends." — [Tear Them Down](https://tearthemdown.medium.com/6-product-lessons-from-bereal-including-user-education-36564408b9c6)

**Android notification access (`NotificationListenerService`, needed for media sessions)**
- It is granted only on a dedicated system Settings page (Settings → Notifications → Notification access), not a runtime dialog. — [ACM study "Walls Have Ears"](https://dl.acm.org/doi/10.1145/3728898)
- The page shows a warning because the app can read every notification, including OTPs and message previews. — [ptkd](https://ptkd.com/journal/android-notification-listener-service-security); [AOSP policy](https://source.android.com/docs/automotive/hmi/notifications/notification-access)

### Inferences
- **Push:** do not ask at launch. Ask at a moment of intent:
  - after the first friend is added ("Get a ping when Riya goes Live"), or
  - after joining a circle ("Know when the Drop lands at 9 pm").
  Use a full-screen Jingle primer, and only call the OS prompt on "Yes." Re-ask contextually later.
- **Contacts:** treat contact sync as optional. On iOS 18+, design for Limited access by default. Use `ContactAccessButton` inline in "Find friends." Lead with invite links (WhatsApp / Instagram share sheet) and username/QR search.
- **Android notification access:**
  - Build a dedicated guided screen. Explain that Jingle reads only media playback, not messages. Add a short animated walkthrough, then deep-link with `Settings.ACTION_NOTIFICATION_LISTENER_SETTINGS`.
  - On return, detect the grant and immediately show "You're Live" with the current track. That instant proof is the reward for a scary-looking permission.
  - Always offer the Spotify login or Last.fm path as an alternative.

### Gaps
- No published opt-in or drop-off rates for Android notification-access grants.
- No public data on iOS 18 Limited-versus-Full contact share rates beyond Bier's anecdotal 65%.
- Not researched here: Android 13+ "restricted settings" blocking notification-access grants for sideloaded APKs (worth verifying if Jingle distributes APKs outside Play).
- No India-specific push opt-in benchmarks found.

## 4. Sign-in methods: Apple/Google, phone OTP (India), passkeys

### Takeaway
One-tap federated sign-in beats email and password. Passkeys have the strongest primary data (93% login success versus 63% for other methods) but mainly help returning logins, not first sign-up. In India, phone-number identity is the norm. Truecaller one-tap verification removes the SMS OTP step on Android, though cited conversion claims for it come from vendor blogs.

### Cited Findings
- FIDO Passkey Index (Oct 2025; data from Amazon, Google, Microsoft, PayPal, Target, TikTok): 93% passkey login success versus 63% for other methods.
- Google reports 30% higher sign-in success and 20% faster logins. Amazon reports 175M customers with passkeys and "six times faster" sign-in. — [FIDO Passkey Index PDF](https://fidoalliance.org/wp-content/uploads/2025/10/FIDO-Passkey-Index-October-2025.pdf); [ID Tech](https://idtechwire.com/fido-alliance-launches-passkey-index-proving-30-conversion-lift-over-passwords/)
- Social login is said to lift sign-up completion by 20–40% versus email and password. Spotify is said to have 80% of new users using Facebook or Google login. Both claims come from vendor/agency blogs and are unverified. — [Dogtown Media](https://www.dogtownmedia.com/social-login-for-mobile-apps-google-apple-linkedin-boosting-sign-up-conversion-by-removing-friction/); [Appy Pie](https://www.appypie.com/blog/social-login-for-apps)
- Truecaller SDK: a one-tap consent sheet returns a verified phone profile with no SMS. Truecaller claims 180M+ active users in India and up to 90% lower verification costs (vendor claims). — [NamoID](https://namoid.in/blog/truecaller-verification-sdk-integration); [Startup India / Truecaller](https://www.startupindia.gov.in/content/sih/en/reources/resource-partners/application-based-services/Truecaller_New.html)
- OTP login via Indian mobile number is "preferred by Indian users" (agency blog, weak). — [Ideamagix](https://www.ideamagix.com/blog/how-much-does-a-mobile-app-cost-in-india-in-2026/)
- BeReal uses phone number plus OTP as its primary identity, and phone numbers double as the friend-finding key. — [Page Flows](https://pageflows.com/post/ios/onboarding/bereal/)

### Inferences
- **India Android:** Google one-tap and phone (Truecaller one-tap, falling back to SMS OTP).
- **iOS:** Sign in with Apple and Google.
- Offer passkey enrolment after the first session rather than at sign-up.
- For Spotify-heavy users, consider making "Continue with Spotify" itself the account creation. That merges identity and source connection into one tap. Check Spotify's developer terms first.
- A phone number is a valuable friend-matching key, but it should be optional or deferred to "Find friends."

### Gaps
- No primary A/B data found comparing Sign in with Apple, Google, phone OTP and Truecaller conversion in India.
- No data found on SMS OTP delivery failure rates in India.

## 5. Personalisation quizzes, progress indicators, skip affordances

### Takeaway
Taste pickers (Spotify's 3+ artists, TikTok interests) exist to prevent an empty first screen. Jingle can skip the quiz entirely, because connecting a source gives real taste data. Soft walls with "Later" (Duolingo) and an optional interest picker (TikTok) are the proven skip patterns.

### Cited Findings
- Spotify requires at least 3 artists before Home. Each screen has one clear action. Search is not mandatory. — [Medium teardown](https://medium.com/@TheAhmadkabir/how-spotify-onboards-new-users-and-what-id-improve-as-a-pm-c05b4eb318df); [Page Flows](https://pageflows.com/post/ios/onboarding/spotify/)
- TikTok's interest picker is skippable. TikTok tells users the feed improves as they scroll. — [Appcues GoodUX](https://goodux.appcues.com/blog/tiktok-user-onboarding)
- Duolingo's soft walls have a "Later" button, followed by a hard wall once commitment is primed. — [Taplytics](https://taplytics.com/blog/duolingo-ab-test-onboarding/)
- Gas used a location-prefilled school list, a zero-typing taste/graph proxy. — [Medium / Bier](https://medium.com/@illyism/how-to-build-successful-social-apps-lessons-from-nikita-bier-creator-of-tbh-and-gas-11c564ece467)

### Inferences
- **No upfront quiz for Jingle.** Connect a source and derive taste. Offer an artist picker only to users who skip or fail source connection (e.g., Amazon-only users), so suggestions and the Drop still work.
- Use a 3-dot progress indicator for **Connect → Friends → Notifications**. Each step after Connect should be skippable.
- The college/school-based discovery that Gas and Airbuds use could map to "your college" or "your city" circles for India.

### Gaps
- No published A/B data on progress indicators or onboarding length found in 2024–26 sources.
- Appcues and Amplitude benchmarks on step counts were not retrievable.

## 6. Deferred deep links and invite-link onboarding

### Takeaway
Invites should carry context through install: you open the app and land in the inviter's circle. Firebase Dynamic Links, the free default, shut down on 25 Aug 2025, so Jingle needs Branch or AppsFlyer or a self-built approach. The Partiful lesson is to make the link useful even before install.

### Cited Findings
- Firebase Dynamic Links sunset on 25 Aug 2025; all links now 404. Google recommends Adjust, Airbridge, AppsFlyer, Bitly, Branch, Kochava or Singular. Branch has a free developer tier; full MMP suites start at about $500/month. — [AppsFlyer](https://www.appsflyer.com/blog/mobile-marketing/fdl-deprecation-deep-linking/); [u2l.ai](https://u2l.ai/blog/firebase-dynamic-links-alternative)
- Partiful links work in iMessage, Instagram and WhatsApp with no install needed to RSVP. — [Sacra](https://sacra.com/chat/h/ca6c792b-7d6d-42a9-ae5f-0970a819c66c/)
- Airbuds gates its full recap on inviting friends. — [TechCrunch](https://techcrunch.com/2025/09/17/airbuds-is-the-music-social-network-apple-and-spotify-wish-they-had-built/)
- Referral benchmarks (generic blog, weak): 8–20% of active users share referral links, and 50–70% of referred users complete onboarding. — [GrowSurf](https://growsurf.com/examples/mobile-app-referral-programs/)

### Inferences
**Proposed invite flow for Jingle:**
1. The friend shares a circle invite via the WhatsApp or Instagram share sheet.
2. The recipient lands on a web preview showing the circle name, member faces, the shared playlist and today's Drop.
3. They install from the store.
4. A deferred deep link (Branch, or a self-hosted token matched at first open plus the Play Install Referrer on Android) carries the invite.
5. Sign in with one tap.
6. Already a member of the circle, with the inviter auto-friended.
7. Connect a source, framed as "so Riya and the circle see what you play."

Inviter context in step 2 is the strongest motivation to connect.

### Gaps
- No published conversion numbers for deferred-deep-link versus plain store-link invites found.
- iOS deferred deep-link reliability after ATT (no fingerprinting) was not verified here.

## 7. Onboarding anti-patterns that kill activation

### Takeaway
The repeat offenders:
- asking for permissions before showing value,
- a hard sign-up wall before any value for content-led products,
- long forms (Spotify's email, password, DOB, gender and name),
- contact-sync dependence,
- and an empty first screen.

### Cited Findings
- BeReal asks for contacts before the user has experienced value. — [Tear Them Down](https://tearthemdown.substack.com/p/bereal-product-case-study)
- Duolingo's sign-up before a lesson cost about 20% of DAU versus delaying it. — [Taplytics](https://taplytics.com/blog/duolingo-ab-test-onboarding/)
- Cold system push prompts at launch underperform primed, in-context asks (vendor data). — [ngrow](https://www.ngrow.ai/blog/push-notifications-how-to-maximize-opt-ins); [Plotline](https://www.plotline.so/blog/how-to-improve-push-notification-opt-in-rates)
- Relying on contact sync is risky after iOS 18. — [Podcast Notes / Bier](https://podcastnotes.org/lennys-podcast-with-lenny-rachitsky/nikita-bier-how-to-consistently-go-viral-the-playbook-for-winning-at-consumer-apps-lennys-podcast/)
- Value must be visible within about 3 seconds. — [Podcast Notes / Bier](https://podcastnotes.org/lennys-podcast-with-lenny-rachitsky/nikita-bier-how-to-consistently-go-viral-the-playbook-for-winning-at-consumer-apps-lennys-podcast/)
- At the median product, more than 98% of new users are inactive within two weeks. — [Amplitude](https://info.amplitude.com/rs/138-CDN-550/images/the-product-benchmark-report.pdf)
- India: large APKs reportedly see 40%+ install drop-off on slow connections, with a recommendation to stay under 25MB. Tier-3 devices are typically under ₹15k with 2–3GB RAM. This comes from a low-quality agency blog; verify before relying on it. — [vMobify](https://vmobify.com/blog/app-install-cost-india)

### Inferences
**Jingle-specific risks:**
- Asking for Android notification access before explaining it.
- Showing a friendless empty feed.
- Faking Live for seeded content, which would break trust.
- Making source connection a hard wall with no fallback for Amazon Music, where no live API is available.
- A heavy first-launch download on low-end Android.
- English-only copy for an India-first audience; Hindi or Hinglish localisation was not researched here.

### Gaps
- No primary India-specific onboarding studies were found (vernacular languages, OTP delivery, data-saver behaviour).
- Lemon8, Arc Search, stats.fm and Instagram 2025 onboarding specifics were not retrieved in this pass.
