/// <reference types="vite/client" />

declare module '*.vue' {
  import type { DefineComponent } from 'vue'
  const component: DefineComponent<{}, {}, any>
  export default component
}

declare module 'vis-network/standalone' {
  export class Network {
    constructor(container: HTMLElement, data: any, options?: any)
    on(event: string, callback: (params: any) => void): void
    setData(data: any): void
    destroy(): void
  }
}
