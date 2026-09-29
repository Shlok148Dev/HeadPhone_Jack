import { describe, expect, it } from "vitest";
import { birthYearOptions, fieldErrors } from "./forms";

describe("sign-up helpers", () => {
  it("offers birth years from 13 to 100 years ago (UX_SPEC §5.2)", () => {
    const opts = birthYearOptions(new Date("2026-09-29"));
    expect(opts[0]!.value).toBe("2013");
    expect(opts.at(-1)!.value).toBe("1926");
  });

  it("takes the first message per field from the error envelope details", () => {
    expect(fieldErrors({ email: ["An account with this email already exists."], x: 3 })).toEqual({
      email: "An account with this email already exists.",
    });
  });
});
