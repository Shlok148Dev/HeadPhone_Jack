/* Jingle web push (JNG-11-02). Shows the title only; details load in the app after a tap. */
self.addEventListener("push", (event) => {
  let data = { title: "Jingle", url: "/notifications" };
  try {
    data = { ...data, ...event.data.json() };
  } catch (e) {
    /* plain-text or empty push: keep the defaults */
  }
  event.waitUntil(self.registration.showNotification(data.title, { data: { url: data.url }, tag: data.url }));
});

self.addEventListener("notificationclick", (event) => {
  event.notification.close();
  const url = new URL(event.notification.data?.url || "/notifications", self.location.origin);
  if (url.origin !== self.location.origin) return; // only ever open Jingle itself
  event.waitUntil(
    self.clients.matchAll({ type: "window", includeUncontrolled: true }).then((wins) => {
      const open = wins.find((w) => w.url.startsWith(self.location.origin));
      return open ? open.navigate(url.href).then((w) => w && w.focus()) : self.clients.openWindow(url.href);
    }),
  );
});
