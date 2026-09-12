import { describe, expect, it } from 'vitest'
import { buildFilter, literal, newCondition, parseFilter } from '../ruleExpressions'
import type { FilterDraft } from '../ruleExpressions'

describe('guided rule expressions', () => {
  it('quotes identifiers and literal text without interpreting SQL or wildcard characters', () => {
    const draft: FilterDraft = {
      join: 'AND',
      conditions: [{ column: 'patient"name', operator: 'contains', value: { type: 'text', text: "O'Brien%_'); DROP TABLE patients; --" } }]
    }
    const sql = buildFilter(draft)!
    expect(sql).toBe('strpos("patient""name", \'O\'\'Brien%_\'\'); DROP TABLE patients; --\') > 0')
    expect(parseFilter(sql)).toEqual(draft)
  })

  it('preserves large numbers and handles dates, booleans and null predicates', () => {
    const draft: FilterDraft = {
      join: 'AND', conditions: [
        { column: 'id', operator: 'gte', value: { type: 'number', text: '900719925474099312345' } },
        { column: 'birth_date', operator: 'lt', value: { type: 'date', text: '2024-02-29' } },
        { column: 'active', operator: 'eq', value: { type: 'boolean', text: 'false' } },
        { ...newCondition('discharge_date'), operator: 'is_null' }
      ]
    }
    expect(buildFilter(draft)).toContain('900719925474099312345')
    expect(parseFilter(buildFilter(draft)!)).toEqual(draft)
    expect(buildFilter({ join: 'AND', conditions: [{ ...newCondition('id'), value: { type: 'number', text: '1; SELECT 2' } }] })).toBeNull()
    expect(buildFilter({ join: 'AND', conditions: [{ ...newCondition('date'), value: { type: 'date', text: '2023-02-29' } }] })).toBeNull()
  })

  it('recognizes basic SQL and homogeneous groups while preserving unsupported SQL for the editor', () => {
    expect(parseFilter("((age >= 18) OR (starts_with(name, 'Al'))) ")?.conditions).toHaveLength(2)
    for (const sql of [
      'age > 18 OR active = true AND id = 1',
      '(age > 18 OR active = true) AND id = 1',
      '(age > 18 AND active = true',
      'age > 18) AND active = true',
      'CAST(id AS VARCHAR) = \'1\'',
      'id IN (SELECT id FROM patients)',
      'id = 1 -- comment',
      "CURRENT_USER = 'admin'",
      "strpos(name, 'a') > '0'",
      "email LIKE 'a%'"
    ]) expect(parseFilter(sql), sql).toBeNull()
    expect(parseFilter('id != 42')?.conditions[0].operator).toBe('ne')
  })

  it('distinguishes empty rules, incomplete forms and intentionally empty strings', () => {
    expect(buildFilter({ join: 'AND', conditions: [] })).toBe('')
    expect(parseFilter(' ')).toEqual({ join: 'AND', conditions: [] })
    expect(buildFilter({ join: 'AND', conditions: [newCondition('name')] })).toBeNull()
  })

  it('validates timestamps and normalizes datetime-local input without losing fractional precision', () => {
    expect(literal({ type: 'timestamp', text: '2024-02-29T13:02' })).toBe("TIMESTAMP '2024-02-29 13:02:00'")
    expect(literal({ type: 'timestamp', text: '2024-02-29 13:02:03.123456789' })).toBe("TIMESTAMP '2024-02-29 13:02:03.123456789'")
    for (const text of ['2023-02-29 00:00:00', '2024-01-01 24:00:00', '2024-01-01 00:60:00', '2024-01-01 00:00:60', "2024-01-01 00:00:00'; SELECT 1", '2024-01-01 00:00:00 UTC']) {
      expect(literal({ type: 'timestamp', text })).toBeNull()
    }
    const sql = `"admitted_at" >= TIMESTAMP '2024-02-29 13:02:03.123456'`
    expect(buildFilter(parseFilter(sql)!)).toBe(sql)
  })
})
