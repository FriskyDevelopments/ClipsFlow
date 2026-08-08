export declare const ALLOWED_ORIGINS: Set<string>;

declare const guard: {
  fetch(request: Request): Promise<Response>;
};
export default guard;
