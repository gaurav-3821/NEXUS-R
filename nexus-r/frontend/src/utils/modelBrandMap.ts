export interface BrandInfo {
  slug: string;
  color: string;
  label: string;
}

export const MODEL_BRAND_MAP: { prefix: string; brand: BrandInfo }[] = [
  // OpenAI
  { prefix: 'gpt', brand: { slug: 'openai', color: '10a37f', label: 'OpenAI' } },
  { prefix: 'o1', brand: { slug: 'openai', color: '10a37f', label: 'OpenAI' } },
  { prefix: 'o3', brand: { slug: 'openai', color: '10a37f', label: 'OpenAI' } },
  { prefix: 'chatgpt', brand: { slug: 'openai', color: '10a37f', label: 'OpenAI' } },
  { prefix: 'openai', brand: { slug: 'openai', color: '10a37f', label: 'OpenAI' } },
  // Anthropic
  { prefix: 'claude', brand: { slug: 'anthropic', color: 'd97757', label: 'Anthropic' } },
  // Meta
  { prefix: 'llama', brand: { slug: 'meta', color: '0467DF', label: 'Meta' } },
  // Google
  { prefix: 'gemini', brand: { slug: 'googlegemini', color: '8E75B2', label: 'Google' } },
  { prefix: 'gemma', brand: { slug: 'google', color: '4285F4', label: 'Google' } },
  { prefix: 'timesfm', brand: { slug: 'google', color: '4285F4', label: 'Google' } },
  { prefix: 'google', brand: { slug: 'google', color: '4285F4', label: 'Google' } },
  // Mistral AI
  { prefix: 'mistral', brand: { slug: 'mistralai', color: 'FF7000', label: 'Mistral AI' } },
  { prefix: 'mixtral', brand: { slug: 'mistralai', color: 'FF7000', label: 'Mistral AI' } },
  { prefix: 'ministral', brand: { slug: 'mistralai', color: 'FF7000', label: 'Mistral AI' } },
  { prefix: 'codestral', brand: { slug: 'mistralai', color: 'FF7000', label: 'Mistral AI' } },
  { prefix: 'mistralai', brand: { slug: 'mistralai', color: 'FF7000', label: 'Mistral AI' } },
  // DeepSeek
  { prefix: 'deepseek', brand: { slug: 'deepseek', color: '4D6BFE', label: 'DeepSeek' } },
  // Alibaba / Qwen
  { prefix: 'qwen', brand: { slug: 'alibabadotcom', color: 'FF6A00', label: 'Alibaba' } },
  { prefix: 'alibaba', brand: { slug: 'alibabadotcom', color: 'FF6A00', label: 'Alibaba' } },
  // Microsoft
  { prefix: 'phi', brand: { slug: 'microsoft', color: '00A4EF', label: 'Microsoft' } },
  { prefix: 'microsoft', brand: { slug: 'microsoft', color: '00A4EF', label: 'Microsoft' } },
  // Cohere
  { prefix: 'command', brand: { slug: 'cohere', color: '39594D', label: 'Cohere' } },
  { prefix: 'cohere', brand: { slug: 'cohere', color: '39594D', label: 'Cohere' } },
  // Perplexity
  { prefix: 'pplx', brand: { slug: 'perplexityai', color: '1B3A5C', label: 'Perplexity' } },
  { prefix: 'sonar', brand: { slug: 'perplexityai', color: '1B3A5C', label: 'Perplexity' } },
  { prefix: 'perplexity', brand: { slug: 'perplexityai', color: '1B3A5C', label: 'Perplexity' } },
  // xAI
  { prefix: 'grok', brand: { slug: 'xai', color: '000000', label: 'xAI' } },
  { prefix: 'xai', brand: { slug: 'xai', color: '000000', label: 'xAI' } },
  // NVIDIA
  { prefix: 'nemotron', brand: { slug: 'nvidia', color: '76B900', label: 'NVIDIA' } },
  { prefix: 'nvidia', brand: { slug: 'nvidia', color: '76B900', label: 'NVIDIA' } },
  // AWS
  { prefix: 'nova', brand: { slug: 'amazonwebservices', color: 'FF9900', label: 'AWS' } },
  { prefix: 'titan', brand: { slug: 'amazonwebservices', color: 'FF9900', label: 'AWS' } },
  { prefix: 'amazon', brand: { slug: 'amazonwebservices', color: 'FF9900', label: 'AWS' } },
  // IBM
  { prefix: 'granite', brand: { slug: 'ibm', color: '052FAD', label: 'IBM' } },
  { prefix: 'ibm', brand: { slug: 'ibm', color: '052FAD', label: 'IBM' } },
  // Databricks
  { prefix: 'dbrx', brand: { slug: 'databricks', color: 'EF3B2D', label: 'Databricks' } },
  { prefix: 'databricks', brand: { slug: 'databricks', color: 'EF3B2D', label: 'Databricks' } },
  // 01.AI / Yi
  { prefix: 'yi', brand: { slug: '01ai', color: 'FF6B35', label: '01.AI' } },
  // Upstage / Solar
  { prefix: 'solar', brand: { slug: 'upstage', color: '4527A0', label: 'Upstage' } },
  { prefix: 'upstage', brand: { slug: 'upstage', color: '4527A0', label: 'Upstage' } },
  // TII / Falcon
  { prefix: 'falcon', brand: { slug: 'technologyinnovationinstitute', color: '2C3E50', label: 'TII' } },
  // AI21 / Jamba
  { prefix: 'jamba', brand: { slug: 'ai21labs', color: '2C3E50', label: 'AI21' } },
  { prefix: 'ai21', brand: { slug: 'ai21labs', color: '2C3E50', label: 'AI21' } },
  // Antigravity
  { prefix: 'antigravity', brand: { slug: 'codeberg', color: '2185D0', label: 'Antigravity' } },
  // Moonshot AI / Kimi
  { prefix: 'moonshot', brand: { slug: 'moonshotai', color: '8B5CF6', label: 'Moonshot AI' } },
  { prefix: 'kimi', brand: { slug: 'moonshotai', color: '8B5CF6', label: 'Kimi' } },
  // OpenRouter
  { prefix: 'openrouter', brand: { slug: 'openrouter', color: '6366F1', label: 'OpenRouter' } },
  // Groq
  { prefix: 'groq', brand: { slug: 'groq', color: 'F97316', label: 'Groq' } },
  // Nous Research / Hermes
  { prefix: 'hermes', brand: { slug: 'nousresearch', color: 'D946EF', label: 'Hermes' } },
  { prefix: 'nous', brand: { slug: 'nousresearch', color: 'D946EF', label: 'Nous Research' } },
  // Sourceful
  { prefix: 'sourceful', brand: { slug: 'sourceful', color: '059669', label: 'Sourceful' } },
  // Poolside
  { prefix: 'poolside', brand: { slug: 'poolside', color: '2563EB', label: 'Poolside' } },
  // z.ai
  { prefix: 'z-ai', brand: { slug: 'z-ai', color: '0EA5E9', label: 'z.ai' } },
  { prefix: 'zai', brand: { slug: 'z-ai', color: '0EA5E9', label: 'z.ai' } },
  // Additional providers
  { prefix: 'snowflake', brand: { slug: 'snowflake', color: '29B5E8', label: 'Snowflake' } },
  { prefix: 'arctic', brand: { slug: 'snowflake', color: '29B5E8', label: 'Snowflake' } },
  { prefix: 'reka', brand: { slug: 'reka', color: 'FF4D4D', label: 'Reka' } },
  { prefix: 'phind', brand: { slug: 'phind', color: '1E3A5F', label: 'Phind' } },
  { prefix: 'together', brand: { slug: 'together', color: 'FF6B6B', label: 'Together AI' } },
  { prefix: 'fireworks', brand: { slug: 'fireworks', color: 'FF7700', label: 'Fireworks AI' } },
  { prefix: 'replicate', brand: { slug: 'replicate', color: '1B1B1B', label: 'Replicate' } },
  { prefix: 'huggingface', brand: { slug: 'huggingface', color: 'FFD21E', label: 'Hugging Face' } },
  { prefix: 'liquid', brand: { slug: 'liquid', color: '6B46C1', label: 'Liquid AI' } },
  { prefix: 'minimax', brand: { slug: 'minimax', color: 'FF5A5F', label: 'MiniMax' } },
  { prefix: 'inflection', brand: { slug: 'inflection', color: '3B82F6', label: 'Inflection AI' } },
  { prefix: 'adept', brand: { slug: 'adept', color: '8B5CF6', label: 'Adept' } },
  { prefix: 'intel', brand: { slug: 'intel', color: '0071C5', label: 'Intel' } },
  { prefix: 'samsung', brand: { slug: 'samsung', color: '1428A0', label: 'Samsung' } },
  { prefix: 'dolphin', brand: { slug: 'cognitivecomputations', color: '0891B2', label: 'Cognitive' } },
  { prefix: 'midnight', brand: { slug: 'sophosympatheia', color: '6B21A8', label: 'Sophosympatheia' } },
  { prefix: 'mythomax', brand: { slug: 'gryphe', color: 'BE185D', label: 'Gryphe' } },
  { prefix: 'eagle', brand: { slug: 'recursal', color: 'D97706', label: 'Recursal' } },
  { prefix: 'orca', brand: { slug: 'microsoft', color: '00A4EF', label: 'Microsoft' } },
];

export const FALLBACK_BRAND: BrandInfo = {
  slug: 'robot',
  color: '6b7280',
  label: 'Model',
};

/** Inline SVG data URIs for brands without Simple Icons CDN support. */
export const CUSTOM_BRAND_ICONS: Record<string, string> = {
  openrouter: 'data:image/svg+xml,' + encodeURIComponent(
    '<svg xmlns="http://www.w3.org/2000/svg" width="20" height="20" viewBox="0 0 24 24" fill="none">' +
    '<circle cx="12" cy="12" r="10" fill="#6366F1"/>' +
    '<text x="12" y="16" text-anchor="middle" fill="white" font-size="11" font-family="sans-serif" font-weight="bold">OR</text>' +
    '</svg>'
  ),
  groq: 'data:image/svg+xml,' + encodeURIComponent(
    '<svg xmlns="http://www.w3.org/2000/svg" width="20" height="20" viewBox="0 0 24 24" fill="none">' +
    '<circle cx="12" cy="12" r="10" fill="#F97316"/>' +
    '<text x="12" y="16" text-anchor="middle" fill="white" font-size="12" font-family="sans-serif" font-weight="bold">G</text>' +
    '</svg>'
  ),
  moonshotai: 'data:image/svg+xml,' + encodeURIComponent(
    '<svg xmlns="http://www.w3.org/2000/svg" width="20" height="20" viewBox="0 0 24 24" fill="none">' +
    '<circle cx="12" cy="12" r="10" fill="#8B5CF6"/>' +
    '<text x="12" y="16" text-anchor="middle" fill="white" font-size="12" font-family="sans-serif" font-weight="bold">K</text>' +
    '</svg>'
  ),
  nousresearch: 'data:image/svg+xml,' + encodeURIComponent(
    '<svg xmlns="http://www.w3.org/2000/svg" width="20" height="20" viewBox="0 0 24 24" fill="none">' +
    '<circle cx="12" cy="12" r="10" fill="#D946EF"/>' +
    '<text x="12" y="16" text-anchor="middle" fill="white" font-size="12" font-family="sans-serif" font-weight="bold">N</text>' +
    '</svg>'
  ),
  sourceful: 'data:image/svg+xml,' + encodeURIComponent(
    '<svg xmlns="http://www.w3.org/2000/svg" width="20" height="20" viewBox="0 0 24 24" fill="none">' +
    '<circle cx="12" cy="12" r="10" fill="#059669"/>' +
    '<text x="12" y="16" text-anchor="middle" fill="white" font-size="12" font-family="sans-serif" font-weight="bold">S</text>' +
    '</svg>'
  ),
  poolside: 'data:image/svg+xml,' + encodeURIComponent(
    '<svg xmlns="http://www.w3.org/2000/svg" width="20" height="20" viewBox="0 0 24 24" fill="none">' +
    '<circle cx="12" cy="12" r="10" fill="#2563EB"/>' +
    '<text x="12" y="16" text-anchor="middle" fill="white" font-size="12" font-family="sans-serif" font-weight="bold">P</text>' +
    '</svg>'
  ),
  'z-ai': 'data:image/svg+xml,' + encodeURIComponent(
    '<svg xmlns="http://www.w3.org/2000/svg" width="20" height="20" viewBox="0 0 24 24" fill="none">' +
    '<circle cx="12" cy="12" r="10" fill="#0EA5E9"/>' +
    '<text x="12" y="16" text-anchor="middle" fill="white" font-size="12" font-family="sans-serif" font-weight="bold">Z</text>' +
    '</svg>'
  ),
  cognitivecomputations: 'data:image/svg+xml,' + encodeURIComponent(
    '<svg xmlns="http://www.w3.org/2000/svg" width="20" height="20" viewBox="0 0 24 24" fill="none">' +
    '<circle cx="12" cy="12" r="10" fill="#0891B2"/>' +
    '<text x="12" y="16" text-anchor="middle" fill="white" font-size="12" font-family="sans-serif" font-weight="bold">C</text>' +
    '</svg>'
  ),
  sophosympatheia: 'data:image/svg+xml,' + encodeURIComponent(
    '<svg xmlns="http://www.w3.org/2000/svg" width="20" height="20" viewBox="0 0 24 24" fill="none">' +
    '<circle cx="12" cy="12" r="10" fill="#6B21A8"/>' +
    '<text x="12" y="16" text-anchor="middle" fill="white" font-size="12" font-family="sans-serif" font-weight="bold">M</text>' +
    '</svg>'
  ),
  gryphe: 'data:image/svg+xml,' + encodeURIComponent(
    '<svg xmlns="http://www.w3.org/2000/svg" width="20" height="20" viewBox="0 0 24 24" fill="none">' +
    '<circle cx="12" cy="12" r="10" fill="#BE185D"/>' +
    '<text x="12" y="16" text-anchor="middle" fill="white" font-size="12" font-family="sans-serif" font-weight="bold">G</text>' +
    '</svg>'
  ),
  recursal: 'data:image/svg+xml,' + encodeURIComponent(
    '<svg xmlns="http://www.w3.org/2000/svg" width="20" height="20" viewBox="0 0 24 24" fill="none">' +
    '<circle cx="12" cy="12" r="10" fill="#D97706"/>' +
    '<text x="12" y="16" text-anchor="middle" fill="white" font-size="12" font-family="sans-serif" font-weight="bold">R</text>' +
    '</svg>'
  ),
  technologyinnovationinstitute: 'data:image/svg+xml,' + encodeURIComponent(
    '<svg xmlns="http://www.w3.org/2000/svg" width="20" height="20" viewBox="0 0 24 24" fill="none">' +
    '<circle cx="12" cy="12" r="10" fill="#2C3E50"/>' +
    '<text x="12" y="16" text-anchor="middle" fill="white" font-size="10" font-family="sans-serif" font-weight="bold">TII</text>' +
    '</svg>'
  ),
};

export function getModelBrandInfo(modelId: string): BrandInfo {
  if (!modelId) return FALLBACK_BRAND;
  const lower = modelId.toLowerCase();
  for (const entry of MODEL_BRAND_MAP) {
    if (lower.includes(entry.prefix)) return entry.brand;
  }
  return FALLBACK_BRAND;
}
