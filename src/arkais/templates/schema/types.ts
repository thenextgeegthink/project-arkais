/**
 * Arkais Scientific Template Types
 * Generated from arkais-template-schema.v1.json
 */

export type AssetCategory = 'figures' | 'tables';

export type Discipline =
  | 'physics'
  | 'computer_science'
  | 'medicine'
  | 'economics'
  | 'engineering'
  | 'general';

export type EngineType =
  | 'vega-lite'
  | 'latex-booktabs'
  | 'matplotlib'
  | 'mermaid'
  | 'svg-custom';

export type WeavingArchetype =
  | 'parenthetical_grounding'
  | 'lead_in_assertion'
  | 'comparative_delta'
  | 'methodological_protocol'
  | 'tabular_baseline';

export interface SignatureIntegration {
  recommended_gate: string;
  weaving_archetype: WeavingArchetype;
  in_prose_blueprint: string;
  required_metrics?: string[];
  unit_discipline?: string;
  grounding_rules?: string[];
}

export interface ParameterDefinition {
  type: 'string' | 'number' | 'integer' | 'boolean' | 'array' | 'color';
  description: string;
  default?: any;
  choices?: any[];
  min_value?: number;
  max_value?: number;
}

export interface TemplateEnvelope<TSpec = Record<string, any> | string, TData = any> {
  $schema?: string;
  id: string;
  version: string;
  name: string;
  description?: string;
  category: AssetCategory;
  discipline: Discipline;
  tags: string[];
  engine: EngineType;
  min_engine_version?: string;
  author: string;
  license?: string;
  provenance_ark?: string;
  signature_integration: SignatureIntegration;
  caption_blueprint?: string;
  notes?: string;
  parameters?: Record<string, ParameterDefinition>;
  spec: TSpec;
  sample_data?: TData;
}
