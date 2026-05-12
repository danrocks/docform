/**
 * Safe expression evaluator for computed interview fields.
 *
 * Supports:
 *   - Arithmetic: +, -, *, /
 *   - Numeric literals: 42, 3.14
 *   - Field references: fieldId (top-level), group.child (repeat-group)
 *   - Aggregate functions: sum(), count(), avg(), min(), max()
 *   - round(expr, digits)
 *   - Parentheses for grouping
 *
 * Mirrors the backend expression_eval.py — no eval().
 */

const TOKEN_RE = /(\d+(?:\.\d+)?)|([a-zA-Z_]\w*(?:\.[a-zA-Z_]\w*)*)|([+\-*/(),])/g

const FUNCTIONS = new Set(['sum', 'count', 'avg', 'min', 'max', 'round'])
const AGGREGATES = new Set(['sum', 'count', 'avg', 'min', 'max'])

function tokenise(expr) {
  const tokens = []
  let m
  TOKEN_RE.lastIndex = 0
  while ((m = TOKEN_RE.exec(expr)) !== null) {
    if (m[1] !== undefined) tokens.push({ t: 'NUM', v: m[1] })
    else if (m[2] !== undefined) tokens.push({ t: 'ID', v: m[2] })
    else if (m[3] !== undefined) tokens.push({ t: 'OP', v: m[3] })
  }
  return tokens
}

class Parser {
  constructor(tokens) {
    this.tokens = tokens
    this.pos = 0
  }

  peek() { return this.pos < this.tokens.length ? this.tokens[this.pos] : null }
  advance() { return this.tokens[this.pos++] }
  expect(t, v) {
    const tok = this.peek()
    if (!tok || tok.t !== t || (v !== undefined && tok.v !== v))
      throw new Error(`Expected '${v || t}', got '${tok ? tok.v : 'EOF'}'`)
    return this.advance()
  }

  parseExpr() {
    let node = this.parseTerm()
    while (true) {
      const tok = this.peek()
      if (tok && tok.t === 'OP' && (tok.v === '+' || tok.v === '-')) {
        const op = this.advance().v
        node = { op, left: node, right: this.parseTerm() }
      } else break
    }
    return node
  }

  parseTerm() {
    let node = this.parseUnary()
    while (true) {
      const tok = this.peek()
      if (tok && tok.t === 'OP' && (tok.v === '*' || tok.v === '/')) {
        const op = this.advance().v
        node = { op, left: node, right: this.parseUnary() }
      } else break
    }
    return node
  }

  parseUnary() {
    const tok = this.peek()
    if (tok && tok.t === 'OP' && tok.v === '-') {
      this.advance()
      return { op: 'neg', operand: this.parseUnary() }
    }
    return this.parseAtom()
  }

  parseAtom() {
    const tok = this.peek()
    if (!tok) throw new Error('Unexpected end of expression')

    if (tok.t === 'NUM') {
      this.advance()
      return { lit: parseFloat(tok.v) }
    }

    if (tok.t === 'ID') {
      const name = tok.v
      this.advance()
      const nxt = this.peek()
      if (nxt && nxt.t === 'OP' && nxt.v === '(') {
        if (!FUNCTIONS.has(name)) throw new Error(`Unknown function '${name}'`)
        this.advance() // consume '('
        if (name === 'count') {
          const arg = this.expect('ID')
          this.expect('OP', ')')
          return { func: 'count', group: arg.v }
        }
        if (name === 'round') {
          const arg = this.parseExpr()
          this.expect('OP', ',')
          const digits = this.expect('NUM')
          this.expect('OP', ')')
          return { func: 'round', arg, digits: parseInt(digits.v) }
        }
        // sum/avg/min/max
        const arg = this.parseExpr()
        this.expect('OP', ')')
        return { func: name, arg }
      }
      return { ref: name }
    }

    if (tok.t === 'OP' && tok.v === '(') {
      this.advance()
      const node = this.parseExpr()
      this.expect('OP', ')')
      return node
    }

    throw new Error(`Unexpected token '${tok.v}'`)
  }
}

function toNum(v) {
  if (v == null || v === '') return 0
  const n = parseFloat(v)
  return isNaN(n) ? 0 : n
}

function collectGroups(node) {
  const groups = new Set()
  if (node.ref && node.ref.includes('.')) groups.add(node.ref.split('.')[0])
  if (node.left) { collectGroups(node.left).forEach(g => groups.add(g)); collectGroups(node.right).forEach(g => groups.add(g)) }
  if (node.operand) collectGroups(node.operand).forEach(g => groups.add(g))
  if (node.arg && typeof node.arg === 'object') collectGroups(node.arg).forEach(g => groups.add(g))
  return groups
}

function evalRow(node, row, data) {
  if ('lit' in node) return node.lit
  if ('ref' in node) {
    if (node.ref.includes('.')) {
      const field = node.ref.split('.').slice(1).join('.')
      return toNum(row[field])
    }
    return toNum(data[node.ref])
  }
  if ('op' in node) {
    if (node.op === 'neg') return -evalRow(node.operand, row, data)
    const l = evalRow(node.left, row, data)
    const r = evalRow(node.right, row, data)
    if (node.op === '+') return l + r
    if (node.op === '-') return l - r
    if (node.op === '*') return l * r
    if (node.op === '/') return r !== 0 ? l / r : 0
  }
  if ('func' in node) return evalNode(node, data)
  return 0
}

function evalNode(node, data) {
  if ('lit' in node) return node.lit
  if ('ref' in node) {
    if (node.ref.includes('.')) return 0 // dotted ref outside aggregate
    return toNum(data[node.ref])
  }
  if ('op' in node) {
    if (node.op === 'neg') return -evalNode(node.operand, data)
    const l = evalNode(node.left, data)
    const r = evalNode(node.right, data)
    if (node.op === '+') return l + r
    if (node.op === '-') return l - r
    if (node.op === '*') return l * r
    if (node.op === '/') return r !== 0 ? l / r : 0
  }
  if ('func' in node) {
    const { func } = node
    if (func === 'count') {
      const items = data[node.group]
      return Array.isArray(items) ? items.length : 0
    }
    if (func === 'round') {
      const val = evalNode(node.arg, data)
      const factor = Math.pow(10, node.digits)
      return Math.round(val * factor) / factor
    }
    // sum/avg/min/max
    const groups = collectGroups(node.arg)
    if (groups.size === 0) return 0
    const groupName = [...groups][0]
    const items = data[groupName]
    if (!Array.isArray(items) || items.length === 0) return 0
    const values = items.map(row => evalRow(node.arg, row, data))
    if (func === 'sum') return values.reduce((a, b) => a + b, 0)
    if (func === 'avg') return values.reduce((a, b) => a + b, 0) / values.length
    if (func === 'min') return Math.min(...values)
    if (func === 'max') return Math.max(...values)
  }
  return 0
}

export function evaluateExpression(expr, data) {
  try {
    const tokens = tokenise(expr)
    if (tokens.length === 0) return null
    const parser = new Parser(tokens)
    const ast = parser.parseExpr()
    return evalNode(ast, data)
  } catch {
    return null
  }
}

/**
 * Evaluate all computed fields in a component list and return updated data.
 */
export function evaluateComputedFields(components, data) {
  const result = { ...data }
  evalComponents(components, result)
  return result
}

function evalComponents(components, data) {
  for (const comp of components) {
    if (comp.type === 'dialog') {
      evalComponents(comp.components || [], data)
    } else if (comp.type === 'repeat') {
      const items = data[comp.id]
      if (Array.isArray(items)) {
        for (const row of items) {
          for (const child of (comp.components || [])) {
            if (child.type === 'number' && child.expression) {
              const val = evaluateExpression(child.expression, { ...data, ...row })
              if (val !== null) row[child.id] = val
            }
          }
        }
      }
    } else if (comp.type === 'number' && comp.expression) {
      const val = evaluateExpression(comp.expression, data)
      if (val !== null) data[comp.id] = val
    }
  }
}
