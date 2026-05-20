import { DatePicker } from "@mui/x-date-pickers/DatePicker";
import type { SxProps, Theme } from "@mui/material/styles";
import { alpha, useTheme } from "@mui/material/styles";
import type { TextFieldProps } from "@mui/material/TextField";
import dayjs, { type Dayjs } from "dayjs";
import customParseFormat from "dayjs/plugin/customParseFormat";
import { useMemo } from "react";
import { Controller, type Control, type FieldPath, type FieldValues } from "react-hook-form";

dayjs.extend(customParseFormat);

export type GiDatePickerProps = {
  /** Optional stable id for accessibility (`label for` -> input `id`). */
  id?: string;
  label: string;
  /** Valeur `YYYY-MM-DD` ou chaîne vide. */
  value: string;
  /** Livré au format `YYYY-MM-DD` (chaîne vide si effacé). */
  onChange: (_isoDate: string) => void;
  disabled?: boolean;
  error?: boolean;
  helperText?: string;
  size?: TextFieldProps["size"];
  fullWidth?: boolean;
  sx?: SxProps<Theme>;
};

/** Layout: flush with popper — no inner rounding or side gutters (theme handles chrome). */
function layoutSx(): SxProps<Theme> {
  return {
    width: "100%",
    maxWidth: "100%",
    borderRadius: 0,
    overflow: "hidden",
    "& .MuiDateCalendar-root": {
      width: "100%",
      maxWidth: "100%",
    },
  };
}

/** Sélecteur de date MUI X — calendrier aligné sur le thème global (tokens + `theme.components`). */
export function GiDatePicker({
  id,
  label,
  value,
  onChange,
  disabled,
  error,
  helperText,
  size = "small",
  fullWidth,
  sx,
}: GiDatePickerProps) {
  const theme = useTheme();
  const parsed = useMemo(() => {
    if (!value?.trim()) return null;
    const d = dayjs(value, "YYYY-MM-DD", true);
    return d.isValid() ? d : null;
  }, [value]);

  return (
    <DatePicker
      label={label}
      value={parsed}
      onChange={(nv: Dayjs | null) => {
        onChange(nv?.isValid() ? nv.format("YYYY-MM-DD") : "");
      }}
      format="DD/MM/YYYY"
      disabled={disabled}
      slotProps={{
        textField: {
          id,
          size,
          fullWidth,
          error,
          helperText,
          sx,
          InputLabelProps: { shrink: true },
        },
        openPickerButton: {
          sx: {
            borderRadius: 1.25,
            color: "primary.light",
            "&:hover": {
              backgroundColor: alpha(theme.palette.primary.main, 0.12),
            },
          },
        },
        popper: {
          placement: "bottom-start",
          sx: { zIndex: (t) => t.zIndex.modal + 2 },
        },
        layout: {
          sx: layoutSx(),
        },
        actionBar: {
          actions: ["clear", "today"],
        },
      }}
    />
  );
}

/** Variante branchée sur react-hook-form (valeur texte `YYYY-MM-DD`). */
export function GiDatePickerRhf<T extends FieldValues>({
  name,
  control,
  label,
  disabled,
  fullWidth,
  size,
  sx,
}: {
  name: FieldPath<T>;
  control: Control<T>;
  label: string;
  disabled?: boolean;
  fullWidth?: boolean;
  size?: TextFieldProps["size"];
  sx?: SxProps<Theme>;
}) {
  const id = `gi-date-${String(name).replaceAll(".", "-")}`;
  return (
    <Controller
      name={name}
      control={control}
      render={({ field, fieldState }) => (
        <GiDatePicker
          id={id}
          label={label}
          value={typeof field.value === "string" ? field.value : ""}
          onChange={field.onChange}
          disabled={disabled}
          error={!!fieldState.error}
          helperText={fieldState.error?.message as string | undefined}
          fullWidth={fullWidth}
          size={size}
          sx={sx}
        />
      )}
    />
  );
}
