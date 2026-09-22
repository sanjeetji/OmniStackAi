/** An error with an HTTP status and a message that is safe to show to the user. */
export class HttpError extends Error {
  readonly status: number;
  readonly code: string;

  constructor(status: number, code: string, message: string) {
    super(message);
    this.status = status;
    this.code = code;
  }
}

export const badRequest = (message: string, code = "bad_request") => new HttpError(400, code, message);
export const unauthorized = (message = "Please sign in.") => new HttpError(401, "unauthorized", message);
export const forbidden = (message = "You do not have access to this.") => new HttpError(403, "forbidden", message);
export const notFound = (what = "That") => new HttpError(404, "not_found", `${what} was not found.`);
export const conflict = (message: string, code = "conflict") => new HttpError(409, code, message);
