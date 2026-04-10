/// <reference types="vite/client" />
declare const GITHUB_RUNTIME_PERMANENT_NAME: string
declare const BASE_KV_SERVICE_URL: string

declare module '*.PNG' {
  const src: string
  export default src
}

declare module '*.png' {
  const src: string
  export default src
}