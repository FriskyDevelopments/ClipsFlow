export declare const ALLOWED_ORIGINS: Set<string>;
export declare const WORKOS_AUTH_PATH: RegExp;

declare const guard: {
  fetch(request: Request): Promise<Response>;
};
export default guard;
