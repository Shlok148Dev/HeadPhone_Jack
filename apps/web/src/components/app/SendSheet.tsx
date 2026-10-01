"use client";

import { useMemo, useState } from "react";
import { Button, Chip, Dialog, IconButton, Icons, useToast, Artwork } from "@/components/ds";
import { TextField } from "@/components/app/forms";
import { useCircles } from "@/lib/circles";
import type { SendRequest } from "@/lib/send";
import { MIXTAPE_MAX, MIXTAPE_MIN, NOTE_MAX, useSendActions, useSongSearch, type Song } from "@/lib/sends";
import { useFriends } from "@/lib/social";

const keyOf = (s: Song) => `${s.artist.toLowerCase()}|${s.title.toLowerCase()}`;

function SongRow({ song, action }: { song: Song; action?: React.ReactNode }) {
  return (
    <li className="flex min-h-14 items-center gap-3">
      <div className="h-11 w-11 shrink-0 overflow-hidden rounded-sm">
        <Artwork url={song.artwork_small ?? song.artwork_url ?? null} seed={keyOf(song)} alt="" rounded="none" />
      </div>
      <div className="min-w-0 flex-1">
        <p className="truncate text-sm font-medium">{song.title}</p>
        <p className="truncate text-xs text-text-muted">{song.artist}</p>
      </div>
      {action}
    </li>
  );
}

/** Send sheet (UX_SPEC Send sheet; JNG-06-01, 06-02, 06-06 reply with a song). */
export function SendSheet({ request, onClose }: { request: SendRequest; onClose: () => void }) {
  const friends = useFriends();
  const circles = useCircles();
  const { send } = useSendActions();
  const toast = useToast();
  const reply = request.replyTo;
  const [songs, setSongs] = useState<Song[]>(request.song ? [request.song] : []);
  const [mixtape, setMixtape] = useState(!request.song);
  const [q, setQ] = useState("");
  const results = useSongSearch(q);
  const [who, setWho] = useState("");
  const [users, setUsers] = useState<Set<string>>(new Set());
  const [circleIds, setCircleIds] = useState<Set<string>>(new Set());
  const [note, setNote] = useState("");

  const toggle = (set: Set<string>, id: string, update: (s: Set<string>) => void) => {
    const n = new Set(set);
    if (n.has(id)) n.delete(id);
    else n.add(id);
    update(n);
  };
  const needle = who.trim().toLowerCase();
  const people = useMemo(
    () =>
      (friends.data ?? [])
        .filter((f) => !needle || f.display_name.toLowerCase().includes(needle) || f.username.includes(needle))
        .slice(0, 30),
    [friends.data, needle],
  );
  const groups = (circles.data ?? []).filter((c) => !needle || c.name.toLowerCase().includes(needle));

  const n = songs.length;
  const countOk = n === 1 || (n >= MIXTAPE_MIN && n <= MIXTAPE_MAX);
  const noteOk = note.length <= NOTE_MAX;
  const hasRecipients = !!reply || users.size + circleIds.size > 0;
  const hint = !n
    ? "Find a song to send"
    : !countOk
      ? "Add at least 5 songs, or remove extras to send one song"
      : !hasRecipients
        ? "Pick at least one friend or circle"
        : null;

  const names = [
    ...(circles.data ?? []).filter((c) => circleIds.has(c.id)).map((c) => c.name),
    ...(friends.data ?? []).filter((f) => users.has(f.id)).map((f) => f.display_name),
  ];
  const target = reply ? reply.name : names.length === 1 ? names[0] : `${names.length} ${names.length === 1 ? "person" : "people"}`;

  function submit() {
    const body = {
      items: songs.map((s) => ({ recording_id: s.recording_id, title: s.title, artist: s.artist })),
      note: note.trim(),
      user_ids: [...users],
      circle_ids: [...circleIds],
      reply_to: reply?.deliveryId,
    };
    // Optimistic: the sheet closes right away (UX_SPEC). mutateAsync, because per-call mutate
    // callbacks are dropped once this component unmounts.
    onClose();
    send.mutateAsync(body).then(
      () => toast.toast({ title: `Sent to ${target}`, tone: "success" }),
      (e: Error) => toast.toast({ title: `Couldn't send to ${target}. ${e.message}`, tone: "danger" }),
    );
  }

  return (
    <Dialog
      open
      onClose={onClose}
      variant="sheet"
      title={reply ? `Reply to ${reply.name} with a song` : n > 1 || mixtape ? "Send a mixtape" : "Send a song"}
      footer={
        <div className="flex w-full flex-col items-stretch gap-2">
          {hint && <p className="text-xs text-text-muted" id="send-hint">{hint}</p>}
          <Button disabled={!!hint || !noteOk} aria-describedby={hint ? "send-hint" : undefined} onClick={submit}>
            Send
          </Button>
        </div>
      }
    >
      <div className="flex flex-col gap-5">
        <section aria-label="Songs" className="flex flex-col gap-2">
          <ul className="flex flex-col gap-1">
            {songs.map((s) => (
              <SongRow
                key={keyOf(s)}
                song={s}
                action={
                  <IconButton label={`Remove ${s.title}`} variant="ghost" onClick={() => setSongs(songs.filter((x) => x !== s))}>
                    <Icons.Close size={16} />
                  </IconButton>
                }
              />
            ))}
          </ul>
          {!mixtape ? (
            <Button variant="ghost" onClick={() => setMixtape(true)}>Add more songs to make a mixtape</Button>
          ) : (
            n < MIXTAPE_MAX && (
              <div className="flex flex-col gap-2">
                <TextField label="Find a song" value={q} onChange={(e) => setQ(e.target.value)} placeholder="Song or artist" />
                {q.trim().length >= 2 && (
                  <ul className="flex max-h-56 flex-col overflow-y-auto" aria-label="Search results">
                    {results.data?.length ? (
                      results.data
                        .filter((s) => !songs.some((x) => keyOf(x) === keyOf(s)))
                        .map((s) => (
                          <SongRow
                            key={keyOf(s)}
                            song={s}
                            action={
                              <Button variant="secondary" onClick={() => setSongs([...songs, s])}>
                                Add
                              </Button>
                            }
                          />
                        ))
                    ) : (
                      <li className="py-2 text-sm text-text-muted">
                        {results.isLoading ? "Searching…" : "No songs found. Try another spelling."}
                      </li>
                    )}
                  </ul>
                )}
                <p className="font-mono text-xs text-text-muted">{n}/{MIXTAPE_MAX} songs · mixtapes have 5–8</p>
              </div>
            )
          )}
        </section>

        {!reply && (
          <section aria-label="Recipients" className="flex flex-col gap-2">
            <TextField label="Send to" value={who} onChange={(e) => setWho(e.target.value)} placeholder="Search friends and circles" />
            <div className="flex max-h-48 flex-wrap gap-2 overflow-y-auto">
              {groups.map((c) => (
                <Chip key={c.id} selected={circleIds.has(c.id)} onSelectedChange={() => toggle(circleIds, c.id, setCircleIds)} icon={<Icons.Circles size={14} />}>
                  {c.name}
                </Chip>
              ))}
              {people.map((f) => (
                <Chip key={f.id} selected={users.has(f.id)} onSelectedChange={() => toggle(users, f.id, setUsers)}>
                  {f.display_name}
                </Chip>
              ))}
              {!groups.length && !people.length && <p className="text-sm text-text-muted">No friends or circles match.</p>}
            </div>
          </section>
        )}

        <label className="flex flex-col gap-1 text-sm font-medium">
          Note (optional)
          <textarea
            value={note}
            onChange={(e) => setNote(e.target.value)}
            rows={3}
            aria-describedby="note-count"
            aria-invalid={!noteOk}
            className="rounded-md border border-border bg-surface-2 px-3 py-2 font-normal"
            placeholder="Why this one?"
          />
          <span id="note-count" className={noteOk ? "self-end font-mono text-xs text-text-muted" : "self-end font-mono text-xs text-danger"}>
            {note.length}/{NOTE_MAX}
          </span>
        </label>
      </div>
    </Dialog>
  );
}
