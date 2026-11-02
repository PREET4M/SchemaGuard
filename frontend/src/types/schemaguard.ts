/**
 * frontend/src/types/schemaguard.ts
 * Type definitions for SchemaGuard API responses and state.
 */

export interface ContractResult {
  name: string;
  contract_type: "OLD_APP" | "NEW_APP" | string;
  status: "PASS" | "FAIL" | "REJECTED" | string;
  sql_statement: string;
  column_names: string[];
  row_count_post: number;
  execution_time_ms: number;
  error_message: string;
}

export interface InvariantResult {
  name: string;
  status: "PASS" | "FAIL" | "ERROR" | string;
  sql: string;
  violating_rows_count: number;
  sample_violations: Record<string, unknown>[];
  execution_time_ms: number;
  error_message: string;
  held: boolean;
}

export interface SchemaFinding {
  rule_id: string;
  severity: "CRITICAL" | "HIGH" | "MODERATE" | "LOW" | string;
  title: string;
  explanation: string;
  evidence: string;
  statement_index: number;
  human_review_action: string;
}

export interface SchemaDiff {
  tables_added: string[];
  tables_removed: string[];
  tables_modified: string[];
  columns_added: Record<string, string[]>;
  columns_removed: Record<string, string[]>;
  columns_modified: Record<string, Record<string, [string, string]>>;
  indexes_added: string[];
  indexes_removed: string[];
  foreign_keys_added: Record<string, string[]>;
  foreign_keys_removed: Record<string, string[]>;
  is_clean: boolean;
}

export interface TableProfile {
  table_name: string;
  pre_count: number;
  post_count: number;
  delta: number | null;
  status: string;
  is_row_drop: boolean;
}

export interface RiskFactor {
  category: string;
  points: number;
  description: string;
}

export interface RiskAssessment {
  overall_severity: "CRITICAL" | "HIGH" | "MODERATE" | "LOW" | string;
  risk_score: number;
  summary_label: string;
  factors: RiskFactor[];
}

export interface MigrationResult {
  migration_applied: boolean;
  migration_error: string;
  elapsed_total_ms: number;
  migration_sql: string;
}

export interface RehearsalReport {
  rehearsal_id: string;
  severity: "CRITICAL" | "HIGH" | "MODERATE" | "LOW";
  label: string;
  succeeded: boolean;
  post_checks_run: boolean;
  migration_result: MigrationResult;
  risk_assessment: RiskAssessment;
  schema_diff: SchemaDiff;
  contract_results: ContractResult[];
  invariant_results: InvariantResult[];
  data_profile: TableProfile[];
  schema_findings: SchemaFinding[];
  timestamp: string;
}

export interface DemoScenario {
  key: string;
  name: string;
  filename: string;
  severity: string;
  description: string;
  migration_sql: string;
}

export interface DemoMetadata {
  database_name: string;
  database_path: string;
  tables: Array<{ name: string; row_count: number }>;
  scenarios: {
    safe: DemoScenario;
    break_contract: DemoScenario;
    drop_table: DemoScenario;
  };
  default_contracts: {
    old_app_sql: string;
    new_app_sql: string;
  };
  default_invariants_sql: string;
}

export interface SystemSettings {
  constraints: {
    max_upload_size_mb: number;
    statement_timeout_seconds: number;
    max_sample_rows: number;
    sandbox_directory: string;
    sandbox_clone_filename: string;
  };
  pragmas: Record<string, string>;
  authorizer_rules: string[];
  runtime: {
    python_version: string;
    sqlite_version: string;
    sqlglot_version: string;
    platform: string;
  };
}

