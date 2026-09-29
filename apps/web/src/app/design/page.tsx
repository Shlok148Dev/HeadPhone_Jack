import type { Metadata } from "next";
import { DesignShowcase } from "./showcase";

export const metadata: Metadata = {
  title: "Design system · Jingle",
  description: "Jingle tokens, components, card states and motion — the reference implementation.",
};

export default function DesignPage() {
  return <DesignShowcase />;
}
