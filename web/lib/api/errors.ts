import { z } from "zod";

const errorEnvelopeSchema = z.object({
  error: z.object({
    code: z.string(),
    message: z.string(),
    retryable: z.boolean().optional().default(false),
    details: z.unknown().optional(),
    request_id: z.string(),
  }),
});

export type ApiErrorEnvelope = z.infer<typeof errorEnvelopeSchema>;

export class ApiClientError extends Error {
  readonly code: string;

  constructor(code: string, message: string, options?: ErrorOptions) {
    super(message, options);
    this.name = "ApiClientError";
    this.code = code;
  }
}

export class ApiHttpError extends ApiClientError {
  readonly status: number;
  readonly retryable: boolean;
  readonly requestId?: string;
  readonly details?: unknown;

  constructor(status: number, envelope: ApiErrorEnvelope) {
    super(envelope.error.code, envelope.error.message);
    this.name = "ApiHttpError";
    this.status = status;
    this.retryable = envelope.error.retryable;
    this.requestId = envelope.error.request_id;
    this.details = envelope.error.details;
  }
}

export class ApiResponseValidationError extends ApiClientError {
  readonly cause: unknown;

  constructor(cause: unknown) {
    super("INVALID_RESPONSE", "服务器返回的数据不符合预期", { cause });
    this.name = "ApiResponseValidationError";
    this.cause = cause;
  }
}

export class ApiNetworkError extends ApiClientError {
  readonly cause: unknown;

  constructor(cause: unknown) {
    super("NETWORK_ERROR", "无法连接研究服务", { cause });
    this.name = "ApiNetworkError";
    this.cause = cause;
  }
}

export function parseErrorEnvelope(value: unknown): ApiErrorEnvelope | null {
  const result = errorEnvelopeSchema.safeParse(value);
  return result.success ? result.data : null;
}
