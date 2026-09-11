import { describe, expect, it } from 'vitest'
import { buildTransform, compatibleFunctions, newTransform, parseTransform, ruleFunctions, typeFamily, type TransformDraft } from '../ruleFunctions'

const draft = (functionId: string, values: TransformDraft['values'] = {}): TransformDraft => ({ ...newTransform(functionId), values: { ...newTransform(functionId).values, ...values } })
const ids = (type: string | null) => compatibleFunctions(type).map(item => item.id)

describe('guided transformation catalog', () => {
  it('offers only compatible signatures, including the MaskQL encryption limits', () => {
    for (const type of [null, 'array(varchar)', 'timestamp(3) with time zone', 'time', 'uuid']) expect(ids(type)).toEqual(['null'])
    for (const type of ['varchar', 'char(20)', 'bigint', 'integer', 'smallint', 'tinyint', 'double', 'real', 'boolean', 'date', 'varbinary', 'timestamp(6)']) expect(ids(type)).toContain('encrypt')
    for (const type of ['decimal(18,2)', 'timestamp(9)']) {
      expect(ids(type)).not.toContain('encrypt')
      expect(ids(type)).not.toContain('decrypt')
    }
    expect(ids('boolean')).not.toContain('text_pseudo')
    expect(ids('varbinary')).toContain('pdf_to_text')
    expect(ids('varchar')).not.toContain('pdf_to_text')
    expect(typeFamily(' DECIMAL ( 18, 2 ) ')).toBe('number')
    expect(typeFamily('timestamp(6)')).toBe('timestamp')
    expect(ruleFunctions.find(item => item.id === 'encrypt')!.caution?.('varchar(20)')).toContain('truncation')
  })

  it('quotes identifiers and string parameters without interpreting their contents', () => {
    const transform = draft('replace_text', { search: "O'Brien", replacement: "X'); SELECT 1 --" })
    const sql = buildTransform('patient"name', 'varchar', transform)!
    expect(sql).toBe('replace("patient""name", \'O\'\'Brien\', \'X\'\'); SELECT 1 --\')')
    expect(parseTransform('patient"name', 'varchar', sql)).toEqual({ transform })
    expect(parseTransform('name', 'varchar', 'lower(name)')).toEqual({ transform: draft('lower') })
  })

  it('preserves explicit seeds, including a quoted seed column', () => {
    const columnSeed = draft('text_pseudo', { seedSource: 'column', seed: 'patient"id' })
    const fixedSeed = draft('text_pseudo', { seed: "patient-é-'142'" })
    expect(buildTransform('note', 'varchar', columnSeed)).toBe('text_pseudo("note", CAST("patient""id" AS VARCHAR))')
    for (const transform of [columnSeed, fixedSeed]) expect(parseTransform('note', 'varchar', buildTransform('note', 'varchar', transform)!)).toEqual({ transform })
    expect(buildTransform('active', 'boolean', fixedSeed)).toBeNull()
    expect(buildTransform('note', 'varchar', newTransform('text_pseudo'))).toBeNull()
    expect(parseTransform('note', 'varchar', 'text_pseudo(note)')).toBeNull()
  })

  it('preserves typed constants and exact integer values', () => {
    const bigint = draft('replace', { value: '9007199254740993123' })
    expect(buildTransform('id', 'bigint', bigint)).toBe('CAST(9007199254740993123 AS BIGINT)')
    expect(parseTransform('id', 'bigint', buildTransform('id', 'bigint', bigint)!)).toEqual({ transform: bigint })
    expect(buildTransform('id', 'bigint', draft('replace', { value: '9223372036854775808' }))).toBeNull()
    expect(buildTransform('id', 'bigint', draft('replace', { value: '1.5' }))).toBeNull()
    expect(buildTransform('id', 'tinyint', draft('replace', { value: '128' }))).toBeNull()
    expect(buildTransform('x', 'real', draft('replace', { value: '1.5' }))).toBe('CAST(1.5 AS REAL)')
    expect(buildTransform('x', 'integer', draft('null'))).toBe('CAST(NULL AS INTEGER)')
    const timestamp = draft('replace', { value: '2024-02-29 13:02:03.123456' })
    const sql = buildTransform('admitted_at', 'timestamp(6)', timestamp)!
    expect(sql).toBe("CAST(TIMESTAMP '2024-02-29 13:02:03.123456' AS TIMESTAMP(6))")
    expect(parseTransform('admitted_at', 'timestamp(6)', sql)).toEqual({ transform: timestamp })
    expect(buildTransform('cipher', 'char(20)', draft('decrypt', { password: "a'b" }))).toBe('decrypt(CAST("cipher" AS VARCHAR), \'a\'\'b\')')
  })

  it('round-trips every catalog function with complete parameters', () => {
    const cases: [string, string, TransformDraft['values']][] = [
      ['null', 'varchar', {}], ['replace', 'varchar', { value: '' }], ['coalesce', 'boolean', { value: 'false' }],
      ['encrypt', 'bigint', {}], ['decrypt', 'char(20)', { password: 'secret' }], ['text_pseudo', 'varchar', { seed: 'p-1' }],
      ['pdf_to_text', 'varbinary', {}], ['lower', 'varchar', {}], ['upper', 'varchar', {}], ['trim', 'varchar', {}],
      ['replace_text', 'varchar', { search: 'Mr ', replacement: '' }], ['regexp_replace', 'varchar', { pattern: "[O']+", replacement: '$1' }],
      ['substring', 'varchar', { start: '-3', length: '3' }], ['concat_prefix', 'varchar', { text: 'ID-' }], ['concat_suffix', 'varchar', { text: '-masked' }],
      ['lpad', 'varchar', { size: '8' }], ['rpad', 'varchar', { size: '8' }], ['round', 'decimal(18,2)', { decimals: '1' }],
      ['abs', 'integer', {}], ['floor', 'double', {}], ['ceil', 'real', {}], ['date_trunc', 'date', {}],
      ['date_add', 'timestamp(3)', { amount: '-7' }], ['boolean_not', 'boolean', {}],
    ]
    expect(cases.map(([id]) => id)).toEqual(ruleFunctions.map(item => item.id))
    for (const [id, type, values] of cases) {
      const transform = draft(id, values)
      const sql = buildTransform('value', type, transform)
      expect(sql, id).not.toBeNull()
      expect(parseTransform('value', type, sql!), id).toEqual({ transform })
    }
  })

  it('keeps incomplete forms distinct from empty values and leaves complex SQL in the free-form editor', () => {
    expect(buildTransform('name', 'varchar', null)).toBe('')
    expect(parseTransform('name', 'varchar', ' ')).toEqual({ transform: null })
    expect(parseTransform('name', 'varchar', 'name')).toEqual({ transform: null })
    expect(parseTransform('name', 'varchar', 'NULL')).toEqual({ transform: draft('null') })
    expect(buildTransform('name', 'varchar', draft('replace'))).toBeNull()
    expect(buildTransform('name', 'varchar', draft('replace', { value: '' }))).toBe("''")
    expect(buildTransform('name', 'varchar', draft('lpad', { size: '-1' }))).toBeNull()
    expect(buildTransform('name', 'varchar', draft('lpad', { size: '2', pad: '' }))).toBeNull()
    expect(buildTransform('when', 'date', draft('date_add', { unit: 'hour', amount: '1' }))).toBeNull()
    const binary = draft('replace', { value: '00a1FF' })
    expect(buildTransform('bytes', 'varbinary', binary)).toBe("from_hex('00a1FF')")
    expect(parseTransform('bytes', 'varbinary', "from_hex('00a1FF')")).toEqual({ transform: binary })
    expect(buildTransform('bytes', 'varbinary', draft('replace', { value: '0G' }))).toBeNull()
    for (const sql of ["CASE WHEN name IS NULL THEN '' ELSE name END", 'encrypt(other_column)', 'lower(name) -- note', "regexp_replace(name, '[0-9]', upper(name))", 'CAST(name AS BIGINT)', "text_pseudo(name, concat('p', id))", 'substr(name, 1)', 'lower(name) + 1', 'lower(trim(name))', "encrypt('fixed value')", 'coalesce(lower(name), \'Unknown\')', "concat('ID-', trim(name))"]) {
      expect(parseTransform('name', 'varchar', sql), sql).toBeNull()
    }
    for (const [type, sql] of [
      ['double', 'CAST(1 AS DOU BLE)'],
      ['varchar(20)', "CAST('x' AS VARCHAR(2 0))"],
      ['decimal(18,2)', 'CAST(1 AS DECIMAL(1 8, 2))'],
      ['decimal(18,2)', 'CAST(1 AS DECIMAL(18, 2, 0))'],
      ['timestamp(3)', "CAST(TIMESTAMP '2024-01-01 00:00:00' AS TIMESTAMP(+3))"],
      ['bigint', 'encrypt(CAST(42 AS BIGINT))'],
      ['boolean', 'NOT (NOT (name))'],
    ]) expect(parseTransform('name', type, sql), sql).toBeNull()
  })
})
