import React, { useState, useEffect, useRef, useCallback, forwardRef, useImperativeHandle } from 'react';
import { z } from 'zod';
import { Button } from '@shared';

function buildSchema(assignment) {
  const { value_type, min, max, allowed_values } = assignment;
  if (value_type === 'boolean') {
    return z.boolean({ required_error: 'Please select Yes or No' });
  }
  if (value_type === 'number') {
    let schema = z.number({ required_error: 'A value is required', invalid_type_error: 'Must be a number' });
    if (min !== null && min !== undefined) schema = schema.min(min, `Must be at least ${min}`);
    if (max !== null && max !== undefined) schema = schema.max(max, `Must be at most ${max}`);
    return schema;
  }
  if (value_type === 'enum' && allowed_values?.length) {
    return z.enum(allowed_values, { required_error: 'Please select a value' });
  }
  return z.string().min(1, 'Please select a value');
}

function coerce(rawValue, value_type) {
  if (value_type === 'number') return rawValue === '' ? NaN : Number(rawValue);
  if (value_type === 'boolean') {
    if (rawValue === '') return undefined;
    return rawValue === 'true';
  }
  return rawValue;
}

export const AttributeForm = forwardRef(function AttributeForm({ assignment, onSubmit, submitting = false }, ref) {
  const startRef = useRef(performance.now());
  const [rawValue, setRawValue] = useState(() =>
    assignment.value_type === 'number' ? String(assignment.min ?? 0) : ''
  );
  const [fieldError, setFieldError] = useState(null);

  useEffect(() => {
    startRef.current = performance.now();
    setRawValue(assignment.value_type === 'number' ? String(assignment.min ?? 0) : '');
    setFieldError(null);
  }, [assignment.attribute_key]);

  const handleSubmit = useCallback((e) => {
    e?.preventDefault?.();
    if (submitting) return;
    const val = coerce(rawValue, assignment.value_type);
    if (assignment.required && (val === undefined || val === '' || (typeof val === 'number' && isNaN(val)))) {
      setFieldError('This field is required');
      return;
    }
    const result = buildSchema(assignment).safeParse(val);
    if (!result.success) {
      setFieldError(result.error.issues[0]?.message ?? 'Invalid value');
      return;
    }
    setFieldError(null);
    onSubmit(result.data, Math.round(performance.now() - startRef.current));
  }, [assignment, rawValue, onSubmit, submitting]);

  useImperativeHandle(ref, () => ({ submit: handleSubmit }), [handleSubmit]);

  const { value_type, allowed_values, min, max, step, prompt, attribute_name, required } = assignment;

  return (
    <form onSubmit={handleSubmit} className="flex flex-col gap-4" noValidate>
      <div>
        <p className="text-sm font-semibold text-gray-800 mb-1">
          {attribute_name}
          {required && <span className="text-red-500 ml-1" aria-hidden="true">*</span>}
        </p>
        <p className="text-sm text-gray-600 mb-3">{prompt}</p>

        {value_type === 'boolean' && (
          <BooleanField value={rawValue} onChange={setRawValue} />
        )}
        {value_type === 'number' && (
          <NumberField value={rawValue} onChange={setRawValue} min={min} max={max} step={step} />
        )}
        {value_type === 'enum' && (
          <EnumField value={rawValue} onChange={setRawValue} allowed_values={allowed_values || []} />
        )}

        {fieldError && (
          <p role="alert" className="mt-2 text-sm text-red-600">{fieldError}</p>
        )}
      </div>

      <Button type="submit" variant="primary" disabled={submitting} className="self-start">
        {submitting ? 'Submitting…' : 'Submit  ↵ Enter'}
      </Button>
    </form>
  );
});

function BooleanField({ value, onChange }) {
  return (
    <div className="flex gap-6" role="radiogroup" aria-label="Value">
      {[{ label: 'Yes', val: 'true' }, { label: 'No', val: 'false' }].map(({ label, val }) => (
        <label key={val} className="flex items-center gap-2 cursor-pointer">
          <input
            type="radio"
            name="wb-boolean"
            value={val}
            checked={value === val}
            onChange={() => onChange(val)}
            className="h-4 w-4 text-blue-600 focus:ring-blue-500 focus:ring-offset-1"
          />
          <span className="text-sm font-medium text-gray-900">{label}</span>
        </label>
      ))}
    </div>
  );
}

function NumberField({ value, onChange, min, max, step }) {
  const numMin = min ?? 0;
  const numMax = max ?? 100;
  const numStep = step ?? 1;
  return (
    <div className="flex flex-col gap-2">
      <div className="flex items-center gap-3">
        <input
          type="range"
          min={numMin}
          max={numMax}
          step={numStep}
          value={value || numMin}
          onChange={(e) => onChange(e.target.value)}
          className="flex-1 h-2 rounded appearance-none cursor-pointer accent-blue-600"
          aria-label="Value slider"
        />
        <input
          type="number"
          min={numMin}
          max={numMax}
          step={numStep}
          value={value}
          onChange={(e) => onChange(e.target.value)}
          className="w-24 px-2 py-1.5 border border-gray-300 rounded text-sm text-right focus:outline-none focus:ring-2 focus:ring-blue-500 focus:border-blue-500"
          aria-label="Value"
        />
      </div>
      {min !== null && max !== null && (
        <div className="flex justify-between text-xs text-gray-400">
          <span>{min}</span>
          <span>{max}</span>
        </div>
      )}
    </div>
  );
}

function EnumField({ value, onChange, allowed_values }) {
  if (allowed_values.length > 5) {
    return (
      <select
        value={value}
        onChange={(e) => onChange(e.target.value)}
        className="block w-full px-3 py-2 border border-gray-300 rounded-md text-sm focus:outline-none focus:ring-2 focus:ring-blue-500 focus:border-blue-500"
        aria-label="Value"
      >
        <option value="">Select a value…</option>
        {allowed_values.map((v) => (
          <option key={v} value={v}>{v}</option>
        ))}
      </select>
    );
  }
  return (
    <div className="flex flex-col gap-2" role="radiogroup" aria-label="Value">
      {allowed_values.map((v) => (
        <label key={v} className="flex items-center gap-2 cursor-pointer">
          <input
            type="radio"
            name="wb-enum"
            value={v}
            checked={value === v}
            onChange={() => onChange(v)}
            className="h-4 w-4 text-blue-600 focus:ring-blue-500 focus:ring-offset-1"
          />
          <span className="text-sm text-gray-900">{v}</span>
        </label>
      ))}
    </div>
  );
}
