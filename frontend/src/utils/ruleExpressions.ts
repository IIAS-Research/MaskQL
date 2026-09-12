export type ValueType = 'text' | 'number' | 'boolean' | 'date' | 'timestamp'
export type RuleValue = { type: ValueType; text: string | null }
export type FilterOperator = 'eq' | 'ne' | 'gt' | 'gte' | 'lt' | 'lte' | 'contains' | 'starts' | 'ends' | 'is_null' | 'not_null'
export type FilterCondition = { column: string; operator: FilterOperator; value: RuleValue }
export type FilterDraft = { join: 'AND' | 'OR'; conditions: FilterCondition[] }
export function newCondition(column = ''): FilterCondition {
  return { column, operator: 'eq', value: { type: 'text', text: null } }
}

const comparisons = { eq: '=', ne: '<>', gt: '>', gte: '>=', lt: '<', lte: '<=' } as const
const textFunctions = { contains: 'strpos', starts: 'starts_with', ends: 'ends_with' } as const
export const numberPattern = /^[+-]?(?:\d+(?:\.\d*)?|\.\d+)(?:[eE][+-]?\d+)?$/
export const quoteText = (value: string) => `'${value.replace(/'/g, "''")}'`
export const quoteColumn = (value: string) => `"${value.replace(/"/g, '""')}"`

export function literal(value: RuleValue): string | null {
  if (value.text === null) return null
  switch (value.type) {
    case 'text': return quoteText(value.text)
    case 'number': return numberPattern.test(value.text.trim()) ? value.text.trim() : null
    case 'boolean': return /^(true|false)$/i.test(value.text.trim()) ? value.text.trim().toUpperCase() : null
    case 'date': {
      const text = value.text.trim()
      const date = new Date(`${text}T00:00:00Z`)
      return /^\d{4}-\d{2}-\d{2}$/.test(text) && !Number.isNaN(date.getTime()) && date.toISOString().slice(0, 10) === text
        ? `DATE ${quoteText(text)}` : null
    }
    case 'timestamp': {
      const text = value.text.trim().replace('T', ' ')
      const match = /^(\d{4}-\d{2}-\d{2}) (\d{2}):(\d{2})(?::(\d{2})(\.\d{1,12})?)?$/.exec(text)
      if (!match || literal({ type: 'date', text: match[1] }) === null || Number(match[2]) > 23 || Number(match[3]) > 59 || Number(match[4] ?? '0') > 59) return null
      return `TIMESTAMP ${quoteText(`${match[1]} ${match[2]}:${match[3]}:${match[4] ?? '00'}${match[5] ?? ''}`)}`
    }
  }
}

export function buildFilter(draft: FilterDraft): string | null {
  if (draft.join !== 'AND' && draft.join !== 'OR') return null
  const expressions: string[] = []
  for (const condition of draft.conditions) {
    if (!condition.column) return null
    const column = quoteColumn(condition.column)
    if (condition.operator === 'is_null' || condition.operator === 'not_null') {
      expressions.push(`${column} IS ${condition.operator === 'not_null' ? 'NOT ' : ''}NULL`)
      continue
    }
    const value = literal(condition.value)
    if (value === null) return null
    if (condition.operator in textFunctions) {
      if (condition.value.type !== 'text') return null
      const fn = textFunctions[condition.operator as keyof typeof textFunctions]
      expressions.push(`${fn}(${column}, ${value})${condition.operator === 'contains' ? ' > 0' : ''}`)
    } else {
      const operator = comparisons[condition.operator as keyof typeof comparisons]
      if (!operator) return null
      expressions.push(`${column} ${operator} ${value}`)
    }
  }
  return expressions.length <= 1 ? expressions.join('') : expressions.map(expression => `(${expression})`).join(` ${draft.join} `)
}

export type Token = { kind: 'word' | 'column' | 'text' | 'number' | 'symbol'; text: string }

// Recognize only the builder's grammar; all other SQL stays in the free-form editor.
export function tokenize(sql: string): Token[] | null {
  const pattern = /\s*("(?:[^"]|"")*"|'(?:[^']|'')*'|[+-]?(?:\d+(?:\.\d*)?|\.\d+)(?:[eE][+-]?\d+)?|[a-zA-Z_][a-zA-Z_0-9]*|>=|<=|<>|!=|[(),=<>])/y
  const tokens: Token[] = []
  const text = sql.trim()
  while (pattern.lastIndex < text.length) {
    const match = pattern.exec(text)
    if (!match) return null
    const raw = match[1]
    if (raw.startsWith('"')) tokens.push({ kind: 'column', text: raw.slice(1, -1).replace(/""/g, '"') })
    else if (raw.startsWith("'")) tokens.push({ kind: 'text', text: raw.slice(1, -1).replace(/''/g, "'") })
    else if (numberPattern.test(raw)) tokens.push({ kind: 'number', text: raw })
    else tokens.push({ kind: /^[a-zA-Z_]/.test(raw) ? 'word' : 'symbol', text: raw })
  }
  return tokens
}

export class Reader {
  index = 0
  constructor(readonly tokens: Token[]) {}
  get done() { return this.index === this.tokens.length }
  take(text: string): boolean {
    const token = this.tokens[this.index]
    if (!token || !['word', 'symbol'].includes(token.kind) || token.text.toUpperCase() !== text.toUpperCase()) return false
    this.index++
    return true
  }
  column(): string | null {
    const token = this.tokens[this.index]
    if (!token || !token.text || !['column', 'word'].includes(token.kind)) return null
    if (token.kind === 'word' && /^(AND|OR|IS|NOT|NULL|TRUE|FALSE|DATE|TIMESTAMP|CAST|AS|SELECT|FROM|WHERE|CURRENT_.*|LOCALTIME|LOCALTIMESTAMP|SESSION_USER|SYSTEM_USER|USER)$/i.test(token.text)) return null
    this.index++
    return token.text
  }
  text(): string | null {
    const token = this.tokens[this.index]
    if (token?.kind !== 'text') return null
    this.index++
    return token.text
  }
  value(): RuleValue | null {
    const token = this.tokens[this.index]
    if (!token) return null
    if (token.kind === 'text' || token.kind === 'number') {
      this.index++
      return { type: token.kind, text: token.text }
    }
    if (this.take('TRUE')) return { type: 'boolean', text: 'true' }
    if (this.take('FALSE')) return { type: 'boolean', text: 'false' }
    if (token.kind === 'word' && /^(DATE|TIMESTAMP)$/i.test(token.text)) {
      const date = this.tokens[this.index + 1]
      if (date?.kind !== 'text') return null
      const value: RuleValue = { type: token.text.toLowerCase() as 'date' | 'timestamp', text: date.text }
      if (literal(value) === null) return null
      this.index += 2
      return value
    }
    return null
  }
}

function unwrap(tokens: Token[]): Token[] {
  while (tokens[0]?.text === '(' && tokens[0]?.kind === 'symbol') {
    let depth = 0
    const end = tokens.findIndex(token => {
      if (token.kind === 'symbol' && token.text === '(') depth++
      if (token.kind === 'symbol' && token.text === ')') depth--
      return depth === 0
    })
    if (end !== tokens.length - 1) break
    tokens = tokens.slice(1, -1)
  }
  return tokens
}

function parseCondition(tokens: Token[]): FilterCondition | null {
  const reader = new Reader(unwrap(tokens))
  for (const [operator, fn] of Object.entries(textFunctions)) {
    if (!reader.take(fn)) continue
    if (!reader.take('(')) return null
    const column = reader.column()
    if (!column || !reader.take(',')) return null
    const text = reader.text()
    if (text === null || !reader.take(')')) return null
    if (operator === 'contains') {
      if (!reader.take('>')) return null
      const limit = reader.value()
      if (limit?.type !== 'number' || limit.text !== '0') return null
    }
    return reader.done ? { column, operator: operator as FilterOperator, value: { type: 'text', text } } : null
  }
  const column = reader.column()
  if (!column) return null
  if (reader.take('IS')) {
    const operator = reader.take('NOT') ? 'not_null' : 'is_null'
    return reader.take('NULL') && reader.done ? { ...newCondition(column), operator } : null
  }
  for (const [operator, sql] of Object.entries(comparisons)) {
    if (!reader.take(sql) && !(operator === 'ne' && reader.take('!='))) continue
    const value = reader.value()
    return value && reader.done ? { column, operator: operator as FilterOperator, value } : null
  }
  return null
}

export function parseFilter(sql: string): FilterDraft | null {
  const raw = tokenize(sql)
  if (!raw) return null
  if (raw.length === 0) return { join: 'AND', conditions: [] }
  const tokens = unwrap(raw)
  const groups: Token[][] = []
  let join: 'AND' | 'OR' | undefined
  let depth = 0
  let start = 0
  for (let i = 0; i < tokens.length; i++) {
    const token = tokens[i]
    if (token.kind === 'symbol' && token.text === '(') depth++
    if (token.kind === 'symbol' && token.text === ')') depth--
    if (depth < 0) return null
    if (depth === 0 && token.kind === 'word' && /^(AND|OR)$/i.test(token.text)) {
      const current = token.text.toUpperCase() as 'AND' | 'OR'
      if (join && join !== current) return null
      join = current
      groups.push(tokens.slice(start, i))
      start = i + 1
    }
  }
  if (depth !== 0) return null
  groups.push(tokens.slice(start))
  const conditions: FilterCondition[] = []
  for (const group of groups) {
    const condition = parseCondition(group)
    if (!condition) return null
    conditions.push(condition)
  }
  return { join: join || 'AND', conditions }
}

