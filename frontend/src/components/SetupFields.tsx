import { useQuery, useQueryClient } from "@tanstack/react-query";
import {
  Checkbox,
  NumberInput,
  Select,
  TagsInput,
  Textarea,
  TextInput,
} from "@mantine/core";
import { DateInput } from "@mantine/dates";
import { api } from "../api";
import type { FieldDef } from "../types";

interface ProtocolOpt {
  id: number;
  title: string;
}

function useVocab(category: string | undefined) {
  return useQuery<string[]>({
    queryKey: ["vocab", category],
    queryFn: () => api.get(`/vocab/${category}`),
    enabled: !!category,
  });
}

export function FieldInput({
  field,
  value,
  onChange,
  protocols,
}: {
  field: FieldDef;
  value: unknown;
  onChange: (v: unknown) => void;
  protocols: ProtocolOpt[];
}) {
  const qc = useQueryClient();
  const category = field.vocab || field.key;
  const isVocab = field.kind === "multiselect" || field.kind === "select";
  const { data: terms } = useVocab(isVocab ? category : undefined);
  const options = terms ?? [];

  switch (field.kind) {
    case "multiselect": {
      const selected = Array.isArray(value) ? (value as string[]) : [];
      return (
        <TagsInput
          label={field.label}
          data={options}
          value={selected}
          onChange={async (vals) => {
            onChange(vals);
            // Persist any newly typed term back into the vocab list.
            const fresh = vals.filter((v) => !options.includes(v));
            for (const v of fresh) {
              await api.post("/vocab", { category, value: v });
            }
            if (fresh.length) qc.invalidateQueries({ queryKey: ["vocab", category] });
          }}
          placeholder={`Select or add ${field.label.toLowerCase()}…`}
        />
      );
    }
    case "select":
      return (
        <Select
          label={field.label}
          data={options}
          value={(value as string) ?? null}
          onChange={onChange}
          clearable
          searchable
        />
      );
    case "protocol":
      return (
        <Select
          label={field.label}
          data={protocols.map((p) => ({ value: String(p.id), label: p.title }))}
          value={value != null ? String(value) : null}
          onChange={(v) => onChange(v ? Number(v) : null)}
          clearable
          searchable
          placeholder="—"
        />
      );
    case "number":
      return (
        <NumberInput
          label={field.label}
          value={(value as number) ?? ""}
          onChange={(v) => onChange(v === "" ? null : Number(v))}
        />
      );
    case "date":
      return (
        <DateInput
          label={field.label}
          valueFormat="YYYY-MM-DD"
          value={value ? new Date((value as string) + "T00:00:00") : null}
          onChange={(d) => onChange(d ? d.toISOString().slice(0, 10) : null)}
          clearable
        />
      );
    case "checkbox":
      return (
        <Checkbox
          label={field.label}
          checked={Boolean(value)}
          onChange={(e) => onChange(e.currentTarget.checked)}
        />
      );
    case "textarea":
      return (
        <Textarea
          label={field.label}
          autosize
          minRows={2}
          value={(value as string) ?? ""}
          onChange={(e) => onChange(e.currentTarget.value)}
        />
      );
    default:
      return (
        <TextInput
          label={field.label}
          value={(value as string) ?? ""}
          onChange={(e) => onChange(e.currentTarget.value)}
        />
      );
  }
}
