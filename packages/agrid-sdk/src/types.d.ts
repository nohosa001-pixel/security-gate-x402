declare module "@elizaos/core" {
  export type Action = any;
  export type ActionResult = any;
  export type Content = any;
  export type ContentValue = any;
  export type HandlerCallback = any;
  export type IAgentRuntime = any;
  export type Memory = any;
  export type State = any;
  export type Plugin = any;
  export type Evaluator<T = any> = any;
  export type EvaluatorProcessorContext<T = any> = any;
  export type EvaluatorPromptContext<T = any> = any;
  export type EvaluatorRunContext<T = any> = any;
  export type JsonValue = any;
  export type Provider = any;
  export type ProviderResult = any;
  export type Service = any;
  export type ChatPreHandler = any;
  export type ChatPostHandler = any;
  export const elizaLogger: any;
}

declare module "@elizaos/agent" {
  export type Agent = any;
}
