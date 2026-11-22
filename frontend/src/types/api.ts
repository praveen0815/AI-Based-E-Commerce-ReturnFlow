export interface SuccessResponse<T> {
  success: true;
  data: T;
  message?: string;
  request_id: string;
}

export interface ErrorBody {
  code: string;
  message: string;
  details?: unknown;
}

export interface ErrorResponse {
  success: false;
  error: ErrorBody;
  request_id: string;
}
