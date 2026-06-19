export interface AuthStatus {
  unlocked: boolean;
  encryption: boolean;
  db_exists: boolean;
}

export interface Meta {
  entry_types: string[];
  entry_type_labels: Record<string, string>;
  statuses: string[];
  field_kinds: string[];
  vocab_categories: string[];
  vocab_category_labels: Record<string, string>;
}

export interface Entry {
  id: number;
  created_at: string;
  entry_type: string;
  source: string;
  text: string;
  experiment_id: number | null;
  experiment_name: string | null;
  protocol_title: string | null;
}

export interface Dashboard {
  entries_today: number;
  protocols: number;
  experiments: number;
  pending_notes: number;
  pending_tasks: PendingTask[];
  today_entries: Entry[];
}

export interface PendingTask {
  id: number;
  task_name: string;
  planned_date: string | null;
  sample: string | null;
  reagent: string | null;
  experiment_name: string | null;
}

export interface Experiment {
  id: number;
  name: string;
  description: string | null;
  status: string;
  type_id: number | null;
  type_name: string | null;
  start_date: string | null;
  end_date: string | null;
  duration_days: number | null;
  protocol_id: number | null;
  setup: Record<string, unknown>;
  task_total: number;
  task_done: number;
}

export interface Task {
  id: number;
  experiment_id: number;
  task_name: string;
  planned_date: string | null;
  sample: string | null;
  reagent: string | null;
  notes: string | null;
  status: string;
}

export interface FieldDef {
  key: string;
  label: string;
  kind: string;
  vocab?: string;
}

export interface ExpType {
  id: number;
  name: string;
  fields: FieldDef[];
}

export interface Protocol {
  id: number;
  title: string;
  source_filename: string | null;
  version: string | null;
  imported_at: string;
  body_text: string | null;
  tags: string | null;
  has_file: boolean;
  steps: { step_no: number; text: string }[];
}

export interface Report {
  html: string;
  markdown: string;
  text: string;
}

export interface DirEntry {
  name: string;
  path: string;
}

export interface FileEntry {
  name: string;
  path: string;
  ext: string;
  size: number;
  is_experiment: boolean;
}

export interface Listing {
  path: string;
  parent: string | null;
  dirs: DirEntry[];
  files: FileEntry[];
}

export interface ExcelPreview {
  sheet: string;
  sheet_names: string[];
  columns: string[];
  rows: Record<string, unknown>[];
}
