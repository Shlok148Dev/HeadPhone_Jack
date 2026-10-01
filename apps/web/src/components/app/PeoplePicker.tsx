"use client";

import { useMemo, useState } from "react";
import { Chip, Icons } from "@/components/ds";
import { TextField } from "@/components/app/forms";
import { useCircles } from "@/lib/circles";
import { useFriends } from "@/lib/social";

export interface Picked {
  users: Set<string>;
  circle: string | null;
}

/** Pick friends, or one whole circle (Blends and sessions: JNG-07-01, 07-05). */
export function PeoplePicker({ value, onChange, maxFriends }: { value: Picked; onChange: (v: Picked) => void; maxFriends?: number }) {
  const friends = useFriends();
  const circles = useCircles();
  const [q, setQ] = useState("");
  const needle = q.trim().toLowerCase();
  const people = useMemo(
    () => (friends.data ?? []).filter((f) => !needle || f.display_name.toLowerCase().includes(needle) || f.username.includes(needle)).slice(0, 30),
    [friends.data, needle],
  );
  const groups = (circles.data ?? []).filter((c) => !needle || c.name.toLowerCase().includes(needle));
  const full = maxFriends !== undefined && value.users.size >= maxFriends;

  return (
    <div className="flex flex-col gap-2">
      <TextField label="Who's in?" value={q} onChange={(e) => setQ(e.target.value)} placeholder="Search friends and circles" />
      <div className="flex max-h-56 flex-wrap gap-2 overflow-y-auto" role="group" aria-label="Friends and circles">
        {groups.map((c) => (
          <Chip
            key={c.id}
            icon={<Icons.Circles size={14} />}
            selected={value.circle === c.id}
            onSelectedChange={(on) => onChange({ users: new Set(), circle: on ? c.id : null })}
          >
            {c.name}
          </Chip>
        ))}
        {people.map((f) => {
          const on = value.users.has(f.id);
          return (
            <Chip
              key={f.id}
              selected={on}
              disabled={!on && full}
              onSelectedChange={() => {
                const users = new Set(value.users);
                if (on) users.delete(f.id);
                else users.add(f.id);
                onChange({ users, circle: null });
              }}
            >
              {f.display_name}
            </Chip>
          );
        })}
        {!groups.length && !people.length && <p className="text-sm text-text-muted">No friends or circles match.</p>}
      </div>
      {full && <p className="font-mono text-xs text-text-muted">Up to {maxFriends} friends.</p>}
    </div>
  );
}
