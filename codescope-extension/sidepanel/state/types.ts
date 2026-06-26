export interface Parameter {
  name: string;
  annotation: string | null;
}

export interface MethodSignature {
  name: string;
  parameters: string[];
  return_type: string | null;
}

export interface FunctionInfo {
  name: string;
  parameters: Parameter[];
  return_type: string | null;
  docstring: string | null;
  decorators: string[];
  source_code: string;
  start_line: number;
  end_line: number;
  summary: string | null;
  summary_source: string | null;
}

export interface ClassInfo {
  name: string;
  base_classes: string[];
  docstring: string | null;
  methods: MethodSignature[];
  start_line: number;
  end_line: number;
}

export interface ModuleInfo {
  path: string;
  functions: string[];
  classes: string[];
  imports: string[];
  summary: string | null;
}

export interface ImportInfo {
  module: string;
  names: string[];
  aliases: Record<string, string>;
  is_relative: boolean;
  relative_level: number;
  resolved_path: string | null;
}

export type SearchItemType = 'function' | 'class' | 'method';

export interface SearchItem {
  type: SearchItemType;
  name: string;
  file: string;
  lines?: [number, number];
  signature?: string;
  summary?: string | null;
  source_preview?: string;
  github_url?: string;
  return_type?: string | null;
  class?: string;
  called_by?: string[];
  relevance_score: number;
}

export interface SearchGroup {
  file: string;
  relevance_score: number;
  items: SearchItem[];
}

export interface SearchResponse {
  results: SearchGroup[];
}

export interface GraphNode {
  id: string;
  type: 'function' | 'method' | 'class' | 'source' | 'external';
  file: string | null;
}

export interface GraphEdge {
  from: string;
  to: string;
  type: 'calls' | 'imports';
}

export interface GraphData {
  nodes: GraphNode[];
  edges: GraphEdge[];
}

export interface IndexResponse {
  owner: string;
  repo: string;
  status: string;
  file_count: number;
  function_count: number;
  class_count: number;
}

export interface RepoOverview {
  files: string[];
  function_count: number;
  class_count: number;
  functions: string[];
  classes: string[];
}

export interface FileDetail {
  module: ModuleInfo;
  functions: FunctionInfo[];
  classes: ClassInfo[];
  imports: ImportInfo[];
}

export type View = 'search' | 'explorer' | 'graph';

export type SearchMode = 'hybrid' | 'bm25' | 'faiss';

export type GraphType = 'calls' | 'imports';
