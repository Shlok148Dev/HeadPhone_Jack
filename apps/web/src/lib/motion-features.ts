// Full feature set (layout, layoutId, drag), loaded after first paint via <LazyMotion> in providers.
// Components import `m` (aliased as `motion`), so only the small core ships in first-load JS.
import { domMax } from "motion/react";

export default domMax;
