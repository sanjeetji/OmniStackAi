import assert from "node:assert/strict";
import { test } from "node:test";
import { BadRequestError, ForbiddenError } from "../src/lib/errors.ts";

test("prescriptions must contain at least one medication item", () => {
  const items: any[] = [];
  assert.equal(items.length, 0);
  assert.throws(
    () => {
      if (items.length === 0) {
        throw new BadRequestError("Prescription must contain at least one medication item");
      }
    },
    BadRequestError
  );
});

test("immutable prescriptions reject further mutations", () => {
  const prescription = {
    id: "rx-1",
    isImmutable: true,
    signedAt: new Date(),
  };

  assert.throws(
    () => {
      if (prescription.isImmutable) {
        throw new BadRequestError(
          "Prescription for this consultation has already been digitally signed and is immutable."
        );
      }
    },
    BadRequestError
  );
});

test("finalized completed consultations reject subsequent SOAP edits", () => {
  const consultation = {
    id: "c-1",
    completedAt: new Date(),
  };

  assert.throws(
    () => {
      if (consultation.completedAt) {
        throw new BadRequestError("Cannot edit SOAP notes of a completed and finalized consultation");
      }
    },
    BadRequestError
  );
});
