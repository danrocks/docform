/**
 * Expression parser and evaluator for computed `number` components.
 *
 * Mirrors backend/expression_eval.py: same grammar, same semantics. Used to
 * compute the value of number components that have an `expression` property.
 *
 * Grammar:
 *   expression     = additive
 *   additive       = multiplicative ( ("+" | "-") multiplicative )*
 *   multiplicative = unary ( ("*" | "/") unary )*
 *   unary          = "-" unary | primary
 *   primary        = NUMBER | FUNCTION "(" argument ")" | field_ref | "(" expression ")"
 *   field_ref      = IDENTIFIER ( "." IDENTIFIER )?
 *   FUNCTION       = "sum" | "count" | "avg" | "min" | "max"
 *
 * Evaluation rules:
 *   - Missing/empty values are treated as 0
 *   - Division by zero returns 0
 *   - No `eval()`; expressions are parsed and walked explicitly
 *
 * @typedef {{ type: 'num', value: number } |
 *           { type: 'binop', op: string, left: any, right: any } |
 *           { type: 'neg', operand: any } |
 *           { type: 'field', path: string[] } |
 *           { type: 'call', name: string, arg: any }} Node
 */

const AGGREGATE_FUNCTIONS = new Set(['sum', 'count', 'avg', 'min', 'max'])

class ExpressionError extends Error {}

// ---------------------------------------------------------------------------
// Tokenizer
// ---------------------------------------------------------------------------

function tokenize(expr) {
  const tokens = []
  let i = 0
  const n = expr.length
  const isDigit = c => c >= '0' && c <= '9'
  const isAlpha = c => (c >= 'a' && c <= 'z') || (c >= 'A' && c <= 'Z') || c === '_'
  const isAlphaNum = c => isAlpha(c) || isDigit(c)

  while (i < n) {
    const c = expr[i]
    if (c === ' ' || c === '\t' || c === '\n' || c === '\r') {
      i++
      continue
    }
    if (isDigit(c) || (c === '.' && i + 1 < n && isDigit(expr[i + 1]))) {
      const start = i
      let seenDot = false
      while (i < n && (isDigit(expr[i]) || (expr[i] === '.' && !seenDot))) {
        if (expr[i] === '.') seenDot = true
        i++
      }
      tokens.push({ kind: 'NUMBER', value: parseFloat(expr.slice(start, i)), pos: start })
      continue
    }
    if (isAlpha(c)) {
      const start = i
      while (i < n && isAlphaNum(expr[i])) i++
      tokens.push({ kind: 'IDENT', value: expr.slice(start, i), pos: start })
      continue
    }
    if (c === '+' || c === '-' || c === '*' || c === '/') {
      tokens.push({ kind: 'OP', value: c, pos: i })
      i++
      continue
    }
    if (c === '(') { tokens.push({ kind: 'LPAREN', value: c, pos: i }); i++; continue }
    if (c === ')') { tokens.push({ kind: 'RPAREN', value: c, pos: i }); i++; continue }
    if (c === ',') { tokens.push({ kind: 'COMMA', value: c, pos: i }); i++; continue }
    if (c === '.') { tokens.push({ kind: 'DOT', value: c, pos: i }); i++; continue }
    throw new ExpressionError(`Unexpected character '${c}' at position ${i}`)
  }
  tokens.push({ kind: 'EOF', value: null, pos: n })
  return tokens
}

// ---------------------------------------------------------------------------
// Parser (recursive descent)
// ---------------------------------------------------------------------------

class Parser {
  constructor(tokens) {
    this.tokens = tokens
    this.pos = 0
  }
  peek() { return this.tokens[this.pos] }
  consume() { return this.tokens[this.pos++] }
  expect(kind, value) {
    const tok = this.peek()
    if (tok.kind !== kind || (value !== undefined && tok.value !== value)) {
      const expected = value === undefined ? kind : `${kind} '${value}'`
      throw new ExpressionError(
        `Expected ${expected} at position ${tok.pos}, got ${tok.kind} '${tok.value}'`
      )
    }
    return this.consume()
  }

  parse() {
    const node = this.parseExpression()
    if (this.peek().kind !== 'EOF') {
      const tok = this.peek()
      throw new ExpressionError(`Unexpected token '${tok.value}' at position ${tok.pos}`)
    }
    return node
  }

  parseExpression() { return this.parseAdditive() }

  parseAdditive() {
    let node = this.parseMultiplicative()
    while (this.peek().kind === 'OP' && (this.peek().value === '+' || this.peek().value === '-')) {
      const op = this.consume().value
      const right = this.parseMultiplicative()
      node = { type: 'binop', op, left: node, right }
    }
    return node
  }

  parseMultiplicative() {
    let node = this.parseUnary()
    while (this.peek().kind === 'OP' && (this.peek().value === '*' || this.peek().value === '/')) {
      const op = this.consume().value
      const right = this.parseUnary()
      node = { type: 'binop', op, left: node, right }
    }
    return node
  }

  parseUnary() {
    if (this.peek().kind === 'OP' && this.peek().value === '-') {
      this.consume()
      return { type: 'neg', operand: this.parseUnary() }
    }
    if (this.peek().kind === 'OP' && this.peek().value === '+') {
      this.consume()
      return this.parseUnary()
    }
    return this.parsePrimary()
  }

  parsePrimary() {
    const tok = this.peek()
    if (tok.kind === 'NUMBER') {
      this.consume()
      return { type: 'num', value: tok.value }
    }
    if (tok.kind === 'LPAREN') {
      this.consume()
      const node = this.parseExpression()
      this.expect('RPAREN')
      return node
    }
    if (tok.kind === 'IDENT') {
      const name = this.consume().value
      if (this.peek().kind === 'LPAREN') {
        if (!AGGREGATE_FUNCTIONS.has(name)) {
          throw new ExpressionError(`Unknown function '${name}' at position ${tok.pos}`)
        }
        this.consume()
        const arg = this.parseExpression()
        this.expect('RPAREN')
        return { type: 'call', name, arg }
      }
      const path = [name]
      while (this.peek().kind === 'DOT') {
        this.consume()
        const next = this.expect('IDENT')
        path.push(next.value)
      }
      return { type: 'field', path }
    }
    throw new ExpressionError(`Unexpected token '${tok.value}' at position ${tok.pos}`)
  }
}

function parse(expr) {
  if (typeof expr !== 'string' || expr.trim() === '') {
    throw new ExpressionError('Expression must be a non-empty string')
  }
  return new Parser(tokenize(expr)).parse()
}

// ---------------------------------------------------------------------------
// Evaluation
// ---------------------------------------------------------------------------

function coerceNumber(v) {
  if (v === null || v === undefined) return 0
  if (typeof v === 'boolean') return v ? 1 : 0
  if (typeof v === 'number') return Number.isFinite(v) ? v : 0
  if (typeof v === 'string') {
    const s = v.trim()
    if (s === '') return 0
    const n = Number(s)
    return Number.isFinite(n) ? n : 0
  }
  return 0
}

function resolveField(path, data) {
  if (!path || path.length === 0) return null
  if (data === null || typeof data !== 'object') return null

  if (path.length === 1) {
    const v = data[path[0]]
    return v === undefined ? null : v
  }

  const head = path[0]
  const rest = path.slice(1)
  const container = data[head]
  if (container === undefined || container === null) return []
  if (Array.isArray(container)) {
    return container.map(item => {
      if (item && typeof item === 'object' && !Array.isArray(item)) {
        let cur = item
        for (const key of rest) {
          if (cur && typeof cur === 'object' && !Array.isArray(cur)) {
            cur = cur[key]
          } else {
            cur = null
            break
          }
        }
        return cur === undefined ? null : cur
      }
      return null
    })
  }
  if (typeof container === 'object') {
    let cur = container
    for (const key of rest) {
      if (cur && typeof cur === 'object' && !Array.isArray(cur)) {
        cur = cur[key]
      } else {
        return null
      }
    }
    return cur === undefined ? null : cur
  }
  return null
}

function toArray(v) {
  if (v === null || v === undefined) return []
  if (Array.isArray(v)) return v
  return [v]
}

function evalNode(node, data) {
  switch (node.type) {
    case 'num':
      return node.value
    case 'neg': {
      const v = evalNode(node.operand, data)
      if (Array.isArray(v)) return v.map(x => -coerceNumber(x))
      return -coerceNumber(v)
    }
    case 'binop': {
      const left = evalNode(node.left, data)
      const right = evalNode(node.right, data)
      return applyBinop(node.op, left, right)
    }
    case 'field':
      return resolveField(node.path, data)
    case 'call':
      return applyAggregate(node.name, evalNode(node.arg, data))
    default:
      throw new ExpressionError(`Unknown node type: ${node.type}`)
  }
}

function applyBinop(op, left, right) {
  const leftIsArr = Array.isArray(left)
  const rightIsArr = Array.isArray(right)
  if (leftIsArr || rightIsArr) {
    if (leftIsArr && rightIsArr) {
      const length = Math.min(left.length, right.length)
      const out = new Array(length)
      for (let i = 0; i < length; i++) out[i] = scalarOp(op, left[i], right[i])
      return out
    }
    if (leftIsArr) return left.map(x => scalarOp(op, x, right))
    return right.map(x => scalarOp(op, left, x))
  }
  return scalarOp(op, left, right)
}

function scalarOp(op, a, b) {
  const x = coerceNumber(a)
  const y = coerceNumber(b)
  switch (op) {
    case '+': return x + y
    case '-': return x - y
    case '*': return x * y
    case '/': return y === 0 ? 0 : x / y
    default: throw new ExpressionError(`Unknown operator: ${op}`)
  }
}

function applyAggregate(name, arg) {
  const items = toArray(arg)
  const nums = items.map(coerceNumber)
  if (name === 'count') return items.length
  if (nums.length === 0) return 0
  switch (name) {
    case 'sum': return nums.reduce((a, b) => a + b, 0)
    case 'avg': return nums.reduce((a, b) => a + b, 0) / nums.length
    case 'min': return Math.min(...nums)
    case 'max': return Math.max(...nums)
    default: throw new ExpressionError(`Unknown function: ${name}`)
  }
}

/**
 * Parse and evaluate `expression` against form `data`.
 *
 * @param {string} expression - The expression to evaluate.
 * @param {object} data - The full form data object.
 * @returns {number | null} The numeric result, or null if the expression
 *     cannot be parsed.
 */
export function evaluateExpression(expression, data) {
  let ast
  try {
    ast = parse(expression)
  } catch (e) {
    return null
  }
  if (data === null || typeof data !== 'object') data = {}
  const result = evalNode(ast, data)
  if (Array.isArray(result)) {
    let total = 0
    for (const x of result) total += coerceNumber(x)
    return total
  }
  return coerceNumber(result)
}
