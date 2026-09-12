import { literal, numberPattern, quoteColumn, quoteText, Reader, tokenize, type RuleValue } from './ruleExpressions'

export type ColumnInfo = { name: string; type: string | null }
export type TypeFamily = 'text' | 'integer' | 'number' | 'boolean' | 'date' | 'timestamp' | 'binary' | 'other' | 'unknown'
export type TransformDraft = { functionId: string; values: Record<string, string | null> }
export type ParameterDefinition = {
  key: string
  label: string
  help: string
  kind: 'text' | 'number' | 'integer' | 'value' | 'seed' | 'unit' | 'secret'
  options?: { value: string; label: string }[]
  defaultValue?: string
}
export type FunctionDefinition = {
  id: string
  label: string
  group: string
  description: string
  example: string
  parameters: ParameterDefinition[]
  caution?: (type: string | null) => string | undefined
}

const normalizeType = (type: string) => type.trim().toLowerCase().replace(/\s+/g, ' ').replace(/\s*([(),])\s*/g, '$1')

export function typeFamily(type: string | null): TypeFamily {
  if (!type?.trim()) return 'unknown'
  const name = normalizeType(type)
  if (/^(varchar|char)(\(\d+\))?$/.test(name)) return 'text'
  if (/^(tinyint|smallint|integer|bigint)$/.test(name)) return 'integer'
  if (/^(real|double|decimal(?:\(\d+(?:,\d+)?\))?)$/.test(name)) return 'number'
  if (name === 'boolean') return 'boolean'
  if (name === 'date') return 'date'
  if (/^timestamp(?:\(\d+\))?$/.test(name)) return 'timestamp'
  if (name === 'varbinary') return 'binary'
  return 'other'
}

const dateUnits = ['day', 'week', 'month', 'quarter', 'year'].map(value => ({ value, label: value }))
const param = (key: string, label: string, kind: ParameterDefinition['kind'], help: string, defaultValue?: string): ParameterDefinition => ({ key, label, kind, help, ...(defaultValue === undefined ? {} : { defaultValue }) })
const value = param('value', 'Value', 'value', 'Use the column type. Binary values use hexadecimal bytes; timestamps use YYYY-MM-DD HH:mm:ss.')
const unit: ParameterDefinition = { key: 'unit', label: 'Unit', kind: 'unit', help: 'Calendar unit applied to the date or timestamp.', options: dateUnits, defaultValue: 'day' }
const cipherCaution = (type: string | null) => type && /^(char|varchar)\(\d+\)$/.test(normalizeType(type))
  ? 'Encrypted text is longer than the original. This column has a length limit: truncation can prevent decryption.' : undefined

export const ruleFunctions: FunctionDefinition[] = [
  { id: 'null', label: 'Hide value', group: 'General', description: 'Return NULL for every row.', example: '"Alice Martin" -> NULL', parameters: [] },
  { id: 'replace', label: 'Replace with a value', group: 'General', description: 'Use one fixed value instead of the current value.', example: '"Alice Martin" -> "REDACTED"\n"Bob Smith" -> "REDACTED"', parameters: [value] },
  { id: 'coalesce', label: 'Fill missing values', group: 'General', description: 'Replace NULL values and keep other values.', example: 'NULL -> "Unknown"\n"Alice Martin" -> "Alice Martin"', parameters: [value] },
  { id: 'encrypt', label: 'Encrypt', group: 'MaskQL', description: 'Encrypt with the password configured on the MaskQL server.', example: '142 -> 1678131456', parameters: [], caution: cipherCaution },
  { id: 'decrypt', label: 'Decrypt', group: 'MaskQL', description: 'Decrypt compatible MaskQL ciphertext using its original password.', example: '1678131456 -> 142', parameters: [param('password', 'Password', 'secret', 'The encryption password. It is stored in the rule expression.')] },
  { id: 'text_pseudo', label: 'Pseudonymize text', group: 'MaskQL', description: 'Replace detected identifiers in text using an explicit seed.', example: '"Alice Martin has asthma." -> "Emma Wilson has asthma."', parameters: [param('seed', 'Seed', 'seed', 'Context passed to the pseudonymizer: one fixed value for the rule, or a patient ID column for a context per patient.')] },
  { id: 'pdf_to_text', label: 'Extract PDF text', group: 'MaskQL', description: 'Extract text from PDF bytes. The result contains UTF-8 bytes, not a PDF; scanned images need OCR.', example: 'PDF: "Diagnosis: asthma." -> Text: "Diagnosis: asthma."', parameters: [] },
  { id: 'lower', label: 'Lowercase', group: 'Text', description: 'Convert letters to lowercase.', example: '"ALICE MARTIN" -> "alice martin"', parameters: [] },
  { id: 'upper', label: 'Uppercase', group: 'Text', description: 'Convert letters to uppercase.', example: '"Alice Martin" -> "ALICE MARTIN"', parameters: [] },
  { id: 'trim', label: 'Trim whitespace', group: 'Text', description: 'Remove whitespace at the beginning and end.', example: '"  Alice Martin  " -> "Alice Martin"', parameters: [] },
  { id: 'replace_text', label: 'Replace text', group: 'Text', description: 'Replace every occurrence of a literal string.', example: '"Ward A" -> "Unit A"', parameters: [param('search', 'Text to find', 'text', 'Literal text to replace.'), param('replacement', 'Replacement', 'text', 'Replacement text; leave empty to remove matches.', '')] },
  { id: 'regexp_replace', label: 'Replace a pattern', group: 'Text', description: 'Replace matches of a regular expression.', example: '"Patient 12345" -> "Patient XXXXX"', parameters: [param('pattern', 'Pattern', 'text', 'Trino regular expression, for example [0-9]+.'), param('replacement', 'Replacement', 'text', 'Replacement text; $1 refers to a captured group.', '')] },
  { id: 'substring', label: 'Keep part of the text', group: 'Text', description: 'Keep a fixed number of characters from a starting position.', example: '"Alice Martin" -> "Alice"', parameters: [param('start', 'Start position', 'integer', 'Positions start at 1; negative positions count from the end.', '1'), param('length', 'Length', 'integer', 'Number of characters to keep, zero or greater.')] },
  { id: 'concat_prefix', label: 'Add a prefix', group: 'Text', description: 'Add fixed text before the current value.', example: '"142" -> "PAT-142"', parameters: [param('text', 'Prefix', 'text', 'Text to add at the beginning.')] },
  { id: 'concat_suffix', label: 'Add a suffix', group: 'Text', description: 'Add fixed text after the current value.', example: '"PAT-142" -> "PAT-142-TEST"', parameters: [param('text', 'Suffix', 'text', 'Text to add at the end.')] },
  { id: 'lpad', label: 'Pad on the left', group: 'Text', description: 'Pad to a target length on the left. Longer values are shortened.', example: '"142" -> "00000142"', parameters: [param('size', 'Target length', 'integer', 'Number of characters in the result, zero or greater.'), param('pad', 'Padding text', 'text', 'Nonempty text repeated as padding.', '0')] },
  { id: 'rpad', label: 'Pad on the right', group: 'Text', description: 'Pad to a target length on the right. Longer values are shortened.', example: '"142" -> "14200000"', parameters: [param('size', 'Target length', 'integer', 'Number of characters in the result, zero or greater.'), param('pad', 'Padding text', 'text', 'Nonempty text repeated as padding.', 'X')] },
  { id: 'round', label: 'Round', group: 'Numbers', description: 'Round to a chosen number of decimal places.', example: '72.678 -> 72.7', parameters: [param('decimals', 'Decimal places', 'integer', 'Use zero for whole numbers or a negative value for tens or hundreds.', '0')] },
  { id: 'abs', label: 'Absolute value', group: 'Numbers', description: 'Remove the sign from a number.', example: '-12 -> 12', parameters: [] },
  { id: 'floor', label: 'Round down', group: 'Numbers', description: 'Round down to a whole number.', example: '12.9 -> 12', parameters: [] },
  { id: 'ceil', label: 'Round up', group: 'Numbers', description: 'Round up to a whole number.', example: '12.1 -> 13', parameters: [] },
  { id: 'date_trunc', label: 'Reduce date precision', group: 'Dates', description: 'Keep the beginning of the chosen calendar period.', example: '1990-05-17 -> 1990-05-01', parameters: [{ ...unit, defaultValue: 'month' }] },
  { id: 'date_add', label: 'Shift date', group: 'Dates', description: 'Add or subtract a fixed number of calendar units.', example: '1990-05-17 -> 1990-05-24', parameters: [unit, param('amount', 'Amount', 'integer', 'Positive values move forward; negative values move backward.')] },
  { id: 'boolean_not', label: 'Invert boolean', group: 'Booleans', description: 'Swap true and false; NULL remains NULL.', example: 'true -> false\nfalse -> true', parameters: [] },
]

function supports(id: string, type: string | null): boolean {
  if (id === 'null') return true
  const family = typeFamily(type)
  if (family === 'unknown' || family === 'other') return false
  if (id === 'replace' || id === 'coalesce') return true
  if (id === 'encrypt' || id === 'decrypt') {
    if (family === 'number') return /^(real|double)$/.test(normalizeType(type!))
    if (family === 'timestamp') return Number(/\((\d+)\)/.exec(type!)?.[1] ?? '3') <= 6
    return true
  }
  if (id === 'pdf_to_text') return family === 'binary'
  if (id === 'text_pseudo' || ['lower', 'upper', 'trim', 'replace_text', 'regexp_replace', 'substring', 'concat_prefix', 'concat_suffix', 'lpad', 'rpad'].includes(id)) return family === 'text'
  if (['round', 'abs', 'floor', 'ceil'].includes(id)) return family === 'number' || family === 'integer'
  if (id === 'date_trunc' || id === 'date_add') return family === 'date' || family === 'timestamp'
  return id === 'boolean_not' && family === 'boolean'
}

export function compatibleFunctions(type: string | null): FunctionDefinition[] {
  return ruleFunctions.filter(definition => supports(definition.id, type))
}

export function newTransform(id: string): TransformDraft {
  const definition = ruleFunctions.find(item => item.id === id)
  const values: Record<string, string | null> = Object.fromEntries((definition?.parameters ?? []).map(parameter => [parameter.key, parameter.defaultValue ?? null]))
  if (id === 'text_pseudo') values.seedSource = 'fixed'
  return { functionId: id, values }
}

function integer(text: string | null | undefined, min = '-9223372036854775808', max = '9223372036854775807'): string | null {
  if (text == null || !/^[+-]?\d+$/.test(text.trim())) return null
  const number = BigInt(text.trim())
  return number >= BigInt(min) && number <= BigInt(max) ? text.trim() : null
}

function typedLiteral(text: string | null | undefined, type: string): string | null {
  if (text == null) return null
  const family = typeFamily(type)
  let sql: string | null
  if (family === 'binary') return /^(?:[a-fA-F0-9]{2})*$/.test(text) ? `from_hex(${quoteText(text)})` : null
  if (family === 'integer') {
    const bounds: Record<string, [string, string]> = {
      tinyint: ['-128', '127'], smallint: ['-32768', '32767'], integer: ['-2147483648', '2147483647'], bigint: ['-9223372036854775808', '9223372036854775807'],
    }
    sql = integer(text, ...bounds[normalizeType(type)])
  }
  else if (family === 'text') sql = quoteText(text)
  else if (family === 'number') sql = numberPattern.test(text.trim()) ? text.trim() : null
  else if (family === 'boolean' || family === 'date' || family === 'timestamp') sql = literal({ type: family, text })
  else return null
  if (sql === null) return null
  // Keep typed constants in the same overload family as the source column.
  return family === 'text' || family === 'date' || family === 'boolean' ? sql : `CAST(${sql} AS ${normalizeType(type).toUpperCase()})`
}

export function buildTransform(column: string, type: string | null, transform: TransformDraft | null): string | null {
  if (!transform) return ''
  if (!column) return null
  const input = quoteColumn(column)
  const id = transform.functionId
  if (!supports(id, type)) return null
  const values = transform.values
  const text = (key: string) => values[key] == null ? null : quoteText(values[key]!)
  const call = (name: string, args: (string | null)[]) => args.some(value => value === null) ? null : `${name}(${args.join(', ')})`
  if (id === 'null') return typeFamily(type) === 'other' || typeFamily(type) === 'unknown' ? 'NULL' : `CAST(NULL AS ${normalizeType(type!).toUpperCase()})`
  if (id === 'replace') return typedLiteral(values.value, type!)
  if (id === 'coalesce') return call('coalesce', [input, typedLiteral(values.value, type!)])
  if (id === 'text_pseudo') {
    const seed = values.seedSource === 'column'
      ? values.seed ? `CAST(${quoteColumn(values.seed)} AS VARCHAR)` : null
      : values.seedSource === 'fixed' ? text('seed') : null
    return call(id, [input, seed])
  }
  if (id === 'decrypt') return call(id, [/^char\(/.test(normalizeType(type!)) ? `CAST(${input} AS VARCHAR)` : input, values.password ? text('password') : null])
  if (id === 'replace_text') return call('replace', [input, text('search'), text('replacement')])
  if (id === 'regexp_replace') return call(id, [input, text('pattern'), text('replacement')])
  if (id === 'substring') return call(id, [input, integer(values.start, '-2147483648', '2147483647'), integer(values.length, '0', '2147483647')])
  if (id === 'concat_prefix') return call('concat', [text('text'), input])
  if (id === 'concat_suffix') return call('concat', [input, text('text')])
  if (id === 'lpad' || id === 'rpad') return call(id, [input, integer(values.size, '0', '2147483647'), values.pad ? text('pad') : null])
  if (id === 'round') return call(id, [input, integer(values.decimals, '-2147483648', '2147483647')])
  if (id === 'date_trunc' || id === 'date_add') {
    if (!dateUnits.some(unit => unit.value === values.unit)) return null
    return call(id, id === 'date_add' ? [text('unit'), integer(values.amount), input] : [text('unit'), input])
  }
  if (id === 'boolean_not') return `NOT (${input})`
  return ['encrypt', 'pdf_to_text', 'lower', 'upper', 'trim', 'abs', 'floor', 'ceil'].includes(id) ? call(id, [input]) : null
}

type Expression = { kind: 'column'; name: string } | { kind: 'literal'; value: RuleValue } | { kind: 'null' } | { kind: 'call'; name: string; args: Expression[] } | { kind: 'cast'; value: Expression; type: string } | { kind: 'not'; value: Expression }

function readExpression(reader: Reader, depth = 0): Expression | null {
  if (depth > 64) return null
  if (reader.take('(')) {
    const inner = readExpression(reader, depth + 1)
    return inner && reader.take(')') ? inner : null
  }
  if (reader.take('NULL')) return { kind: 'null' }
  if (reader.take('NOT')) {
    const inner = readExpression(reader, depth + 1)
    return inner ? { kind: 'not', value: inner } : null
  }
  if (reader.take('CAST')) {
    if (!reader.take('(')) return null
    const inner = readExpression(reader, depth + 1)
    if (!inner || !reader.take('AS')) return null
    const name = reader.tokens[reader.index]
    if (name?.kind !== 'word') return null
    reader.index++
    let type = name.text
    if (reader.take('(')) {
      const parameters: string[] = []
      do {
        const parameter = reader.tokens[reader.index]
        if (parameter?.kind !== 'number' || !/^\d+$/.test(parameter.text) || parameters.length === 2) return null
        parameters.push(parameter.text)
        reader.index++
      } while (reader.take(','))
      if (!reader.take(')')) return null
      type += `(${parameters.join(',')})`
    }
    return reader.take(')') && typeFamily(type) !== 'other' && typeFamily(type) !== 'unknown' ? { kind: 'cast', value: inner, type } : null
  }
  const value = reader.value()
  if (value) return { kind: 'literal', value }
  const token = reader.tokens[reader.index]
  if (token?.kind === 'word' && reader.tokens[reader.index + 1]?.text === '(') {
    reader.index += 2
    const args: Expression[] = []
    do {
      const argument = readExpression(reader, depth + 1)
      if (!argument) return null
      args.push(argument)
    } while (reader.take(','))
    return reader.take(')') ? { kind: 'call', name: token.text.toLowerCase(), args } : null
  }
  const column = reader.column()
  return column === null ? null : { kind: 'column', name: column }
}

function readTypedValue(expression: Expression, type: string): string | null {
  if (expression.kind === 'cast') {
    if (normalizeType(expression.type) !== normalizeType(type)) return null
    expression = expression.value
  }
  const family = typeFamily(type)
  if (family === 'binary' && expression.kind === 'call' && expression.name === 'from_hex' && expression.args.length === 1) {
    const argument = expression.args[0]
    return argument.kind === 'literal' && argument.value.type === 'text' && typedLiteral(argument.value.text, type) !== null ? argument.value.text : null
  }
  if (expression.kind !== 'literal') return null
  const expected = family === 'integer' ? 'number' : family
  return expression.value.type === expected && typedLiteral(expression.value.text, type) !== null ? expression.value.text : null
}

const callLayouts: Record<string, { id: string; input: number; parameters: string[] }[]> = {
  encrypt: [{ id: 'encrypt', input: 0, parameters: [] }], decrypt: [{ id: 'decrypt', input: 0, parameters: ['password'] }],
  text_pseudo: [{ id: 'text_pseudo', input: 0, parameters: ['seed'] }], pdf_to_text: [{ id: 'pdf_to_text', input: 0, parameters: [] }],
  lower: [{ id: 'lower', input: 0, parameters: [] }], upper: [{ id: 'upper', input: 0, parameters: [] }], trim: [{ id: 'trim', input: 0, parameters: [] }],
  coalesce: [{ id: 'coalesce', input: 0, parameters: ['value'] }], replace: [{ id: 'replace_text', input: 0, parameters: ['search', 'replacement'] }],
  regexp_replace: [{ id: 'regexp_replace', input: 0, parameters: ['pattern', 'replacement'] }], substring: [{ id: 'substring', input: 0, parameters: ['start', 'length'] }],
  concat: [{ id: 'concat_prefix', input: 1, parameters: ['text'] }, { id: 'concat_suffix', input: 0, parameters: ['text'] }],
  lpad: [{ id: 'lpad', input: 0, parameters: ['size', 'pad'] }], rpad: [{ id: 'rpad', input: 0, parameters: ['size', 'pad'] }],
  round: [{ id: 'round', input: 0, parameters: ['decimals'] }], abs: [{ id: 'abs', input: 0, parameters: [] }], floor: [{ id: 'floor', input: 0, parameters: [] }], ceil: [{ id: 'ceil', input: 0, parameters: [] }],
  date_trunc: [{ id: 'date_trunc', input: 1, parameters: ['unit'] }], date_add: [{ id: 'date_add', input: 2, parameters: ['unit', 'amount'] }],
}

function readTransform(column: string, type: string | null, expression: Expression): TransformDraft | null {
  if (expression.kind === 'null') return newTransform('null')
  if (expression.kind === 'cast' && expression.value.kind === 'null' && type && normalizeType(expression.type) === normalizeType(type)) return newTransform('null')
  if (type) {
    const value = readTypedValue(expression, type)
    if (value !== null) return { functionId: 'replace', values: { value } }
  }
  if (expression.kind === 'not') {
    return expression.value.kind === 'column' && expression.value.name === column ? newTransform('boolean_not') : null
  }
  if (expression.kind !== 'call') return null
  for (const layout of callLayouts[expression.name] ?? []) {
    if (expression.args.length !== layout.parameters.length + 1) continue
    let input = expression.args[layout.input]
    if (layout.id === 'decrypt' && type && /^char\(/.test(normalizeType(type)) && input.kind === 'cast' && normalizeType(input.type) === 'varchar') input = input.value
    if (input.kind !== 'column' || input.name !== column) continue
    const transform = newTransform(layout.id)
    const args = expression.args.filter((_, index) => index !== layout.input)
    let valid = true
    for (let index = 0; index < layout.parameters.length; index++) {
      const key = layout.parameters[index]
      const argument = args[index]
      if (key === 'seed' && argument.kind === 'cast' && normalizeType(argument.type) === 'varchar' && argument.value.kind === 'column') {
        transform.values.seedSource = 'column'
        transform.values.seed = argument.value.name
      } else if (key === 'value') {
        transform.values.value = type ? readTypedValue(argument, type) : null
        if (transform.values.value === null) valid = false
      } else {
        const parameter = ruleFunctions.find(item => item.id === layout.id)!.parameters.find(item => item.key === key)!
        const kind = ['integer', 'number'].includes(parameter.kind) ? 'number' : 'text'
        if (argument.kind !== 'literal' || argument.value.type !== kind || argument.value.text === null) { valid = false; break }
        transform.values[key] = argument.value.text
      }
    }
    if (valid) return transform
  }
  return null
}

export function parseTransform(column: string, type: string | null, sql: string): { transform: TransformDraft | null } | null {
  const tokens = tokenize(sql)
  if (!tokens) return null
  if (!tokens.length) return { transform: null }
  const reader = new Reader(tokens)
  const expression = readExpression(reader)
  if (!expression || !reader.done) return null
  if (expression.kind === 'column') return expression.name === column ? { transform: null } : null
  const transform = readTransform(column, type, expression)
  return transform && buildTransform(column, type, transform) !== null ? { transform } : null
}
